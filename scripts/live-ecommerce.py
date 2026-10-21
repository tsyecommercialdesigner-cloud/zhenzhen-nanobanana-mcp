"""Explicitly authorized, budgeted live MCP acceptance. Never invoked by CI.

All live inputs, images and ledgers must be outside the Git checkout. This uses
the real Provider, with a fresh HTTPS transport per request so the cloud's
explicit outbound proxy does not disable certificate checks or alter adapters.
"""

import argparse
import asyncio
import hashlib
import json
import os
import sqlite3
import ssl
import sys
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path

import httpx
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from zhenzhen_nanobanana_mcp.config import API_KEY_FIELD, BusinessError, Settings
from zhenzhen_nanobanana_mcp.media import MediaLoader
from zhenzhen_nanobanana_mcp.provider import Provider
from zhenzhen_nanobanana_mcp.reference_tools import ReferenceReplicaBrief, ReferencePromptExport
from zhenzhen_nanobanana_mcp.server import create_server
from zhenzhen_nanobanana_mcp.tasks import ACTIVE, TaskQueue

LIMITS = {"main": 5, "detail": 8, "sku": 3}
TOTAL = sum(LIMITS.values())


def save(path: Path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


class PaidBudget:
    def __init__(self, root: Path, manifest: dict):
        self.root, self.manifest = root, manifest
        self.brief = ReferenceReplicaBrief.model_validate(manifest["brief"])
        frames = self.brief.reference_replica.frames
        if (
            self.brief.reference_replica.scope != "product_suite"
            or Counter(f.kind for f in frames) != LIMITS
        ):
            raise BusinessError("收费验收manifest必须精确为5主图+8详情+3SKU。")
        if manifest.get("expected_revision", 0) != 0:
            raise BusinessError("手动验收只接受原始manifest；重启不建立新版本或新任务身份。")
        self.allowed = {f"r1-{f.panel_id}": f.kind for f in frames}
        self.path = root / "paid-budget.sqlite3"
        encoded = json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode()
        digest = hashlib.sha256(encoded).hexdigest()
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA synchronous=FULL")
            db.execute(
                "CREATE TABLE IF NOT EXISTS budget_config (singleton INTEGER PRIMARY KEY, digest TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS paid_attempts (provider_key TEXT PRIMARY KEY, task_id TEXT UNIQUE NOT NULL, kind TEXT NOT NULL, model TEXT NOT NULL, prompt_sha256 TEXT NOT NULL, requested REAL NOT NULL)"
            )
            old = db.execute("SELECT digest FROM budget_config WHERE singleton=1").fetchone()
            if old and old[0] != digest:
                raise BusinessError("验收manifest已变化；禁止重置预算或更换收费任务。")
            db.execute("INSERT OR IGNORE INTO budget_config VALUES (1,?)", (digest,))

    def reserve(self, request: httpx.Request, body: bytes):
        key = request.headers.get("Idempotency-Key", "")
        db_path = self.root / "output/tasks.sqlite3"
        with sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True) as tasks:
            tasks.row_factory = sqlite3.Row
            row = tasks.execute("SELECT * FROM image_tasks WHERE provider_key=?", (key,)).fetchone()
        if (
            row is None
            or row["checkpointer"] != "ecommerce-design"
            or row["thread_id"] != self.manifest["design_id"]
            or row["task_id"] not in self.allowed
        ):
            raise BusinessError("收费HTTP请求不属于本轮允许的固定任务。")
        spec = json.loads(row["request"])
        payload = json.loads(body)
        expected = spec["prompt"] + f"\n画面比例：{spec['aspect_ratio']}。"
        texts = payload.get("contents", [{}])[0].get("parts", [])
        if (
            request.method != "POST"
            or request.url
            != httpx.URL(row["base_url"] + f"/v1beta/models/{row['actual_model']}:generateContent")
            or payload.get("contents") is None
            or not texts
            or texts[0].get("text") != expected
        ):
            raise BusinessError("实际模型端点/提示词与批准的任务不一致；未发送。")
        kind = self.allowed[row["task_id"]]
        with sqlite3.connect(self.path, timeout=10) as db:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            if db.execute(
                "SELECT 1 FROM paid_attempts WHERE provider_key=? OR task_id=?",
                (key, row["task_id"]),
            ).fetchone():
                raise BusinessError("本任务已有收费请求预留，禁止再次POST。")
            counts = dict(db.execute("SELECT kind,count(*) FROM paid_attempts GROUP BY kind"))
            if sum(counts.values()) >= TOTAL or counts.get(kind, 0) >= LIMITS[kind]:
                raise BusinessError("本轮收费调用预算已用完；未发送。")
            db.execute(
                "INSERT INTO paid_attempts VALUES (?,?,?,?,?,?)",
                (
                    key,
                    row["task_id"],
                    kind,
                    row["actual_model"],
                    hashlib.sha256(spec["prompt"].encode()).hexdigest(),
                    time.time(),
                ),
            )

    def summary(self):
        with sqlite3.connect(self.path) as db:
            counts = dict(db.execute("SELECT kind,count(*) FROM paid_attempts GROUP BY kind"))
        return {"reserved_post_attempts": sum(counts.values()), "counts": counts, "limit": LIMITS}


