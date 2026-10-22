"""Reviewable ecommerce briefs, storyboards and approval receipts."""

from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from .replica_models import ReplicaReview, ReplicaSpec
from .suite_models import ProductSuiteSpec
from .reference_models import ReferenceReplicaSpec

from .models import (
    ApiChoice,
    AspectRatio,
    Contract,
    Endpoint,
    ModelName,
    RequestId,
    Resolution,
    TaskResult,
)

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
ImageLocation = Annotated[str, StringConstraints(min_length=1, max_length=4096)]
Images = Annotated[list[ImageLocation], Field(max_length=4)]
DesignKind = Literal["main", "detail", "sku"]
Revision = Annotated[int, Field(strict=True, ge=1)]
Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class ProductFact(Contract):
    fact_id: RequestId
    label: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
    value: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    source: Text = Field(description="用户核实的信息来源；不以竞品参数作为本商品事实。")
    category: Literal["benefit", "material", "size", "usage", "trust", "offer"] = "benefit"
    pain_point: Annotated[str, Field(max_length=160)] = ""


class DesignStyle(Contract):
    palette: Text = "干净中性背景，使用与商品协调的品牌色"
    typography: Text = "统一有合法使用权的无衬线字体；主标题粗、副文案细，移动端可读"
    layout: Text = "主体完整，信息层级清晰，标题与标签固定位置，适度留白"
    tone: Text = "简洁真实，以用户易懂的语言表达"


class BenchmarkReview(Contract):
    source: Text = Field(description="对标来源链接/图片路径/用户提供的说明，不由本工具抓取网页。")
    visual_focus: Text
    hierarchy: Text
    copy_approach: Text
    strengths: Text
    weaknesses: Text
    adaptation: Text = Field(description="仅借鉴构图、节奏、色调等；不复制品牌、参数或承诺。")


class SkuVariant(Contract):
    sku_id: RequestId
    label: Label
    attributes: dict[Label, Label] = Field(min_length=1, max_length=8)
    product_images: Annotated[Images, Field(min_length=1)]
    visual_observations: Annotated[str, Field(max_length=2000)] = Field(
        default="", description="可选，本SKU实图的独立外观观察；不要沿用其他版本颜色或配置。"
    )
    fact_ids: list[RequestId] = Field(default_factory=list, max_length=10)


