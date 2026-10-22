"""MCP registration. stdout belongs exclusively to the protocol."""

import json
from contextlib import asynccontextmanager
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools.base import ToolResult
from mcp import types
from pydantic import Field

from . import __version__
from .config import BusinessError, Settings
from .design_tools import register_design_tools
from .replica_tools import register_replica_tools
from .suite_tools import register_suite_tools
from .reference_tools import register_reference_tools
from .models import (
    MODELS,
    AspectRatio,
    BatchResult,
    ImagePlan,
    ImageTasks,
    TaskIds,
    TaskPage,
    TaskWaitResult,
    WaitTimeout,
    ScopeId,
    FORMAT_SUPPORT,
    base_model,
    ModelCatalog,
    NonEmpty,
    RequestId,
    Resolution,
    Scene,
)
from .planning import build_plan
from .service import BatchService
from .tasks import TaskQueue
from .limits import MAX_BATCH_ITEMS


def batch_response(result: BatchResult) -> ToolResult:
    data = result.model_dump()
    return ToolResult(
        content=[types.TextContent(type="text", text=json.dumps(data, ensure_ascii=False))],
        structured_content=data,
        is_error=result.status != "succeeded",
    )


def task_response(result: TaskPage) -> ToolResult:
    data = result.model_dump(mode="json")
    return ToolResult(
        content=[types.TextContent(type="text", text=json.dumps(data, ensure_ascii=False))],
        structured_content=data,
        is_error=(isinstance(result, TaskWaitResult) and result.wait_timed_out)
        or any(task.status in ("failed", "unknown", "cancelled") for task in result.tasks),
    )


