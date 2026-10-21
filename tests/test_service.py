import asyncio
import base64
import io
import json
import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from fastmcp import Client
from jsonschema import validate
from PIL import Image
from pydantic import ValidationError

from zhenzhen_nanobanana_mcp.config import BusinessError, Settings
from zhenzhen_nanobanana_mcp.media import (
    MAX_OUTPUT_BYTES,
    MediaLoader,
    bounded_read,
    decode_b64,
    decode_image,
    public_ip,
)
from zhenzhen_nanobanana_mcp.models import (
    MODELS,
    FORMAT_SUPPORT,
    BatchResult,
    ImageSpec,
    ImageTask,
    TaskPage,
    Resolution,
    base_model,
    route_model,
)
from zhenzhen_nanobanana_mcp.planning import build_plan
from zhenzhen_nanobanana_mcp.provider import Provider
from zhenzhen_nanobanana_mcp.server import create_server
from zhenzhen_nanobanana_mcp.service import BatchService
from zhenzhen_nanobanana_mcp.tasks import TaskQueue


def png():
    stream = io.BytesIO()
    Image.new("RGB", (16, 16), (100, 180, 210)).save(stream, format="PNG")
    return stream.getvalue()


class Base(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / "input"
        self.inputs.mkdir()
        self.ref = self.inputs / "sample.png"
        self.ref.write_bytes(png())
        self.settings = Settings(
            api_key="unit-test-secret",
            input_dirs=(self.inputs,),
            output_dir=self.root / "output",
            timeout=2,
        )
        self.calls = []

    def provider(self, handler=None):
        async def default(request):
            self.calls.append(request)
            return httpx.Response(
                200, json={"data": [{"b64_json": base64.b64encode(png()).decode()}]}
            )

        loader = MediaLoader(self.settings.input_dirs, self.settings.timeout)
        return Provider(self.settings, loader, httpx.MockTransport(handler or default))

    async def wait_page(self, queue, count=1):
        async with asyncio.timeout(4):
            while True:
                page = queue.get("cp", "thread")
                if len(page.tasks) == count and all(
                    task.status not in ("queued", "preparing", "running", "recovering")
                    for task in page.tasks
                ):
                    return page
                await asyncio.sleep(0.02)


class ResolutionTests(unittest.TestCase):
    def test_boundaries_variants_flash_and_unspecified(self):
        for model in MODELS:
            self.assertEqual(route_model(model, None), model)
            for edge, suffix in [
                (1, ""),
                (1024, ""),
                (1025, "-2k"),
                (2047, "-2k"),
                (2048, "-2k"),
                (2049, "-4k"),
                (4096, "-4k"),
            ]:
                for width, height in [(edge, 1), (1, edge)]:
                    actual = route_model(model, Resolution(width=width, height=height))
                    expected = (
                        model
                        if model == "gemini-3.1-flash-lite-image"
                        else model.removesuffix("-2k").removesuffix("-4k") + suffix
                    )
                    self.assertEqual(actual, expected)

    def test_invalid_resolution_and_plan_preservation(self):
        for value in [
            {"width": 0, "height": 1},
            {"width": -1, "height": 1},
            {"width": 1.5, "height": 1},
            {"width": True, "height": 1},
            {"width": "2048", "height": 1},
            {"width": 1},
            {"width": 1, "height": 1, "unit": "px"},
        ]:
            with self.assertRaises(ValidationError):
                ImageSpec(prompt="test", resolution=value)
        resolution = Resolution(width=1536, height=2048)
        plan = build_plan("篮子", [], "detail", 6, "3:4", [], "", "", resolution)
        self.assertTrue(all(item.resolution == resolution for item in plan.items))


class AdapterTests(Base):
    async def test_unsupported_model_formats_and_edits_never_post(self):
        for model in MODELS:
            for fmt in ("dalle", "chat", "gemini"):
                if fmt in FORMAT_SUPPORT[base_model(model)]:
                    continue
                with self.assertRaises(BusinessError):
                    await self.provider().render(ImageSpec(prompt="test"), [], model, fmt)
            if base_model(model) == "gemini-nano-banana-2.1":
                with self.assertRaises(BusinessError):
                    await self.provider().render(
                        ImageTask(task_id="test", prompt="test", endpoint="edits"),
                        [],
                        model,
                        "dalle",
                    )
        self.assertEqual(self.calls, [])

    async def test_edits_without_reference_uses_multipart_and_url(self):
        async def handler(request):
            self.assertEqual(request.url.path, "/v1/images/edits")
            self.assertIn("multipart/form-data", request.headers["content-type"])
            self.assertIn(b'name="response_format"', request.content)
            self.assertIn(b"url", request.content)
            self.assertNotIn(b'name="image"', request.content)
            return httpx.Response(200, json={"data": [{"url": "https://example.com/image"}]})

        provider = self.provider(handler)
        provider.loader.download = AsyncMock(return_value=png())
        result = await provider.render(
            ImageTask(task_id="test", prompt="test", endpoint="edits"),
            [],
            "nano-banana-pro",
            "dalle",
        )
        self.assertEqual(result[0].data, png())
        provider.loader.download.assert_awaited_once()

    async def test_all_models_and_formats_generate_and_edit(self):
        for model in MODELS:
            for fmt in FORMAT_SUPPORT[base_model(model)]:
                for edit in (False, True):

                    async def handler(request):
                        self.calls.append(request)
                        encoded = base64.b64encode(png()).decode()
                        if fmt == "dalle":
                            expected = (
                                "/v1/images/edits"
                                if edit and base_model(model) == "nano-banana-pro"
                                else "/v1/images/generations"
                            )
                            self.assertEqual(request.url.path, expected)
                            body = await request.aread()
                            if edit and base_model(model) == "nano-banana-pro":
                                self.assertIn(b'name="image"', body)
                                self.assertIn(b'name="aspect_ratio"', body)
                                self.assertNotIn(b'name="size"', body)
                                self.assertIn(b"4:5", body)
                                self.assertIn(model.encode(), body)
                            else:
                                self.assertEqual(json.loads(body)["aspect_ratio"], "4:5")
                                self.assertEqual(json.loads(body)["model"], model)
                                self.assertEqual(json.loads(body)["response_format"], "url")
                                if edit:
                                    self.assertEqual(len(json.loads(body)["image"]), 1)
                            payload = {"data": [{"b64_json": encoded}]}
                        elif fmt == "chat":
                            self.assertEqual(request.url.path, "/v1/chat/completions")
                            body = json.loads(await request.aread())
                            self.assertEqual(body["model"], model)
                            if edit:
                                self.assertEqual(len(body["messages"][0]["content"]), 2)
                            else:
                                self.assertIsInstance(body["messages"][0]["content"], str)
                            self.assertNotIn("aspect_ratio", body)
                            payload = {
                                "choices": [
                                    {
                                        "message": {
                                            "content": [
                                                {
                                                    "type": "image_url",
                                                    "image_url": {
                                                        "url": "data:image/png;base64," + encoded
                                                    },
                                                }
                                            ]
                                        }
                                    }
                                ]
                            }
                        else:
                            self.assertEqual(
                                request.url.path, f"/v1beta/models/{model}:generateContent"
                            )
                            body = json.loads(await request.aread())
                            self.assertNotIn("generationConfig", body)
                            self.assertIn("4:5", body["contents"][0]["parts"][0]["text"])
                            self.assertEqual(len(body["contents"][0]["parts"]), 2 if edit else 1)
                            payload = {
                                "candidates": [
                                    {
                                        "content": {
                                            "parts": [
                                                {
                                                    "inlineData": {
                                                        "mimeType": "image/png",
                                                        "data": encoded,
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                ]
                            }
                        return httpx.Response(200, json=payload)

                    provider = self.provider(handler)
                    result = await provider.render(
                        ImageSpec(prompt="保留商品", aspect_ratio="4:5"),
                        [decode_image(png())] if edit else [],
                        model,
                        fmt,
                    )
                    self.assertEqual(result[0].data, png())
        self.assertEqual(len(self.calls), 28)

    async def test_multiple_edit_files(self):
        async def handler(request):
            body = await request.aread()
            self.assertEqual(body.count(b'name="image"'), 2)
            return httpx.Response(
                200, json={"data": [{"b64_json": base64.b64encode(png()).decode()}]}
            )

        await self.provider(handler).render(
            ImageSpec(prompt="组合"), [decode_image(png())] * 2, "nano-banana-pro", "dalle"
        )

    async def test_provider_failures_no_retry_or_secret(self):
        for status, payload in [
            (401, {"error": "unit-test-secret"}),
            (200, {}),
            (200, {"data": [{"b64_json": "bad"}]}),
            (200, {"error": {"message": "unit-test-secret"}}),
        ]:
            calls = []

            async def handler(request):
                calls.append(request)
                return httpx.Response(status, json=payload)

            with self.assertRaises(BusinessError) as ctx:
                await self.provider(handler).render(
                    ImageSpec(prompt="test"), [], "nano-banana-pro", "dalle"
                )
            self.assertNotIn("unit-test-secret", str(ctx.exception))
            self.assertEqual(len(calls), 1)


class BatchTests(Base):
    async def test_default_model_and_resolution_through_mcp(self):
        queue = TaskQueue(self.settings, self.provider())
        async with Client(create_server(self.settings, queue=queue)) as client:
            catalog = await client.call_tool("list_models", {})
            self.assertEqual(catalog.structured_content["default_model"], "gemini-nano-banana-2.1")
            result = await client.call_tool(
                "submit_image_tasks",
                {
                    "checkpointer": "cp",
                    "thread_id": "thread",
                    "tasks": [
                        {"task_id": "base", "prompt": "base"},
                        {
                            "task_id": "2k",
                            "prompt": "2k",
                            "resolution": {"width": 2048, "height": 1024},
                        },
                        {
                            "task_id": "4k",
                            "prompt": "4k",
                            "resolution": {"width": 2049, "height": 1024},
                        },
                    ],
                },
            )
            self.assertFalse(result.is_error)
            done = await self.wait_page(queue, 3)
            self.assertTrue(all(task.status == "succeeded" for task in done.tasks))
            self.assertEqual(
                [json.loads(call.content)["model"] for call in self.calls],
                [
                    "gemini-nano-banana-2.1",
                    "gemini-nano-banana-2.1-2k",
                    "gemini-nano-banana-2.1-4k",
                ],
            )

    async def test_routed_models_reach_all_formats_and_flash_stays_original(self):
        for fmt in ("dalle", "chat", "gemini"):
            for base in (
                "nano-banana-pro",
                "gemini-nano-banana-2.1",
                "gemini-3.1-flash-lite-image",
            ):
                if fmt not in FORMAT_SUPPORT[base_model(base)]:
                    continue
                provider = self.provider()
                provider.render = AsyncMock(return_value=[decode_image(png())])
                service = BatchService(self.settings, provider)
                specs = [
                    ImageSpec(
                        prompt="test",
                        resolution={"width": edge, "height": 800},
                        reference_images=[str(self.ref)] if edit else [],
                    )
                    for edge, edit in [(2048, False), (2049, True)]
                ]
                result = await service.run(base + "-" + fmt, specs, base, fmt)
                validate(result.model_dump(), BatchResult.model_json_schema())
                for call, edge in zip(provider.render.await_args_list, (2048, 2049)):
                    expected = (
                        base
                        if base.endswith("flash-lite-image")
                        else base + ("-2k" if edge == 2048 else "-4k")
                    )
                    self.assertEqual(call.args[2:], (expected, fmt))
                self.assertEqual(result.model, base)

    async def test_resolution_routing_mixed_batch_and_idempotency(self):
        for base in ("nano-banana-pro", "gemini-nano-banana-2.1"):
            service = BatchService(self.settings, self.provider())
            specs = [
                ImageSpec(prompt="test", resolution=r, reference_images=refs)
                for r, refs in [
                    (None, []),
                    (Resolution(width=1024, height=800), []),
                    (Resolution(width=800, height=1025), []),
                    (Resolution(width=2048, height=1000), [str(self.ref)]),
                    (Resolution(width=1000, height=2049), []),
                ]
            ]
            result = await service.run(base, specs, base, "dalle")
            expected = [base, base, base + "-2k", base + "-2k", base + "-4k"]
            self.assertEqual([item.actual_model for item in result.items], expected)
            calls = self.calls[-5:]
            for request, model in zip(calls, expected):
                if request.url.path.endswith("edits"):
                    self.assertIn(model.encode(), request.content)
                    self.assertNotIn(b'name="resolution"', request.content)
                else:
                    body = json.loads(request.content)
                    self.assertEqual(body["model"], model)
                    self.assertNotIn("resolution", body)
                    self.assertNotIn("size", body)
            count = len(self.calls)
            reused = await BatchService(self.settings, self.provider()).run(
                base, specs, base, "dalle"
            )
            self.assertTrue(reused.reused)
            self.assertEqual([item.actual_model for item in reused.items], expected)
            self.assertEqual(len(self.calls), count)
            specs[0].resolution = Resolution(width=1500, height=1000)
            with self.assertRaises(BusinessError):
                await service.run(base, specs, base, "dalle")
            self.assertEqual(len(self.calls), count)

    async def test_old_ledger_remains_queryable_and_idempotent(self):
        import hashlib

        service = BatchService(self.settings, self.provider())
        spec = ImageSpec(prompt="old")
        result = await service.run("old", [spec], "nano-banana-pro", "dalle")
        old = result.model_dump()
        for item in old["items"]:
            item.pop("actual_model")
        canonical = json.dumps(
            {
                "items": [{"prompt": "old", "aspect_ratio": "1:1", "reference_images": []}],
                "model": "nano-banana-pro",
                "api_format": "dalle",
                "base_url": self.settings.base_url,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        with service.connect() as db:
            db.execute(
                "UPDATE batches SET fingerprint=?, result=? WHERE request_id='old'",
                (hashlib.sha256(canonical.encode()).hexdigest(), json.dumps(old)),
            )
        reused = await service.run("old", [spec], "nano-banana-pro", "dalle")
        self.assertEqual(reused.items[0].actual_model, "nano-banana-pro")
        self.assertEqual(len(self.calls), 1)

    async def test_save_and_durable_idempotency(self):
        service = BatchService(self.settings, self.provider())
        items = [
            ImageSpec(prompt="主图"),
            ImageSpec(prompt="详情", reference_images=[str(self.ref)]),
        ]
        result = await service.run("batch-1", items, "nano-banana-pro", "dalle")
        self.assertEqual(result.status, "succeeded")
        validate(result.model_dump(), BatchResult.model_json_schema())
        for item in result.items:
            image = item.images[0]
            self.assertEqual(Path(image.path).read_bytes(), png())
            self.assertEqual(image.sha256, decode_image(png()).digest)
            self.assertTrue(Path(image.path).is_absolute())
        self.assertTrue(Path(result.manifest_path).is_file())
        self.ref.unlink()  # A repeated ID returns its snapshot without reloading changed references.
        restarted = BatchService(self.settings, self.provider())
        reused = await restarted.run("batch-1", items, "nano-banana-pro", "dalle")
        self.assertTrue(reused.reused)
        self.assertEqual(len(self.calls), 2)
        with self.assertRaises(BusinessError):
            await restarted.run("batch-1", [ImageSpec(prompt="其他")], "nano-banana-pro", "dalle")

    async def test_partial_failure_is_error_with_saved_result(self):
        async def handler(request):
            if json.loads(await request.aread())["prompt"] == "fail":
                return httpx.Response(429, json={"error": "private"})
            return httpx.Response(
                200, json={"data": [{"b64_json": base64.b64encode(png()).decode()}]}
            )

        queue = TaskQueue(self.settings, self.provider(handler))
        async with Client(create_server(self.settings, queue=queue)) as client:
            await client.call_tool(
                "submit_image_tasks",
                {
                    "checkpointer": "cp",
                    "thread_id": "thread",
                    "tasks": [
                        {"task_id": "ok", "prompt": "ok"},
                        {"task_id": "fail", "prompt": "fail"},
                    ],
                },
            )
            await self.wait_page(queue, 2)
            result = await client.call_tool(
                "get_image_tasks",
                {"checkpointer": "cp", "thread_id": "thread"},
                raise_on_error=False,
            )
            self.assertTrue(result.is_error)
            self.assertEqual(
                [t["status"] for t in result.structured_content["tasks"]], ["succeeded", "failed"]
            )
            validate(result.structured_content, TaskPage.model_json_schema())
            self.assertTrue(
                Path(result.structured_content["tasks"][0]["images"][0]["path"]).exists()
            )

    async def test_preflight_failure_never_posts(self):
        service = BatchService(self.settings, self.provider())
        with self.assertRaises(BusinessError):
            await service.run(
                "invalid",
                [
                    ImageSpec(prompt="first"),
                    ImageSpec(prompt="second", reference_images=[str(self.root / "missing.png")]),
                ],
                "nano-banana-pro",
                "dalle",
            )
        self.assertFalse(self.calls)

    async def test_cancellation_keeps_completed_images_and_prevents_replay(self):
        waiting = asyncio.Event()

        async def handler(request):
            prompt = json.loads(await request.aread())["prompt"]
            if prompt == "slow":
                waiting.set()
                await asyncio.Event().wait()
            return httpx.Response(
                200, json={"data": [{"b64_json": base64.b64encode(png()).decode()}]}
            )

        service = BatchService(self.settings, self.provider(handler))
        items = [ImageSpec(prompt="fast"), ImageSpec(prompt="slow")]
        task = asyncio.create_task(service.run("cancel", items, "nano-banana-pro", "dalle"))
        await waiting.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        result = service.get("cancel")
        self.assertEqual(result.status, "cancelled")
        self.assertEqual(result.items[0].status, "succeeded")
        self.assertEqual(result.items[1].status, "cancelled")
        replay = await service.run("cancel", items, "nano-banana-pro", "dalle")
        self.assertEqual(replay.status, "cancelled")

    async def test_same_id_concurrent_claim(self):
        waiting = asyncio.Event()
        release = asyncio.Event()

        async def handler(request):
            self.calls.append(request)
            waiting.set()
            await release.wait()
            return httpx.Response(
                200, json={"data": [{"b64_json": base64.b64encode(png()).decode()}]}
            )

        service = BatchService(self.settings, self.provider(handler))
        items = [ImageSpec(prompt="one")]
        task = asyncio.create_task(service.run("unique", items, "nano-banana-pro", "dalle"))
        await waiting.wait()
        with self.assertRaises(BusinessError):
            await BatchService(self.settings, self.provider(handler)).run(
                "unique", items, "nano-banana-pro", "dalle"
            )
        release.set()
        await task
        self.assertEqual(len(self.calls), 1)

    async def test_timeout_no_retry(self):
        async def handler(request):
            self.calls.append(request)
            raise httpx.ReadTimeout("unit-test-secret")

        result = await BatchService(self.settings, self.provider(handler)).run(
            "timeout", [ImageSpec(prompt="test")], "nano-banana-pro", "dalle"
        )
        self.assertEqual(result.status, "failed")
        self.assertNotIn("unit-test-secret", result.model_dump_json())
        self.assertEqual(len(self.calls), 1)


class SafetyTests(Base):
    async def test_network_urls_and_local_paths_in_same_edit(self):
        downloads = []

        async def handler(request):
            downloads.append(request)
            self.assertNotIn("authorization", request.headers)
            self.assertEqual(request.url.host, "93.184.216.34")
            self.assertEqual(request.headers["host"], "example.com")
            if request.url.path == "/redirect":
                return httpx.Response(302, headers={"Location": "/image?token=not-real"})
            return httpx.Response(200, content=png())

        loader = MediaLoader(self.settings.input_dirs, 2, httpx.MockTransport(handler))
        outside = self.root / "原始素材.png"
        outside.write_bytes(png())
        queue = TaskQueue(self.settings, self.provider(), loader)
        with patch(
            "zhenzhen_nanobanana_mcp.media.public_ip", new=AsyncMock(return_value="93.184.216.34")
        ) as dns:
            async with Client(create_server(self.settings, queue=queue)) as client:
                result = await client.call_tool(
                    "submit_image_tasks",
                    {
                        "checkpointer": "cp",
                        "thread_id": "thread",
                        "tasks": [
                            {
                                "task_id": "mixed",
                                "prompt": "combine",
                                "model": "nano-banana-pro",
                                "reference_images": [
                                    str(outside),
                                    "http://example.com/redirect",
                                    "https://example.com/image",
                                ],
                            }
                        ],
                    },
                )
                self.assertFalse(result.is_error)
                done = await self.wait_page(queue)
                self.assertEqual(done.tasks[0].endpoint, "edits")
                catalog = await client.call_tool("list_models", {})
                self.assertEqual(catalog.structured_content["input_dirs"], [])
            self.assertEqual([c.args[1] for c in dns.await_args_list], [80, 80, 443])
        self.assertEqual(len(downloads), 3)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0].content.count(b'name="image"'), 3)

    async def test_url_error_preflight_never_posts(self):
        for response in (httpx.Response(404), httpx.Response(200, content=b"not an image")):
            loader = MediaLoader((), 2, httpx.MockTransport(lambda request: response))
            service = BatchService(self.settings, self.provider(), loader)
            with patch(
                "zhenzhen_nanobanana_mcp.media.public_ip",
                new=AsyncMock(return_value="93.184.216.34"),
            ):
                with self.assertRaises(BusinessError):
                    await service.run(
                        "bad-url",
                        [ImageSpec(prompt="edit", reference_images=["http://example.com/image"])],
                        "gemini-nano-banana-2.1",
                        "dalle",
                    )
        self.assertEqual(self.calls, [])

    async def test_default_access_uses_original_paths_and_saved_outputs(self):
        from dataclasses import replace

        outside = self.root / "素材 文件夹" / "商品.png"
        outside.parent.mkdir()
        outside.write_bytes(png())
        settings = replace(self.settings, input_dirs=())
        service = BatchService(settings, self.provider())
        result = await service.run(
            "original-path",
            [ImageSpec(prompt="edit", reference_images=[str(outside)])],
            "gemini-nano-banana-2.1",
            "dalle",
        )
        self.assertEqual(result.items[0].operation, "edit")
        saved = result.items[0].images[0].path
        second = await service.run(
            "saved-output",
            [ImageSpec(prompt="edit again", reference_images=[saved])],
            "gemini-nano-banana-2.1",
            "dalle",
        )
        self.assertEqual(second.status, "succeeded")
        self.assertEqual(len(self.calls), 2)
        async with Client(create_server(settings, service)) as client:
            catalog = await client.call_tool("list_models", {})
            self.assertEqual(catalog.structured_content["input_dirs"], [])
            self.assertEqual(catalog.structured_content["local_file_access"], "readable_files")

    async def test_unrestricted_still_validates_files_and_permissions(self):
        loader = MediaLoader((), 2)
        invalid = self.root / "not-image.txt"
        invalid.write_text("not an image", encoding="utf-8")
        for value in (str(invalid), str(self.root), str(self.root / "missing.png"), "relative.png"):
            with self.assertRaises(BusinessError):
                await loader.load(value)
        with patch.object(Path, "open", side_effect=PermissionError("private-not-real")):
            with self.assertRaises(BusinessError) as ctx:
                await loader.load(str(self.ref))
            self.assertNotIn("private-not-real", str(ctx.exception))

    async def test_junction_outside_old_input_is_readable(self):
        outside = self.root / "outside-dir"
        outside.mkdir()
        (outside / "image.png").write_bytes(png())
        link = self.inputs / "link"
        # Pass literal paths through a script's parameter binding.
        script = self.root / "junction.ps1"
        script.write_text(
            "param([string]$Link,[string]$Target)\n"
            "$ErrorActionPreference='Stop'\n"
            "$LinkType = if ($IsWindows) { 'Junction' } else { 'SymbolicLink' }\n"
            "New-Item -ItemType $LinkType -Path $Link -Target $Target | Out-Null\n",
            encoding="utf-8",
        )
        command = [
            "pwsh",
            "-NoProfile",
            "-File",
            str(script),
            "-Link",
            str(link),
            "-Target",
            str(outside),
        ]
        subprocess.run(command, capture_output=True, check=True)
        loader = MediaLoader(self.settings.input_dirs, 2)
        self.assertEqual((await loader.load(str(link / "image.png"))).data, png())

    async def test_size_and_pixel_limits(self):
        with self.assertRaises(BusinessError):
            decode_image(png(), limit=10)
        with self.assertRaises(BusinessError):
            decode_b64("A" * (((MAX_OUTPUT_BYTES + 2) // 3) * 4 + 1))
        data = bytearray(png())
        data[16:24] = struct.pack(">II", 9000, 9000)
        data[29:33] = struct.pack(">I", zlib.crc32(data[12:29]))
        with self.assertRaises(BusinessError):
            decode_image(bytes(data))
        response = httpx.Response(200, content=b"123456", headers={"Content-Length": "6"})
        with self.assertRaises(BusinessError):
            await bounded_read(response, 5)

    async def test_boundaries(self):
        loader = MediaLoader(self.settings.input_dirs, 2)
        outside = self.root / "outside.png"
        outside.write_bytes(png())
        self.assertEqual((await loader.load(str(outside))).data, png())
        for value in ("relative.png", "http://127.0.0.1/a", "file:///a"):
            with self.assertRaises(BusinessError):
                await loader.load(value)
        with self.assertRaises(BusinessError):
            decode_image(b"not an image")
        with self.assertRaises(BusinessError):
            decode_b64("invalid!")
        with self.assertRaises(ValidationError):
            ImageSpec(prompt=" ")
        with self.assertRaises(ValidationError):
            ImageSpec(prompt="test", size="1:1")

    async def test_dns_private_rejected(self):
        for host in ("127.0.0.1", "::1", "192.168.1.1", "169.254.169.254", "224.0.0.1"):
            with self.assertRaises(BusinessError):
                await public_ip(host)

    async def test_redirect_and_dns_pinning_no_auth(self):
        calls = []

        async def handler(request):
            calls.append(request)
            self.assertNotIn("authorization", request.headers)
            self.assertEqual(request.url.host, "93.184.216.34")
            self.assertEqual(request.headers["host"], "example.com")
            self.assertEqual(request.extensions["sni_hostname"], "example.com")
            return httpx.Response(302, headers={"Location": "https://127.0.0.1/private"})

        loader = MediaLoader(self.settings.input_dirs, 2, httpx.MockTransport(handler))

        async def resolved(host, port=443):
            if host != "example.com":
                raise BusinessError("拒绝访问非公网图片地址。")
            return "93.184.216.34"

        with patch("zhenzhen_nanobanana_mcp.media.public_ip", new=resolved):
            with self.assertRaises(BusinessError):
                await loader.download("https://example.com/picture")
        self.assertEqual(len(calls), 1)

    async def test_url_download_saved(self):
        provider = self.provider(
            lambda request: httpx.Response(
                200, json={"data": [{"url": "https://example.com/image.png"}]}
            )
        )
        provider.loader.download = AsyncMock(return_value=png())
        result = await provider.render(ImageSpec(prompt="test"), [], "nano-banana-pro", "dalle")
        self.assertEqual(result[0].data, png())

    async def test_free_plan_and_protocol_validation(self):
        plan = build_plan("收纳篮", ["棉麻"], "detail", 6, "3:4", [], "", "")
        self.assertEqual(len(plan.items), 6)
        self.assertIn("未提供则不标尺寸", plan.items[4].prompt)
        async with Client(create_server(self.settings)) as client:
            for arguments in (
                {"checkpointer": "cp", "thread_id": "thread"},
                {
                    "checkpointer": "cp",
                    "thread_id": "thread",
                    "tasks": [{"task_id": "bad", "prompt": "ok", "model": "fake"}],
                },
                {
                    "checkpointer": "",
                    "thread_id": "thread",
                    "tasks": [{"task_id": "bad", "prompt": "ok"}],
                },
                {"checkpointer": "cp", "thread_id": "thread", "tasks": []},
            ):
                result = await client.call_tool(
                    "submit_image_tasks", arguments, raise_on_error=False
                )
                self.assertTrue(result.is_error)


if __name__ == "__main__":
    unittest.main()
