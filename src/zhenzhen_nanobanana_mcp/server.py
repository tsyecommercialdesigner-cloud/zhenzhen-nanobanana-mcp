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
from .models import (
    MODELS,
    AspectRatio,
    BatchResult,
    ImagePlan,
    ImageTasks,
    TaskIds,
    TaskPage,
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
        is_error=any(task.status in ("failed", "unknown", "cancelled") for task in result.tasks),
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
            "参考图直接使用本机可读取的图片绝对路径或公开HTTP/HTTPS图片URL；"
            "没有文件目录白名单，无需复制到input，也可直接编辑已生成的图片。"
            "submit_image_tasks立即返回并在后台收费出图，最多12项，默认并发4。"
            "按(checkpointer,thread_id,task_id)唯一幂等；用get_image_tasks查询，不同步等待。"
            "failed/unknown/取消后先查询，禁止自动更换编号重试。"
        ),
    )

    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
    def list_models() -> ModelCatalog:
        """列出七个模型（含 2k/4k 变体）、API 格式、访问目录与限制；不联网、不返回密钥。"""
        return ModelCatalog(
            models=list(MODELS),
            api_formats=["dalle", "chat", "gemini"],
            default_model="gemini-nano-banana-2.1",
            default_api_format="dalle",
            max_batch_items=12,
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
        count: Annotated[int, Field(ge=1, le=12)] = 1,
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
        """批量登记1–12个后台图像任务并立即返回，不等待绘图/下载（会在后台收费）。

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

    @mcp.resource("nanobanana://capabilities")
    def capabilities() -> str:
        """模型能力、边界与真实联调状态。"""
        return json.dumps(
            {
                "models": list(MODELS),
                "api_formats": ["dalle", "chat", "gemini"],
                "capabilities": {model: FORMAT_SUPPORT[base_model(model)] for model in MODELS},
                "operations": ["submit", "query", "cancel", "legacy_batch_query"],
                "identity": ["checkpointer", "thread_id", "task_id"],
                "async_tasks": True,
                "transport": "stdio",
                "upstream_verified": False,
                "max_batch_items": 12,
            },
            ensure_ascii=False,
        )

    @mcp.prompt()
    def ecommerce_brief(product_name: str) -> str:
        """收集家居日用品绘图所需的事实，规划后由用户决定是否出图。"""
        return (
            f"为商品 {product_name} 制作电商图片。先确认平台、真实卖点、材质、尺寸、"
            "参考图路径和图片中文案；调用 plan_ecommerce_images 审阅主图或详情计划。"
            "实际出图使用submit_image_tasks，给每项稳定task_id及同一checkpointer/thread_id；"
            "稍后get_image_tasks查询，不等待整批完成。不得捏造产品事实。"
        )

    return mcp