class DesignBrief(Contract):
    kind: DesignKind
    product_name: Label
    platform: Annotated[str, Field(max_length=200)] = ""
    audience: Annotated[str, Field(max_length=500)] = ""
    objective: Annotated[str, Field(max_length=500)] = ""
    product_images: Images = Field(default_factory=list)
    visual_observations: Annotated[str, Field(max_length=2000)] = Field(
        default="", description="Host 查看实图后的外形/比例/颜色/材质描述，不含猜测的性能。"
    )
    facts: list[ProductFact] = Field(default_factory=list, max_length=30)
    style: DesignStyle = Field(default_factory=DesignStyle)
    main_count: int = Field(default=5, strict=True, ge=1, le=8)
    detail_count: int = Field(default=10, strict=True, ge=8, le=15)
    variants: list[SkuVariant] = Field(default_factory=list, max_length=48)
    aspect_ratio: AspectRatio = "1:1"
    resolution: Resolution | None = None
    model: ModelName = "gemini-nano-banana-2.1"
    api_format: ApiChoice = "auto"
    endpoint: Endpoint = "auto"
    requirements: Annotated[str, Field(max_length=2000)] = ""
    reference_choice: Literal["request", "provided", "skip"] = "request"
    reference_reason: Annotated[str, Field(max_length=1000)] = ""
    benchmarks: list[BenchmarkReview] = Field(default_factory=list, max_length=6)
    replica: ReplicaSpec | None = Field(
        default=None, description="竞品图复刻的Agent分析和逐图目标方案；普通设计无需填写。"
    )
    suite: ProductSuiteSpec | None = Field(
        default=None,
        description="同一商品的主图+详情+SKU共享规范和逐图方案；由整套提示词工具构建。",
    )
    reference_replica: ReferenceReplicaSpec | None = Field(
        default=None,
        description="新版共享规范竞品复刻；单图/同类系列或主图+详情+SKU整套，与旧replica/suite互斥。",
    )

    @model_validator(mode="after")
    def unique_ids(self):
        ids = [f.fact_id for f in self.facts]
        skus = [v.sku_id for v in self.variants]
        if len(set(ids)) != len(ids) or len(set(skus)) != len(skus):
            raise ValueError("fact_id 和 sku_id 各自必须唯一。")
        for variant in self.variants:
            if not set(variant.fact_ids) <= set(ids):
                raise ValueError("SKU 引用了未知的 fact_id。")
        if (
            sum(value is not None for value in (self.suite, self.replica, self.reference_replica))
            > 1
        ):
            raise ValueError("suite、replica、reference_replica只能选择一个方案来源。")
        if self.suite or self.reference_replica:
            shared = self.suite or self.reference_replica
            assert shared is not None
            complete = bool(
                self.suite
                or (self.reference_replica and self.reference_replica.scope == "product_suite")
            )
            if complete and self.kind != "main":
                raise ValueError("整套方案的brief.kind须为main；对标分析可记录在benchmarks。")
            if not complete and any(f.kind != self.kind for f in shared.frames):
                raise ValueError("同类复刻的frames.kind须与brief.kind一致。")
            for frame in shared.frames:
                allowed = set(ids)
                if frame.kind == "sku" and self.variants:
                    variant = next((v for v in self.variants if v.sku_id == frame.sku_id), None)
                    if variant is None:
                        raise ValueError("整套SKU图引用了未知的sku_id。")
                    allowed = set(variant.fact_ids)
                if not set(frame.fact_ids) <= allowed:
                    raise ValueError("整套文案引用了未知事实或其他SKU的事实。")
            bindings = [f.sku_id for f in shared.frames if f.kind == "sku"]
            uses_skus = complete or self.kind == "sku"
            if len(set(bindings)) != len(bindings) or (
                uses_skus and skus and set(bindings) != set(skus)
            ):
                raise ValueError("整套SKU图必须与实际variants一一对应，不可重复或遗漏。")
            if (
                uses_skus
                and self.variants
                and any(
                    set(v.attributes) != set(self.variants[0].attributes) for v in self.variants
                )
            ):
                raise ValueError("同组SKU需提供相同属性字段，真实缺项须先向用户核实。")
        return self


class PanelCopy(Contract):
    panel_id: RequestId
    headline: Annotated[str, Field(max_length=80)] = Field(
        description="可为空；白底无字图需标题和正文均为空。"
    )
    body: Annotated[str, Field(max_length=600)] = ""
    visual: Text
    layout: Text
    fact_ids: list[RequestId] = Field(default_factory=list, max_length=30)


class DesignPanel(PanelCopy):
    order: int
    purpose: str
    sku_id: str | None = None
    reference_images: list[str]


class DesignAsset(Contract):
    source: str
    path: str
    sha256: Digest
    mime_type: str
    width: int
    height: int


class InspectedImage(Contract):
    source: str
    width: int
    height: int
    sha256: Digest


class ImageInspection(Contract):
    images: list[InspectedImage]


class DesignRecord(Contract):
    reference_hash_binding: bool = False
    design_id: RequestId
    revision: Revision
    digest: Digest
    status: Literal["needs_input", "draft", "approved"]
    brief: DesignBrief
    questions: list[str]
    panels: list[DesignPanel]
    assets: list[DesignAsset]
    approved_digest: str | None = None
    confirmation_note: str | None = None
    notes: list[str]


class DesignProgress(Contract):
    design: DesignRecord
    checkpointer: str = "ecommerce-design"
    thread_id: str
    tasks: list[TaskResult]
    unsubmitted_panel_ids: list[str]
    replica_reviews: list[ReplicaReview] = Field(default_factory=list)
