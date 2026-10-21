import asyncio
import hashlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from jsonschema import validate
from PIL import Image

from zhenzhen_nanobanana_mcp.config import BusinessError, Settings
from zhenzhen_nanobanana_mcp.media import decode_image
from zhenzhen_nanobanana_mcp.models import ImageTask, TaskWaitResult
from zhenzhen_nanobanana_mcp.server import create_server
from zhenzhen_nanobanana_mcp.tasks import TaskQueue


class SyncToolsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.settings = Settings(api_key="sync-test-not-real", output_dir=self.root, concurrency=2)
        self.queue = TaskQueue(self.settings)
        self.addAsyncCleanup(self.queue.close)
        data = io.BytesIO()
        Image.new("RGB", (16, 16), "blue").save(data, format="PNG")
        self.media = decode_image(data.getvalue())
        self.queue.storage.provider.render = AsyncMock(return_value=[self.media])
        self.scope = {"checkpointer": "sync-test", "thread_id": "thread"}

    def task(self, task_id="one", **kwargs):
        return ImageTask(task_id=task_id, prompt="商品主图", **kwargs)

    async def test_sync_waits_for_files_and_cross_entry_replay_is_free(self):
        entered, release = asyncio.Event(), asyncio.Event()

        async def render(*args):
            entered.set()
            await release.wait()
            return [self.media]

        self.queue.storage.provider.render.side_effect = render
        async with Client(create_server(self.settings, queue=self.queue)) as client:
            args = {**self.scope, "tasks": [self.task().model_dump()]}
            call = asyncio.create_task(client.call_tool("generate_images", args))
            await asyncio.wait_for(entered.wait(), 3)
            self.assertFalse(call.done())
            query = await client.call_tool("get_image_tasks", self.scope)
            self.assertEqual(query.structured_content["tasks"][0]["status"], "running")
            duplicate = await client.call_tool("submit_image_tasks", args)
            self.assertTrue(duplicate.structured_content["tasks"][0]["reused"])
            release.set()
            result = await asyncio.wait_for(call, 5)
            self.assertFalse(result.is_error)
            validate(result.structured_content, TaskWaitResult.model_json_schema())
            image = result.structured_content["tasks"][0]["images"][0]
            self.assertEqual(
                hashlib.sha256(Path(image["path"]).read_bytes()).hexdigest(), image["sha256"]
            )
            replay = await client.call_tool("generate_images", {**args, "wait_timeout_seconds": 1})
            self.assertFalse(replay.is_error)
            self.assertTrue(replay.structured_content["tasks"][0]["reused"])
            self.assertEqual(replay.structured_content["tasks"][0]["images"], [image])
            self.queue.storage.provider.render.assert_awaited_once()

    async def test_timeout_returns_pending_and_wait_continues_without_resubmit(self):
        release = asyncio.Event()

        async def render(*args):
            await release.wait()
            return [self.media]

        self.queue.storage.provider.render.side_effect = render
        async with Client(create_server(self.settings, queue=self.queue)) as client:
            result = await client.call_tool(
                "generate_images",
                {**self.scope, "tasks": [self.task().model_dump()], "wait_timeout_seconds": 1},
                raise_on_error=False,
            )
            self.assertTrue(result.is_error)
            self.assertTrue(result.structured_content["wait_timed_out"])
            self.assertIn(
                result.structured_content["tasks"][0]["status"], ("queued", "preparing", "running")
            )
            release.set()
            done = await client.call_tool("wait_image_tasks", {**self.scope, "task_ids": ["one"]})
            self.assertFalse(done.is_error)
            self.assertFalse(done.structured_content["wait_timed_out"])
            self.assertEqual(done.structured_content["tasks"][0]["status"], "succeeded")
            self.queue.storage.provider.render.assert_awaited_once()

    async def test_cancelled_wait_does_not_cancel_worker(self):
        entered, release = asyncio.Event(), asyncio.Event()

        async def render(*args):
            entered.set()
            await release.wait()
            return [self.media]

        self.queue.storage.provider.render.side_effect = render
        await self.queue.submit(**self.scope, tasks=[self.task()])
        await asyncio.wait_for(entered.wait(), 3)
        waiter = asyncio.create_task(self.queue.wait(**self.scope, task_ids=["one"]))
        await asyncio.sleep(0)
        waiter.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await waiter
        self.assertEqual(self.queue.get(**self.scope).tasks[0].status, "running")
        release.set()
        result = await self.queue.wait(**self.scope, task_ids=["one"], wait_timeout_seconds=5)
        self.assertEqual(result.tasks[0].status, "succeeded")
        self.queue.storage.provider.render.assert_awaited_once()

    async def test_mixed_terminal_states_return_error_with_successful_files(self):
        async def render(task, *args):
            if task.task_id == "failed":
                raise BusinessError("fake business failure")
            if task.task_id == "unknown":
                raise httpx.ReadTimeout("fake uncertain provider")
            return [self.media]

        self.queue.storage.provider.render.side_effect = render
        async with Client(create_server(self.settings, queue=self.queue)) as client:
            result = await client.call_tool(
                "generate_images",
                {
                    **self.scope,
                    "tasks": [self.task(i).model_dump() for i in ("ok", "failed", "unknown")],
                },
                raise_on_error=False,
            )
            self.assertTrue(result.is_error)
            self.assertFalse(result.structured_content["wait_timed_out"])
            self.assertEqual(
                [t["status"] for t in result.structured_content["tasks"]],
                ["succeeded", "failed", "unknown"],
            )
            self.assertTrue(
                Path(result.structured_content["tasks"][0]["images"][0]["path"]).is_file()
            )

    async def test_edit_uses_existing_reference_and_resolution_routing(self):
        reference = self.root / "reference.png"
        Image.new("RGB", (16, 16), "red").save(reference)
        task = self.task(model="nano-banana-pro", reference_images=[str(reference)])
        async with Client(create_server(self.settings, queue=self.queue)) as client:
            result = await client.call_tool(
                "generate_images",
                {
                    **self.scope,
                    "tasks": [{**task.model_dump(), "resolution": {"width": 1536, "height": 2048}}],
                },
            )
            self.assertFalse(result.is_error)
            self.assertEqual(result.structured_content["tasks"][0]["endpoint"], "edits")
            self.assertEqual(
                result.structured_content["tasks"][0]["actual_model"], "nano-banana-pro-2k"
            )
            args = self.queue.storage.provider.render.await_args.args
            self.assertEqual(len(args[1]), 1)
            self.assertEqual(args[2:], ("nano-banana-pro-2k", "dalle"))

    async def test_terminal_cancelled_task_is_error_without_wait_timeout(self):
        await self.queue.submit(**self.scope, tasks=[self.task()])
        self.queue.cancel(**self.scope, task_ids=["one"])
        async with Client(create_server(self.settings, queue=self.queue)) as client:
            result = await client.call_tool(
                "wait_image_tasks", {**self.scope, "task_ids": ["one"]}, raise_on_error=False
            )
            self.assertTrue(result.is_error)
            self.assertFalse(result.structured_content["wait_timed_out"])
            self.assertEqual(result.structured_content["tasks"][0]["status"], "cancelled")
            self.queue.storage.provider.render.assert_not_awaited()

    async def test_client_cancelled_generate_call_preserves_background_task(self):
        entered, release = asyncio.Event(), asyncio.Event()

        async def render(*args):
            entered.set()
            await release.wait()
            return [self.media]

        self.queue.storage.provider.render.side_effect = render
        async with Client(create_server(self.settings, queue=self.queue)) as client:
            call = asyncio.create_task(
                client.call_tool(
                    "generate_images", {**self.scope, "tasks": [self.task().model_dump()]}
                )
            )
            await asyncio.wait_for(entered.wait(), 3)
            call.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await call
            self.assertEqual(self.queue.get(**self.scope).tasks[0].status, "running")
            release.set()
            result = await client.call_tool("wait_image_tasks", {**self.scope, "task_ids": ["one"]})
            self.assertFalse(result.is_error)
            self.queue.storage.provider.render.assert_awaited_once()

    async def test_invalid_wait_parameters_fail_before_charging_or_ledger_creation(self):
        async with Client(create_server(self.settings, queue=self.queue)) as client:
            for value in (0, 1201, True, "1", 1.5):
                result = await client.call_tool(
                    "generate_images",
                    {
                        **self.scope,
                        "tasks": [self.task().model_dump()],
                        "wait_timeout_seconds": value,
                    },
                    raise_on_error=False,
                )
                self.assertTrue(result.is_error, value)
            for ids in ([], ["missing"], ["one", "one"]):
                result = await client.call_tool(
                    "wait_image_tasks", {**self.scope, "task_ids": ids}, raise_on_error=False
                )
                self.assertTrue(result.is_error)
            self.queue.storage.provider.render.assert_not_awaited()
            self.assertEqual(self.queue.get(**self.scope).tasks, [])

    async def test_cross_instance_wait_and_conflict_remain_atomic(self):
        await self.queue.submit(**self.scope, tasks=[self.task()])
        await self.queue.wait(**self.scope, task_ids=["one"], wait_timeout_seconds=5)
        peer = TaskQueue(self.settings)
        self.addAsyncCleanup(peer.close)
        peer.storage.provider.render = AsyncMock(return_value=[self.media])
        async with Client(create_server(self.settings, queue=peer)) as client:
            result = await client.call_tool(
                "generate_images", {**self.scope, "tasks": [self.task().model_dump()]}
            )
            self.assertTrue(result.structured_content["tasks"][0]["reused"])
            result = await client.call_tool(
                "generate_images",
                {
                    **self.scope,
                    "tasks": [
                        self.task("new").model_dump(),
                        {**self.task().model_dump(), "prompt": "changed"},
                    ],
                },
                raise_on_error=False,
            )
            self.assertTrue(result.is_error)
            self.assertEqual(len(self.queue.get(**self.scope).tasks), 1)
            peer.storage.provider.render.assert_not_awaited()
            self.queue.storage.provider.render.assert_awaited_once()

    async def test_sync_and_wait_over_both_real_stdio_protocols(self):
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
            async with Client(transport, mode=mode, timeout=15) as client:
                args = {**self.scope, "tasks": [self.task().model_dump()]}
                result = await client.call_tool(
                    "generate_images", {**args, "wait_timeout_seconds": 1}, raise_on_error=False
                )
                self.assertTrue(result.is_error)
                self.assertTrue(result.structured_content["wait_timed_out"])
                (project / "release-gate").touch()
                result = await client.call_tool(
                    "wait_image_tasks",
                    {**self.scope, "task_ids": ["one"], "wait_timeout_seconds": 10},
                )
                self.assertFalse(result.is_error)
                replay = await client.call_tool("generate_images", args)
                self.assertTrue(replay.structured_content["tasks"][0]["reused"])
                validate(replay.structured_content, TaskWaitResult.model_json_schema())
                self.assertTrue(
                    Path(replay.structured_content["tasks"][0]["images"][0]["path"]).is_file()
                )
                self.assertEqual(len(list((project / "fake-posts").iterdir())), 1)
