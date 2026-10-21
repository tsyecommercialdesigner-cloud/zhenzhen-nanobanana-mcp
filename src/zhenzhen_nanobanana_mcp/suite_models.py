"""Typed, shared art direction and individual pages of one product's image suite."""

from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator, model_validator

from .models import AspectRatio, Contract, ImageTask, RequestId, Resolution

Short = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
Direction = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
HexColor = Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$")]
Kind = Literal["main", "detail", "sku"]
TemplateId = Literal[
    "main.hero",
    "main.benefit",
    "main.scene",
    "detail.opening",
    "detail.solution",
    "detail.feature",
    "detail.material",
    "detail.size",
    "detail.usage",
    "detail.proof",
    "detail.closing",
    "sku.variant",
]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class SuitePalette(Contract):
    primary: HexColor = "#245A50"
    secondary: HexColor = "#DDE9E2"
    accent: HexColor = "#B55A30"
    background: HexColor = "#FAF8F2"
    text: HexColor = "#202B28"
    usage: Direction = (
        "背景用background，标题与标签用primary，正文用text，强调仅少量accent；不改变商品固有颜色。"
    )

    @field_validator("primary", "secondary", "accent", "background", "text")
    @classmethod
    def normalize_hex(cls, value: str) -> str:
        return value.upper()


class SuiteTypography(Contract):
    font_family: Short = "Noto Sans CJK SC"
    fallback_families: list[Short] = Field(
        default_factory=lambda: ["思源黑体", "sans-serif"], max_length=4
    )
    title_weight: Literal[500, 600, 700, 800] = 700
    subtitle_weight: Literal[400, 500, 600] = 500
    body_weight: Literal[400, 500] = 400
    alignment: Literal["left", "center"] = "left"
    font_rights_note: Direction = "发布前核实所用实际字体的授权；模型生成字形仍需人工检查。"

    @model_validator(mode="after")
    def ordered_weights(self):
        if not self.title_weight >= self.subtitle_weight >= self.body_weight:
            raise ValueError("字重层级必须满足标题>=副标题>=正文。")
        return self


class SuiteHierarchy(Contract):
    """Ratios refer to canvas width, so different aspect ratios share a type scale."""

    title_pct: float = Field(default=5.0, ge=3, le=9, allow_inf_nan=False)
    subtitle_pct: float = Field(default=3.2, ge=2, le=7, allow_inf_nan=False)
    body_pct: float = Field(default=2.4, ge=1.5, le=5, allow_inf_nan=False)
    safe_margin_pct: float = Field(default=5.0, ge=2, le=12, allow_inf_nan=False)
    product_scale_pct: float = Field(default=65.0, ge=40, le=80, allow_inf_nan=False)
    title_area_pct: float = Field(default=20.0, ge=12, le=30, allow_inf_nan=False)
    spacing_unit_pct: float = Field(default=2.0, ge=1, le=4, allow_inf_nan=False)

    @model_validator(mode="after")
    def ordered_scale(self):
        if not self.title_pct > self.subtitle_pct > self.body_pct:
            raise ValueError("字号层级必须满足title_pct > subtitle_pct > body_pct。")
        if self.product_scale_pct + 2 * self.safe_margin_pct > 100:
            raise ValueError("商品缩放比例与两侧安全边距不能超出画布。")
        return self


class SuiteCopyStyle(Contract):
    tone: Direction = "简洁、克制、真实，以用户能理解的利益点表达。"
    sentence_pattern: Direction = "短标题聚焦一个信息点，副标题解释用途，正文只补充有依据的细节。"
    terminology: dict[Short, Short] = Field(default_factory=dict, max_length=12)
    forbidden_terms: list[Short] = Field(default_factory=list, max_length=12)


class SuiteStyle(Contract):
    palette: SuitePalette = Field(default_factory=SuitePalette)
    typography: SuiteTypography = Field(default_factory=SuiteTypography)
    hierarchy: SuiteHierarchy = Field(default_factory=SuiteHierarchy)
    copywriting: SuiteCopyStyle = Field(default_factory=SuiteCopyStyle)
    aesthetic: Direction = "自然、干净的商业产品摄影，真实材质和清楚轮廓。"
    lighting: Direction = "柔和侧前方主光，统一阴影方向、反差与色温。"
    background: Direction = "干净低干扰的背景，同组使用一致的纹理语言。"
    rendering: Direction = "保留实物细节，避免塑料化、畸变和过度锐化。"


