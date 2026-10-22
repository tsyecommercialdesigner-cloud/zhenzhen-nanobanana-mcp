import hashlib
import io
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
from zhenzhen_nanobanana_mcp.design import DesignService
from zhenzhen_nanobanana_mcp.design_models import DesignBrief, PanelCopy, SkuVariant
from zhenzhen_nanobanana_mcp.media import decode_image
from zhenzhen_nanobanana_mcp.replica import export_replica, review_replica
from zhenzhen_nanobanana_mcp.replica_models import ReplicaAssessment, ReplicaExport, ReplicaSpec
from zhenzhen_nanobanana_mcp.tasks import TaskQueue


def png(color):
    stream = io.BytesIO()
    Image.new("RGB", (16, 16), color).save(stream, format="PNG")
    return stream.getvalue()


def spec_for(reference):
    visual = {
        "aesthetic_style": "温暖、克制、材质真实的电商摄影",
        "graphics_structure": "上方短标题、中央产品、底部标签",
        "product_representation": "展示产品真实比例与表面纹理，不改变实际配件",
    }
    scene = {
        "color_palette": "米色背景和柔和金色点缀",
        "optical_vibe": "左上方柔和自然光，保留接触阴影",
        "rendering_details": "表面纹理清晰、自然景深，不虚构内部剖面",
    }
    layout = {
        "objects_composition": "产品居中，留白约三成",
        "text_arrangement": "深色粗标题在上，浅色短副标题紧随其下",
        "object_interaction": "道具与商品保持真实接触，不遮挡主体",
    }
    return ReplicaSpec.model_validate(
        {
            "reference_image": str(reference),
            "source_category": "家居花瓶",
            "target_category": "厨房杯具",
            "analysis": {
                "visual_schema": visual,
                "scene": scene,
                "layout": layout,
                "copywriting_style": "利益点短句；源图出现竞品销量99999，仅记录不迁移",
                "information_order": "先主体，后卖点，再行动提示",
            },
            "adaptations": [
                {
                    "dimension": "产品表现",
                    "action": "adapt",
                    "reference_observation": "花瓶和装饰花材",
                    "target_decision": "换为用户杯具，突出真实杯口及杯身",
                    "reason": "适配杯具的使用认知，不能照搬花瓶结构",
                }
            ],
            "frames": [
                {
                    "panel_id": "hero",
                    "purpose": "单图风格适配",
                    "visual_schema": visual,
                    "scene": scene,
                    "layout": layout,
                    "textual_contents": {"title": "陶瓷杯", "subtitle": "陶瓷材质"},
                    "fact_ids": ["material"],
                }
            ],
            "prompt_target": "gemini-nano-banana-2.1",
        }
    )


def assessment(status="pass"):
    criteria = (
        "product_fidelity",
        "style_fidelity",
        "category_fit",
        "layout_and_lighting",
        "text_accuracy",
        "factual_accuracy",
    )
    return ReplicaAssessment.model_validate(
        {
            k: {
                "status": status,
                "evidence": f"Agent对实际生成图的{k}观察记录",
                "correction": "" if status == "pass" else "核对实图并修订对应控制维度",
            }
            for k in criteria
        }
    )


class ReplicaTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.reference = self.root / "参考.png"
        self.product = self.root / "产品.png"
        self.reference.write_bytes(png("goldenrod"))
        self.product.write_bytes(png("blue"))
        self.settings = Settings(api_key="replica-test-not-real", output_dir=self.root / "output")
        self.queue = TaskQueue(self.settings)
        self.queue.storage.provider.render = AsyncMock(return_value=[decode_image(png("green"))])
        self.addAsyncCleanup(self.queue.close)
        self.design = DesignService(self.queue)

    def brief(self, **updates):
        data = {
            "kind": "main",
            "product_name": "陶瓷杯",
            "platform": "用户指定平台1:1图",
            "audience": "厨房杯具购买者",
            "objective": "展示真实材质和设计",
            "product_images": [str(self.product)],
            "visual_observations": "蓝色陶瓷杯，真实杯身与杯口",
            "facts": [
                {
                    "fact_id": "material",
                    "label": "陶瓷材质",
                    "value": "杯身为陶瓷",
                    "source": "用户核实资料",
                    "category": "material",
                }
            ],
            "reference_choice": "skip",
            "reference_reason": "普通设计测试默认值",
            "replica": spec_for(self.reference),
        }
        data.update(updates)
        return DesignBrief.model_validate(data)

    async def plan(self, design_id="replica", **updates):
        return await self.design.plan(design_id, 0, self.brief(**updates), [])

    def args(self, record):
        return record.design_id, record.revision, record.digest

    async def render(self, record):
        self.design.approve(*self.args(record), True, "用户确认当前复刻方案")
        await self.design.submit(*self.args(record), [record.panels[0].panel_id], True)
        page = await self.queue.wait(
            "ecommerce-design",
            record.design_id,
            [f"r{record.revision}-{record.panels[0].panel_id}"],
            5,
        )
        self.assertEqual(page.tasks[0].status, "succeeded")
        return page.tasks[0]

    async def test_complete_format_source_target_separation_and_single_detail(self):
        record = await self.plan(kind="detail")
        self.assertEqual(len(record.panels), 1)
        result = export_replica(self.design, "replica", None, ["hero"])
        text = result.items[0].prompt_markdown
        validate(result.model_dump(mode="json"), ReplicaExport.model_json_schema())
        for title in (
            "# Visual Schema",
            ">## Aesthetic Style",
            ">## Graphics Structure",
            ">## Visual Representation of Product",
            "# Scene Configuration",
            ">## Color Palette",
            ">## Optical Vibe",
            ">## Rendering Details",
            "# Layout Configuration",
            ">## Objects Composition",
            ">## Text Arrangment",
            ">## Interaction between Objects",
            "# Textual Contents",
            ">## Title",
            ">## Subtile",
            ">## Other Textual Contents",
        ):
            self.assertIn(title, text)
        self.assertNotIn("# Logical Structure", text)
        self.assertIn("蓝色陶瓷杯", text)
        self.assertNotIn("竞品销量99999", text)
        self.assertEqual(result.execution_model, "gemini-nano-banana-2.1")
        self.assertEqual(result.aspect_ratio, "1:1")
        self.assertIn("画幅比例：1:1", text)
        self.queue.storage.provider.render.assert_not_awaited()

    async def test_optional_logic_and_actual_resolution_routing(self):
        data = spec_for(self.reference).model_dump()
        data["frames"][0]["logical_structure"] = {
            "design_logic": "真实商品解决收纳需求",
            "narrative_order": "主体到材质到选择",
            "visual_flow": "从上到下",
        }
        await self.plan(replica=data, resolution={"width": 2048, "height": 2048})
        exported = export_replica(self.design, "replica", 1, ["hero"])
        self.assertIn("# Logical Structure", exported.items[0].prompt_markdown)
        self.assertIn(">## Visual Flow", exported.items[0].prompt_markdown)
        self.assertEqual(exported.execution_model, "gemini-nano-banana-2.1-2k")
        self.assertEqual(exported.resolution.width, 2048)
        self.assertIn("用户像素需求：2048x2048", exported.items[0].prompt_markdown)

    async def test_replica_targets_all_three_actual_model_families(self):
        for index, (model, api, endpoint) in enumerate(
            (
                ("gemini-3.1-flash-lite-image", "gemini", "generateContent"),
                ("nano-banana-pro", "dalle", "edits"),
                ("gemini-nano-banana-2.1", "dalle", "generations"),
            )
        ):
            record = await self.plan(design_id=f"family{index}", model=model)
            exported = export_replica(self.design, record.design_id, None, ["hero"])
            self.assertEqual((exported.prompt_target, exported.execution_model), (model, model))
            self.assertEqual((exported.api_format, exported.endpoint), (api, endpoint))
            self.assertEqual(record.brief.replica.prompt_target, model)

    async def test_exact_role_order_and_same_prompt_reaches_existing_queue(self):
        record = await self.plan()
        exported = export_replica(self.design, "replica", None, ["hero"])
        roles = exported.items[0].input_images
        self.assertEqual([r.role for r in roles], ["style_only", "product_identity"])
        self.assertEqual(roles[0].sha256, hashlib.sha256(self.reference.read_bytes()).hexdigest())
        self.assertEqual(roles[1].sha256, hashlib.sha256(self.product.read_bytes()).hexdigest())
        self.reference.unlink()
        self.product.unlink()
        await self.render(record)
        await self.design.submit(*self.args(record), ["hero"], True)
        self.queue.storage.provider.render.assert_awaited_once()
        task = self.queue.storage.provider.render.await_args.args[0]
        self.assertEqual(task.prompt, exported.items[0].prompt_markdown)
        self.assertEqual(task.reference_images, [r.path for r in roles])

    async def test_unresolved_questions_block_export_approval_and_submission(self):
        spec = spec_for(self.reference).model_copy(update={"open_questions": ["请核实产品材质"]})
        record = await self.plan(replica=spec)
        self.assertEqual(record.status, "needs_input")
        self.assertIn("请核实产品材质", record.questions)
        with self.assertRaises(BusinessError):
            self.design.approve(*self.args(record), True, "不能批准")
        with self.assertRaises(BusinessError):
            export_replica(self.design, "replica", None, ["hero"])

    async def test_cross_category_requires_actual_adaptation(self):
        spec = spec_for(self.reference).model_dump()
        spec["adaptations"][0]["action"] = "preserve"
        with self.assertRaisesRegex(BusinessError, "跨类目"):
            await self.plan(replica=spec)
        spec["target_category"] = spec["source_category"]
        self.assertEqual((await self.plan(replica=spec)).status, "draft")

    async def test_bad_images_role_collisions_and_four_product_inputs(self):
        for source in (str(self.product), "relative.png", "http://127.0.0.1/style.png"):
            spec = spec_for(self.reference).model_copy(update={"reference_image": source})
            with self.assertRaises(BusinessError):
                await self.plan(replica=spec)
        with self.assertRaisesRegex(BusinessError, "1–3"):
            await self.plan(product_images=[str(self.product)] * 4)
        self.queue.storage.provider.render.assert_not_awaited()

    async def test_structural_validation_and_unknown_fact_references(self):
        spec = spec_for(self.reference).model_dump()
        del spec["frames"][0]["scene"]["optical_vibe"]
        with self.assertRaises(ValidationError):
            ReplicaSpec.model_validate(spec)
        spec = spec_for(self.reference).model_dump()
        spec["frames"] *= 2
        with self.assertRaises(ValidationError):
            ReplicaSpec.model_validate(spec)
        spec = spec_for(self.reference).model_dump()
        spec["frames"][0]["fact_ids"] = ["competitor-claim"]
        with self.assertRaisesRegex(BusinessError, "未知事实"):
            await self.plan(replica=spec)
        spec["frames"][0]["fact_ids"] = []
        with self.assertRaisesRegex(BusinessError, "fact_ids"):
            await self.plan(replica=spec)

    async def test_sku_uses_own_image_and_observation(self):
        red = self.root / "red.png"
        red.write_bytes(png("red"))
        spec = spec_for(self.reference).model_dump()
        first = spec["frames"][0]
        first["sku_id"] = "blue"
        spec["frames"].append({**first, "panel_id": "red", "sku_id": "red"})
        variants = [
            SkuVariant(
                sku_id="blue",
                label="蓝杯",
                attributes={"颜色": "蓝"},
                product_images=[str(self.product)],
                visual_observations="蓝色实物",
                fact_ids=["material"],
            ),
            SkuVariant(
                sku_id="red",
                label="红杯",
                attributes={"颜色": "红"},
                product_images=[str(red)],
                visual_observations="红色实物",
                fact_ids=["material"],
            ),
        ]
        record = await self.plan(kind="sku", variants=variants, replica=spec)
        self.assertEqual(len(record.panels), 2)
        exported = export_replica(self.design, "replica", None, ["hero", "red"])
        self.assertIn("红色实物", exported.items[1].prompt_markdown)
        self.assertNotIn("蓝色陶瓷杯", exported.items[1].prompt_markdown)
        self.assertNotEqual(
            exported.items[0].input_images[1].path, exported.items[1].input_images[1].path
        )
        spec["frames"][1]["sku_id"] = "blue"
        with self.assertRaisesRegex(BusinessError, "一版本一图"):
            await self.design.plan(
                "bad-sku", 0, self.brief(kind="sku", variants=variants, replica=spec), []
            )

    async def test_source_snapshot_tamper_and_model_constraints(self):
        record = await self.plan()
        self.design.approve(*self.args(record), True, "用户确认")
        Path(record.panels[0].reference_images[0]).write_bytes(png("purple"))
        with self.assertRaisesRegex(BusinessError, "更改"):
            await self.design.submit(*self.args(record), ["hero"], True)
        with self.assertRaises(ValidationError):
            self.brief(model="unknown-image-model")
        self.queue.storage.provider.render.assert_not_awaited()

    async def test_revision_invalidates_confirmation_and_disallows_ordinary_edits(self):
        record = await self.plan()
        self.design.approve(*self.args(record), True, "用户确认")
        spec = spec_for(self.reference).model_dump()
        spec["frames"][0]["textual_contents"]["title"] = "真实陶瓷材质"
        spec["iteration_notes"] = "依据上次实际图片修正文案层级"
        revised = await self.design.plan("replica", 1, self.brief(replica=spec), [])
        self.assertIsNone(revised.approved_digest)
        with self.assertRaisesRegex(BusinessError, "过期"):
            await self.design.submit(*self.args(record), ["hero"], True)
        with self.assertRaisesRegex(BusinessError, "普通edits"):
            await self.design.plan(
                "replica",
                2,
                self.brief(replica=spec),
                [
                    PanelCopy(
                        panel_id="hero",
                        headline="改稿",
                        visual="实物",
                        layout="留白",
                        fact_ids=["material"],
                    )
                ],
            )

    async def test_full_review_is_persisted_without_more_generation(self):
        record = await self.plan()
        task = await self.render(record)
        review = review_replica(
            self.design, "replica", 1, task.task_id, task.images[0].sha256, assessment()
        )
        self.assertEqual(review.outcome, "agent_passed")
        self.assertEqual(review.reviewer, "host_agent")
        self.assertIn("用户", review.next_steps[-1])
        reopened = DesignService(TaskQueue(self.settings)).progress("replica")
        self.assertEqual(reopened.replica_reviews, [review])
        self.assertEqual(reopened.design.digest, record.digest)
        self.queue.storage.provider.render.assert_awaited_once()

    async def test_review_revise_uncertain_and_evidence_requirements(self):
        record = await self.plan()
        task = await self.render(record)
        for status, outcome in (("revise", "revise"), ("uncertain", "needs_user_review")):
            review = review_replica(
                self.design, "replica", 1, task.task_id, task.images[0].sha256, assessment(status)
            )
            self.assertEqual(review.outcome, outcome)
            self.assertIn("不自动重画", review.next_steps[-1])
        invalid = assessment().model_dump()
        invalid["text_accuracy"] = {"status": "uncertain", "evidence": "小字不可辨识"}
        with self.assertRaises(ValidationError):
            ReplicaAssessment.model_validate(invalid)
        self.queue.storage.provider.render.assert_awaited_once()

    async def test_reviews_reject_other_revision_hash_and_changed_output(self):
        record = await self.plan()
        task = await self.render(record)
        for task_id, digest in (("r2-hero", task.images[0].sha256), (task.task_id, "0" * 64)):
            with self.assertRaises(BusinessError):
                review_replica(self.design, "replica", 1, task_id, digest, assessment())
        Path(task.images[0].path).write_bytes(png("purple"))
        with self.assertRaisesRegex(BusinessError, "变化"):
            review_replica(
                self.design, "replica", 1, task.task_id, task.images[0].sha256, assessment()
            )

    async def test_tools_resource_prompt_and_real_stdio_loop_both_protocols(self):
        fixture = Path(__file__).with_name("stdio_task_fixture.py")
        for mode in ("auto", "legacy"):
            root = self.root / mode
            root.mkdir()
            (root / "release-gate").touch()
            transport = StdioTransport(
                command=sys.executable, args=[str(fixture), str(root)], keep_alive=False
            )
            async with Client(transport, mode=mode, timeout=15, init_timeout=15) as client:
                resource = await client.read_resource("nanobanana://reference-replication")
                self.assertIn("iterate_or_stop", resource[0].text)
                prompt = await client.get_prompt(
                    "reference_replication_brief", {"product_name": "杯", "target_category": "杯具"}
                )
                self.assertTrue(prompt.messages)
                brief = self.brief().model_dump()
                replica = brief.pop("replica")
                planned = await client.call_tool(
                    "plan_reference_replica",
                    {"design_id": "stdio-replica", "brief": brief, "replica": replica},
                )
                record = planned.structured_content
                self.assertEqual(record["brief"]["reference_choice"], "provided")
                exported = await client.call_tool(
                    "export_reference_replica",
                    {"design_id": "stdio-replica", "panel_ids": ["hero"]},
                )
                self.assertIn(
                    "# Visual Schema", exported.structured_content["items"][0]["prompt_markdown"]
                )
                args = {
                    "design_id": "stdio-replica",
                    "revision": record["revision"],
                    "digest": record["digest"],
                }
                denied = await client.call_tool(
                    "submit_ecommerce_design",
                    {**args, "panel_ids": ["hero"], "authorize_paid": True},
                    raise_on_error=False,
                )
                self.assertTrue(denied.is_error)
                await client.call_tool(
                    "confirm_ecommerce_design",
                    {**args, "confirmation_note": "用户确认", "user_confirmed": True},
                )
                await client.call_tool(
                    "submit_ecommerce_design",
                    {**args, "panel_ids": ["hero"], "authorize_paid": True},
                )
                done = await client.call_tool(
                    "wait_image_tasks",
                    {
                        "checkpointer": "ecommerce-design",
                        "thread_id": "stdio-replica",
                        "task_ids": ["r1-hero"],
                        "wait_timeout_seconds": 5,
                    },
                )
                image = done.structured_content["tasks"][0]["images"][0]
                inspected = await client.call_tool(
                    "inspect_design_images", {"images": [image["path"]]}
                )
                self.assertEqual(
                    inspected.structured_content["images"][0]["sha256"], image["sha256"]
                )
                reviewed = await client.call_tool(
                    "review_reference_replica",
                    {
                        "design_id": "stdio-replica",
                        "revision": 1,
                        "task_id": "r1-hero",
                        "image_sha256": image["sha256"],
                        "assessment": assessment().model_dump(),
                    },
                )
                self.assertEqual(reviewed.structured_content["outcome"], "agent_passed")
                progress = await client.call_tool(
                    "get_ecommerce_design", {"design_id": "stdio-replica"}
                )
                self.assertEqual(len(progress.structured_content["replica_reviews"]), 1)
                self.assertEqual(len(list((root / "fake-posts").iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
