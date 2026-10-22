"""Discoverable suite recipes, workflow prompts and validated prompt construction."""

import json
from typing import Annotated, Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from .config import BusinessError
from .design import DesignService
from .design_models import DesignBrief, DesignRecord, Revision
from .models import Contract, RequestId
from .suite import compile_suite, style_digest
from .suite_models import CompiledSuitePrompt, ProductSuiteSpec, Sha256, SuiteStyle
from .suite_templates import TEMPLATES_V1, WORKFLOW, style_presets, suite_resource
from .tasks import TaskQueue


class ProductSuiteBrief(DesignBrief):
    kind: Literal["main"] = "main"
    suite: ProductSuiteSpec
    replica: None = None
    reference_replica: None = None


class SuitePromptExport(Contract):
    design: DesignRecord
    style_digest: Sha256
    prompts: list[CompiledSuitePrompt]


def export_suite(record: DesignRecord) -> SuitePromptExport:
    if not record.brief.suite:
        raise BusinessError("该版本不是整套图方案，请使用对应设计工具。")
    return SuitePromptExport(
        design=record,
        style_digest=style_digest(record.brief.suite.style),
        prompts=[compile_suite(record, p) for p in record.panels],
    )


def register_suite_tools(mcp: FastMCP, queue: TaskQueue):
    design = DesignService(queue)

    @mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True})
    async def build_product_suite_prompts(
        design_id: RequestId,
        brief: ProductSuiteBrief,
        expected_revision: Annotated[int, Field(strict=True, ge=0)] = 0,
    ) -> SuitePromptExport:
        """免费构造同一商品主图+详情+SKU整套绘图提示词，Pydantic校验后保存新版本；不收费出图。

        先读nanobanana://templates/product-suite和styles/main/detail/sku，或product_suite_brief。
        Agent先观察实图、分析需求/对标、策划文案和构图。suite.style是全套唯一风格来源：
        颜色角色、画面/光线、文案语气/术语、字体家族/字重、排版层级比例；brief.style不参与整套编译。
        frames选择模板并填写本图内容，不接受逐图style覆盖。1–8张主图、8–15屏详情、每个SKU一图。
        主图一图一信息；详情opening→solution→产品/证据→closing；SKU需真实独立实图/相同属性字段。
        画幅按suite.canvases分类型设置；未设分辨率继承brief.resolution；仅使用list_models中三类模型。
        返回design/统一style_digest/逐图task.prompt及执行参数，缺需求返回needs_input和questions，无提示词。
        修改传当前expected_revision和完整brief，旧确认失效；不要用普通edits修改整套。
        展示并研讨→confirm_ecommerce_design锁定版本→明确收费授权后submit_ecommerce_design。
        实际提交从保存的类型化方案重新校验编译，与返回提示词相同；不回填或替换task.prompt。
        """
        try:
            return export_suite(await design.plan(design_id, expected_revision, brief, []))
        except BusinessError as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False})
    def export_product_suite_prompts(
        design_id: RequestId,
        revision: Revision | None = None,
    ) -> SuitePromptExport:
        """只读重新导出整套的已校验提示词、统一风格摘要和实际执行配置；不改版本、不确认、不出图。

        默认当前版，可查看历史版；历史版不能用于当前提交。与实际执行共用DrawingPrompt/ImageTask校验和编译器。
        prompts.task给出商品冻结图及SHA256、三模型实际选档、接口与分类型画幅；不得绕过确认/收费流程直接回填通用出图入口。
        """
        try:
            return export_suite(design.get(design_id, revision))
        except BusinessError as exc:
            raise ToolError(str(exc)) from exc

    @mcp.resource("nanobanana://templates/product-suite", mime_type="application/json")
    def product_suite_templates() -> str:
        """整套组图模板入口、Agent循环、字段schema、资源导航和执行边界。"""
        return json.dumps(suite_resource(), ensure_ascii=False)

    @mcp.resource("nanobanana://templates/styles", mime_type="application/json")
    def product_suite_styles() -> str:
        """自然简洁、理性精确、温暖生活三套可编辑共享规范及Pydantic schema。"""
        return json.dumps(
            {
                "schema": SuiteStyle.model_json_schema(),
                "presets": style_presets(),
                "instruction": "整款产品只选定并确认一份完整style；修改后应用全部主图、详情与SKU。保持商品固有色，字体授权和视觉效果需实图核对。",
            },
            ensure_ascii=False,
        )

    def recipes(kind: str) -> str:
        return json.dumps(
            {
                "template_version": 1,
                "kind": kind,
                "templates": [t.model_dump() for t in TEMPLATES_V1 if t.kind == kind],
                "inherits": "suite.style；禁止逐图重新设置配色、字体、语气或比例",
                "workflow": WORKFLOW,
            },
            ensure_ascii=False,
        )

    @mcp.resource("nanobanana://templates/main", mime_type="application/json")
    def main_templates() -> str:
        """首图、单卖点、真实场景主图模板；一图一个信息中心。"""
        return recipes("main")

    @mcp.resource("nanobanana://templates/detail", mime_type="application/json")
    def detail_templates() -> str:
        """开篇、方案、功能、材质、尺寸、步骤、证据、收束八类详情模板及证据要求。"""
        return recipes("detail")

    @mcp.resource("nanobanana://templates/sku", mime_type="application/json")
    def sku_templates() -> str:
        """真实SKU版本模板，统一商品比例/视角/背景/文字锚点与属性顺序。"""
        return recipes("sku")

    @mcp.prompt()
    def product_suite_brief(product_name: str) -> str:
        """启动同款商品的整套主图、详情页、SKU设计，先定共享规范再构建校验提示词。"""
        return (
            f"为商品{product_name}制作主图+详情+SKU整套图。读取nanobanana://templates/product-suite及styles/main/detail/sku；Host无法读取时按以下同等指引执行。\n"
            + "\n".join(WORKFLOW)
        )

    @mcp.prompt()
    def product_suite_review(design_id: str) -> str:
        """引导Agent查看整套真实结果，按统一风格与商品事实复核；不触发绘图或自动评分。"""
        return (
            f"复核整套设计{design_id}。用get_ecommerce_design读取批准版本、原图和落盘路径，"
            "export_product_suite_prompts读取共享规范与提示。用inspect_design_images分批查看所有实际结果，"
            "并排比较主图、详情和各SKU：颜色角色/光线/背景、画面表现、字体家族/字重、标题副标题正文的比例、"
            "留白/锚点、文案语气/术语、商品身份与SKU真实属性。先核对商品再核对风格。"
            "逐图引用具体可见证据；看不清字形/缺图时标记不确定，不声称通过。数据校验不保证视觉一致或字体授权。"
            "输出差异图片、证据、应修改全套style还是单图内容及原因，向用户展示验收。"
            "若需修改，build_product_suite_prompts保存新版本，重新研讨确认和收费授权；不要自动重画。"
        )
