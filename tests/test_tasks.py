import asyncio
import io
import tempfile
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from jsonschema import validate
from PIL import Image

from zhenzhen_nanobanana_mcp.config import BusinessError, Settings
from zhenzhen_nanobanana_mcp.media import decode_image
from zhenzhen_nanobanana_mcp.models import ImageTask, TaskPage
from zhenzhen_nanobanana_mcp.server import create_server
from zhenzhen_nanobanana_mcp.tasks import TaskQueue


class TaskTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.settings = Settings(
            api_key="test-not-real", output_dir=self.root, concurrency=2, timeout=2
        )
        buffer = io.BytesIO()
        Image.new("RGB", (16, 16), "blue").save(buffer, format="PNG")
        self.media = decode_image(buffer.getvalue())
        self.queue = TaskQueue(self.settings)
        self.queue.storage.provider.render = AsyncMock(return_value=[self.media])
        self.addAsyncCleanup(self.queue.close)

    def task(self, task_id="one", **kwargs):
        return ImageTask(task_id=task_id, prompt="商品主图", **kwargs)

    async def wait_done(self, queue=None, count=1, scope=("cp", "thread")):
        queue = queue or self.queue
        async with asyncio.timeout(5):
            while True:
                page = queue.get(*scope)
                if len(page.tasks) == count and all(
                    t.status not in ("queued", "preparing", "running", "recovering")
                    for t in page.tasks
                ):
                    return page
                await asyncio.sleep(0.02)

    async def test_mcp_ten_tasks_return_without_waiting_and_are_bounded(self):
        entered = asyncio.Event()
        release = asyncio.Event()
        active, maximum = 0, 0

        async def render(*args):
            nonlocal active, maximum
            active += 1
            maximum = max(maximum, active)
            entered.set()
            try:
                await release.wait()
                return [self.media]
            finally:
                active -= 1

        self.queue.storage.provider.render = AsyncMock(side_effect=render)
        async with Client(create_server(self.settings, queue=self.queue)) as client:
            submitted = await asyncio.wait_for(
                client.call_tool(
                    "submit_image_tasks",
                    {
                        "checkpointer": "cp",
                        "thread_id": "thread",
                        "tasks": [self.task(f"detail-{i}").model_dump() for i in range(10)],
                    },
                ),
                2,
            )
            self.assertFalse(submitted.is_error)
            validate(submitted.structured_content, TaskPage.model_json_schema())
            self.assertEqual(len(submitted.structured_content["tasks"]), 10)
            await asyncio.wait_for(entered.wait(), 1)
            status = await client.call_tool(
                "get_image_tasks", {"checkpointer": "cp", "thread_id": "thread"}
            )
            self.assertFalse(status.is_error)
            self.assertTrue(
                any(t["status"] == "running" for t in status.structured_content["tasks"])
            )
            self.assertLessEqual(maximum, 2)
            release.set()
            done = await self.wait_done(count=10)
            self.assertTrue(all(t.status == "succeeded" for t in done.tasks))
            self.assertEqual(self.queue.storage.provider.render.await_count, 10)
            self.assertEqual(maximum, 2)
            for task in done.tasks:
                self.assertTrue(Path(task.images[0].path).is_file())

    async def test_atomic_conflict_reuse_and_namespace_separation(self):
        first = self.task()
        await self.queue.submit("cp", "thread", [first])
        reused = await self.queue.submit("cp", "thread", [first])
        self.assertTrue(reused.tasks[0].reused)
        changed = first.model_copy(update={"prompt": "other"})
        with self.assertRaises(BusinessError):
            await self.queue.submit("cp", "thread", [self.task("new"), changed])
        self.assertEqual(len(self.queue.get("cp", "thread").tasks), 1)
        await self.queue.submit("other", "thread", [first])
        await self.queue.submit("cp", "other", [first])
        await self.wait_done()
        await self.wait_done(scope=("other", "thread"))
        await self.wait_done(scope=("cp", "other"))
        self.assertEqual(self.queue.storage.provider.render.await_count, 3)

    async def test_restarted_queue_reuses_finished_result_without_loading_inputs(self):
        await self.queue.submit("cp", "thread", [self.task()])
        original = await self.wait_done()
        await self.queue.close()
        restarted = TaskQueue(self.settings)
        self.addAsyncCleanup(restarted.close)
        restarted.storage.provider.render = AsyncMock(side_effect=AssertionError("must not resend"))
        restarted.storage.loader.load = AsyncMock(side_effect=AssertionError("must not reload"))
        reused = await restarted.submit("cp", "thread", [self.task()])
        self.assertTrue(reused.tasks[0].reused)
        self.assertEqual(reused.tasks[0].images, original.tasks[0].images)
        restarted.storage.provider.render.assert_not_awaited()

    async def test_restart_recovers_queued_and_preparing_but_not_running(self):
        await self.queue.submit(
            "cp", "thread", [self.task("queued"), self.task("preparing"), self.task("running")]
        )
        await self.queue.close()
        with self.queue.connect() as db:
            db.execute("INSERT INTO task_owners VALUES ('dead',0)")
            for state in ("preparing", "running"):
                db.execute(
                    "UPDATE image_tasks SET state=?,owner='dead' WHERE task_id=?", (state, state)
                )
        restarted = TaskQueue(self.settings)
        restarted.storage.provider.render = AsyncMock(return_value=[self.media])
        self.addAsyncCleanup(restarted.close)
        await restarted.start()
        done = await self.wait_done(restarted, count=3)
        self.assertEqual(
            {t.task_id: t.status for t in done.tasks},
            {"queued": "succeeded", "preparing": "succeeded", "running": "unknown"},
        )
        self.assertEqual(restarted.storage.provider.render.await_count, 2)

        unknown = await restarted.submit("cp", "thread", [self.task("running")])
        self.assertEqual(unknown.tasks[0].status, "unknown")
        self.assertEqual(restarted.storage.provider.render.await_count, 2)

    async def test_queued_request_never_moves_to_a_different_provider(self):
        await self.queue.submit("cp", "thread", [self.task()])
        await self.queue.close()
        changed = TaskQueue(replace(self.settings, base_url="https://other.invalid"))
        changed.storage.provider.render = AsyncMock(return_value=[self.media])
        self.addAsyncCleanup(changed.close)
        await changed.start()
        done = await self.wait_done(changed)
        self.assertEqual(done.tasks[0].status, "failed")
        self.assertIn("服务地址", done.tasks[0].error)
        changed.storage.provider.render.assert_not_awaited()
        self.queue.storage.provider.render.assert_not_awaited()

    async def test_result_write_failure_is_reconciled_without_resubmission(self):
        self.queue.finish = Mock(side_effect=BusinessError("simulated ledger write failure"))
        with patch("zhenzhen_nanobanana_mcp.tasks.HEARTBEAT_SECONDS", 0.02):
            await self.queue.submit("cp", "thread", [self.task()])
            done = await self.wait_done()
        self.assertEqual(done.tasks[0].status, "unknown")
        self.assertIn("账本写入", done.tasks[0].error)
        self.assertFalse(self.queue.reconcile)
        await self.queue.submit("cp", "thread", [self.task()])
        self.queue.storage.provider.render.assert_awaited_once()

    async def test_cross_thread_submit_has_one_durable_claim(self):
        def submit_once():
            async def execute():
                queue = TaskQueue(self.settings)
                try:
                    return await queue.submit("cp", "thread", [self.task()])
                finally:
                    await queue.close()

            return asyncio.run(execute())

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(submit_once) for _ in range(2)]
            pages = await asyncio.gather(*[asyncio.wrap_future(f) for f in futures])
        self.assertEqual(sum(p.tasks[0].reused for p in pages), 1)
        await self.queue.start()
        await self.wait_done()
        self.assertEqual(self.queue.storage.provider.render.await_count, 1)

    async def test_shared_instances_enforce_global_concurrency(self):
        second = TaskQueue(self.settings)
        self.addAsyncCleanup(second.close)
        active, maximum = 0, 0

        async def render(*args):
            nonlocal active, maximum
            active += 1
            maximum = max(maximum, active)
            await asyncio.sleep(0.03)
            active -= 1
            return [self.media]

        self.queue.storage.provider.render = AsyncMock(side_effect=render)
        second.storage.provider.render = AsyncMock(side_effect=render)
        await self.queue.submit("cp", "thread", [self.task(str(i)) for i in range(10)])
        await second.start()
        await self.wait_done(count=10)
        self.assertLessEqual(maximum, 2)
        self.assertEqual(
            self.queue.storage.provider.render.await_count
            + second.storage.provider.render.await_count,
            10,
        )

    async def test_cancel_preparing_never_posts_and_running_becomes_unknown(self):
        loading = asyncio.Event()
        self.queue.storage.loader.load = AsyncMock(side_effect=lambda *args: None)

        async def load(*args):
            loading.set()
            await asyncio.Event().wait()

        self.queue.storage.loader.load = AsyncMock(side_effect=load)
        await self.queue.submit(
            "cp", "thread", [self.task("preparing", reference_images=[str(self.root / "x.png")])]
        )
        await loading.wait()
        cancelled = self.queue.cancel("cp", "thread", ["preparing"])
        self.assertEqual(cancelled.tasks[0].status, "cancelled")
        self.queue.storage.provider.render.assert_not_awaited()
        entered = asyncio.Event()

        async def render(*args):
            entered.set()
            await asyncio.Event().wait()

        self.queue.storage.provider.render = AsyncMock(side_effect=render)
        await self.queue.submit("cp", "thread", [self.task("running")])
        await entered.wait()
        cancelled = self.queue.cancel("cp", "thread", ["running"])
        self.assertEqual(cancelled.tasks[0].status, "unknown")
        reused = await self.queue.submit("cp", "thread", [self.task("running")])
        self.assertEqual(reused.tasks[0].status, "unknown")

    async def test_shutdown_inflight_stays_unknown(self):
        entered = asyncio.Event()

        async def render(*args):
            entered.set()
            await asyncio.Event().wait()

        self.queue.storage.provider.render = AsyncMock(side_effect=render)
        await self.queue.submit("cp", "thread", [self.task()])
        await entered.wait()
        await self.queue.close()
        self.assertEqual(self.queue.get("cp", "thread").tasks[0].status, "unknown")

    async def test_preflight_failure_and_timeout_have_no_retries(self):
        await self.queue.submit(
            "cp",
            "thread",
            [self.task("missing", reference_images=[str(self.root / "missing.png")])],
        )
        failed = await self.wait_done()
        self.assertEqual(failed.tasks[0].status, "failed")
        self.queue.storage.provider.render.assert_not_awaited()
        self.queue.storage.provider.render = AsyncMock(
            side_effect=httpx.ReadTimeout("do-not-expose")
        )
        await self.queue.submit("cp", "timeout", [self.task()])
        failed = await self.wait_done(scope=("cp", "timeout"))
        self.assertEqual(failed.tasks[0].status, "unknown")
        self.assertNotIn("do-not-expose", failed.model_dump_json())
        await self.queue.submit("cp", "timeout", [self.task()])
        self.assertEqual(self.queue.storage.provider.render.await_count, 1)

    async def test_pagination_capacity_and_invalid_combinations_are_atomic(self):
        self.queue.settings = replace(self.settings, max_pending_tasks=20)
        await self.queue.submit("cp", "thread", [self.task(str(i)) for i in range(20)])
        with self.assertRaises(BusinessError):
            await self.queue.submit("cp", "thread", [self.task("overflow")])
        page = self.queue.get("cp", "thread", limit=5)
        next_page = self.queue.get("cp", "thread", limit=5, cursor=page.next_cursor)
        self.assertFalse({t.task_id for t in page.tasks} & {t.task_id for t in next_page.tasks})
        with self.assertRaises(BusinessError):
            await self.queue.submit(
                "cp",
                "invalid",
                [self.task("ok"), self.task("bad", model="nano-banana-pro", api_format="chat")],
            )
        self.assertEqual(self.queue.get("cp", "invalid").tasks, [])
        self.queue.cancel("cp", "thread", [str(i) for i in range(20)])
        self.queue.storage.provider.render.assert_not_awaited()

    async def test_mcp_business_error_schema_and_invalid_inputs(self):
        self.queue.storage.provider.render = AsyncMock(
            side_effect=BusinessError("upstream rejected")
        )
        async with Client(create_server(self.settings, queue=self.queue)) as client:
            await client.call_tool(
                "submit_image_tasks",
                {"checkpointer": "cp", "thread_id": "thread", "tasks": [self.task().model_dump()]},
            )
            await self.wait_done()
            failed = await client.call_tool(
                "get_image_tasks",
                {"checkpointer": "cp", "thread_id": "thread"},
                raise_on_error=False,
            )
            self.assertTrue(failed.is_error)
            validate(failed.structured_content, TaskPage.model_json_schema())
            for args in (
                {"checkpointer": "", "thread_id": "thread", "tasks": [self.task().model_dump()]},
                {"checkpointer": "cp", "thread_id": "thread", "tasks": []},
                {
                    "checkpointer": "cp",
                    "thread_id": "thread",
                    "tasks": [self.task().model_dump()] * 2,
                },
            ):
                bad = await client.call_tool("submit_image_tasks", args, raise_on_error=False)
                self.assertTrue(bad.is_error)
            missing = await client.call_tool(
                "get_image_tasks",
                {"checkpointer": "cp", "thread_id": "wrong", "task_ids": ["one"]},
                raise_on_error=False,
            )
            self.assertTrue(missing.is_error)

    async def test_expired_owner_cannot_dispatch(self):
        await self.queue.submit("cp", "thread", [self.task()])
        row = self.queue.claim()
        with self.queue.connect() as db:
            db.execute(
                "UPDATE task_owners SET heartbeat=? WHERE owner=?",
                (time.time() - 60, self.queue.owner),
            )
        await self.queue.execute(row)
        self.queue.storage.provider.render.assert_not_awaited()

    async def test_two_stdio_protocols_submit_then_query_without_provider_network(self):
        for mode in ("auto", "legacy"):
            project = self.root / mode
            project.mkdir()
            transport = StdioTransport(
                command=sys.executable,
                args=[str(Path(__file__).with_name("stdio_task_fixture.py")), str(project)],
                cwd=str(project),
                keep_alive=False,
            )
            self.addAsyncCleanup(transport.close)
            peer_transport = StdioTransport(
                command=sys.executable,
                args=[str(Path(__file__).with_name("stdio_task_fixture.py")), str(project)],
                cwd=str(project),
                keep_alive=False,
            )
            self.addAsyncCleanup(peer_transport.close)
            async with (
                Client(transport, mode=mode, timeout=5) as client,
                Client(peer_transport, mode=mode, timeout=5) as peer,
            ):
                scope = {"checkpointer": "cp", "thread_id": "thread"}
                submitted = await client.call_tool(
                    "submit_image_tasks",
                    {**scope, "tasks": [self.task(str(i)).model_dump() for i in range(10)]},
                )
                self.assertFalse(submitted.is_error)
                self.assertEqual(len(submitted.structured_content["tasks"]), 10)
                self.assertTrue(
                    any(
                        t["status"] in ("queued", "preparing", "running")
                        for t in submitted.structured_content["tasks"]
                    )
                )
                pending = await client.call_tool("get_image_tasks", scope)
                self.assertFalse(pending.is_error)
                self.assertFalse((project / "release-gate").exists())
                duplicate = await peer.call_tool(
                    "submit_image_tasks",
                    {**scope, "tasks": [self.task(str(i)).model_dump() for i in range(10)]},
                )
                self.assertTrue(all(t["reused"] for t in duplicate.structured_content["tasks"]))
                async with asyncio.timeout(3):
                    while len(list((project / "fake-posts").glob("*"))) < 2:
                        await asyncio.sleep(0.02)
                await asyncio.sleep(0.1)
                self.assertEqual(len(list((project / "fake-posts").glob("*"))), 2)
                (project / "release-gate").touch()
                async with asyncio.timeout(5):
                    while True:
                        done = await client.call_tool("get_image_tasks", scope)
                        if all(
                            t["status"] == "succeeded" for t in done.structured_content["tasks"]
                        ):
                            break
                        await asyncio.sleep(0.03)
                validate(done.structured_content, TaskPage.model_json_schema())
                reused = await client.call_tool(
                    "submit_image_tasks",
                    {**scope, "tasks": [self.task(str(i)).model_dump() for i in range(10)]},
                )
                self.assertTrue(all(t["reused"] for t in reused.structured_content["tasks"]))
                self.assertEqual(len(list((project / "fake-posts").glob("*"))), 10)

    async def test_other_owner_cancellation_keeps_concurrency_slot_until_waiter_exits(self):
        started = asyncio.Event()
        release = asyncio.Event()
        second = TaskQueue(self.settings)
        self.addAsyncCleanup(second.close)
        calls = []

        async def render(spec, *args):
            calls.append(spec.task_id)
            if len(calls) == 2:
                started.set()
            await release.wait()
            return [self.media]

        self.queue.storage.provider.render = AsyncMock(side_effect=render)
        await self.queue.submit(
            "cp", "thread", [self.task("one"), self.task("two"), self.task("three")]
        )
        await asyncio.wait_for(started.wait(), 2)
        second.cancel("cp", "thread", ["one"])
        await asyncio.sleep(0.25)
        self.assertEqual(len(calls), 2)
        release.set()
        done = await self.wait_done(count=3)
        self.assertEqual([t.status for t in done.tasks], ["unknown", "succeeded", "succeeded"])
