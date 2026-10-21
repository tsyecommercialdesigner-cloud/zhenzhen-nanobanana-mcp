import copy
import hashlib
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
from test_replica import assessment, spec_for
from zhenzhen_nanobanana_mcp.config import BusinessError, Settings
from zhenzhen_nanobanana_mcp.design import DesignService, prompt_for
from zhenzhen_nanobanana_mcp.design_models import DesignBrief, PanelCopy
from zhenzhen_nanobanana_mcp.media import decode_image
from zhenzhen_nanobanana_mcp.models import resolve_api
from zhenzhen_nanobanana_mcp.reference import compile_reference
from zhenzhen_nanobanana_mcp.reference_models import ReplicaDrawingPrompt, ReferenceReplicaSpec
from zhenzhen_nanobanana_mcp.reference_tools import (
    ReferenceReplicaBrief,
    ReferencePromptExport,
    export_validated,
)
from zhenzhen_nanobanana_mcp.replica import compile_replica, review_replica
from zhenzhen_nanobanana_mcp.server import create_server
from zhenzhen_nanobanana_mcp.suite import style_digest
from zhenzhen_nanobanana_mcp.suite_tools import ProductSuiteBrief, export_suite
from zhenzhen_nanobanana_mcp.tasks import TaskQueue

ROOT = Path(__file__).resolve().parents[1]


class ReferenceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.reference, self.blue, self.red = [
            self.root / p for p in ("参考.png", "蓝色.png", "红色.png")
        ]
        for p, color in ((self.reference, "goldenrod"), (self.blue, "blue"), (self.red, "red")):
            p.write_bytes(png(color))
        self.settings = Settings(
            api_key="reference-test-not-real", output_dir=self.root / "outputs"
        )
        self.queue = TaskQueue(self.settings)
        self.queue.storage.provider.render = AsyncMock(return_value=[decode_image(png("green"))])
        self.addAsyncCleanup(self.queue.close)
        self.design = DesignService(self.queue)

    def data(self, scope="series", kind="main"):
        data = json.loads((ROOT / "examples/product-suite.json").read_text(encoding="utf-8"))[
            "brief"
        ]
        data["product_images"] = [str(self.blue)]
        for variant, path in zip(data["variants"], (self.blue, self.red)):
            variant["product_images"] = [str(path)]
        suite = data.pop("suite")
        old = spec_for(self.reference)
        frames = suite["frames"]
        if scope == "series":
            frames = [f for f in frames if f["kind"] == kind]
            if kind == "detail":
                frames = frames[2:3]
        for frame in frames:
            frame["composition"] = {
                "graphics_structure": "上方短标题、中间产品、下方真实说明，继承参考的疏密节奏",
                "product_representation": "以本商品实图的真实外形和织纹取代源参考花瓶",
                "layout": old.frames[0].layout.model_dump(),
            }
        data["kind"] = "main" if scope == "product_suite" else kind
        data["reference_replica"] = {
            "scope": scope,
            "reference_image": str(self.reference),
            "source_category": "家居花瓶",
            "target_category": "家居收纳",
            "analysis": old.analysis.model_dump(),
            "adaptations": [
                {
                    "dimension": "商品表现",
                    "action": "adapt",
                    "reference_observation": "源图展示花瓶",
                    "target_decision": "用收纳篮实物和真实收纳用途替代花瓶",
                    "reason": "适应目标商品结构与购买顾虑",
                }
            ],
            "style": suite["style"],
            "frames": frames,
        }
        data["reference_choice"] = "provided"
        data["reference_reason"] = ""
        data["benchmarks"] = [
            {
                "source": "用户实图",
                "visual_focus": "商品为主",
                "hierarchy": "先图后文",
                "copy_approach": "短句",
                "strengths": "留白",
                "weaknesses": "细字难辨",
                "adaptation": "按共享规范和目标构图迁移",
            }
        ]
        return data

    def brief(self, scope="series", kind="main", **changes):
        data = self.data(scope, kind)
        data.update(changes)
        return ReferenceReplicaBrief.model_validate(data)

    async def plan(self, design_id="reference", brief=None):
        return await self.design.plan(design_id, 0, brief or self.brief(), [])

    def approve(self, record):
        return self.design.approve(
            record.design_id,
            record.revision,
            record.digest,
            True,
            "用户确认源图迁移、共享规范和逐图内容",
        )

    async def render(self, record, ids=None):
        record = self.approve(record)
        selected = ids or [p.panel_id for p in record.panels]
        page = await self.design.submit(
            record.design_id, record.revision, record.digest, selected, True
        )
        return await self.queue.wait(
            "ecommerce-design", record.design_id, [t.task_id for t in page.tasks], 10
        )

    async def test_single_and_series_keep_complete_classic_format_and_shared_style(self):
        data = self.data()
        second = copy.deepcopy(data["reference_replica"]["frames"][0])
        second["panel_id"] = "other"
        second["composition"]["graphics_structure"] = "产品居右，左侧留白，但保持共享标题锚点"
        data["reference_replica"]["frames"].append(second)
        record = await self.plan(brief=ReferenceReplicaBrief.model_validate(data))
        exported = export_validated(record)
        self.assertEqual(len(exported.prompts), 2)
        blocks = set()
        for p in exported.prompts:
            text = p.task.prompt
            for title in (
                "Visual Schema",
                "Scene Configuration",
                "Layout Configuration",
                "Textual Contents",
            ):
                self.assertIn(f"# {title}", text)
            self.assertNotIn("# Logical Structure", text)
            self.assertIn("Noto Sans CJK SC", text)
            self.assertNotIn("99999", text)
            blocks.add(text.split("# 全套统一规范")[1].split("# Product Adaptation")[0])
        self.assertEqual(len(blocks), 1)
        self.assertEqual(len({p.style_digest for p in exported.prompts}), 1)
        self.queue.storage.provider.render.assert_not_awaited()

    async def test_full_suite_actual_tasks_equal_preview_and_use_only_own_sku(self):
        record = await self.plan(brief=self.brief("product_suite"))
        preview = export_validated(record)
        self.assertEqual(len(preview.prompts), 11)
        self.assertEqual({p.kind for p in preview.prompts}, {"main", "detail", "sku"})
        self.assertEqual(len(record.assets), 3)
        self.blue.unlink()
        self.red.unlink()
        self.reference.unlink()
        done = await self.render(record)
        self.assertTrue(all(t.status == "succeeded" for t in done.tasks))
        sent = {
            c.args[0].task_id: c.args[0] for c in self.queue.storage.provider.render.await_args_list
        }
        for p in preview.prompts:
            self.assertEqual(p.task.prompt, sent[p.task.task_id].prompt)
            self.assertEqual(p.task.reference_sha256, sent[p.task.task_id].reference_sha256)
            self.assertEqual([r.role for r in p.input_images], ["style_only", "product_identity"])
            self.assertEqual(p.input_images[0].sha256, hashlib.sha256(png("goldenrod")).hexdigest())
            self.assertEqual(p.task.aspect_ratio, "3:4" if p.kind == "detail" else "1:1")
        red = next(p for p in preview.prompts if p.panel_id == "red")
        self.assertIn("红色圆篮", red.task.prompt)
        self.assertNotIn("蓝色圆篮", red.task.prompt)
        self.assertIn('{"颜色": "红色", "材质": "棉麻"}', red.task.prompt)
        self.assertEqual(red.input_images[1].sha256, hashlib.sha256(png("red")).hexdigest())
        await self.design.submit(record.design_id, 1, record.digest, ["red"], True)
        self.assertEqual(self.queue.storage.provider.render.await_count, 11)

    async def test_all_three_models_and_per_kind_resolution_use_real_routes(self):
        for i, model in enumerate(
            ("gemini-3.1-flash-lite-image", "nano-banana-pro", "gemini-nano-banana-2.1")
        ):
            data = self.data("product_suite")
            data["model"] = model
            data["reference_replica"]["canvases"] = {
                "detail": {"aspect_ratio": "3:4", "resolution": {"width": 1536, "height": 2048}}
            }
            record = await self.plan(f"model{i}", ReferenceReplicaBrief.model_validate(data))
            detail = next(p for p in export_validated(record).prompts if p.kind == "detail")
            self.assertEqual(detail.task.model, model if i == 0 else model + "-2k")
            self.assertEqual(
                detail.execution_endpoint,
                resolve_api(detail.task.model, detail.task.api_format, detail.task.endpoint, True)[
                    1
                ],
            )
        with self.assertRaises(BusinessError):
            await self.plan("invalid", self.brief(api_format="gemini", model="nano-banana-pro"))

    async def test_shared_style_fields_and_per_frame_overrides_are_validated(self):
        for change in (
            "missing_style",
            "hex",
            "font",
            "ratio",
            "frame_style",
            "scene",
            "layout_extra",
            "body_length",
        ):
            data = self.data()
            spec = data["reference_replica"]
            if change == "missing_style":
                del spec["style"]
            if change == "hex":
                spec["style"]["palette"]["primary"] = "blue"
            if change == "font":
                spec["style"]["typography"]["font_family"] = " "
            if change == "ratio":
                spec["style"]["hierarchy"]["body_pct"] = 9
            if change == "frame_style":
                spec["frames"][0]["style"] = {}
            if change == "scene":
                spec["frames"][0]["scene"] = {"color_palette": "red"}
            if change == "layout_extra":
                spec["frames"][0]["composition"]["layout"]["font_family"] = "serif"
            if change == "body_length":
                spec["frames"][0].update(subtitle="字" * 200, body="字" * 400)
            with self.subTest(change=change), self.assertRaises(ValidationError):
                ReferenceReplicaBrief.model_validate(data)

    async def test_categories_scope_templates_story_order_and_ids(self):
        for change in (
            "all_preserve",
            "duplicate_dimension",
            "duplicate_id",
            "wrong_kind",
            "wrong_template",
            "story_order",
        ):
            data = self.data("product_suite")
            spec = data["reference_replica"]
            if change == "all_preserve":
                spec["adaptations"][0]["action"] = "preserve"
            if change == "duplicate_dimension":
                spec["adaptations"] *= 2
            if change == "duplicate_id":
                spec["frames"][1]["panel_id"] = "main"
            if change == "wrong_kind":
                spec["scope"] = "series"
            if change == "wrong_template":
                spec["frames"][0]["template_id"] = "detail.feature"
            if change == "story_order":
                spec["frames"][1], spec["frames"][3] = spec["frames"][3], spec["frames"][1]
            with self.subTest(change=change), self.assertRaises(ValidationError):
                ReferenceReplicaBrief.model_validate(data)
        for kind in ("detail", "sku"):
            record = await self.plan(kind, self.brief(kind=kind))
            self.assertEqual(len(record.panels), 1 if kind == "detail" else 2)
        data = self.data()
        data["kind"] = "detail"
        with self.assertRaises(ValidationError):
            ReferenceReplicaBrief.model_validate(data)

    async def test_real_sku_facts_and_attributes_cannot_be_crossed(self):
        for change in (
            "missing",
            "duplicate",
            "foreign_fact",
            "unknown_fact",
            "attribute",
            "unknown_sku",
        ):
            data = self.data("product_suite")
            frames = data["reference_replica"]["frames"]
            if change == "missing":
                frames.pop()
            if change == "duplicate":
                frames[-1]["sku_id"] = "blue"
            if change == "foreign_fact":
                frames[-1]["fact_ids"] = ["material"]
            if change == "unknown_fact":
                frames[0]["fact_ids"] = ["fake"]
            if change == "attribute":
                del data["variants"][1]["attributes"]["颜色"]
            if change == "unknown_sku":
                frames[-1]["sku_id"] = "fake"
            with self.subTest(change=change), self.assertRaises(ValidationError):
                ReferenceReplicaBrief.model_validate(data)

    async def test_copy_terms_and_template_evidence_requirements_are_enforced(self):
        for change in ("size", "no_fact", "forbidden", "terminology"):
            data = self.data(kind="detail")
            spec = data["reference_replica"]
            if change == "size":
                spec["frames"][0]["template_id"] = "detail.size"
            if change == "no_fact":
                spec["frames"][0]["fact_ids"] = []
            if change == "forbidden":
                spec["style"]["copywriting"]["forbidden_terms"] = ["桌面"]
            if change == "terminology":
                spec["style"]["copywriting"]["terminology"] = {"桌面收纳": "桌面整理"}
            with self.subTest(change=change), self.assertRaises(BusinessError):
                await self.plan(change, ReferenceReplicaBrief.model_validate(data))
        self.queue.storage.provider.render.assert_not_awaited()

    async def test_image_roles_reject_same_bytes_private_url_and_too_many_inputs(self):
        same = self.root / "duplicate.png"
        same.write_bytes(self.blue.read_bytes())
        for source in (str(same), str(self.blue), "http://127.0.0.1/ref.png"):
            data = self.data()
            data["reference_replica"]["reference_image"] = source
            with self.assertRaises(BusinessError):
                await self.plan("role", ReferenceReplicaBrief.model_validate(data))
        with self.assertRaisesRegex(BusinessError, "1–3"):
            await self.plan("count", self.brief(product_images=[str(self.blue)] * 4))
        self.queue.storage.provider.render.assert_not_awaited()

    async def test_missing_requirements_and_open_questions_block_prompt_and_approval(self):
        for change in ("audience", "variants", "question"):
            data = self.data("product_suite")
            if change == "audience":
                data["audience"] = ""
            if change == "variants":
                data["variants"] = []
            if change == "question":
                data["reference_replica"]["open_questions"] = ["源图字体无法确认，请用户选择替代"]
            record = await self.plan(change, ReferenceReplicaBrief.model_validate(data))
            self.assertEqual(record.status, "needs_input")
            self.assertEqual(export_validated(record).prompts, [])
            with self.assertRaises(BusinessError):
                self.approve(record)

    async def test_reference_and_style_revision_invalidate_confirmation_and_preserve_old_inputs(
        self,
    ):
        record = self.approve(await self.plan())
        original = export_validated(record)
        self.reference.write_bytes(png("black"))
        changed = await self.design.plan("reference", 1, record.brief, [])
        self.assertNotEqual(record.digest, changed.digest)
        self.assertNotEqual(
            original.prompts[0].input_images[0].sha256,
            export_validated(changed).prompts[0].input_images[0].sha256,
        )
        self.assertEqual(
            export_validated(self.design.get("reference", 1)).prompts, original.prompts
        )
        data = changed.brief.model_dump(mode="json")
        data["reference_replica"]["style"]["palette"]["primary"] = "#123456"
        final = await self.design.plan("reference", 2, DesignBrief.model_validate(data), [])
        self.assertNotEqual(
            style_digest(record.brief.reference_replica.style),
            style_digest(final.brief.reference_replica.style),
        )
        with self.assertRaisesRegex(BusinessError, "过期"):
            await self.design.submit("reference", 1, record.digest, ["main"], True)
        with self.assertRaisesRegex(BusinessError, "尚未"):
            await self.design.submit("reference", 3, final.digest, ["main"], True)

    async def test_authorization_edits_and_digest_or_model_copy_tampering_fail_closed(self):
        record = await self.plan()
        with self.assertRaisesRegex(BusinessError, "收费"):
            await self.design.submit("reference", 1, record.digest, ["main"], False)
        with self.assertRaisesRegex(BusinessError, "尚未"):
            await self.design.submit("reference", 1, record.digest, ["main"], True)
        edit = PanelCopy(panel_id="main", headline="changed", visual="changed", layout="changed")
        with self.assertRaisesRegex(BusinessError, "edits"):
            await self.design.plan("reference", 1, record.brief, [edit])
        with self.assertRaisesRegex(BusinessError, "不一致"):
            compile_reference(record, record.panels[0].model_copy(update={"headline": "changed"}))
        broken = record.brief.model_copy(update={"audience": "changed"})
        with self.assertRaisesRegex(BusinessError, "摘要"):
            compile_reference(record.model_copy(update={"brief": broken}), record.panels[0])
        original_spec = record.brief.reference_replica
        bad_palette = original_spec.style.palette.model_copy(update={"primary": "invalid"})
        spec = original_spec.model_copy(
            update={"style": original_spec.style.model_copy(update={"palette": bad_palette})}
        )
        with self.assertRaisesRegex(BusinessError, "校验"):
            await self.plan("unsafe", record.brief.model_copy(update={"reference_replica": spec}))
        self.queue.storage.provider.render.assert_not_awaited()

    async def test_logical_structure_is_optional_and_long_prompts_are_not_saved(self):
        data = self.data()
        logic = {
            "design_logic": "先看产品",
            "narrative_order": "再看用途",
            "visual_flow": "自上向下",
        }
        data["reference_replica"]["frames"][0]["logical_structure"] = logic
        record = await self.plan("logic", ReferenceReplicaBrief.model_validate(data))
        self.assertIn("# Logical Structure", export_validated(record).prompts[0].task.prompt)
        data["requirements"] = "长" * 2000
        data["visual_observations"] = "物" * 2000
        for key in ("aesthetic", "lighting", "background", "rendering"):
            data["reference_replica"]["style"][key] = "风" * 500
        with self.assertRaisesRegex(BusinessError, "8000"):
            await self.plan("long", ReferenceReplicaBrief.model_validate(data))
        with self.assertRaises(BusinessError):
            self.design.get("long")

    async def test_result_review_reuses_actual_task_hash_and_persists_agent_evidence(self):
        record = await self.plan()
        done = await self.render(record)
        task = done.tasks[0]
        report = review_replica(
            self.design, record.design_id, 1, task.task_id, task.images[0].sha256, assessment()
        )
        self.assertEqual(report.outcome, "agent_passed")
        self.assertEqual(self.design.progress(record.design_id).replica_reviews, [report])
        with self.assertRaises(BusinessError):
            review_replica(
                self.design, record.design_id, 1, "foreign", task.images[0].sha256, assessment()
            )
        Path(task.images[0].path).write_bytes(b"changed")
        with self.assertRaisesRegex(BusinessError, "变化"):
            review_replica(
                self.design, record.design_id, 1, task.task_id, task.images[0].sha256, assessment()
            )

    async def test_previous_suite_content_hash_and_old_replica_prompt_remain_compatible(self):
        data = json.loads((ROOT / "examples/product-suite.json").read_text(encoding="utf-8"))[
            "brief"
        ]
        data["product_images"] = [str(self.blue)]
        for variant, path in zip(data["variants"], (self.blue, self.red)):
            variant["product_images"] = [str(path)]
        record = await self.plan("old-suite", ProductSuiteBrief.model_validate(data))
        preview = export_suite(record)
        old = record.model_dump(mode="json")
        old["brief"].pop("reference_replica")
        content = {
            key: old[key]
            for key in (
                "reference_hash_binding",
                "design_id",
                "revision",
                "brief",
                "questions",
                "panels",
                "assets",
            )
        }
        self.assertEqual(
            hashlib.sha256(
                json.dumps(content, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest(),
            record.digest,
        )
        with self.design.connect(write=True) as db:
            db.execute(
                "UPDATE designs SET record=? WHERE design_id=?", (json.dumps(old), "old-suite")
            )
        self.assertEqual(export_suite(self.design.get("old-suite")).prompts, preview.prompts)
        done = await self.render(self.design.get("old-suite"), ["main"])
        await self.design.submit("old-suite", 1, record.digest, ["main"], True)
        self.assertEqual(done.tasks[0].status, "succeeded")
        self.assertEqual(self.queue.storage.provider.render.await_count, 1)
        legacy = self.data()
        legacy.pop("reference_replica")
        legacy["replica"] = spec_for(self.reference).model_dump()
        legacy["replica"]["frames"][0]["fact_ids"] = ["usage"]
        legacy_record = await self.plan("legacy", DesignBrief.model_validate(legacy))
        self.assertEqual(
            prompt_for(legacy_record, legacy_record.panels[0]),
            compile_replica(legacy_record, legacy_record.panels[0]),
        )
        with self.assertRaisesRegex(BusinessError, "旧replica"):
            export_validated(legacy_record)

    async def test_templates_schema_prompts_builder_and_readonly_export(self):
        async with Client(create_server(settings=self.settings, queue=self.queue)) as client:
            tools = {t.name: t for t in await client.list_tools()}
            validate(
                {"design_id": "typed", "brief": self.data("product_suite")},
                tools["build_reference_replica_prompts"].input_schema,
            )
            example = json.loads(
                (ROOT / "examples/reference-replica.json").read_text(encoding="utf-8")
            )
            validate(example, tools["build_reference_replica_prompts"].input_schema)
            ReferenceReplicaBrief.model_validate(example["brief"])
            templates = json.loads(
                (await client.read_resource("nanobanana://templates/reference-replica"))[0].text
            )
            self.assertEqual(len(templates["templates"]), 12)
            validate(self.data()["reference_replica"], templates["schema"])
            source = json.loads(
                (await client.read_resource("nanobanana://templates/reference-analysis"))[0].text
            )
            self.assertIn("observational_limits", source["mapping"])
            for prompt, args in (
                ("reference_replica_brief", {"product_name": "篮", "target_category": "家居收纳"}),
                ("reference_replica_review", {"design_id": "typed"}),
            ):
                self.assertTrue((await client.get_prompt(prompt, args)).messages)
            built = await client.call_tool(
                "build_reference_replica_prompts",
                {"design_id": "typed", "brief": self.data("product_suite")},
            )
            validate(
                built.structured_content, tools["build_reference_replica_prompts"].output_schema
            )
            exported = ReferencePromptExport.model_validate(built.structured_content)
            self.assertEqual(exported.design.brief.reference_choice, "provided")
            self.assertEqual(len(exported.prompts), 11)
            again = await client.call_tool(
                "export_validated_reference_replica", {"design_id": "typed"}
            )
            self.assertEqual(again.structured_content, built.structured_content)
            invalid = self.data()
            invalid["reference_replica"]["frames"][0]["style"] = {}
            rejected = await client.call_tool(
                "build_reference_replica_prompts",
                {"design_id": "bad", "brief": invalid},
                raise_on_error=False,
            )
            self.assertTrue(rejected.is_error)
        self.assertFalse(ReplicaDrawingPrompt.model_json_schema()["additionalProperties"])
        self.assertIn("style", ReferenceReplicaSpec.model_json_schema()["required"])

    async def test_large_reference_suite_exports_all_and_submits_twenty_then_five(self):
        data = self.data("product_suite")
        frames = data["reference_replica"]["frames"]
        data["reference_replica"]["frames"] = (
            [dict(frames[0], panel_id=f"m{i}") for i in range(8)]
            + frames[1:8]
            + [dict(frames[3], panel_id=f"extra{i}") for i in range(7)]
            + frames[8:]
        )
        record = self.approve(await self.plan(brief=ReferenceReplicaBrief.model_validate(data)))
        self.assertEqual(len(export_validated(record).prompts), 25)
        ids = [p.panel_id for p in record.panels]
        with self.assertRaisesRegex(BusinessError, "1–20"):
            await self.design.submit("reference", 1, record.digest, ids, True)
        task_ids = []
        for selected in (ids[:20], ids[20:]):
            task_ids += [
                t.task_id
                for t in (
                    await self.design.submit("reference", 1, record.digest, selected, True)
                ).tasks
            ]
        done = await self.queue.wait("ecommerce-design", "reference", task_ids, 10)
        self.assertTrue(all(t.status == "succeeded" for t in done.tasks))
        self.assertEqual(self.queue.storage.provider.render.await_count, 25)

    async def test_real_stdio_shared_replica_loop_in_both_protocols(self):
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
                    "build_reference_replica_prompts",
                    {"design_id": "stdio-ref", "brief": self.data("product_suite")},
                )
                output = ReferencePromptExport.model_validate(built.structured_content)
                record = output.design
                identity = {
                    "design_id": record.design_id,
                    "revision": record.revision,
                    "digest": record.digest,
                }
                args = {**identity, "panel_ids": ["main", "d0", "red"], "authorize_paid": True}
                denied = await client.call_tool(
                    "submit_ecommerce_design", args, raise_on_error=False
                )
                self.assertTrue(denied.is_error)
                await client.call_tool(
                    "confirm_ecommerce_design",
                    {**identity, "confirmation_note": "用户确认共享复刻", "user_confirmed": True},
                )
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
                for task in done.structured_content["tasks"]:
                    image = task["images"][0]
                    inspected = await client.call_tool(
                        "inspect_design_images", {"images": [image["path"]]}
                    )
                    self.assertEqual(
                        inspected.structured_content["images"][0]["sha256"], image["sha256"]
                    )
                    review = await client.call_tool(
                        "review_reference_replica",
                        {
                            "design_id": record.design_id,
                            "revision": 1,
                            "task_id": task["task_id"],
                            "image_sha256": image["sha256"],
                            "assessment": assessment().model_dump(),
                        },
                    )
                    self.assertEqual(review.structured_content["outcome"], "agent_passed")
                await client.call_tool("submit_ecommerce_design", args)
                again = await client.call_tool(
                    "export_validated_reference_replica", {"design_id": record.design_id}
                )
                self.assertEqual(
                    again.structured_content["prompts"], built.structured_content["prompts"]
                )
                progress = await client.call_tool(
                    "get_ecommerce_design", {"design_id": record.design_id}
                )
                self.assertEqual(len(progress.structured_content["replica_reviews"]), 3)
                self.assertEqual(len(list((root / "fake-posts").iterdir())), 3)
