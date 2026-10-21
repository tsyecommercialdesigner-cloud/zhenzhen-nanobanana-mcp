import asyncio
import base64
import hashlib
import io
import json
import sqlite3
import sys
import tempfile
import time
import unittest
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from PIL import Image
from pydantic import ValidationError

from zhenzhen_nanobanana_mcp.config import BusinessError, Settings
from zhenzhen_nanobanana_mcp.media import MediaLoader, decode_image
from zhenzhen_nanobanana_mcp.models import ImageTask, resolve_api
from zhenzhen_nanobanana_mcp.provider import Provider
from zhenzhen_nanobanana_mcp.server import create_server
from zhenzhen_nanobanana_mcp.tasks import TaskQueue
from zhenzhen_nanobanana_mcp.integrity import publish


def png(color="blue"):
    stream = io.BytesIO()
    Image.new("RGB", (16, 16), color).save(stream, format="PNG")
    return stream.getvalue()


class ReliabilityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.settings = Settings(
            api_key="reliability-not-real",
            output_dir=self.root / "output",
            retry_delay=0.01,
            timeout=5,
        )
        self.queue = TaskQueue(self.settings)
        self.addAsyncCleanup(self.queue.close)
        self.queue.storage.provider.render = AsyncMock(return_value=[decode_image(png())])

    def task(self, key="one", **kwargs):
        return ImageTask(task_id=key, prompt="真实商品图", **kwargs)

    def provider(self, handler, get_handler=None, settings=None):
        settings = settings or self.settings
        loader = MediaLoader(
            (),
            settings.timeout,
            transport=httpx.MockTransport(get_handler) if get_handler else None,
            safe_attempts=settings.safe_attempts,
            retry_delay=settings.retry_delay,
        )
        provider = Provider(settings, loader, httpx.MockTransport(handler))
        self.queue.storage.provider, self.queue.storage.loader = provider, loader
        return provider

    async def done(self, key="one", thread="thread", timeout=10):
        page = await self.queue.wait("cp", thread, [key], timeout)
        self.assertFalse(page.wait_timed_out)
        return page.tasks[0]

    async def test_five_simultaneous_sync_calls_and_twenty_async_items(self):
        entered, release = asyncio.Event(), asyncio.Event()
        active = maximum = 0

        async def render(*args):
            nonlocal active, maximum
            active += 1
            maximum = max(maximum, active)
            if active == 5:
                entered.set()
            try:
                await release.wait()
                return [decode_image(png())]
            finally:
                active -= 1

        self.queue.storage.provider.render = AsyncMock(side_effect=render)
        async with Client(create_server(self.settings, queue=self.queue)) as client:
            calls = [
                asyncio.create_task(
                    client.call_tool(
                        "generate_images",
                        {
                            "checkpointer": "cp",
                            "thread_id": "sync",
                            "tasks": [self.task(str(i)).model_dump()],
                            "wait_timeout_seconds": 5,
                        },
                    )
                )
                for i in range(5)
            ]
            await asyncio.wait_for(entered.wait(), 3)
            self.assertTrue(all(not call.done() for call in calls))
            pending = await client.call_tool(
                "submit_image_tasks",
                {
                    "checkpointer": "cp",
                    "thread_id": "async",
                    "tasks": [self.task(str(i)).model_dump() for i in range(20)],
                },
            )
            self.assertEqual(len(pending.structured_content["tasks"]), 20)
            self.assertEqual(maximum, 5)
            release.set()
            self.assertTrue(all(not r.is_error for r in await asyncio.gather(*calls)))
            done = await self.queue.wait("cp", "async", [str(i) for i in range(20)], 5)
            self.assertTrue(all(t.status == "succeeded" for t in done.tasks))
            self.assertEqual(self.queue.storage.provider.render.await_count, 25)
            self.assertEqual(maximum, 5)
            invalid = await client.call_tool(
                "submit_image_tasks",
                {
                    "checkpointer": "cp",
                    "thread_id": "too-many",
                    "tasks": [self.task(str(i)).model_dump() for i in range(21)],
                },
                raise_on_error=False,
            )
            self.assertTrue(invalid.is_error)

    async def test_connection_retry_preserves_one_provider_key(self):
        requests = []

        def handler(request):
            requests.append(request)
            if len(requests) < 3:
                raise httpx.ConnectError("fake connect failure")
            return httpx.Response(
                200, json={"data": [{"b64_json": base64.b64encode(png()).decode()}]}
            )

        self.provider(handler)
        await self.queue.submit("cp", "thread", [self.task()])
        result = await self.done()
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.post_attempts, 3)
        self.assertEqual(
            {r.headers["Idempotency-Key"] for r in requests}, {result.provider_idempotency_key}
        )
        await self.queue.submit("cp", "thread", [self.task()])
        self.assertEqual(len(requests), 3)

    async def test_read_timeout_and_http_failure_are_not_blindly_reposted(self):
        for thread, response in (("timeout", None), ("server", 503)):
            calls = []

            def handler(request):
                calls.append(request)
                if response is None:
                    raise httpx.ReadTimeout("fake uncertain post")
                return httpx.Response(response, json={"error": "fake rejection"})

            self.provider(handler)
            await self.queue.submit("cp", thread, [self.task()])
            done = await self.done(thread=thread)
            self.assertEqual(done.status, "unknown" if response is None else "failed")
            self.assertFalse(done.safe_to_retry)
            with self.assertRaisesRegex(BusinessError, "禁止重发"):
                await self.queue.retry("cp", thread, ["one"])
            await self.queue.submit("cp", thread, [self.task()])
            self.assertEqual(len(calls), 1)

    async def test_download_exhaustion_then_explicit_resume_never_reposts(self):
        posts, gets, healthy = [], [], False

        def post(request):
            posts.append(request)
            return httpx.Response(
                200, json={"data": [{"url": "https://example.com/generated.png"}]}
            )

        def get(request):
            gets.append(request)
            return httpx.Response(200, content=png()) if healthy else httpx.Response(503)

        self.provider(post, get)
        with patch(
            "zhenzhen_nanobanana_mcp.media.public_ip", AsyncMock(return_value="93.184.216.34")
        ):
            await self.queue.submit("cp", "thread", [self.task()])
            failed = await self.done()
            self.assertEqual(failed.status, "failed")
            self.assertTrue(failed.safe_to_retry)
            self.assertEqual(failed.recovery_attempts, 3)
            self.assertEqual(len(gets), 9)
            healthy = True
            await self.queue.retry("cp", "thread", ["one"])
            result = await self.done()
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(len(posts), 1)
        self.assertEqual(result.provider_idempotency_key, failed.provider_idempotency_key)

    async def test_shutdown_after_response_resumes_download_only(self):
        entered, release = asyncio.Event(), asyncio.Event()
        posts = []

        def post(request):
            posts.append(request)
            return httpx.Response(
                200, json={"data": [{"url": "https://example.com/generated.png"}]}
            )

        async def get(request):
            entered.set()
            await release.wait()
            return httpx.Response(200, content=png())

        provider = self.provider(post, get)
        with patch(
            "zhenzhen_nanobanana_mcp.media.public_ip", AsyncMock(return_value="93.184.216.34")
        ):
            await self.queue.submit("cp", "thread", [self.task()])
            await asyncio.wait_for(entered.wait(), 3)
            await self.queue.close()
            self.assertEqual(self.queue.get("cp", "thread").tasks[0].status, "recovering")
            restarted = TaskQueue(self.settings, provider=provider, loader=provider.loader)
            self.addAsyncCleanup(restarted.close)
            release.set()
            await restarted.start()
            done = await restarted.wait("cp", "thread", ["one"], 5)
        self.assertEqual(done.tasks[0].status, "succeeded")
        self.assertEqual(len(posts), 1)

    async def test_output_corruption_is_detected_and_preserved_during_repair(self):
        await self.queue.submit("cp", "thread", [self.task()])
        original = await self.done()
        path = Path(original.images[0].path)
        broken = b"broken bytes much longer than the original tiny image" * 20
        path.write_bytes(broken)
        bad = self.queue.get("cp", "thread").tasks[0]
        self.assertEqual((bad.status, bad.file_integrity), ("failed", "failed"))
        with self.assertRaisesRegex(BusinessError, "repair_files"):
            await self.queue.retry("cp", "thread", ["one"])
        await self.queue.retry("cp", "thread", ["one"], repair_files=True)
        repaired = await self.done()
        self.assertEqual(repaired.status, "succeeded")
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), original.images[0].sha256)
        backups = list(path.parent.glob(path.name + ".corrupt-*"))
        self.assertEqual([p.read_bytes() for p in backups], [broken])
        self.queue.storage.provider.render.assert_awaited_once()

    async def test_input_hash_preflight_and_pinned_retry(self):
        source = self.root / "source.png"
        source.write_bytes(png("red"))
        expected = hashlib.sha256(png()).hexdigest()
        task = self.task(reference_images=[str(source)], reference_sha256=[expected])
        await self.queue.submit("cp", "thread", [task])
        failed = await self.done()
        self.assertEqual((failed.status, failed.post_attempts), ("failed", 0))
        self.assertIn("SHA256", failed.error)
        source.write_bytes(png())
        await self.queue.retry("cp", "thread", ["one"])
        done = await self.done()
        self.assertEqual(done.reference_sha256, [expected])
        self.queue.storage.provider.render.assert_awaited_once()
        with self.assertRaises(ValidationError):
            self.task(reference_images=[str(source)], reference_sha256=[])

    async def test_transient_output_write_failure_recovers_without_generation(self):
        writes = 0

        def flaky_publish(path, data, **kwargs):
            nonlocal writes
            if path.name == "01.png":
                writes += 1
                if writes == 1:
                    raise OSError("fake temporary disk failure")
            return publish(path, data, **kwargs)

        with patch("zhenzhen_nanobanana_mcp.tasks.publish", side_effect=flaky_publish):
            await self.queue.submit("cp", "thread", [self.task()])
            done = await self.done()
        self.assertEqual(done.status, "succeeded")
        self.assertEqual(done.recovery_attempts, 2)
        self.queue.storage.provider.render.assert_awaited_once()

    async def test_changed_download_cannot_replace_original_output_hash(self):
        posts, changed = [], False

        def post(request):
            posts.append(request)
            return httpx.Response(200, json={"data": [{"url": "https://example.com/image.png"}]})

        def get(request):
            return httpx.Response(200, content=png("red") if changed else png())

        self.provider(post, get)
        with patch(
            "zhenzhen_nanobanana_mcp.media.public_ip", AsyncMock(return_value="93.184.216.34")
        ):
            await self.queue.submit("cp", "thread", [self.task()])
            original = await self.done()
            path = Path(original.images[0].path)
            path.write_bytes(b"corrupted")
            changed = True
            for _ in range(2):
                await self.queue.retry("cp", "thread", ["one"], True)
                failed = await self.done()
                self.assertEqual(failed.status, "failed")
                self.assertEqual(failed.images[0].sha256, original.images[0].sha256)
                self.assertEqual(path.read_bytes(), b"corrupted")
            changed = False
            await self.queue.retry("cp", "thread", ["one"], True)
            restored = await self.done()
            self.assertEqual(restored.status, "succeeded")
        self.assertEqual(len(posts), 1)

    async def test_connect_failure_retry_uses_frozen_inputs_and_same_key(self):
        source = self.root / "source.png"
        source.write_bytes(png())
        healthy, requests = False, []

        def handler(request):
            requests.append(request)
            if not healthy:
                raise httpx.ConnectError("fake unavailable")
            return httpx.Response(
                200, json={"data": [{"b64_json": base64.b64encode(png()).decode()}]}
            )

        settings = replace(self.settings, safe_attempts=1)
        self.queue.settings = settings
        self.provider(handler, settings=settings)
        task = self.task(reference_images=[str(source)])
        await self.queue.submit("cp", "thread", [task])
        failed = await self.done()
        self.assertTrue(failed.safe_to_retry)
        source.write_bytes(png("red"))
        healthy = True
        await self.queue.retry("cp", "thread", ["one"])
        done = await self.done()
        self.assertEqual(done.status, "succeeded")
        self.assertEqual(len({r.headers["Idempotency-Key"] for r in requests}), 1)
        payload = json.loads(requests[-1].content)
        self.assertEqual(base64.b64decode(payload["image"][0]), png())

    async def test_response_hash_tampering_and_atomic_unsafe_retry_batch(self):
        await self.queue.submit("cp", "thread", [self.task()])
        done = await self.done()
        with self.queue.connect() as db:
            row = db.execute("SELECT response_path FROM image_tasks WHERE task_id='one'").fetchone()
        Path(row[0]).write_text("tampered", encoding="utf-8")
        Path(done.images[0].path).unlink()
        await self.queue.retry("cp", "thread", ["one"], True)
        failed = await self.done()
        self.assertEqual(failed.status, "failed")
        self.assertIn("检查点SHA256", failed.error)
        self.queue.storage.provider.render.assert_awaited_once()
        self.queue.storage.provider.render = AsyncMock(side_effect=httpx.ReadTimeout("uncertain"))
        await self.queue.submit("cp", "thread", [self.task("unsafe")])
        await self.done("unsafe")
        with self.assertRaises(BusinessError):
            await self.queue.retry("cp", "thread", ["one", "unsafe"], True)
        self.assertEqual(self.queue.get("cp", "thread", ["one"]).tasks[0].status, "failed")

    async def test_legacy_schema_and_fingerprint_replay_are_preserved(self):
        self.settings.output_dir.mkdir()
        image = self.settings.output_dir / "old.png"
        image.write_bytes(png())
        task = self.task()
        request = task.model_dump(exclude={"reference_sha256"})
        api, endpoint = resolve_api(task.model, task.api_format, task.endpoint, False)
        canonical = json.dumps(
            {
                "request": request,
                "model": task.model,
                "api": api,
                "endpoint": endpoint,
                "base_url": self.settings.base_url,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        with closing(sqlite3.connect(self.queue.db_path)) as db, db:
            db.execute(
                "CREATE TABLE image_tasks (seq INTEGER PRIMARY KEY AUTOINCREMENT,checkpointer TEXT,thread_id TEXT,task_id TEXT,fingerprint TEXT,request TEXT,actual_model TEXT,api_format TEXT,endpoint TEXT,state TEXT,base_url TEXT,owner TEXT,images TEXT,error TEXT,created REAL,updated REAL,UNIQUE(checkpointer,thread_id,task_id))"
            )
            media = decode_image(png())
            images = [
                {
                    "path": str(image),
                    "sha256": media.digest,
                    "bytes": len(media.data),
                    "width": 16,
                    "height": 16,
                    "mime_type": media.mime,
                }
            ]
            db.execute(
                "INSERT INTO image_tasks(checkpointer,thread_id,task_id,fingerprint,request,actual_model,api_format,endpoint,state,base_url,images,created,updated) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    "cp",
                    "thread",
                    "one",
                    hashlib.sha256(canonical.encode()).hexdigest(),
                    json.dumps(request),
                    task.model,
                    api,
                    endpoint,
                    "succeeded",
                    self.settings.base_url,
                    json.dumps(images),
                    time.time(),
                    time.time(),
                ),
            )
        replay = await self.queue.submit("cp", "thread", [task])
        self.assertTrue(replay.tasks[0].reused)
        self.assertEqual(replay.tasks[0].file_integrity, "verified")
        self.queue.storage.provider.render.assert_not_awaited()

    async def test_three_processes_two_hundred_jobs_share_five_slots(self):
        root = self.root / "load"
        root.mkdir()
        (root / "posts").mkdir()
        settings = replace(self.settings, output_dir=root / "output")
        staging = TaskQueue(settings)
        with patch.object(staging, "ensure_workers"):
            for start in range(0, 200, 20):
                await staging.submit(
                    "load", "load", [self.task(str(i)) for i in range(start, start + 20)]
                )
        with closing(sqlite3.connect(root / "metrics.sqlite3")) as db, db:
            db.execute("CREATE TABLE metrics(active INTEGER,peak INTEGER)")
            db.execute("INSERT INTO metrics VALUES (0,0)")
        fixture = Path(__file__).with_name("queue_load_fixture.py")
        processes = [
            await asyncio.create_subprocess_exec(
                sys.executable,
                str(fixture),
                str(root),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            for _ in range(3)
        ]
        started = time.monotonic()
        try:
            async with asyncio.timeout(20):
                while len(list(root.glob("ready-*"))) != 3:
                    if any(p.returncode is not None for p in processes):
                        self.fail("Load process exited before readiness")
                    await asyncio.sleep(0.02)
            (root / "go").touch()
            # This is a bounded completion guard, not a throughput requirement.
            # Windows fsync under coverage is slower; keep every correctness check.
            async with asyncio.timeout(90 if sys.platform == "win32" else 30):
                while True:
                    rows = []
                    cursor = 0
                    while True:
                        page = staging.get("load", "load", cursor=cursor)
                        rows.extend(page.tasks)
                        if page.next_cursor is None:
                            break
                        cursor = page.next_cursor
                    if all(
                        t.status not in ("queued", "preparing", "running", "recovering")
                        for t in rows
                    ):
                        break
                    await asyncio.sleep(0.05)
            self.assertEqual(len(rows), 200)
            self.assertTrue(
                all(t.status == "succeeded" and t.file_integrity == "verified" for t in rows)
            )
            self.assertEqual(len(list((root / "posts").iterdir())), 200)
            self.assertEqual(len({t.provider_idempotency_key for t in rows}), 200)
            with closing(sqlite3.connect(root / "metrics.sqlite3")) as db:
                peak = db.execute("SELECT peak FROM metrics").fetchone()[0]
            self.assertEqual(peak, 5)
            with closing(sqlite3.connect(staging.db_path)) as db:
                self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertEqual(db.execute("PRAGMA journal_mode").fetchone()[0], "wal")
            report = {
                "jobs": 200,
                "processes": 3,
                "peak_concurrency": peak,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "duplicate_dispatches": 0,
                "verified_outputs": 200,
                "sqlite_integrity": "ok",
            }
            target = Path(__file__).resolve().parents[1] / "test-reports/sqlite-load.json"
            target.write_text(json.dumps(report, indent=2), encoding="utf-8")
        finally:
            (root / "stop").touch()
            for process in processes:
                try:
                    _, stderr = await asyncio.wait_for(process.communicate(), 5)
                    self.assertEqual(process.returncode, 0, stderr.decode(errors="replace")[-1500:])
                finally:
                    if process.returncode is None:
                        process.kill()
                        await process.wait()

    async def test_twenty_item_stdio_and_retry_tool_in_both_protocol_modes(self):
        fixture = Path(__file__).with_name("stdio_task_fixture.py")
        for mode in ("auto", "legacy"):
            root = self.root / mode
            root.mkdir()
            (root / "release-gate").touch()
            transport = StdioTransport(
                command=sys.executable, args=[str(fixture), str(root)], keep_alive=False
            )
            async with Client(transport, mode=mode, timeout=20, init_timeout=15) as client:
                catalog = await client.call_tool("list_models", {})
                self.assertEqual(catalog.structured_content["max_batch_items"], 20)
                self.assertEqual(len(catalog.structured_content["base_models"]), 3)
                result = await client.call_tool(
                    "generate_images",
                    {
                        "checkpointer": "cp",
                        "thread_id": "stdio",
                        "tasks": [self.task(str(i)).model_dump() for i in range(20)],
                        "wait_timeout_seconds": 10,
                    },
                )
                self.assertFalse(result.is_error)
                image = result.structured_content["tasks"][0]["images"][0]
                Path(image["path"]).write_bytes(b"corrupted")
                restored = await client.call_tool(
                    "retry_image_tasks",
                    {
                        "checkpointer": "cp",
                        "thread_id": "stdio",
                        "task_ids": ["0"],
                        "repair_files": True,
                    },
                )
                self.assertFalse(restored.is_error)
                done = await client.call_tool(
                    "wait_image_tasks",
                    {
                        "checkpointer": "cp",
                        "thread_id": "stdio",
                        "task_ids": ["0"],
                        "wait_timeout_seconds": 5,
                    },
                )
                self.assertFalse(done.is_error)
                self.assertEqual(len(list((root / "fake-posts").iterdir())), 20)


if __name__ == "__main__":
    unittest.main()
