"""No real credentials or network: verify the manual live-test fee boundary."""

import asyncio
import importlib.util
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from zhenzhen_nanobanana_mcp.config import API_KEY_FIELD, BusinessError, Settings

ROOT = Path(__file__).resolve().parents[1]
MODULE = importlib.util.spec_from_file_location(
    "live_ecommerce", ROOT / "scripts/live-ecommerce.py"
)
assert MODULE and MODULE.loader
live = importlib.util.module_from_spec(MODULE)
MODULE.loader.exec_module(live)


class LiveBudgetTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        manifest = json.loads(
            (ROOT / "examples/reference-replica.json").read_text(encoding="utf-8")
        )
        frames = manifest["brief"]["reference_replica"]["frames"]
        mains = [dict(frames[0], panel_id=f"m{i}") for i in range(5)]
        third_variant = dict(manifest["brief"]["variants"][0], sku_id="green", label="绿色款")
        manifest["brief"]["variants"].append(third_variant)
        manifest["brief"]["reference_replica"]["frames"] = (
            mains + frames[1:] + [dict(frames[-1], panel_id="green", sku_id="green")]
        )
        self.manifest = manifest
        self.budget = live.PaidBudget(self.root, manifest)
        (self.root / "output").mkdir()
        with sqlite3.connect(self.root / "output/tasks.sqlite3") as db:
            db.execute(
                "CREATE TABLE image_tasks (provider_key TEXT, checkpointer TEXT, thread_id TEXT, task_id TEXT, request TEXT, actual_model TEXT, base_url TEXT)"
            )
            for i, task_id in enumerate(self.budget.allowed):
                db.execute(
                    "INSERT INTO image_tasks VALUES (?,?,?,?,?,?,?)",
                    (
                        f"key-{i}",
                        "ecommerce-design",
                        manifest["design_id"],
                        task_id,
                        json.dumps({"prompt": "已批准提示", "aspect_ratio": "1:1"}),
                        "gemini-nano-banana-2.1",
                        "https://example.com",
                    ),
                )

    def request(
        self,
        i=0,
        text="已批准提示\n画面比例：1:1。",
        path="/v1beta/models/gemini-nano-banana-2.1:generateContent",
    ):
        return httpx.Request(
            "POST",
            "https://example.com" + path,
            headers={"Idempotency-Key": f"key-{i}"},
            json={"contents": [{"role": "user", "parts": [{"text": text}]}]},
        )

    async def test_original_prompt_and_identity_are_checked_before_network(self):
        calls = []
        transport = live.BudgetTransport(
            self.budget,
            httpx.MockTransport(lambda req: calls.append(req) or httpx.Response(200, json={})),
        )
        async with httpx.AsyncClient(transport=transport) as client:
            for request in (
                self.request(text="changed"),
                self.request(path="/v1/images/generations"),
                self.request(i=99),
            ):
                with self.assertRaises(BusinessError):
                    await client.send(request)
            self.assertEqual(calls, [])
            self.assertEqual((await client.send(self.request())).status_code, 200)
            with self.assertRaisesRegex(BusinessError, "再次POST"):
                await client.send(self.request())
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.budget.summary()["reserved_post_attempts"], 1)

    async def test_full_exact_budget_and_restart_never_reset_attempts(self):
        for i in range(16):
            request = self.request(i)
            self.budget.reserve(request, await request.aread())
        summary = self.budget.summary()
        self.assertEqual(summary["counts"], {"main": 5, "detail": 8, "sku": 3})
        self.assertEqual(summary["reserved_post_attempts"], 16)
        restarted = live.PaidBudget(self.root, self.manifest)
        self.assertEqual(restarted.summary(), summary)
        request = self.request()
        with self.assertRaises(BusinessError):
            restarted.reserve(request, await request.aread())
        changed = dict(self.manifest, design_id="other")
        with self.assertRaisesRegex(BusinessError, "manifest已变化"):
            live.PaidBudget(self.root, changed)

    async def test_uncertain_post_and_concurrent_duplicate_cannot_spend_twice(self):
        request = self.request()
        body = await request.aread()
        results = await asyncio.gather(
            *[asyncio.to_thread(self.budget.reserve, request, body) for _ in range(2)],
            return_exceptions=True,
        )
        self.assertEqual(sum(isinstance(r, BusinessError) for r in results), 1)
        self.assertEqual(self.budget.summary()["reserved_post_attempts"], 1)

        def timeout(req):
            raise httpx.ReadTimeout("mock response uncertain")

        async with httpx.AsyncClient(
            transport=live.BudgetTransport(self.budget, httpx.MockTransport(timeout))
        ) as client:
            with self.assertRaises(httpx.ReadTimeout):
                await client.send(self.request(1))
            with self.assertRaises(BusinessError):
                await client.send(self.request(1))
        self.assertEqual(self.budget.summary()["reserved_post_attempts"], 2)

    async def test_cli_never_runs_without_explicit_authorization_flag(self):
        result = await asyncio.to_thread(
            subprocess.run,
            [
                sys.executable,
                str(ROOT / "scripts/live-ecommerce.py"),
                "execute",
                "--root",
                str(self.root),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("明确授权", result.stderr)
        self.assertEqual(self.budget.summary()["reserved_post_attempts"], 0)

    async def test_child_env_forwards_server_key_without_other_credentials(self):
        with patch.dict(
            "os.environ",
            {
                "GH_TOKEN": "test-github-secret",
                "HTTPS_PROXY": "http://proxy.test:8080",
                "SSL_CERT_FILE": "/tmp/test-ca.pem",
            },
        ):
            env = live.server_environment(Settings(api_key="fake-live-test-value"))
        self.assertEqual(env[API_KEY_FIELD], "fake-live-test-value")
        self.assertEqual(env["HTTPS_PROXY"], "http://proxy.test:8080")
        self.assertNotIn("GH_TOKEN", env)
        self.assertNotIn("GITHUB_TOKEN", env)
