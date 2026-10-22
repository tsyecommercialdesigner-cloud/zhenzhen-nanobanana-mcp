import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from jsonschema import validate
from pydantic import ValidationError

from test_design import png
from zhenzhen_nanobanana_mcp.config import BusinessError, Settings
from zhenzhen_nanobanana_mcp.design import DesignService, prompt_for
from zhenzhen_nanobanana_mcp.design_models import DesignBrief, PanelCopy
from zhenzhen_nanobanana_mcp.media import decode_image
from zhenzhen_nanobanana_mcp.models import resolve_api
from zhenzhen_nanobanana_mcp.server import create_server
from zhenzhen_nanobanana_mcp.suite import compile_suite, style_digest
from zhenzhen_nanobanana_mcp.suite_models import DrawingPrompt, ProductSuiteSpec, SuiteStyle
from zhenzhen_nanobanana_mcp.suite_templates import TEMPLATES_V1, style_presets
from zhenzhen_nanobanana_mcp.suite_tools import ProductSuiteBrief, SuitePromptExport, export_suite
from zhenzhen_nanobanana_mcp.tasks import TaskQueue


class SuiteTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.blue, self.red = self.root / "blue.png", self.root / "red.png"
        self.blue.write_bytes(png())
        self.red.write_bytes(png("red"))
        self.settings = Settings(api_key="suite-test-not-real", output_dir=self.root / "outputs")
        self.queue = TaskQueue(self.settings)
        self.queue.storage.provider.render = AsyncMock(return_value=[decode_image(png())])
        self.addAsyncCleanup(self.queue.close)
        self.design = DesignService(self.queue)

    def data(self):
        def frame(panel_id, kind, template_id, **extra):
            return {
                "panel_id": panel_id,
                "kind": kind,
                "template_id": template_id,
                "purpose": "说明真实用途",
                "title": "桌面收纳",
                "subtitle": "收纳桌面小物",
                "visual": "展示实物正面与侧面纹理",
                "fact_ids": ["usage"],
                **extra,
            }

        detail_ids = [
            "opening",
            "solution",
            "feature",
            "material",
            "usage",
            "feature",
            "proof",
            "closing",
        ]
        frames = [frame("main", "main", "main.hero")]
        frames += [
            frame(
                f"d{i}",
                "detail",
                f"detail.{tid}",
                fact_ids=["material"] if tid == "material" else ["usage"],
            )
            for i, tid in enumerate(detail_ids)
        ]
        frames += [
            frame("blue", "sku", "sku.variant", sku_id="blue", title="蓝色款"),
            frame("red", "sku", "sku.variant", sku_id="red", title="红色款"),
        ]
        return {
            "product_name": "收纳篮",
            "platform": "用户指定的测试平台",
            "audience": "需要桌面收纳的用户",
            "objective": "展示用途、材质与规格差异",
            "product_images": [str(self.blue)],
            "visual_observations": "蓝色圆篮、织纹表面",
            "reference_choice": "skip",
            "reference_reason": "用户选择按实物定风格，本轮不用对标",
            "facts": [
                {
                    "fact_id": "usage",
                    "label": "桌面收纳",
                    "value": "收纳桌面小物",
                    "source": "用户核实",
                    "category": "usage",
                },
                {
                    "fact_id": "material",
                    "label": "棉麻材质",
                    "value": "棉麻",
                    "source": "用户商品资料",
                    "category": "material",
                },
            ],
            "variants": [
                {
                    "sku_id": "blue",
                    "label": "蓝色款",
                    "attributes": {"颜色": "蓝色", "材质": "棉麻"},
                    "product_images": [str(self.blue)],
                    "fact_ids": ["usage", "material"],
                },
                {
                    "sku_id": "red",
                    "label": "红色款",
                    "attributes": {"材质": "棉麻", "颜色": "红色"},
                    "product_images": [str(self.red)],
                    "visual_observations": "红色圆篮，织纹表面",
                    "fact_ids": ["usage"],
                },
            ],
            "suite": {"frames": frames},
        }

    def brief(self, **changes):
        data = self.data()
        data.update(changes)
        return ProductSuiteBrief.model_validate(data)

    async def plan(self, design_id="suite", brief=None):
        return await self.design.plan(design_id, 0, brief or self.brief(), [])

    def approve(self, record):
        return self.design.approve(
            record.design_id, record.revision, record.digest, True, "用户确认整套规范与逐图内容"
        )

    async def test_all_kinds_share_exact_style_and_type_scale_but_use_own_canvas(self):
        record = await self.plan()
        exported = export_suite(record)
        self.assertEqual(len(exported.prompts), 11)
        self.assertEqual({p.kind for p in exported.prompts}, {"main", "detail", "sku"})
        self.assertEqual({p.style_digest for p in exported.prompts}, {exported.style_digest})
        blocks = set()
        for p in exported.prompts:
            text = p.task.prompt
            self.assertEqual(
                text, prompt_for(record, next(f for f in record.panels if f.panel_id == p.panel_id))
            )
            self.assertIn("Noto Sans CJK SC", text)
            self.assertIn("primary=#245A50", text)
            self.assertIn("标题5%，副标题3.2%，正文2.4%", text)
            blocks.add(text.split("# 全套统一规范")[1].split("# 商品身份与事实")[0])
            self.assertEqual(p.task.aspect_ratio, "3:4" if p.kind == "detail" else "1:1")
        self.assertEqual(len(blocks), 1)
        self.queue.storage.provider.render.assert_not_awaited()

    async def test_real_submission_uses_preview_validated_prompt_and_bound_sku_images(self):
        record = self.approve(await self.plan())
        exported = export_suite(record)
        page = await self.design.submit(
            record.design_id,
            record.revision,
            record.digest,
            [p.panel_id for p in record.panels],
            True,
        )
        final = await self.queue.wait(
            "ecommerce-design",
            record.design_id,
            [t.task_id for t in page.tasks],
            30 if sys.platform == "win32" else 10,
        )
        self.assertFalse(
            final.wait_timed_out,
            [(t.task_id, t.status, t.error) for t in final.tasks],
        )
        self.assertTrue(
            all(t.status == "succeeded" for t in final.tasks),
            [(t.task_id, t.status, t.error) for t in final.tasks],
        )
        sent = {
            call.args[0].task_id: call.args[0]
            for call in self.queue.storage.provider.render.await_args_list
        }
        for p in exported.prompts:
            self.assertEqual(sent[p.task.task_id].prompt, p.task.prompt)
            self.assertEqual(sent[p.task.task_id].reference_sha256, p.task.reference_sha256)
        red = next(p for p in exported.prompts if p.panel_id == "red")
        self.assertIn("红色圆篮", red.task.prompt)
        self.assertNotIn("蓝色圆篮", red.task.prompt)
        self.assertIn('{"颜色": "红色", "材质": "棉麻"}', red.task.prompt)
        asset = next(a for a in record.assets if a.source == str(self.red))
        self.assertEqual(red.task.reference_images, [asset.path])
        again = await self.design.submit(
            record.design_id, record.revision, record.digest, ["red"], True
        )
        self.assertTrue(again.tasks[0].reused)
        self.assertEqual(self.queue.storage.provider.render.await_count, 11)

    async def test_each_model_family_routes_actual_format_and_resolution(self):
        for index, model in enumerate(
            ("gemini-3.1-flash-lite-image", "nano-banana-pro", "gemini-nano-banana-2.1")
        ):
            brief = self.brief(model=model)
            data = brief.model_dump(mode="json")
            data["suite"]["canvases"]["detail"]["resolution"] = {"width": 2048, "height": 1536}
            record = await self.plan(f"model{index}", ProductSuiteBrief.model_validate(data))
            p = next(p for p in export_suite(record).prompts if p.kind == "detail")
            self.assertEqual(p.task.model, model if index == 0 else model + "-2k")
            self.assertEqual(
                p.execution_endpoint,
                resolve_api(p.task.model, p.task.api_format, p.task.endpoint, True)[1],
            )
        with self.assertRaises(BusinessError):
            await self.plan("unsupported", self.brief(model="nano-banana-pro", api_format="gemini"))

    async def test_palette_font_and_ratio_validation_and_no_frame_style_override(self):
        invalid = [
            {"palette": {"primary": "green"}},
            {"palette": {"text": "#123"}},
            {"typography": {"font_family": " "}},
            {"typography": {"title_weight": 501}},
            {"hierarchy": {"title_pct": 3, "subtitle_pct": 4}},
            {"hierarchy": {"title_pct": float("nan")}},
            {"hierarchy": {"safe_margin_pct": 12, "product_scale_pct": 80}},
            {"unrecognized_style": "x"},
        ]
        for style in invalid:
            with self.subTest(style=style), self.assertRaises(ValidationError):
                SuiteStyle.model_validate(style)
        self.assertEqual(
            SuiteStyle.model_validate({"palette": {"primary": "#abcdef"}}).palette.primary,
            "#ABCDEF",
        )
        data = self.data()
        data["suite"]["frames"][0]["style"] = {"palette": "red"}
        with self.assertRaises(ValidationError):
            ProductSuiteBrief.model_validate(data)

    async def test_template_kind_story_order_unique_panels_and_all_kinds_are_required(self):
        for change in (
            "wrong_template",
            "missing_kind",
            "duplicate_id",
            "story_order",
            "empty_copy_fact",
        ):
            data = self.data()
            frames = data["suite"]["frames"]
            if change == "wrong_template":
                frames[0]["template_id"] = "sku.variant"
            if change == "missing_kind":
                data["suite"]["frames"] = frames[1:]
            if change == "duplicate_id":
                frames[1]["panel_id"] = frames[0]["panel_id"]
            if change == "story_order":
                frames[1], frames[3] = frames[3], frames[1]
            if change == "empty_copy_fact":
                frames[0]["fact_ids"] = []
            with self.subTest(change=change):
                if change == "empty_copy_fact":
                    with self.assertRaisesRegex(BusinessError, "事实"):
                        await self.plan(change, ProductSuiteBrief.model_validate(data))
                else:
                    with self.assertRaises(ValidationError):
                        ProductSuiteBrief.model_validate(data)

    async def test_sku_and_fact_bindings_reject_missing_wrong_or_foreign_versions(self):
        for change in (
            "missing_sku",
            "duplicate_sku",
            "unknown_sku",
            "foreign_fact",
            "missing_attribute",
            "unknown_fact",
        ):
            data = self.data()
            frames = data["suite"]["frames"]
            if change == "missing_sku":
                frames.pop()
            if change == "duplicate_sku":
                frames[-1]["sku_id"] = "blue"
            if change == "unknown_sku":
                frames[-1]["sku_id"] = "missing"
            if change == "foreign_fact":
                frames[-1]["fact_ids"] = ["material"]
            if change == "missing_attribute":
                del data["variants"][1]["attributes"]["材质"]
            if change == "unknown_fact":
                frames[0]["fact_ids"] = ["fake"]
            with self.subTest(change=change), self.assertRaises(ValidationError):
                ProductSuiteBrief.model_validate(data)

    async def test_style_or_copy_change_invalidates_all_previous_approval(self):
        record = self.approve(await self.plan())
        data = record.brief.model_dump(mode="json")
        data["suite"]["style"]["palette"]["primary"] = "#123456"
        updated = await self.design.plan("suite", 1, DesignBrief.model_validate(data), [])
        self.assertNotEqual(record.digest, updated.digest)
        self.assertNotEqual(
            style_digest(record.brief.suite.style), style_digest(updated.brief.suite.style)
        )
        self.assertEqual(updated.status, "draft")
        self.assertIsNone(updated.approved_digest)
        with self.assertRaisesRegex(BusinessError, "过期"):
            await self.design.submit("suite", 1, record.digest, ["main"], True)
        with self.assertRaisesRegex(BusinessError, "尚未"):
            await self.design.submit("suite", 2, updated.digest, ["main"], True)
        self.queue.storage.provider.render.assert_not_awaited()

    async def test_incomplete_requirements_or_open_questions_produce_no_prompt(self):
        for index, changes in enumerate(
            ({"audience": ""}, {"variants": []}, {"product_images": []}, {"facts": []})
        ):
            data = self.data()
            if "facts" in changes:
                for f in data["suite"]["frames"]:
                    f["fact_ids"] = []
                for v in data["variants"]:
                    v["fact_ids"] = []
            data.update(changes)
            record = await self.plan(f"missing{index}", ProductSuiteBrief.model_validate(data))
            self.assertEqual(record.status, "needs_input")
            self.assertEqual(export_suite(record).prompts, [])
            with self.assertRaises(BusinessError):
                self.approve(record)
        data = self.data()
        data["suite"]["open_questions"] = ["用户需核实字体选择"]
        record = await self.plan("question", ProductSuiteBrief.model_validate(data))
        self.assertIn("用户需核实字体选择", record.questions)

    async def test_paid_authorization_and_plain_edits_cannot_bypass_typed_plan(self):
        record = await self.plan()
        with self.assertRaisesRegex(BusinessError, "收费"):
            await self.design.submit("suite", 1, record.digest, ["main"], False)
        with self.assertRaisesRegex(BusinessError, "尚未"):
            await self.design.submit("suite", 1, record.digest, ["main"], True)
        edit = PanelCopy(panel_id="main", headline="changed", visual="changed", layout="changed")
        with self.assertRaisesRegex(BusinessError, "edits"):
            await self.design.plan("suite", 1, record.brief, [edit])
        altered = record.panels[0].model_copy(update={"headline": "changed"})
        with self.assertRaisesRegex(BusinessError, "不一致"):
            compile_suite(record, altered)
        modified_style = record.brief.suite.style.model_copy(update={"aesthetic": "另一种风格"})
        changed_brief = record.brief.model_copy(
            update={"suite": record.brief.suite.model_copy(update={"style": modified_style})}
        )
        with self.assertRaisesRegex(BusinessError, "摘要"):
            compile_suite(record.model_copy(update={"brief": changed_brief}), record.panels[0])

    async def test_template_evidence_and_copy_terms_are_checked_without_calling_model(self):
        for field in ("size", "term", "alias"):
            data = self.data()
            if field == "size":
                data["suite"]["frames"][3]["template_id"] = "detail.size"
            if field == "term":
                data["suite"]["style"] = {"copywriting": {"forbidden_terms": ["桌面"]}}
            if field == "alias":
                data["suite"]["style"] = {"copywriting": {"terminology": {"桌面收纳": "桌面整理"}}}
            with self.assertRaises(BusinessError):
                await self.plan(field, ProductSuiteBrief.model_validate(data))
        self.queue.storage.provider.render.assert_not_awaited()

    async def test_server_revalidates_constructed_data_and_prompt_length(self):
        brief = self.brief()
        broken = brief.suite.style.hierarchy.model_copy(update={"body_pct": 99})
        unsafe = brief.model_copy(
            update={
                "suite": brief.suite.model_copy(
                    update={"style": brief.suite.style.model_copy(update={"hierarchy": broken})}
                )
            }
        )
        with self.assertRaisesRegex(BusinessError, "校验"):
            await self.plan("unsafe", unsafe)
        data = self.data()
        data["requirements"] = "长" * 2000
        data["audience"] = "人" * 500
        data["objective"] = "标" * 500
        data["visual_observations"] = "物" * 2000
        data["suite"]["style"] = {
            "aesthetic": "风" * 500,
            "lighting": "光" * 500,
            "background": "景" * 500,
            "rendering": "节" * 500,
        }
        with self.assertRaisesRegex(BusinessError, "8000"):
            await self.plan("long", ProductSuiteBrief.model_validate(data))
        with self.assertRaises(BusinessError):
            self.design.get("long")
        self.queue.storage.provider.render.assert_not_awaited()

    async def test_templates_resources_prompts_and_pydantic_contracts(self):
        async with Client(create_server(settings=self.settings, queue=self.queue)) as client:
            tools = {t.name: t for t in await client.list_tools()}
            schema = tools["build_product_suite_prompts"].input_schema
            validate({"design_id": "typed", "brief": self.data()}, schema)
            example = json.loads(
                (Path(__file__).resolve().parents[1] / "examples/product-suite.json").read_text(
                    encoding="utf-8"
                )
            )
            validate(example, schema)
            ProductSuiteBrief.model_validate(example["brief"])
            names = {str(r.uri) for r in await client.list_resources()}
            self.assertIn("nanobanana://templates/product-suite", names)
            presets = json.loads(
                (await client.read_resource("nanobanana://templates/styles"))[0].text
            )
            for style in presets["presets"].values():
                SuiteStyle.model_validate(style)
            for kind in ("main", "detail", "sku"):
                resource = json.loads(
                    (await client.read_resource(f"nanobanana://templates/{kind}"))[0].text
                )
                self.assertTrue(all(t["kind"] == kind for t in resource["templates"]))
            suite = json.loads(
                (await client.read_resource("nanobanana://templates/product-suite"))[0].text
            )
            validate(self.data()["suite"], suite["schema"])
            for name, args in (
                ("product_suite_brief", {"product_name": "篮"}),
                ("product_suite_review", {"design_id": "typed"}),
            ):
                self.assertTrue((await client.get_prompt(name, args)).messages)
            result = await client.call_tool(
                "build_product_suite_prompts", {"design_id": "typed", "brief": self.data()}
            )
            validate(result.structured_content, tools["build_product_suite_prompts"].output_schema)
            built = SuitePromptExport.model_validate(result.structured_content)
            self.assertEqual(built.design.revision, 1)
            again = await client.call_tool("export_product_suite_prompts", {"design_id": "typed"})
            self.assertEqual(result.structured_content, again.structured_content)
            invalid = copy.deepcopy(self.data())
            invalid["suite"]["style"] = {"palette": {"primary": "invalid"}}
            error = await client.call_tool(
                "build_product_suite_prompts",
                {"design_id": "bad", "brief": invalid},
                raise_on_error=False,
            )
            self.assertTrue(error.is_error)
        self.assertEqual(len(TEMPLATES_V1), 12)
        self.assertEqual(len(style_presets()), 3)
        self.assertEqual(DrawingPrompt.model_json_schema()["additionalProperties"], False)
        self.assertTrue(ProductSuiteSpec.model_json_schema()["$defs"])

    async def test_large_suite_submits_in_twenty_item_batches_with_same_style(self):
        data = self.data()
        frames = data["suite"]["frames"]
        main = [dict(frames[0], panel_id=f"m{i}") for i in range(8)]
        detail = (
            frames[1:8] + [dict(frames[3], panel_id=f"extra{i}") for i in range(7)] + [frames[8]]
        )
        data["suite"]["frames"] = main + detail + frames[-2:]
        record = self.approve(await self.plan(brief=ProductSuiteBrief.model_validate(data)))
        ids = [p.panel_id for p in record.panels]
        self.assertEqual(len(ids), 25)
        with self.assertRaisesRegex(BusinessError, "1–20"):
            await self.design.submit("suite", 1, record.digest, ids, True)
        pages = []
        for batch in (ids[:20], ids[20:]):
            pages.extend((await self.design.submit("suite", 1, record.digest, batch, True)).tasks)
        done = await self.queue.wait(
            "ecommerce-design",
            "suite",
            [t.task_id for t in pages],
            30 if sys.platform == "win32" else 10,
        )
        self.assertTrue(
            all(t.status == "succeeded" for t in done.tasks),
            [(t.task_id, t.status, t.error) for t in done.tasks],
        )
        self.assertEqual(self.queue.storage.provider.render.await_count, 25)
        self.assertEqual(self.design.progress("suite").unsubmitted_panel_ids, [])
        self.assertEqual(len({p.style_digest for p in export_suite(record).prompts}), 1)

    async def test_real_stdio_suite_loop_both_protocols(self):
        fixture = Path(__file__).with_name("stdio_task_fixture.py")
        for mode in ("auto", "legacy"):
            root = self.root / mode
            root.mkdir()
            (root / "release-gate").touch()
            transport = StdioTransport(
                command=sys.executable, args=[str(fixture), str(root)], keep_alive=False
            )
            async with Client(transport, mode=mode, timeout=15, init_timeout=15) as client:
                built = await client.call_tool(
                    "build_product_suite_prompts",
                    {"design_id": "stdio-suite", "brief": self.data()},
                )
                output = SuitePromptExport.model_validate(built.structured_content)
                record = output.design
                identity = {
                    "design_id": record.design_id,
                    "revision": record.revision,
                    "digest": record.digest,
                }
                denied = await client.call_tool(
                    "submit_ecommerce_design",
                    {**identity, "panel_ids": ["main"], "authorize_paid": True},
                    raise_on_error=False,
                )
                self.assertTrue(denied.is_error)
                await client.call_tool(
                    "confirm_ecommerce_design",
                    {**identity, "confirmation_note": "用户确认整套", "user_confirmed": True},
                )
                args = {**identity, "panel_ids": ["main", "d0", "red"], "authorize_paid": True}
                await client.call_tool("submit_ecommerce_design", args)
                done = await client.call_tool(
                    "wait_image_tasks",
                    {
                        "checkpointer": "ecommerce-design",
                        "thread_id": record.design_id,
                        "task_ids": ["r1-main", "r1-d0", "r1-red"],
                        "wait_timeout_seconds": 5,
                    },
                )
                self.assertTrue(
                    all(t["status"] == "succeeded" for t in done.structured_content["tasks"])
                )
                await client.call_tool("submit_ecommerce_design", args)
                again = await client.call_tool(
                    "export_product_suite_prompts", {"design_id": record.design_id}
                )
                self.assertEqual(
                    again.structured_content["prompts"], built.structured_content["prompts"]
                )
                self.assertEqual(len(list((root / "fake-posts").iterdir())), 3)
