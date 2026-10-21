"""Agent-authored reference analysis and target-image control dimensions."""

from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from .models import ApiFormat, AspectRatio, Contract, ModelName, RequestId, Resolution

Detail = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=700)]
Category = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class VisualSchema(Contract):
    aesthetic_style: Detail
    graphics_structure: Detail
    product_representation: Detail


class SceneConfiguration(Contract):
    color_palette: Detail
    optical_vibe: Detail
    rendering_details: Detail


class LayoutConfiguration(Contract):
    objects_composition: Detail
    text_arrangement: Detail
    object_interaction: Detail


class LogicalStructure(Contract):
    design_logic: Detail
    narrative_order: Detail
    visual_flow: Detail


class ReferenceAnalysis(Contract):
    visual_schema: VisualSchema
    scene: SceneConfiguration
    layout: LayoutConfiguration
    copywriting_style: Detail = Field(description="分析行文习惯，不直接复制竞品宣称。")
    information_order: Detail
    observational_limits: list[Detail] = Field(default_factory=list, max_length=8)


class AdaptationDecision(Contract):
    dimension: Category
    action: Literal["preserve", "adapt", "replace", "omit"]
    reference_observation: Detail
    target_decision: Detail
    reason: Detail = Field(description="解释为何适合目标类目、受众与本商品。")


class TextualContents(Contract):
    title: Annotated[str, Field(max_length=80)]
    subtitle: Annotated[str, Field(max_length=300)] = ""
    other: list[Annotated[str, StringConstraints(min_length=1, max_length=160)]] = Field(
        default_factory=list, max_length=8
    )

    @model_validator(mode="after")
    def bounded_body(self):
        if len("\n".join([self.subtitle, *self.other]).strip()) > 600:
            raise ValueError("副标题与其他文案合计不得超过600字。")
        return self


class ReplicaFrame(Contract):
    panel_id: RequestId
    purpose: Category
    sku_id: RequestId | None = None
    visual_schema: VisualSchema
    scene: SceneConfiguration
    layout: LayoutConfiguration
    textual_contents: TextualContents
    logical_structure: LogicalStructure | None = None
    fact_ids: list[RequestId] = Field(default_factory=list, max_length=20)


class ReplicaSpec(Contract):
    reference_image: Annotated[str, StringConstraints(min_length=1, max_length=4096)]
    source_category: Category
    target_category: Category
    analysis: ReferenceAnalysis
    adaptations: list[AdaptationDecision] = Field(min_length=1, max_length=15)
    frames: list[ReplicaFrame] = Field(min_length=1, max_length=48)
    prompt_target: Category = Field(
        default="gemini-nano-banana-2.1",
        description="兼容字段；服务器按brief.model与resolution强制归一为本服务实际执行模型，无需填写外部模型。",
    )
    open_questions: list[Detail] = Field(default_factory=list, max_length=10)
    iteration_notes: Annotated[str, Field(max_length=1500)] = Field(
        default="", description="Agent根据上轮实际图片与用户意见制定的修改；不是自动重画授权。"
    )

    @model_validator(mode="after")
    def unique_panels(self):
        ids = [f.panel_id for f in self.frames]
        if len(ids) != len(set(ids)):
            raise ValueError("复刻方案的panel_id必须唯一。")
        return self


class ImageRole(Contract):
    image_number: int
    role: Literal["style_only", "product_identity"]
    path: str
    sha256: Sha256


class ReplicaExportItem(Contract):
    panel_id: str
    prompt_markdown: str
    input_images: list[ImageRole]


class ReplicaExport(Contract):
    design_id: str
    revision: int
    digest: Sha256
    prompt_target: str
    execution_model: ModelName
    api_format: ApiFormat
    endpoint: str
    aspect_ratio: AspectRatio
    resolution: Resolution | None = None
    items: list[ReplicaExportItem]
    notes: list[str]


class ReviewCriterion(Contract):
    status: Literal["pass", "revise", "uncertain"]
    evidence: Detail = Field(description="Agent查看实际生成图后的具体可见证据，不填推测。")
    correction: Annotated[str, Field(max_length=700)] = ""

    @model_validator(mode="after")
    def explain_next_step(self):
        if self.status != "pass" and not self.correction.strip():
            raise ValueError("未通过或不确定项必须给出修正或澄清动作。")
        return self


class ReplicaAssessment(Contract):
    product_fidelity: ReviewCriterion
    style_fidelity: ReviewCriterion
    category_fit: ReviewCriterion
    layout_and_lighting: ReviewCriterion
    text_accuracy: ReviewCriterion
    factual_accuracy: ReviewCriterion


class ReplicaReview(Contract):
    review_id: int
    design_id: str
    revision: int
    task_id: str
    image_sha256: Sha256
    assessment: ReplicaAssessment
    outcome: Literal["agent_passed", "revise", "needs_user_review"]
    next_steps: list[str]
    reviewer: Literal["host_agent"] = "host_agent"
