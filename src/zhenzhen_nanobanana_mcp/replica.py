"""Compile Agent-authored adaptations; never pretend to perform visual reasoning."""

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from .config import BusinessError
from .media import MAX_OUTPUT_BYTES
from .models import route_model, resolve_api
from .limits import MAX_BATCH_ITEMS
from .replica_models import (
    ImageRole,
    ReplicaAssessment,
    ReplicaExport,
    ReplicaExportItem,
    ReplicaReview,
)

if TYPE_CHECKING:
    from .design import DesignService
    from .design_models import DesignBrief, DesignPanel, DesignRecord


def replica_panels(brief: "DesignBrief", bindings: dict[str, str]) -> list["DesignPanel"]:
    from .design_models import DesignPanel

    spec = brief.replica
    assert spec is not None
    if spec.source_category.casefold() != spec.target_category.casefold() and all(
        d.action == "preserve" for d in spec.adaptations
    ):
        raise BusinessError("跨类目复刻必须说明至少一项适配、替换或舍弃，不能全部照搬。")
    skus = {s.sku_id: s for s in brief.variants}
    if brief.kind == "sku":
        ids = [f.sku_id for f in spec.frames]
        if len(ids) != len(set(ids)) or set(ids) != set(skus):
            raise BusinessError("SKU复刻必须一版本一图，每个frame绑定明确且不重复的sku_id。")
    panels = []
    for index, frame in enumerate(spec.frames):
        if brief.kind != "sku" and frame.sku_id is not None:
            raise BusinessError("只有SKU方案可以指定sku_id。")
        sku = skus.get(frame.sku_id) if frame.sku_id else None
        sources = sku.product_images if sku else brief.product_images
        if not 1 <= len(sources) <= 3:
            raise BusinessError("复刻每图需1–3张本商品实图，加上1张风格图最多4张。")
        if spec.reference_image in sources or any(
            bindings[s] == bindings[spec.reference_image] for s in sources
        ):
            raise BusinessError("风格参考和商品实图必须明确区分，不能使用同一张图片。")
        allowed = set(sku.fact_ids) if sku else {f.fact_id for f in brief.facts}
        if not set(frame.fact_ids) <= allowed:
            raise BusinessError("复刻文案引用了未知事实或不属于本SKU的事实。")
        copy = frame.textual_contents
        if (
            (copy.title.strip() or copy.subtitle.strip() or copy.other)
            and not frame.fact_ids
            and sku is None
        ):
            raise BusinessError("复刻商品文案须关联已核实的本商品fact_ids。")
        panels.append(
            DesignPanel(
                panel_id=frame.panel_id,
                order=index + 1,
                purpose=frame.purpose,
                headline=copy.title,
                body="\n".join([copy.subtitle, *copy.other]).strip(),
                visual=frame.visual_schema.product_representation,
                layout=frame.layout.text_arrangement,
                fact_ids=frame.fact_ids,
                sku_id=frame.sku_id,
                reference_images=[bindings[spec.reference_image], *[bindings[s] for s in sources]],
            )
        )
    return panels


def compile_replica(record: "DesignRecord", panel: "DesignPanel") -> str:
    brief = record.brief
    spec = brief.replica
    assert spec is not None
    frame = next(f for f in spec.frames if f.panel_id == panel.panel_id)
    sku = next((s for s in brief.variants if s.sku_id == panel.sku_id), None)
    appearance = (
        (sku.visual_observations or "以本SKU实图和真实属性为准")
        if sku
        else brief.visual_observations
    )
    facts = (
        "；".join(
            f"{f.fact_id}：{f.label}，{f.value}" for f in brief.facts if f.fact_id in frame.fact_ids
        )
        or "仅按商品实图/列明的SKU属性，不添加性能声明"
    )
    decisions = "；".join(
        f"{d.dimension}[{d.action}]：{d.target_decision}（{d.reason}）" for d in spec.adaptations
    )
    product = (
        f"{frame.visual_schema.product_representation}。本商品：{brief.product_name}；实图观察：{appearance}。"
        f"图1仅为风格/构图/表达逻辑参考，图2至图{len(panel.reference_images)}为本商品身份依据。"
        "高度保持图1的美学、构图、光感和信息表达方式，商品主体必须换为本商品真实外形、比例、颜色、材质、标志及实际配件；"
        "不得把图1的商品外观、品牌、参数、价格或证言当成本商品信息。"
        f"本商品已核实事实：{facts}。"
        + (f"本SKU属性：{json.dumps(sku.attributes, ensure_ascii=False)}。" if sku else "")
        + f"源类目：{spec.source_category}；目标类目：{spec.target_category}；适配决定：{decisions}。"
        + f"业务目标：{brief.objective}；平台：{brief.platform}；受众：{brief.audience}。"
        + f"本图目标：{frame.purpose}；系列顺序：{panel.order}；画幅比例：{brief.aspect_ratio}。"
        + (
            f"用户像素需求：{brief.resolution.width}x{brief.resolution.height}，此为需求而非实际像素保证。"
            if brief.resolution
            else ""
        )
        + f"用户要求：{brief.requirements or '无额外要求'}。"
        + "不添加未核实的性能、认证、促销、赠品或数值对比。无文字字段时不要生成文字。"
    )

    def section(title, fields):
        return "# " + title + "\n" + "\n\n".join(f">## {name}\n{value}" for name, value in fields)

    result = [
        section(
            "Visual Schema",
            [
                ("Aesthetic Style", frame.visual_schema.aesthetic_style),
                ("Graphics Structure", frame.visual_schema.graphics_structure),
                ("Visual Representation of Product", product),
            ],
        ),
        section(
            "Scene Configuration",
            [
                ("Color Palette", frame.scene.color_palette),
                ("Optical Vibe", frame.scene.optical_vibe),
                ("Rendering Details", frame.scene.rendering_details),
            ],
        ),
        section(
            "Layout Configuration",
            [
                ("Objects Composition", frame.layout.objects_composition),
                ("Text Arrangment", frame.layout.text_arrangement),
                ("Interaction between Objects", frame.layout.object_interaction),
            ],
        ),
        section(
            "Textual Contents",
            [
                ("Title", frame.textual_contents.title or "不添加文字"),
                ("Subtile", frame.textual_contents.subtitle or "不添加文字"),
                ("Other Textual Contents", "\n".join(frame.textual_contents.other) or "不添加文字"),
            ],
        ),
    ]
    if frame.logical_structure:
        logic = frame.logical_structure
        result.append(
            section(
                "Logical Structure",
                [
                    ("Design Logic", logic.design_logic),
                    ("Narrative Order", logic.narrative_order),
                    ("Visual Flow", logic.visual_flow),
                ],
            )
        )
    text = "\n\n".join(result)
    if len(text) > 8000:
        raise BusinessError("复刻提示词超过8000字，请精简控制描述或适配理由，不会静默截断。")
    return text


