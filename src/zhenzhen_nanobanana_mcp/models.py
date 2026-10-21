"""Public contracts shared by the planning and paid tools."""

from typing import Annotated, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

ModelName = Literal[
    "gemini-3.1-flash-lite-image",
    "nano-banana-pro",
    "gemini-nano-banana-2.1",
    "gemini-nano-banana-2.1-2k",
    "gemini-nano-banana-2.1-4k",
    "nano-banana-pro-2k",
    "nano-banana-pro-4k",
]
ApiFormat = Literal["dalle", "chat", "gemini"]
ApiChoice = Literal["auto", "dalle", "chat", "gemini"]
Endpoint = Literal["auto", "generations", "edits"]
AspectRatio = Literal["4:3", "3:4", "16:9", "9:16", "2:3", "3:2", "1:1", "4:5", "5:4", "21:9"]
Scene = Literal["main", "detail", "scene", "poster"]
RequestId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=8000)]
MODELS = (
    "gemini-3.1-flash-lite-image",
    "nano-banana-pro",
    "gemini-nano-banana-2.1",
    "gemini-nano-banana-2.1-2k",
    "gemini-nano-banana-2.1-4k",
    "nano-banana-pro-2k",
    "nano-banana-pro-4k",
)
FORMAT_SUPPORT = {
    "gemini-3.1-flash-lite-image": ["gemini", "chat"],
    "nano-banana-pro": ["dalle"],
    "gemini-nano-banana-2.1": ["gemini", "chat", "dalle"],
}


def base_model(model: str) -> str:
    return model.removesuffix("-2k").removesuffix("-4k")


def resolve_api(
    model: ModelName, choice: ApiChoice, endpoint: Endpoint, has_references: bool
) -> tuple[ApiFormat, str]:
    base = base_model(model)
    selected = (
        ("gemini" if base == "gemini-3.1-flash-lite-image" else "dalle")
        if choice == "auto"
        else choice
    )
    if selected not in FORMAT_SUPPORT[base]:
        raise ValueError(f"模型 {model} 不支持 {selected} 格式。")
    if selected != "dalle":
        if endpoint != "auto":
            raise ValueError("generations/edits 端点选项仅用于 dalle 格式。")
        return cast(
            ApiFormat, selected
        ), "generateContent" if selected == "gemini" else "chat/completions"
    actual = (
        ("edits" if base == "nano-banana-pro" and has_references else "generations")
        if endpoint == "auto"
        else endpoint
    )
    if actual == "edits" and base != "nano-banana-pro":
        raise ValueError(f"模型 {model} 不支持 DALL·E Edits；参考图请使用 Generations image 数组。")
    return "dalle", actual


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Resolution(Contract):
    width: int = Field(gt=0, strict=True, description="用户显式指定的宽度，单位 px。")
    height: int = Field(gt=0, strict=True, description="用户显式指定的高度，单位 px。")


def route_model(model: ModelName, resolution: Resolution | None) -> ModelName:
    if resolution is None or model == "gemini-3.1-flash-lite-image":
        return model
    base = model.removesuffix("-2k").removesuffix("-4k")
    edge = max(resolution.width, resolution.height)
    suffix = "-4k" if edge > 2048 else "-2k" if edge > 1024 else ""
    return cast(ModelName, base + suffix)


class ImageSpec(Contract):
    prompt: NonEmpty = Field(description="完整绘图/修改提示词；不自动添加平台要求。")
    aspect_ratio: AspectRatio = "1:1"
    resolution: Resolution | None = Field(
        default=None,
        description="显式像素尺寸，仅按长边选择模型：≤1024 原版，≤2048 2k，否则 4k；不改变比例或保证输出尺寸。",
    )
    reference_images: list[Annotated[str, StringConstraints(min_length=1, max_length=4096)]] = (
        Field(
            default_factory=list,
            max_length=4,
            description="本机可读取图片的绝对路径或公开 HTTP/HTTPS 图片 URL，不限制文件目录，无需搬到 input。有参考图即编辑。",
        )
    )


ImageSpecs = Annotated[list[ImageSpec], Field(min_length=1, max_length=12)]


class ImagePlan(Contract):
    product_name: str
    scene: Scene
    items: list[ImageSpec]
    notes: list[str]


class SavedImage(Contract):
    path: str
    mime_type: str
    width: int
    height: int
    bytes: int
    sha256: str


class ItemResult(Contract):
    index: int
    operation: Literal["generate", "edit"]
    actual_model: ModelName | None = Field(
        default=None, description="本项路由后的实际模型；旧记录查询时补齐。"
    )
    status: Literal["pending", "running", "succeeded", "failed", "cancelled"] = "pending"
    images: list[SavedImage] = Field(default_factory=list)
    error: str | None = None


class BatchResult(Contract):
    request_id: str
    batch_id: str
    model: ModelName
    api_format: ApiFormat
    status: Literal["running", "succeeded", "partial", "failed", "cancelled"]
    items: list[ItemResult]
    manifest_path: str
    reused: bool = False
    warning: str | None = None


class ModelCatalog(Contract):
    models: list[str]
    api_formats: list[str]
    default_model: str
    default_api_format: str
    max_batch_items: int
    max_reference_images: int
    concurrency_per_process: int = Field(
        description="兼容字段：本机配置上限；实际按共享输出目录的SQLite账本限制并发。"
    )
    concurrency_scope: Literal["shared_output_directory"] = "shared_output_directory"
    input_dirs: list[str] = Field(description="兼容字段，始终为空列表，表示没有目录白名单。")
    local_file_access: Literal["readable_files"]
    output_dir: str
    api_key_configured: bool
    upstream_verified: bool = False
    capabilities: dict[str, list[str]] = Field(default_factory=dict)
    supported_endpoints: dict[str, list[str]] = Field(default_factory=dict)
    async_tasks: bool = True
    sync_generation: bool = True
    max_wait_timeout_seconds: int = 1200
    max_pending_tasks: int = 200
    reference_input_note: str = "Gemini/Chat多模态和Generations参考图编码未在本次收费实测；nano-banana-pro仅DALL·E，Edits重复image字段。"


ScopeId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=128, pattern=r"^[^\x00-\x1f\x7f]+$"
    ),
]


class ImageTask(ImageSpec):
    task_id: ScopeId
    model: ModelName = "gemini-nano-banana-2.1"
    api_format: ApiChoice = "auto"
    endpoint: Endpoint = "auto"


ImageTasks = Annotated[list[ImageTask], Field(min_length=1, max_length=12)]
TaskIds = Annotated[list[ScopeId], Field(min_length=1, max_length=100)]
TaskState = Literal["queued", "preparing", "running", "succeeded", "failed", "unknown", "cancelled"]


class TaskResult(Contract):
    checkpointer: str
    thread_id: str
    task_id: str
    status: TaskState
    actual_model: ModelName
    api_format: ApiFormat
    endpoint: str
    images: list[SavedImage] = Field(default_factory=list)
    error: str | None = None
    created_at: float
    updated_at: float
    reused: bool = False


class TaskPage(Contract):
    checkpointer: str
    thread_id: str
    tasks: list[TaskResult]
    next_cursor: int | None = None


WaitTimeout = Annotated[int, Field(strict=True, ge=1, le=1200)]


class TaskWaitResult(TaskPage):
    wait_timed_out: bool = False
