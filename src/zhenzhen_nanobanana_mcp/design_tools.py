"""MCP surface for the guided ecommerce design workflow."""

import json
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools.base import ToolResult
from mcp import types
from pydantic import Field

from .config import BusinessError
from .design import DesignService
from .design_models import (
    DesignBrief,
    DesignProgress,
    DesignRecord,
    Digest,
    ImageInspection,
    InspectedImage,
    Images,
    PanelCopy,
    Revision,
    Text,
)
from .media import MIB
from .models import RequestId, TaskPage
from .tasks import TaskQueue
from .limits import MAX_BATCH_ITEMS


def register_design_tools(mcp: FastMCP, queue: TaskQueue):
    design = DesignService(queue)

    @mcp.tool(
        output_schema=ImageInspection.model_json_schema(),
        annotations={"readOnlyHint": True, "openWorldHint": True},
    )
    async def inspect_design_images(images: Annotated[Images, Field(min_length=1)]) -> ToolResult:
        """免费读取1–4张产品图/对标图并以MCP图片内容交给Host观察，不调用视觉或绘图模型。

        输入本机绝对路径或公开图片直链；沿用格式/大小/公网URL检查，不抓网页。
        Host应记录可见外形、配色、比例、布局；不得从图推断性能参数或照搬竞品事实。
        """
        content: list[types.TextContent | types.ImageContent] = []
        inspected = []
        total = 0
        try:
            for source in images:
                media = await design.storage.loader.load(source)
                total += len(media.data)
                if total > 40 * MIB:
                    raise BusinessError("图片合计不可超过40 MiB。")
                info = InspectedImage(
                    source=source, width=media.width, height=media.height, sha256=media.digest
                )
                inspected.append(info)
                content.append(types.TextContent(type="text", text=info.model_dump_json()))
                content.append(
                    types.ImageContent(type="image", data=media.b64, mime_type=media.mime)
                )
            return ToolResult(
                content=content, structured_content=ImageInspection(images=inspected).model_dump()
            )
        except BusinessError as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(annotations={"readOnlyHint": False, "openWorldHint": True})
    async def plan_ecommerce_design(
        design_id: RequestId,
        brief: DesignBrief,
        expected_revision: Annotated[int, Field(strict=True, ge=0)] = 0,
        edits: Annotated[list[PanelCopy], Field(max_length=48)] | None = None,
    ) -> DesignRecord:
        """免费保存主图/详情页/SKU设计底稿；按需求→参考→文案与排版研讨推进，不出图。

        新建expected_revision=0，修改须传当前revision、完整brief和可选逐图edits；每次产生新版本，需重新确认。
        先查看产品实图，填写visual_observations和有source的已核实facts；对标填写benchmarks，
        或向用户索取参考，或记录用户明确不用参考的理由。缺信息返回needs_input和questions。
        main默认5张、detail默认10屏、sku一版本一图且需各自实图。尺寸/比例按平台与用户确认，非自动合规。
        返回逐图标题、正文、事实引用、主体与排版；先展示用户研讨，不得把底稿视为批准。
        """
        try:
            return await design.plan(design_id, expected_revision, brief, edits or [])
        except BusinessError as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(annotations={"readOnlyHint": False, "openWorldHint": False, "idempotentHint": True})
    def confirm_ecommerce_design(
        design_id: RequestId,
        revision: Revision,
        digest: Digest,
        confirmation_note: Text,
        user_confirmed: Annotated[bool, Field(strict=True)] = False,
    ) -> DesignRecord:
        """仅在用户明确确认当前商品事实、逐图文案与排版后记录方案确认；不收费、不提交。

        必须传本次展示的revision/digest及用户确认说明，user_confirmed=True；旧稿/缺信息拒绝。
        Host不能自行替用户确认，任何改稿须再次展示并确认。收费授权另在提交时提供。
        """
        try:
            return design.approve(design_id, revision, digest, user_confirmed, confirmation_note)
        except BusinessError as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        output_schema=TaskPage.model_json_schema(),
        annotations={
            "readOnlyHint": False,
            "openWorldHint": True,
            "idempotentHint": True,
            "destructiveHint": False,
        },
    )
    async def submit_ecommerce_design(
        design_id: RequestId,
        revision: Revision,
        digest: Digest,
        panel_ids: Annotated[list[RequestId], Field(min_length=1, max_length=MAX_BATCH_ITEMS)],
        authorize_paid: Annotated[bool, Field(strict=True)] = False,
    ) -> ToolResult:
        """将已确认方案中明确选择的1–20图提交后台收费绘图；需用户明确收费授权。

        所有图使用批准版本的商品图副本、文案、排版和模型；当前revision/digest必须匹配。
        固定映射checkpointer=ecommerce-design、thread_id=design_id、task_id=r{revision}-{panel_id}，
        可分批提交超过20图的方案；重复同图复用原任务，不新增收费请求。
        用get_ecommerce_design获取落盘路径；wait_image_tasks等待原任务。失败/超时勿换设计编号重提。
        """
        from .server import task_response

        try:
            return task_response(
                await design.submit(design_id, revision, digest, panel_ids, authorize_paid)
            )
        except BusinessError as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        output_schema=DesignProgress.model_json_schema(),
        annotations={"readOnlyHint": True, "openWorldHint": False, "idempotentHint": True},
    )
    def get_ecommerce_design(design_id: RequestId, revision: Revision | None = None) -> ToolResult:
        """只读查询当前/历史版本、待补信息、未提交图片及已有任务/图片绝对路径，不重新出图。

        已落盘结果包含尺寸、字节数、SHA256；失败/unknown/cancelled返回isError并保留所有结果。
        没有任务或queued/running不代表设计已完成。继续等待/取消用返回的原队列三元组。
        """
        try:
            progress = design.progress(design_id, revision)
            data = progress.model_dump(mode="json")
            return ToolResult(
                content=[types.TextContent(type="text", text=json.dumps(data, ensure_ascii=False))],
                structured_content=data,
                is_error=any(
                    t.status in ("failed", "unknown", "cancelled") for t in progress.tasks
                ),
            )
        except BusinessError as exc:
            raise ToolError(str(exc)) from exc