def export_replica(
    design: "DesignService", design_id: str, revision: int | None, panel_ids: list[str]
) -> ReplicaExport:
    record = design.get(design_id, revision)
    spec = record.brief.replica
    if spec is None or record.questions:
        raise BusinessError("没有完整的竞品复刻方案，请先完成分析和目标方案。")
    panels = {p.panel_id: p for p in record.panels}
    if (
        not 1 <= len(panel_ids) <= MAX_BATCH_ITEMS
        or len(set(panel_ids)) != len(panel_ids)
        or not set(panel_ids) <= panels.keys()
    ):
        raise BusinessError("请明确选择1–20个不同且存在的panel_id。")
    assets = {a.path: a for a in record.assets}
    items = []
    for key in panel_ids:
        panel = panels[key]
        items.append(
            ReplicaExportItem(
                panel_id=key,
                prompt_markdown=compile_replica(record, panel),
                input_images=[
                    ImageRole(
                        image_number=i + 1,
                        role="style_only" if i == 0 else "product_identity",
                        path=p,
                        sha256=assets[p].sha256,
                    )
                    for i, p in enumerate(panel.reference_images)
                ],
            )
        )
    actual_model = route_model(record.brief.model, record.brief.resolution)
    api, endpoint = resolve_api(actual_model, record.brief.api_format, record.brief.endpoint, True)
    return ReplicaExport(
        design_id=record.design_id,
        revision=record.revision,
        digest=record.digest,
        prompt_target=actual_model,
        execution_model=actual_model,
        api_format=api,
        endpoint=endpoint,
        aspect_ratio=record.brief.aspect_ratio,
        resolution=record.brief.resolution,
        items=items,
        notes=[
            "提示词与实际队列使用同一编译器；须按input_images的顺序附图，单独复制文本不能替代图像输入。",
            "提示适配当前三个模型家族；prompt_target和execution_model均为实际分档模型，api_format/endpoint按同一能力矩阵解析。",
            "导出不收费，也不代表用户已批准方案。执行需confirm_ecommerce_design和本次收费授权。",
            "视觉/类目分析来自Host，不是服务器独立识图或对风格相似度的保证。",
        ],
    )


def review_replica(
    design: "DesignService",
    design_id: str,
    revision: int,
    task_id: str,
    image_sha256: str,
    assessment: ReplicaAssessment,
) -> ReplicaReview:
    record = design.get(design_id, revision)
    if (record.brief.replica is None and record.brief.reference_replica is None) or task_id not in {
        f"r{revision}-{p.panel_id}" for p in record.panels
    }:
        raise BusinessError("复核任务不属于该复刻方案版本。")
    page = design.queue.get("ecommerce-design", design_id, [task_id])
    image = next((i for t in page.tasks for i in t.images if i.sha256 == image_sha256), None)
    if image is None:
        raise BusinessError("未找到该任务已落盘且匹配哈希的图片，不能提交复核。")
    path = design.storage.safe_output(Path(image.path))
    try:
        with path.open("rb") as stream:
            data = stream.read(MAX_OUTPUT_BYTES + 1)
    except OSError:
        raise BusinessError("生成图片不可读取，不能保存复核。") from None
    if hashlib.sha256(data).hexdigest() != image_sha256:
        raise BusinessError("生成图片已变化，请重新获取和观察实际图片。")
    criteria = list(assessment.model_dump().values())
    outcome: Literal["agent_passed", "revise", "needs_user_review"] = (
        "revise"
        if any(c["status"] == "revise" for c in criteria)
        else "needs_user_review"
        if any(c["status"] == "uncertain" for c in criteria)
        else "agent_passed"
    )
    steps = [str(c["correction"]) for c in criteria if c["status"] != "pass"]
    steps.append(
        "向用户展示实际图片和复核证据，由用户判断是否验收。"
        if outcome == "agent_passed"
        else "Agent补齐证据或改写目标frames/适配决定，按当前版本重新规划；改稿后重新确认和授权，不自动重画。"
    )
    review = ReplicaReview(
        review_id=0,
        design_id=design_id,
        revision=revision,
        task_id=task_id,
        image_sha256=image_sha256,
        assessment=assessment,
        outcome=outcome,
        next_steps=steps,
    )
    with design.connect(write=True) as db:
        cursor = db.execute(
            "INSERT INTO replica_reviews(design_id,revision,record) VALUES (?,?,?)",
            (design_id, revision, review.model_dump_json()),
        )
        review.review_id = cursor.lastrowid
        db.execute(
            "UPDATE replica_reviews SET record=? WHERE review_id=?",
            (review.model_dump_json(), review.review_id),
        )
    return review
