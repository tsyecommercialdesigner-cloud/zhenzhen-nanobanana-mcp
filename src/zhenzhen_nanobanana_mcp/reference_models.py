"""Shared art direction and typed target compositions for upgraded replication."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from .models import Contract
from .replica_models import (
    AdaptationDecision,
    Category,
    Detail,
    ImageRole,
    LayoutConfiguration,
    LogicalStructure,
    ReferenceAnalysis,
)
from .suite_models import (
    CompiledSuitePrompt,
    DrawingPrompt,
    ProductSuiteSpec,
    SuiteCanvases,
    SuiteFrame,
    SuiteStyle,
)


class ReferenceComposition(Contract):
    graphics_structure: Detail
    product_representation: Detail
    layout: LayoutConfiguration


class ReferenceReplicaFrame(SuiteFrame):
    composition: ReferenceComposition = Field(
        description="Agent适配后的目标构图，不是源图参数或逐图风格覆盖。"
    )
    logical_structure: LogicalStructure | None = None

    def content_frame(self) -> SuiteFrame:
        return SuiteFrame.model_validate(self.model_dump(include=set(SuiteFrame.model_fields)))


class ReferenceReplicaSpec(Contract):
    template_version: Literal[1] = 1
    scope: Literal["series", "product_suite"] = "series"
    reference_image: Annotated[str, Field(min_length=1, max_length=4096)]
    source_category: Category
    target_category: Category
    analysis: ReferenceAnalysis
    adaptations: list[AdaptationDecision] = Field(min_length=1, max_length=15)
    style: SuiteStyle = Field(
        description="Agent从参考拆解并适配到实际商品的唯一共享风格；须明确提供，不能逐图重设。"
    )
    canvases: SuiteCanvases = Field(default_factory=SuiteCanvases)
    frames: list[ReferenceReplicaFrame] = Field(min_length=1, max_length=71)
    open_questions: list[Detail] = Field(default_factory=list, max_length=10)
    iteration_notes: Annotated[str, Field(max_length=1500)] = ""

    @model_validator(mode="after")
    def coherent_plan(self):
        ids = [f.panel_id for f in self.frames]
        if len(ids) != len(set(ids)):
            raise ValueError("复刻panel_id必须唯一。")
        dimensions = [a.dimension for a in self.adaptations]
        if len(dimensions) != len(set(dimensions)):
            raise ValueError("同一适配维度不可重复，请合并为明确决定。")
        if self.source_category.casefold() != self.target_category.casefold() and all(
            a.action == "preserve" for a in self.adaptations
        ):
            raise ValueError("跨类目复刻至少需一项adapt/replace/omit决定，不能全部照搬。")
        if self.scope == "product_suite":
            ProductSuiteSpec(
                style=self.style,
                canvases=self.canvases,
                frames=[f.content_frame() for f in self.frames],
            )
        else:
            kinds = {f.kind for f in self.frames}
            if len(kinds) != 1:
                raise ValueError("series须为同一种图片；三类整套使用product_suite。")
            limit = {"main": 8, "detail": 15, "sku": 48}[self.frames[0].kind]
            if len(self.frames) > limit:
                raise ValueError(f"本类复刻最多{limit}张。")
        return self


class ReplicaDrawingPrompt(Contract):
    product: DrawingPrompt
    source_category: Category
    target_category: Category
    adaptations: list[AdaptationDecision] = Field(min_length=1, max_length=15)
    composition: ReferenceComposition
    logical_structure: LogicalStructure | None = None


class ValidatedReferencePrompt(CompiledSuitePrompt):
    input_images: list[ImageRole] = Field(min_length=2, max_length=4)