class BudgetTransport(httpx.AsyncBaseTransport):
    def __init__(self, budget: PaidBudget, transport: httpx.AsyncBaseTransport):
        self.budget, self.transport = budget, transport

    async def handle_async_request(self, request: httpx.Request):
        self.budget.reserve(request, await request.aread())
        return await self.transport.handle_async_request(request)

    async def aclose(self):
        await self.transport.aclose()


class LiveProvider(Provider):
    def __init__(self, settings: Settings, loader: MediaLoader, budget: PaidBudget):
        super().__init__(settings, loader)
        self.budget = budget

    async def render(self, *args):
        context = ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE"))
        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        transport = BudgetTransport(
            self.budget, httpx.AsyncHTTPTransport(proxy=proxy, verify=context, retries=0)
        )
        provider = Provider(self.settings, self.loader, transport)
        return await provider.render(*args)


def serve(root: Path, manifest: dict):
    budget = PaidBudget(root, manifest)
    settings = replace(
        Settings.from_env(), output_dir=root / "output", concurrency=5, safe_attempts=1, timeout=600
    )
    loader = MediaLoader((), settings.timeout, safe_attempts=1)
    queue = TaskQueue(settings, provider=LiveProvider(settings, loader, budget), loader=loader)
    create_server(settings, queue=queue).run(transport="stdio", show_banner=False)


def server_environment(settings: Settings) -> dict[str, str]:
    # The SDK filters inherited env. Only forward this server's credential and
    # network configuration, never unrelated GitHub credentials.
    env = {
        key: os.environ[key]
        for key in (
            "HTTPS_PROXY",
            "https_proxy",
            "SSL_CERT_FILE",
            "REQUESTS_CA_BUNDLE",
            "NANOBANANA_PROJECT_DIR",
        )
        if key in os.environ
    }
    env[API_KEY_FIELD] = settings.api_key
    env["NANOBANANA_BASE_URL"] = settings.base_url
    return env