class SuiteCanvas(Contract):
    aspect_ratio: AspectRatio = "1:1"
    resolution: Resolution | None = None


class SuiteCanvases(Contract):
    main: SuiteCanvas = Field(default_factory=SuiteCanvas)
    detail: SuiteCanvas = Field(default_factory=lambda: SuiteCanvas(aspect_ratio="3:4"))
    sku: SuiteCanvas = Field(default_factory=SuiteCanvas)


class SuiteFrame(Contract):
    panel_id: RequestId
    kind: Kind
    template_id: TemplateId
    purpose: Short
    title: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)]
    subtitle: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] = ""
    body: Annotated[str, StringConstraints(strip_whitespace=True, max_length=400)] = ""
    visual: Direction = Field(
        description="本图的产品视角、场景和细节；继承全套style，不另设色系/字体/语气。"
    )
    fact_ids: list[RequestId] = Field(default_factory=list, max_length=10)
    sku_id: RequestId | None = None

    @model_validator(mode="after")
    def matches_template(self):
        if not self.template_id.startswith(self.kind + "."):
            raise ValueError("template_id必须属于本图kind。")
        if (self.kind == "sku") != (self.sku_id is not None):
            raise ValueError("SKU图必须绑定sku_id，其他图片不绑定单个SKU。")
        if len("\n".join(s for s in (self.subtitle, self.body) if s)) > 600:
            raise ValueError("副标题与正文合计不得超过600字。")
        if len(set(self.fact_ids)) != len(self.fact_ids):
            raise ValueError("fact_ids不可重复。")
        return self


class ProductSuiteSpec(Contract):
    template_version: Literal[1] = 1
    style: SuiteStyle = Field(default_factory=SuiteStyle)
    canvases: SuiteCanvases = Field(default_factory=SuiteCanvases)
    frames: list[SuiteFrame] = Field(min_length=3, max_length=71)
    open_questions: list[Direction] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def complete_suite(self):
        ids = [f.panel_id for f in self.frames]
        if len(set(ids)) != len(ids):
            raise ValueError("整套panel_id必须唯一。")
        counts = {
            kind: sum(f.kind == kind for f in self.frames) for kind in ("main", "detail", "sku")
        }
        if (
            not 1 <= counts["main"] <= 8
            or not 8 <= counts["detail"] <= 15
            or not 1 <= counts["sku"] <= 48
        ):
            raise ValueError(
                "整套需1–8张主图、8–15屏详情、1–48张SKU图；单类设计请用plan_ecommerce_design。"
            )
        details = [f.template_id for f in self.frames if f.kind == "detail"]
        stages = ["detail.opening", "detail.solution", "detail.closing"]
        if (
            details[:2] != stages[:2]
            or details[-1] != stages[-1]
            or any(details.count(s) != 1 for s in stages)
        ):
            raise ValueError("详情需按开篇、解决方案、产品/信任依据、购买引导组织。")
        return self


class DrawingPrompt(Contract):
    """Validated intermediate representation, compiled by the server, never supplied as free text."""

    product_context: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1800)
    ]
    appearance: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2200)
    ]
    facts: Annotated[str, Field(max_length=2500)]
    sku_attributes: Annotated[str, Field(max_length=1600)]
    frame: SuiteFrame
    style: SuiteStyle
    template_layout: Direction
    reference_direction: Annotated[str, Field(max_length=1200)]
    requirements: Annotated[str, Field(max_length=2000)]


class CompiledSuitePrompt(Contract):
    panel_id: RequestId
    kind: Kind
    template_id: TemplateId
    style_digest: Sha256
    execution_endpoint: str
    task: ImageTask = Field(
        description="经过DrawingPrompt与ImageTask双层校验的实际执行参数；不接收用户回填。"
    )
