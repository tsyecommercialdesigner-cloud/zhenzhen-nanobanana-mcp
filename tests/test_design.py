import asyncio
import hashlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from jsonschema import validate
from PIL import Image
from pydantic import ValidationError

from zhenzhen_nanobanana_mcp.config import BusinessError, Settings
from zhenzhen_nanobanana_mcp.design import DesignService, prompt_for
from zhenzhen_nanobanana_mcp.design_models import (
    BenchmarkReview,
    DesignBrief,
    DesignProgress,
    PanelCopy,
    ProductFact,
    SkuVariant,
)
from zhenzhen_nanobanana_mcp.media import decode_image
from zhenzhen_nanobanana_mcp.server import create_server
from zhenzhen_nanobanana_mcp.tasks import TaskQueue


def png(color="blue"):
    stream = io.BytesIO()
    Image.new("RGB", (16, 16), color).save(stream, format="PNG")
    return stream.getvalue()


class DesignTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.photo = self.root / "商品 实图.png"
        self.photo.write_bytes(png())
        self.other = self.root / "red.png"
        self.other.write_bytes(png("red"))
        self.settings = Settings(api_key="design-test-not-real", output_dir=self.root / "output")
        self.queue = TaskQueue(self.settings)
        self.queue.storage.provider.render = AsyncMock(return_value=[decode_image(png())])
        self.addAsyncCleanup(self.queue.close)
        self.design = DesignService(self.queue)

    def brief(self, kind="main", **updates):
        data = {
            "kind": kind,
            "product_name": "收纳篮",
            "platform": "用户指定测试平台，1:1图片",
            "audience": "需要桌面收纳的用户",
            "objective": "说明用途和真实材质",
            "product_images": [str(self.photo)],
            "visual_observations": "蓝色圆形篮，侧面纹理清晰",
            "reference_choice": "skip",
            "reference_reason": "用户选择本轮不提供对标，按产品风格制作",
            "facts": [
                {
                    "fact_id": "material",
                    "label": "棉麻材质",
                    "value": "材质为棉麻",
                    "source": "用户商品资料",
                    "category": "material",
                },
                {
                    "fact_id": "usage",
                    "label": "桌面收纳",
                    "value": "用于收纳桌面小物",
                    "source": "用户核实用途",
                    "category": "usage",
                },
            ],
        }
        data.update(updates)
        return DesignBrief.model_validate(data)

    def receipt(self, record):
        return (record.design_id, record.revision, record.digest)

    def approve(self, record):
        return self.design.approve(*self.receipt(record), True, "用户确认当前文案和排版")

    async def test_missing_requirements_are_persisted_but_cannot_be_approved(self):
        record = await self.design.plan(
            "missing", 0, DesignBrief(kind="detail", product_name="篮"), []
        )
        self.assertEqual(record.status, "needs_input")
        self.assertGreaterEqual(len(record.questions), 7)
        self.assertEqual(record.panels, [])
        with self.assertRaisesRegex(BusinessError, "补齐"):
            self.approve(record)
        self.assertEqual(DesignService(self.queue).get("missing"), record)
        self.queue.storage.provider.render.assert_not_awaited()

    async def test_benchmark_requires_review_or_explicit_skip_reason(self):
        for index, data in enumerate(
            (
                {"reference_choice": "request"},
                {"reference_choice": "provided"},
                {"reference_reason": " "},
            )
        ):
            record = await self.design.plan(f"ref{index}", 0, self.brief(**data), [])
            self.assertEqual(record.status, "needs_input")
        review = BenchmarkReview(
            source="用户参考图",
            visual_focus="产品居中",
            hierarchy="先产品后卖点",
            copy_approach="短句",
            strengths="层级清晰",
            weaknesses="文字过密",
            adaptation="只参考留白和色调",
        )
        record = await self.design.plan(
            "review", 0, self.brief(reference_choice="provided", benchmarks=[review]), []
        )
        self.assertEqual(record.status, "draft")
        self.assertIn(review.adaptation, prompt_for(record, record.panels[0]))
        self.assertEqual(len(record.assets), 1)

    async def test_main_uses_single_facts_and_detail_has_conversion_sequence(self):
        main = await self.design.plan("main", 0, self.brief(), [])
        self.assertEqual(len(main.panels), 5)
        self.assertEqual(main.panels[0].purpose, "首图点击")
        self.assertIn("70%", main.panels[0].layout)
        self.assertTrue(all(len(p.fact_ids) == 1 for p in main.panels))
        for count in (8, 10, 15):
            record = await self.design.plan(
                f"detail{count}", 0, self.brief("detail", detail_count=count), []
            )
            self.assertEqual(len(record.panels), count)
            self.assertIn("字号", record.panels[0].layout)
            self.assertEqual([p.purpose for p in record.panels[:2]], ["痛点与开篇", "解决方案"])
            self.assertEqual([p.purpose for p in record.panels[-2:]], ["实物细节核对", "购买引导"])
            all_copy = "".join(p.headline + p.body for p in record.panels)
            for unsupported in ("99.99", "3500", "15年", "45分贝", "65L", "认证", "限时", "赠品"):
                self.assertNotIn(unsupported, all_copy)
        self.queue.storage.provider.render.assert_not_awaited()

    async def test_trust_size_and_offer_only_appear_when_supplied(self):
        facts = self.brief().facts + [
            ProductFact(
                fact_id="size",
                label="宽20厘米",
                value="宽20厘米",
                source="用户尺寸表",
                category="size",
            ),
            ProductFact(
                fact_id="trust",
                label="保修一年",
                value="保修一年",
                source="用户售后条款",
                category="trust",
            ),
            ProductFact(
                fact_id="offer",
                label="两件九折",
                value="两件九折",
                source="用户活动条款",
                category="offer",
            ),
        ]
        record = await self.design.plan("evidence", 0, self.brief("detail", facts=facts), [])
        self.assertEqual(record.panels[-2].fact_ids, ["trust"])
        self.assertEqual(record.panels[-1].body, "两件九折")
        sizes = [p for p in record.panels if "size" in p.fact_ids]
        self.assertTrue(sizes)
        self.assertIn("带刻度", sizes[0].visual)

    async def test_sku_binds_each_real_photo_attributes_and_uniform_style(self):
        variants = [
            SkuVariant(
                sku_id="blue",
                label="蓝色基础款",
                attributes={"颜色": "蓝色", "配置": "基础款"},
                product_images=[str(self.photo)],
            ),
            SkuVariant(
                sku_id="red",
                label="红色款",
                attributes={"颜色": "红色"},
                product_images=[str(self.other)],
            ),
        ]
        record = await self.design.plan("sku", 0, self.brief("sku", variants=variants), [])
        self.assertEqual(len(record.panels), 2)
        self.assertEqual([p.sku_id for p in record.panels], ["blue", "red"])
        self.assertNotEqual(record.panels[0].reference_images, record.panels[1].reference_images)
        self.assertEqual(record.panels[0].layout, record.panels[1].layout)
        self.assertIn("颜色：蓝色", record.panels[0].body)
        self.assertIn("配置：基础款", record.panels[0].body)
        self.assertNotIn("蓝色圆形篮", prompt_for(record, record.panels[1]))
        with self.assertRaises(ValidationError):
            SkuVariant(sku_id="empty", label="缺图", attributes={"颜色": "白色"}, product_images=[])

    async def test_conflicting_revision_and_invalid_edits_do_not_replace_plan(self):
        record = await self.design.plan("cas", 0, self.brief(), [])
        with self.assertRaisesRegex(BusinessError, "版本冲突"):
            await self.design.plan("cas", 0, self.brief(), [])
        base = {
            "panel_id": "p01",
            "headline": "棉麻材质",
            "body": "材质为棉麻",
            "visual": "实物特写",
            "layout": "标题在上",
            "fact_ids": ["material"],
        }
        for change in ({"panel_id": "missing"}, {"fact_ids": ["not-real"]}, {"fact_ids": []}):
            with self.assertRaises(BusinessError):
                await self.design.plan("cas", 1, self.brief(), [PanelCopy(**{**base, **change})])
        self.assertEqual(self.design.get("cas"), record)
        revised = await self.design.plan("cas", 1, self.brief(), [PanelCopy(**base)])
        self.assertEqual(revised.panels[0].layout, "标题在上")
        self.assertEqual(revised.revision, 2)

    async def test_revision_invalidates_approval_and_history_survives(self):
        record = await self.design.plan("revision", 0, self.brief(), [])
        approved = self.approve(record)
        revised = await self.design.plan("revision", 1, self.brief(requirements="标题下方留白"), [])
        self.assertIsNone(revised.approved_digest)
        with self.assertRaisesRegex(BusinessError, "过期"):
            await self.design.submit(*self.receipt(record), ["p01"], True)
        self.assertEqual(self.design.get("revision", 1), approved)
        with self.assertRaisesRegex(BusinessError, "确认"):
            await self.design.submit(*self.receipt(revised), ["p01"], True)
        self.queue.storage.provider.render.assert_not_awaited()

    async def test_two_instances_cannot_overwrite_the_same_revision(self):
        await self.design.plan("race", 0, self.brief(), [])
        second = DesignService(TaskQueue(self.settings))
        results = await asyncio.gather(
            self.design.plan("race", 1, self.brief(requirements="方案A"), []),
            second.plan("race", 1, self.brief(requirements="方案B"), []),
            return_exceptions=True,
        )
        self.assertEqual(sum(isinstance(r, BusinessError) for r in results), 1)
        self.assertEqual(self.design.get("race").revision, 2)

    async def test_textless_main_and_supplied_pain_points(self):
        panel = PanelCopy(
            panel_id="p01",
            headline="",
            body="",
            visual="白底实物正面",
            layout="只保留产品，不绘制任何文字",
        )
        record = await self.design.plan("white", 0, self.brief(main_count=1), [panel])
        self.assertIn("主文案：不添加", prompt_for(record, record.panels[0]))
        facts = [self.brief().facts[0].model_copy(update={"pain_point": "桌面物品容易散乱"})]
        detail = await self.design.plan("pain", 0, self.brief("detail", facts=facts), [])
        self.assertIn("桌面物品容易散乱", detail.panels[0].visual)

    async def test_fee_and_confirmation_and_panel_guards_precede_submission(self):
        record = await self.design.plan("guards", 0, self.brief(), [])
        with self.assertRaises(BusinessError):
            self.design.approve(*self.receipt(record), False, "未确认")
        with self.assertRaises(BusinessError):
            await self.design.submit(*self.receipt(record), ["p01"], True)
        self.approve(record)
        for ids, paid in (
            (["p01"], False),
            (["p01", "p01"], True),
            (["p01", "bad"], True),
            ([], True),
        ):
            with self.assertRaises(BusinessError):
                await self.design.submit(*self.receipt(record), ids, paid)
        self.assertFalse(self.queue.db_path.exists())
        self.queue.storage.provider.render.assert_not_awaited()

    async def test_frozen_photo_survives_original_change_and_detects_tampering(self):
        record = await self.design.plan("photo", 0, self.brief(), [])
        self.approve(record)
        self.photo.write_bytes(png("green"))
        self.assertEqual(Path(record.assets[0].path).read_bytes(), png())
        Path(record.assets[0].path).write_bytes(png("red"))
        with self.assertRaisesRegex(BusinessError, "更改"):
            await self.design.submit(*self.receipt(record), ["p01"], True)
        self.queue.storage.provider.render.assert_not_awaited()

    async def test_shared_queue_replay_and_saved_results_after_reopen(self):
        record = await self.design.plan("delivery", 0, self.brief(), [])
        self.approve(record)
        original = await self.design.submit(*self.receipt(record), ["p01"], True)
        replay = await self.design.submit(*self.receipt(record), ["p01"], True)
        self.assertEqual(original.tasks[0].task_id, "r1-p01")
        self.assertTrue(replay.tasks[0].reused)
        done = await self.queue.wait("ecommerce-design", "delivery", ["r1-p01"], 5)
        self.assertEqual(done.tasks[0].status, "succeeded")
        progress = DesignService(TaskQueue(self.settings)).progress("delivery")
        self.assertEqual(len(progress.tasks), 1)
        self.assertEqual(len(progress.unsubmitted_panel_ids), 4)
        image = progress.tasks[0].images[0]
        self.assertEqual(hashlib.sha256(Path(image.path).read_bytes()).hexdigest(), image.sha256)
        self.queue.storage.provider.render.assert_awaited_once()
        spec = self.queue.storage.provider.render.await_args.args[0]
        self.assertEqual(spec.reference_images, record.panels[0].reference_images)

    async def test_fifteen_detail_items_fit_one_batch_and_split_replay_is_free(self):
        record = await self.design.plan("large", 0, self.brief("detail", detail_count=15), [])
        self.approve(record)
        submitted = await self.design.submit(
            *self.receipt(record), [p.panel_id for p in record.panels], True
        )
        self.assertEqual(len(submitted.tasks), 15)
        for subset in (record.panels[:12], record.panels[12:]):
            await self.design.submit(*self.receipt(record), [p.panel_id for p in subset], True)
        done = await self.queue.wait(
            "ecommerce-design", "large", [f"r1-{p.panel_id}" for p in record.panels], 5
        )
        self.assertTrue(all(t.status == "succeeded" for t in done.tasks))
        self.assertEqual(self.design.progress("large").unsubmitted_panel_ids, [])
        self.assertEqual(self.queue.storage.provider.render.await_count, 15)

    async def test_bad_images_and_private_urls_do_not_create_usable_plans(self):
        for index, source in enumerate(
            ("relative.png", str(self.root), "http://127.0.0.1/image.png")
        ):
            with self.assertRaises(BusinessError):
                await self.design.plan(f"unsafe{index}", 0, self.brief(product_images=[source]), [])
        self.queue.storage.provider.render.assert_not_awaited()

    async def test_unsafe_output_symlink_is_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        self.settings.output_dir.mkdir()
        link = self.settings.output_dir / "designs"
        if os.name == "nt":
            script = self.root / "escape-junction.ps1"
            script.write_text(
                "param([string]$Link,[string]$Target)\n"
                "$ErrorActionPreference='Stop'\n"
                "New-Item -ItemType Junction -Path $Link -Target $Target | Out-Null\n",
                encoding="utf-8",
            )
            subprocess.run(
                [
                    "pwsh",
                    "-NoProfile",
                    "-File",
                    str(script),
                    "-Link",
                    str(link),
                    "-Target",
                    str(outside),
                ],
                check=True,
                capture_output=True,
            )
        else:
            link.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(BusinessError, "越过"):
            await self.design.plan("escape", 0, self.brief(), [])

    async def test_strict_schema_duplicate_ids_and_unsupported_model_combination(self):
        for changes in (
            {"main_count": True},
            {"facts": [self.brief().facts[0]] * 2},
            {"kind": "unknown"},
            {"unexpected": "field"},
        ):
            with self.assertRaises(ValidationError):
                self.brief(**changes)
        with self.assertRaisesRegex(BusinessError, "不支持"):
            await self.design.plan(
                "model", 0, self.brief(model="nano-banana-pro", api_format="chat"), []
            )

    async def test_mcp_images_schema_failed_results_and_explicit_authorization(self):
        self.queue.storage.provider.render.side_effect = BusinessError("受控上游失败")
        async with Client(create_server(self.settings, queue=self.queue)) as client:
            inspection = await client.call_tool(
                "inspect_design_images", {"images": [str(self.photo)]}
            )
            self.assertTrue(any(c.type == "image" for c in inspection.content))
            self.assertEqual(
                inspection.structured_content["images"][0]["sha256"],
                hashlib.sha256(png()).hexdigest(),
            )
            plan = await client.call_tool(
                "plan_ecommerce_design", {"design_id": "mcp", "brief": self.brief().model_dump()}
            )
            record = plan.structured_content
            args = {"design_id": "mcp", "revision": record["revision"], "digest": record["digest"]}
            denied = await client.call_tool(
                "confirm_ecommerce_design",
                {**args, "confirmation_note": "未确认", "user_confirmed": "true"},
                raise_on_error=False,
            )
            self.assertTrue(denied.is_error)
            await client.call_tool(
                "confirm_ecommerce_design",
                {**args, "confirmation_note": "用户确认", "user_confirmed": True},
            )
            denied = await client.call_tool(
                "submit_ecommerce_design", {**args, "panel_ids": ["p01"]}, raise_on_error=False
            )
            self.assertTrue(denied.is_error)
            await client.call_tool(
                "submit_ecommerce_design", {**args, "panel_ids": ["p01"], "authorize_paid": True}
            )
            await self.queue.wait("ecommerce-design", "mcp", ["r1-p01"], 5)
            result = await client.call_tool(
                "get_ecommerce_design", {"design_id": "mcp"}, raise_on_error=False
            )
            self.assertTrue(result.is_error)
            validate(result.structured_content, DesignProgress.model_json_schema())
            self.assertEqual(result.structured_content["tasks"][0]["status"], "failed")

    async def test_real_stdio_design_lifecycle_in_both_protocol_modes(self):
        fixture = Path(__file__).with_name("stdio_task_fixture.py")
        for mode in ("auto", "legacy"):
            root = self.root / mode
            root.mkdir()
            (root / "release-gate").touch()
            transport = StdioTransport(
                command=sys.executable, args=[str(fixture), str(root)], keep_alive=False
            )
            async with Client(transport, mode=mode, timeout=15, init_timeout=15) as client:
                plan = await client.call_tool(
                    "plan_ecommerce_design",
                    {"design_id": "stdio", "brief": self.brief(main_count=1).model_dump()},
                )
                record = plan.structured_content
                args = {
                    "design_id": "stdio",
                    "revision": record["revision"],
                    "digest": record["digest"],
                }
                await client.call_tool(
                    "confirm_ecommerce_design",
                    {**args, "confirmation_note": "用户确认", "user_confirmed": True},
                )
                for _ in range(2):
                    await client.call_tool(
                        "submit_ecommerce_design",
                        {**args, "panel_ids": ["p01"], "authorize_paid": True},
                    )
                result = await client.call_tool(
                    "wait_image_tasks",
                    {
                        "checkpointer": "ecommerce-design",
                        "thread_id": "stdio",
                        "task_ids": ["r1-p01"],
                        "wait_timeout_seconds": 5,
                    },
                )
                self.assertFalse(result.is_error)
                progress = await client.call_tool("get_ecommerce_design", {"design_id": "stdio"})
                image = progress.structured_content["tasks"][0]["images"][0]
                self.assertTrue(Path(image["path"]).is_file())
                self.assertEqual(len(list((root / "fake-posts").iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