async def execute(root: Path, manifest: dict):
    budget = PaidBudget(root, manifest)
    transport = StdioTransport(
        command=sys.executable,
        args=[str(Path(__file__).resolve()), "serve", "--root", str(root), "--authorize-paid-test"],
        env=server_environment(Settings.from_env()),
        keep_alive=False,
    )
    async with Client(transport, timeout=650, init_timeout=30) as client:
        await client.read_resource("nanobanana://templates/reference-replica")
        await client.read_resource("nanobanana://templates/reference-analysis")
        await client.get_prompt(
            "reference_replica_brief",
            {
                "product_name": budget.brief.product_name,
                "target_category": budget.brief.reference_replica.target_category,
                "scope": "product_suite",
            },
        )
        for index, source in enumerate(
            [budget.brief.reference_replica.reference_image, *budget.brief.product_images]
        ):
            result = await client.call_tool("inspect_design_images", {"images": [source]})
            save(root / f"input-inspection-{index}.json", result.structured_content)
        existing = await client.call_tool(
            "get_ecommerce_design", {"design_id": manifest["design_id"]}, raise_on_error=False
        )
        if existing.is_error:
            built = await client.call_tool("build_reference_replica_prompts", manifest)
        else:
            built = await client.call_tool(
                "export_validated_reference_replica", {"design_id": manifest["design_id"]}
            )
        output = ReferencePromptExport.model_validate(built.structured_content)
        save(root / "plan.json", built.structured_content)
        record = output.design
        if record.status == "needs_input" or len(output.prompts) != TOTAL or record.revision != 1:
            raise BusinessError("验收方案未就绪，未进入收费阶段。")
        identity = {
            "design_id": record.design_id,
            "revision": record.revision,
            "digest": record.digest,
        }
        if record.status != "approved":
            await client.call_tool(
                "confirm_ecommerce_design",
                {
                    **identity,
                    "user_confirmed": True,
                    "confirmation_note": "用户在本会话明确授权使用公开暖手宝演示完整流程，并将真实收费上限改为5+8+3；此确认仅供收费流程验收，不代表营销上架验收。",
                },
            )
        panel_ids = [p.panel_id for p in record.panels]

        async def submit_wait(selected: list[str]):
            await client.call_tool(
                "submit_ecommerce_design",
                {**identity, "panel_ids": selected, "authorize_paid": True},
            )
            started = time.monotonic()
            while True:
                result = await client.call_tool(
                    "wait_image_tasks",
                    {
                        "checkpointer": "ecommerce-design",
                        "thread_id": record.design_id,
                        "task_ids": [f"r1-{p}" for p in selected],
                        "wait_timeout_seconds": 30,
                    },
                    raise_on_error=False,
                )
                data = result.structured_content
                save(root / "last-wait.json", data)
                states = Counter(t["status"] for t in data["tasks"])
                print(
                    json.dumps(
                        {
                            "stage": "waiting",
                            "selected": len(selected),
                            "states": states,
                            **budget.summary(),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
                if any(status in states for status in ("failed", "unknown", "cancelled")):
                    raise BusinessError("真实任务有失败/未知/取消，停止后续收费提交，保留原任务。")
                if not any(state in ACTIVE for state in states):
                    return data
                if time.monotonic() - started > 1800:
                    raise BusinessError("等待时限已到，禁止重提原任务。")

        await submit_wait(panel_ids[:1])
        print(
            json.dumps({"stage": "pilot_succeeded", "panel_id": panel_ids[0], **budget.summary()}),
            flush=True,
        )
        await submit_wait(panel_ids[1:])
        before = budget.summary()
        await client.call_tool(
            "submit_ecommerce_design", {**identity, "panel_ids": panel_ids, "authorize_paid": True}
        )
        progress = await client.call_tool("get_ecommerce_design", {"design_id": record.design_id})
        save(root / "progress.json", progress.structured_content)
        tasks = progress.structured_content["tasks"]
        if len(tasks) != TOTAL or any(
            t["status"] != "succeeded" or len(t["images"]) != 1 or t["file_integrity"] != "verified"
            for t in tasks
        ):
            raise BusinessError("任务数量、完成状态、图片数量或SHA校验未通过。")
        if progress.structured_content["unsubmitted_panel_ids"] or before != budget.summary():
            raise BusinessError("存在未提交图或复用产生额外收费。")
        exported = await client.call_tool(
            "export_validated_reference_replica", {"design_id": record.design_id}
        )
        if exported.structured_content["prompts"] != built.structured_content["prompts"]:
            raise BusinessError("执行后导出与原提示不一致。")
        save(
            root / "execution-summary.json",
            {
                "status": "execution_passed_pending_visual_review",
                "design_id": record.design_id,
                "digest": record.digest,
                "style_digest": output.style_digest,
                "images": TOTAL,
                **budget.summary(),
            },
        )
        print(
            json.dumps(
                {
                    "stage": "execution_passed_pending_visual_review",
                    "images": TOTAL,
                    **budget.summary(),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("serve", "execute"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--authorize-paid-test", action="store_true")
    args = parser.parse_args()
    if not args.authorize_paid_test:
        parser.error("真实收费必须由用户明确授权，再显式传--authorize-paid-test。")
    root = args.root.resolve(strict=True)
    checkout = Path(__file__).resolve().parents[1]
    if root.is_relative_to(checkout):
        parser.error("真实素材、账本与响应必须存于仓库外。")
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    try:
        if args.mode == "serve":
            serve(root, manifest)
        else:
            asyncio.run(execute(root, manifest))
    except BusinessError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