def create_server(
    settings: Settings | None = None,
    service: BatchService | None = None,
    queue: TaskQueue | None = None,
) -> FastMCP:
    settings = settings or Settings.from_env()
    service = service or BatchService(settings)
    queue = queue or TaskQueue(settings, service.provider, service.loader)

    @asynccontextmanager
    async def lifespan(server):
        await queue.start()
        try:
            yield {}
        finally:
            await queue.close()

    mcp = FastMCP(
        "zhenzhen-nanobanana-mcp",
        version=__version__,
        mask_error_details=True,
        strict_input_validation=True,
        lifespan=lifespan,
        instructions=(
            "用于家居日用百货电商绘图。先检查模型和配置，再规划并核实商品事实。"
            "主图、详情页和SKU设计用inspect_design_images查看实图，先分析需求、索取参考或拆解对标，"
            "再用plan_ecommerce_design策划文案和排版，与用户研讨。缺信息先追问；不得自行填写未知事实。"
            "同款整套图先读nanobanana://templates/product-suite及styles/main/detail/sku或product_suite_brief；"
            "build_product_suite_prompts使用一份共享颜色/画面/文案/字体/层级规范构造已校验提示，"
            "export_product_suite_prompts导出审阅，确认后仍用原设计提交工具，实际提交共用校验编译器。"
            "展示当前版本后取得用户确认，调用confirm_ecommerce_design；取得收费授权才submit_ecommerce_design。"
            "get_ecommerce_design读取方案和落盘结果；不得用通用出图入口绕过用户的方案确认与收费授权。"
            "竞品图复刻先读reference_replica_brief或nanobanana://templates/reference-replica、reference-analysis，Agent自行观察/逆向/适配。"
            "build_reference_replica_prompts构造共享颜色/画面/文案/字体/层级规范下的单图、同类系列或整套，"
            "export_validated_reference_replica审阅，实际提交使用同一校验编译器。"
            "旧plan_reference_replica/export_reference_replica兼容历史replica；两种方案均复用确认和提交。"
            "结果必须看实图后review_reference_replica记录证据，未通过不自动重画。"
            "参考图直接使用本机可读取的图片绝对路径或公开HTTP/HTTPS图片URL；"
            "没有文件目录白名单，无需复制到input，也可直接编辑已生成的图片。"
            "submit_image_tasks立即返回并在后台收费出图，最多20项，默认全局并发5。"
            "需要同步出图时用generate_images，等待本组完成并落盘；已有任务用wait_image_tasks等待。"
            "所有入口按(checkpointer,thread_id,task_id)共享幂等；get_image_tasks立即查询。"
            "等待超时/取消仅结束本次等待，不取消后台任务；用原身份查询，禁止自动换编号重提。"
            "failed/unknown/取消后先查询，禁止自动更换编号重试。"
            "recovering表示按已保存响应恢复图片，不重新绘图；safe_to_retry为真时可用retry_image_tasks保留原幂等键重试安全阶段。"
            "文件校验失败需要repair_files显式修复，原损坏文件会保留；没有响应的未知收费状态不能重发。"
        ),
    )

    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
    def list_models() -> ModelCatalog:
        """列出三个模型家族及已有2k/4k变体（共7个标识）、API格式、目录与限制；不联网、不返回密钥。"""
        return ModelCatalog(
            models=list(MODELS),
            api_formats=["dalle", "chat", "gemini"],
            default_model="gemini-nano-banana-2.1",
            default_api_format="dalle",
            max_batch_items=MAX_BATCH_ITEMS,
            max_reference_images=4,
            concurrency_per_process=settings.concurrency,
            max_pending_tasks=settings.max_pending_tasks,
            capabilities={model: FORMAT_SUPPORT[base_model(model)] for model in MODELS},
            supported_endpoints={
                model: (
                    ["generations", "edits"]
                    if base_model(model) == "nano-banana-pro"
                    else ["generations"]
                    if base_model(model) == "gemini-nano-banana-2.1"
                    else []
                )
                for model in MODELS
            },
            input_dirs=[],
            local_file_access="readable_files",
            output_dir=str(settings.output_dir.resolve()),
            api_key_configured=bool(settings.api_key),
        )

    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
    def plan_ecommerce_images(
        product_name: Annotated[NonEmpty, Field(max_length=200)],
        selling_points: Annotated[
            list[Annotated[NonEmpty, Field(max_length=500)]], Field(max_length=20)
        ],
        scene: Scene = "main",
        count: Annotated[int, Field(ge=1, le=MAX_BATCH_ITEMS)] = 1,
        aspect_ratio: AspectRatio = "1:1",
        reference_images: Annotated[list[str], Field(max_length=4)] | None = None,
        requirements: Annotated[str, Field(max_length=2000)] = "",
        copy_text: Annotated[str, Field(max_length=1000)] = "",
        resolution: Resolution | None = None,
    ) -> ImagePlan:
        """免费生成可审阅的主图/详情页/场景/海报绘图计划。

        scene: main 主图；detail 详情模块；scene 家居场景；poster 营销海报。
        selling_points: 已核实事实，可为空列表；不自动编造商品信息。
        count: 图片项数，详情页推荐 6 项；比例由用户决定。
        reference_images: 原样传入计划，真正出图前才读取/下载并校验。
        resolution: 可选显式 width/height 像素尺寸，原样传入每项用于模型路由。
        """
        return build_plan(
            product_name,
            selling_points,
            scene,
            count,
            aspect_ratio,
            reference_images or [],
            requirements,
            copy_text,
            resolution,
        )

    @mcp.tool(
        output_schema=TaskPage.model_json_schema(),
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def submit_image_tasks(
        checkpointer: ScopeId, thread_id: ScopeId, tasks: ImageTasks
    ) -> ToolResult:
        """批量登记1–20个后台图像任务并立即返回，不等待绘图/下载（会在后台收费）。

        每项task_id在checkpointer/thread_id内唯一且稳定，同内容复用；任何冲突全批不新增。
        每项可选model/api_format(auto)/endpoint(auto)；变体按显式resolution路由。
        Flash-lite仅Gemini/Chat；nano-banana-pro仅DALL·E；gemini-nano仅DALL·E Generations/Gemini/Chat。
        查询get_image_tasks；queued/preparing/running是正常状态，unknown不能盲目重交。
        MCP进程关闭时未发送任务可在重启后继续，已可能发送任务不自动重试。
        """
        try:
            return task_response(await queue.submit(checkpointer, thread_id, tasks))
        except BusinessError as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        output_schema=TaskWaitResult.model_json_schema(),
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def generate_images(
        checkpointer: ScopeId,
        thread_id: ScopeId,
        tasks: ImageTasks,
        wait_timeout_seconds: WaitTimeout = 600,
    ) -> ToolResult:
        """同步生成/编辑1–20项（会收费）：等待本组全部终态且成功图片落盘后返回。

        任务参数与submit_image_tasks相同，支持同样的模型、比例和本机/URL参考图。
        与异步入口共用三元组、防重、队列和并发限额；相同任务不重复提交。
        wait_timeout_seconds默认600，严格整数1–1200，包含排队时间。
        全部成功才isError=false；失败保留所有结果。等待到期返回isError=true、
        wait_timed_out=true及当前状态，不取消后台任务。Host超时/取消也不保证停止上游。
        请保留原三元组，用get_image_tasks查询或wait_image_tasks继续等，不换编号重交。
        """
        try:
            submitted = await queue.submit(checkpointer, thread_id, tasks)
            result = await queue.wait(
                checkpointer, thread_id, [task.task_id for task in tasks], wait_timeout_seconds
            )
            reused = {task.task_id: task.reused for task in submitted.tasks}
            for task in result.tasks:
                task.reused = reused[task.task_id]
            return task_response(result)
        except BusinessError as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        output_schema=TaskWaitResult.model_json_schema(),
        annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False},
    )
    async def wait_image_tasks(
        checkpointer: ScopeId,
        thread_id: ScopeId,
        task_ids: TaskIds,
        wait_timeout_seconds: WaitTimeout = 600,
    ) -> ToolResult:
        """等待1–100个已有任务，不提交、不重新出图；所有指定任务终态后返回结果。

        task_ids必填且不重复；不存在或错误命名空间报错。
        等待时限默认600秒，严格整数1–1200；到期isError=true、wait_timed_out=true，
        保留当前状态和已完成图片，后台继续。客户端取消只停止本次等待。
        终态failed/unknown/cancelled是isError；查询get_image_tasks不等待。
        """
        try:
            return task_response(
                await queue.wait(checkpointer, thread_id, task_ids, wait_timeout_seconds)
            )
        except BusinessError as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        output_schema=TaskPage.model_json_schema(),
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def retry_image_tasks(
        checkpointer: ScopeId,
        thread_id: ScopeId,
        task_ids: Annotated[list[ScopeId], Field(min_length=1, max_length=MAX_BATCH_ITEMS)],
        repair_files: Annotated[bool, Field(strict=True)] = False,
    ) -> ToolResult:
        """按原幂等键重排1–20项安全阶段；不会重发结果不明的收费请求。

        safe_to_retry表示存在原响应可恢复，或确定未发送；成功/进行中的项直接复用。
        有响应时只重新下载/落盘；连接前失败可按同一供应商Idempotency-Key重试。
        文件校验失败需repair_files=True，保留损坏文件后从原响应修复，绝不重画修复。
        任一不安全项使本批全不重排；POST已可能发送且无检查点时先核对费用，禁止换ID盲目重提。
        """
        try:
            return task_response(await queue.retry(checkpointer, thread_id, task_ids, repair_files))
        except BusinessError as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        output_schema=TaskPage.model_json_schema(),
        annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False},
    )
    def get_image_tasks(
        checkpointer: ScopeId,
        thread_id: ScopeId,
        task_ids: TaskIds | None = None,
        cursor: Annotated[int, Field(ge=0)] = 0,
        limit: Annotated[int, Field(ge=1, le=100)] = 100,
    ) -> ToolResult:
        """查询持久任务与图片绝对路径，不重新提交上游。可按task_ids筛选或用next_cursor分页。

        queued/preparing/running正常返回；failed/unknown/cancelled返回isError并保留全部状态。
        checkpointer是本地SQLite字符串命名空间，不是路径、LangGraph对象或认证凭据。
        """
        try:
            return task_response(queue.get(checkpointer, thread_id, task_ids, cursor, limit))
        except BusinessError as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        output_schema=TaskPage.model_json_schema(),
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def cancel_image_tasks(
        checkpointer: ScopeId, thread_id: ScopeId, task_ids: TaskIds
    ) -> ToolResult:
        """取消指定任务；queued/preparing不发图，running只停止本地等待并标unknown，不保证远端停止/退款。"""
        try:
            return task_response(queue.cancel(checkpointer, thread_id, task_ids))
        except BusinessError as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        output_schema=BatchResult.model_json_schema(),
        annotations={
            "readOnlyHint": True,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def get_batch_result(request_id: RequestId) -> ToolResult:
        """读取已登记批次及保存路径，不调用上游、不重发请求；未完成/失败返回 isError。"""
        try:
            return batch_response(service.get(request_id))
        except BusinessError as exc:
            raise ToolError(str(exc)) from exc

    register_design_tools(mcp, queue)
    register_replica_tools(mcp, queue)
    register_suite_tools(mcp, queue)
    register_reference_tools(mcp, queue)

    @mcp.resource("nanobanana://capabilities")
    def capabilities() -> str:
        """模型能力、边界与真实联调状态。"""
        return json.dumps(
            {
                "models": list(MODELS),
                "api_formats": ["dalle", "chat", "gemini"],
                "capabilities": {model: FORMAT_SUPPORT[base_model(model)] for model in MODELS},
                "operations": [
                    "submit",
                    "generate_sync",
                    "wait",
                    "query",
                    "cancel",
                    "safe_retry",
                    "legacy_batch_query",
                ],
                "identity": ["checkpointer", "thread_id", "task_id"],
                "async_tasks": True,
                "sync_generation": True,
                "max_wait_timeout_seconds": 1200,
                "transport": "stdio",
                "upstream_verified": False,
                "max_batch_items": MAX_BATCH_ITEMS,
                "design_workflow": {
                    "kinds": ["main", "detail", "sku"],
                    "stages": [
                        "requirements",
                        "references",
                        "copy_and_layout",
                        "user_confirmation",
                        "paid_submission",
                        "saved_results",
                    ],
                    "vision_by_host": True,
                    "automatic_search": False,
                    "versioned_approval": True,
                    "immutable_product_references": True,
                },
                "reference_replication": {
                    "workflow_resource": "nanobanana://reference-replication",
                    "prompt": "reference_replication_brief",
                    "agent_visual_reasoning": True,
                    "automatic_generation_loop": False,
                    "prompt_export": True,
                    "model_families": list(FORMAT_SUPPORT),
                    "shared_style_builder": "build_reference_replica_prompts",
                    "validated_export": "export_validated_reference_replica",
                    "template_resource": "nanobanana://templates/reference-replica",
                    "scopes": ["series", "product_suite"],
                },
                "product_suite": {
                    "resource": "nanobanana://templates/product-suite",
                    "builder": "build_product_suite_prompts",
                    "export": "export_product_suite_prompts",
                    "prompts": ["product_suite_brief", "product_suite_review"],
                    "shared_style": [
                        "palette",
                        "aesthetic",
                        "lighting",
                        "copywriting",
                        "typography",
                        "hierarchy",
                    ],
                    "validated_submission": True,
                    "visual_consistency_verified": False,
                },
                "safe_retries": {
                    "attempts_per_stage": settings.safe_attempts,
                    "retry_delay_seconds": settings.retry_delay,
                    "response_checkpoint": True,
                    "retry_tool": "retry_image_tasks",
                    "ambiguous_post_replay": False,
                },
            },
            ensure_ascii=False,
        )

    @mcp.prompt()
    def ecommerce_brief(product_name: str) -> str:
        """收集家居日用品绘图所需的事实，规划后由用户决定是否出图。"""
        return (
            f"为商品 {product_name} 制作电商图片。先确认平台、真实卖点、材质、尺寸、"
            "参考图路径和图片中文案。主图一图一个核心卖点；详情按痛点—解决方案—产品展示—信任—购买引导；"
            "SKU统一模板、一图一个版本，需各版本实图和真实属性。"
            "同款整套图使用product_suite_brief及build_product_suite_prompts，共享一份配色/画面/文案/字体/层级比例规范。"
            "先inspect_design_images观察实图，向用户索取对标或记录不用参考的决定，拆解视觉焦点、层级与优缺点。"
            "调用plan_ecommerce_design补齐需求，策划逐图文案及排版，展示用户研讨；"
            "取得用户明确确认后用confirm_ecommerce_design锁定revision/digest，收费授权后submit_ecommerce_design。"
            "get_ecommerce_design获取方案、状态和已落盘路径。plan_ecommerce_images保留为简易无状态计划。"
            "本设计流程通过submit_ecommerce_design登记后，已有任务用wait_image_tasks等待或"
            "get_image_tasks查询。等待超时勿换编号重提。不得捏造产品事实。"
        )

    return mcp
