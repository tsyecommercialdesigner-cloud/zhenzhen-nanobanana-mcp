"""Free design planning and durable review; paid work uses the existing queue."""

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from pydantic import ValidationError

from .config import BusinessError
from .design_models import (
    DesignAsset,
    DesignBrief,
    DesignPanel,
    DesignProgress,
    DesignRecord,
    PanelCopy,
    ProductFact,
)
from .media import MIB, decode_image
from .models import ImageTask, TaskPage, TaskResult, resolve_api, route_model
from .tasks import TaskQueue
from .limits import MAX_BATCH_ITEMS
from .replica import compile_replica, replica_panels
from .replica_models import ReplicaReview
from .suite import compile_suite, suite_panels
from .integrity import publish
from .reference import compile_reference, reference_panels

SCOPE = "ecommerce-design"
NOTES = [
    "免费底稿：Host 负责观察图片、理解需求、找对标或向用户索取参考、润色文案并研讨排版。",
    "未自动搜索或调用视觉模型。外观观察不能证明尺寸、性能、认证、销量或优惠。",
    "一图一个信息中心；主标题建议30字内，优先短句；每屏核心信息突出、移动端可读。",
    "商品图已冻结；竞品只借鉴构图和风格，不作为商品身份或参数来源。",
    "出图前须确认当前版本与摘要，并另行授权收费；生成后人工核对商品、文字、色调与字体版权。",
    "每项为独立图片，不自动拼长图、生成PSD或上传店铺，不保证精确像素和平台审核。",
]


def questions_for(brief: DesignBrief) -> list[str]:
    questions = []
    if brief.replica:
        questions.extend(brief.replica.open_questions)
    if brief.reference_replica:
        questions.extend(brief.reference_replica.open_questions)
        if brief.reference_replica.scope == "product_suite" and not brief.variants:
            questions.append("整套复刻需真实SKU清单、各版本自己的实图与真实属性。")
    if brief.suite:
        questions.extend(brief.suite.open_questions)
        if not brief.variants:
            questions.append("整套图需真实SKU清单、各版本实图与相同字段的真实属性。")
    for field, question in (
        (brief.platform, "用于哪个电商平台？请提供当前适用的尺寸、比例及文字限制。"),
        (brief.audience, "目标用户是谁，主要购买顾虑是什么？"),
        (brief.objective, "这组图片要解决什么业务目标，优先突出哪个信息？"),
        (brief.visual_observations, "请先查看产品实图，记录外形、颜色、比例和可见细节。"),
    ):
        if not field.strip():
            questions.append(question)
    if brief.kind != "sku" and not brief.product_images:
        questions.append("请提供至少一张本商品实图的绝对路径或公开图片直链。")
    if brief.kind != "sku" and not brief.facts:
        questions.append("请提供已核实的核心卖点和信息来源；不从图片猜测性能。")
    if brief.kind == "sku" and not brief.variants:
        questions.append("请提供SKU清单，每个版本需自己的产品图及真实颜色/尺寸/配置属性。")
    if brief.reference_choice == "request":
        questions.append("请提供喜欢或对标的参考图/页面，或明确说明本轮不使用参考的理由。")
    if brief.reference_choice == "provided" and not brief.benchmarks:
        questions.append("请拆解参考的视觉焦点、模块层级、文案、优缺点及可借鉴方式。")
    if brief.reference_choice == "skip" and not brief.reference_reason.strip():
        questions.append("请记录用户明确不使用对标参考的理由。")
    return questions


def storyboard(brief: DesignBrief, bindings: dict[str, str]) -> list[DesignPanel]:
    """Use only supplied facts; omitted trust/size/offer facts never become claims."""
    panels: list[DesignPanel] = []

    def add(purpose, visual, facts=(), headline=None, body=None, sku=None):
        selected: list[ProductFact] = list(facts)
        images = sku.product_images if sku else brief.product_images
        layout = {
            "main": "建议商品占画面约70%，完整居中略偏下；主标题置于顶部安全区，副文案紧随其下，四周留约5%边距，不盖住产品细节。",
            "detail": "建议顶部约20%区域安排主副标题，下部约70%展示产品/证据；主标题字号约为画布宽的5%，副文案约3%，保持清晰对比和连续阅读节奏。",
            "sku": "所有SKU采用同一模板：商品居中占画面约70%，规格标题固定在底部，属性按固定顺序排列；统一商品缩放、边距、字号与背景。",
        }[brief.kind]
        if purpose == "产品展示":
            layout += "细节说明用引线连接实物位置，左右图文交替但保持标题、字体和色调统一。"
        if purpose == "购买引导":
            layout += "行动引导置于商品下方安全区；仅为图片上的提示文字，不绘制虚假的可点击功能。"
        panels.append(
            DesignPanel(
                panel_id=f"p{len(panels) + 1:02}",
                order=len(panels) + 1,
                purpose=purpose,
                headline=headline or (selected[0].label if selected else brief.product_name),
                body=body if body is not None else "；".join(f.value for f in selected),
                visual=visual,
                layout=brief.style.layout + "；" + layout,
                fact_ids=[f.fact_id for f in selected],
                sku_id=sku.sku_id if sku else None,
                reference_images=[bindings[p] for p in images],
            )
        )

    if brief.kind == "sku":
        for sku in brief.variants:
            add(
                "规格辨识",
                "严格使用本SKU实图，保留真实颜色和配置。各图使用同一背景、商品比例、视角、光线及标签位置；不添加赠品或换色。",
                [f for f in brief.facts if f.fact_id in sku.fact_ids],
                headline=sku.label,
                body="；".join(f"{k}：{v}" for k, v in sku.attributes.items()),
                sku=sku,
            )
        return panels

    if brief.kind == "main":
        add(
            "首图点击",
            "产品正面全貌，主体完整清晰，干净背景，突出一个最核心差异点。",
            brief.facts[:1],
        )
        for index in range(1, brief.main_count):
            fact = brief.facts[index % len(brief.facts)]
            add(
                "单一卖点",
                f"围绕「{fact.label}」展示一个细节或真实使用场景，不堆叠其他卖点。第{index + 1}图区分视角；仅展示实图可见结构。",
                [fact],
            )
        return panels

    # The narrative stages remain in order; absent evidence becomes a neutral product view.
    benefits = [f for f in brief.facts if f.category == "benefit"] or brief.facts[:1]
    pain_points = "；".join(f.pain_point for f in brief.facts if f.pain_point.strip())
    add(
        "痛点与开篇",
        "用真实用途建立用户情境，商品为视觉中心；不虚构用户评价或夸张前后对比。"
        + (
            f"用户提供的痛点：{pain_points}"
            if pain_points
            else "尚无具体痛点，先围绕已核实用途组织开篇，向用户进一步核实购买顾虑。"
        ),
        benefits[:1],
    )
    add(
        "解决方案",
        "将已提供卖点与用户需求对应，展示产品如何用于该场景；示意效果标为示意。",
        benefits[:1],
    )
    product_slots = brief.detail_count - 4
    evidence = [f for f in brief.facts if f.category not in ("trust", "offer")] or brief.facts[:1]
    for index in range(product_slots):
        fact = evidence[index % len(evidence)]
        visual = {
            "size": "仅用提供的尺寸数据制作带刻度的尺寸示意；不推算适用体型或容量。",
            "usage": "按提供的操作说明展示步骤及部件；不添加未证实的功能。",
            "material": "局部放大真实材质与工艺，用箭头定位细节；不假造内部结构。",
        }.get(fact.category, "展示对应功能、真实用途或局部细节；不得添加未提供的数值或竞品比较。")
        add("产品展示", visual + f"使用第{index + 1}个独立视角，保持全组配色与排版节奏。", [fact])
    trust = [f for f in brief.facts if f.category == "trust"]
    add(
        "信任依据" if trust else "实物细节核对",
        "只展示提供的信任依据，不伪造报告、认证标识、评价和售后承诺。"
        if trust
        else "无已核实信任资料；改为实物细节展示，发布前向用户核实材质、规格和服务，不加认证或评价。",
        trust[:1],
        headline=None if trust else "看清实物细节",
    )
    offers = [f for f in brief.facts if f.category == "offer"]
    add(
        "购买引导",
        "商品全貌收束，预留清晰行动引导区；只用提供的优惠，不虚构价格、限时、赠品或购买按钮功能。",
        offers[:1],
        headline=None if offers else "核对规格，选择适合的一款",
    )
    return panels


def prompt_for(record: DesignRecord, panel: DesignPanel) -> str:
    if record.brief.reference_replica:
        return compile_reference(record, panel).task.prompt
    if record.brief.suite:
        return compile_suite(record, panel).task.prompt
    if record.brief.replica:
        return compile_replica(record, panel)
    brief = record.brief
    facts = [
        f"{f.fact_id}: {f.label} — {f.value}（来源：{f.source}）"
        for f in brief.facts
        if f.fact_id in panel.fact_ids
    ]
    benchmark = [b.adaptation for b in brief.benchmarks]
    sku = next((s for s in brief.variants if s.sku_id == panel.sku_id), None)
    appearance = (
        sku.visual_observations or "以本SKU实图及属性为准，不使用其他版本的颜色或配置"
        if sku
        else brief.visual_observations
    )
    text = (
        f"为{brief.product_name}设计{brief.kind}电商图片。平台：{brief.platform}；受众：{brief.audience}。\n"
        f"目标：{brief.objective}；本图顺序：{panel.order}；本图任务：{panel.purpose}。\n"
        f"商品外观观察：{appearance}。参考图是本商品实图，必须保留真实外形、比例、颜色、材质、标志和配件。\n"
        f"已核实依据：{'；'.join(facts) or '仅商品外观/所列SKU属性，无额外性能声明'}。\n"
        f"本SKU属性：{json.dumps(sku.attributes, ensure_ascii=False) if sku else '不适用'}。\n"
        f"主文案：{panel.headline or '不添加'}\n副文案：{panel.body or '不添加'}\n"
        f"视觉主体与构图：{panel.visual}\n文案排版：{panel.layout}\n"
        f"全组配色：{brief.style.palette}；字体：{brief.style.typography}；统一布局：{brief.style.layout}；语气：{brief.style.tone}。\n"
        f"对标仅借鉴：{'；'.join(benchmark) or brief.reference_reason}。\n用户要求：{brief.requirements or '无'}。\n"
        "一图一个信息中心，标题和正文层级明确，文字清晰且避免遮挡商品。"
        "不要照搬竞品品牌、参数或文案；不得编造尺寸、认证、功效、销量、用户证言、优惠或赠品。"
        "无数据时不添加比较图；示意不代表实测。不以提示词中的高清/8K字样承诺实际像素。"
    )
    if len(text) > 8000:
        raise BusinessError("单图方案过长，请精简需求、文案或参考说明后重新规划。")
    return text


class DesignService:
    def __init__(self, queue: TaskQueue):
        self.queue = queue
        self.storage = queue.storage
        self.root = self.storage.root / "designs"

    @contextmanager
    def connect(self, write=False):
        path = self.storage.safe_output(self.root / "designs.sqlite3")
        if not write and not path.exists():
            raise BusinessError("未找到设计方案。")
        db = None
        try:
            if write:
                self.storage.safe_output(self.root).mkdir(parents=True, exist_ok=True)
            db = (
                sqlite3.connect(path, timeout=1)
                if write
                else sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)
            )
            if write:
                db.execute("PRAGMA synchronous=FULL")
                db.execute(
                    "CREATE TABLE IF NOT EXISTS designs (design_id TEXT NOT NULL, revision INTEGER NOT NULL, record TEXT NOT NULL, PRIMARY KEY(design_id,revision))"
                )
                db.execute(
                    "CREATE TABLE IF NOT EXISTS replica_reviews (review_id INTEGER PRIMARY KEY AUTOINCREMENT, design_id TEXT NOT NULL, revision INTEGER NOT NULL, record TEXT NOT NULL)"
                )
                db.commit()
                db.execute("BEGIN IMMEDIATE")
            with db:
                yield db
        except (sqlite3.Error, OSError):
            raise BusinessError(
                "设计存储不可用或正被占用；未确认提交成功，请用原设计编号查询。"
            ) from None
        finally:
            if db is not None:
                db.close()

    def read(self, db, design_id, revision=None) -> DesignRecord:
        row = db.execute(
            "SELECT record FROM designs WHERE design_id=? "
            + ("AND revision=?" if revision is not None else "ORDER BY revision DESC LIMIT 1"),
            (design_id, revision) if revision is not None else (design_id,),
        ).fetchone()
        if row is None:
            raise BusinessError("未找到设计方案或版本。")
        return DesignRecord.model_validate_json(row[0])

    def get(self, design_id: str, revision: int | None = None) -> DesignRecord:
        with self.connect() as db:
            return self.read(db, design_id, revision)

    async def freeze(self, brief: DesignBrief) -> list[DesignAsset]:
        sources = list(
            dict.fromkeys(
                [p for s in brief.variants for p in s.product_images]
                if brief.kind == "sku"
                else brief.product_images
            )
        )
        assets = []
        if brief.suite or (
            brief.reference_replica and brief.reference_replica.scope == "product_suite"
        ):
            sources = list(
                dict.fromkeys(
                    [*brief.product_images, *[p for s in brief.variants for p in s.product_images]]
                )
            )
        if brief.replica:
            sources = list(dict.fromkeys([brief.replica.reference_image, *sources]))
        if brief.reference_replica:
            sources = list(dict.fromkeys([brief.reference_replica.reference_image, *sources]))
        total = 0
        for source in sources:
            media = await self.storage.loader.load(source)
            total += len(media.data)
            if total > 40 * MIB:
                raise BusinessError("一组设计的参考和产品图合计不可超过40 MiB。")
            folder = self.storage.safe_output(self.root / "assets")
            folder.mkdir(parents=True, exist_ok=True)
            path = self.storage.safe_output(folder / (media.digest + media.suffix))
            try:
                publish(path, media.data)
            except BusinessError as exc:
                raise BusinessError("冻结商品图已变化，请先核对设计存储；未覆盖已有文件。") from exc
            assets.append(
                DesignAsset(
                    source=source,
                    path=str(path),
                    sha256=media.digest,
                    mime_type=media.mime,
                    width=media.width,
                    height=media.height,
                )
            )
        return assets

    async def plan(
        self, design_id: str, expected_revision: int, brief: DesignBrief, edits: list[PanelCopy]
    ) -> DesignRecord:
        if brief.suite or brief.reference_replica:
            try:
                brief = DesignBrief.model_validate(brief.model_dump(mode="json"))
            except ValidationError as exc:
                raise BusinessError("整套方案字段校验失败，请重新构建完整类型化方案。") from exc
        if brief.replica:
            brief = brief.model_copy(
                update={
                    "replica": brief.replica.model_copy(
                        update={"prompt_target": route_model(brief.model, brief.resolution)}
                    )
                }
            )
        questions = questions_for(brief)
        assets = await self.freeze(brief) if not questions else []
        if brief.replica and edits:
            raise BusinessError(
                "复刻方案请修改replica.frames后重规划，不使用普通edits，以免提示词和展示文案不一致。"
            )
        if brief.suite and edits:
            raise BusinessError("整套图请修改suite.style/frames后重新构建，不使用普通edits。")
        if brief.reference_replica and edits:
            raise BusinessError(
                "共享复刻请修改reference_replica.style/frames后重新构建，不使用普通edits。"
            )
        builder = (
            reference_panels
            if brief.reference_replica
            else suite_panels
            if brief.suite
            else replica_panels
            if brief.replica
            else storyboard
        )
        panels = builder(brief, {a.source: a.path for a in assets}) if not questions else []
        by_id = {p.panel_id: p for p in panels}
        if len({e.panel_id for e in edits}) != len(edits):
            raise BusinessError("同一图不可重复修改。")
        for edit in edits:
            if edit.panel_id not in by_id:
                raise BusinessError("修改引用了不存在的图片；信息不足时请先补齐需求。")
            panel = by_id[edit.panel_id]
            allowed = {f.fact_id for f in brief.facts}
            if panel.sku_id:
                allowed = set(next(s.fact_ids for s in brief.variants if s.sku_id == panel.sku_id))
            if not set(edit.fact_ids) <= allowed:
                raise BusinessError("文案引用了未知事实或其他SKU的事实。")
            if brief.kind != "sku" and edit.body.strip() and not edit.fact_ids:
                raise BusinessError("自定义商品文案必须提供已核实的事实引用。")
            by_id[edit.panel_id] = panel.model_copy(update=edit.model_dump(exclude={"panel_id"}))
        panels = [by_id[p.panel_id] for p in panels]
        revision = expected_revision + 1
        content = {
            "reference_hash_binding": True,
            "design_id": design_id,
            "revision": revision,
            "brief": brief.model_dump(
                mode="json",
                exclude={"reference_replica"} if brief.reference_replica is None else set(),
            ),
            "questions": questions,
            "panels": [p.model_dump() for p in panels],
            "assets": [a.model_dump() for a in assets],
        }
        digest = hashlib.sha256(
            json.dumps(content, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        record = DesignRecord.model_validate(
            {
                **content,
                "digest": digest,
                "status": "needs_input" if questions else "draft",
                "notes": NOTES,
            }
        )
        for panel in panels:
            task = self.task(record, panel)
            try:
                resolve_api(
                    route_model(task.model, task.resolution), task.api_format, task.endpoint, True
                )
            except ValueError as exc:
                raise BusinessError(str(exc)) from exc
        with self.connect(write=True) as db:
            row = db.execute(
                "SELECT MAX(revision) FROM designs WHERE design_id=?", (design_id,)
            ).fetchone()
            if (row[0] or 0) != expected_revision:
                raise BusinessError("设计版本冲突；请先查询当前版本再修改。")
            db.execute(
                "INSERT INTO designs VALUES (?,?,?)",
                (design_id, revision, record.model_dump_json()),
            )
        return record

    def current(self, db, design_id, revision, digest):
        record = self.read(db, design_id)
        if record.revision != revision or record.digest != digest:
            raise BusinessError("版本或摘要已过期；请重新审阅当前方案。")
        if record.questions or not record.panels:
            raise BusinessError("需求信息尚未补齐，不能确认或出图。")
        return record

    def approve(
        self, design_id: str, revision: int, digest: str, user_confirmed: bool, note: str
    ) -> DesignRecord:
        if not user_confirmed:
            raise BusinessError("请先向用户展示文案和排版，取得明确确认后再调用。")
        with self.connect(write=True) as db:
            record = self.current(db, design_id, revision, digest)
            record.status, record.approved_digest, record.confirmation_note = (
                "approved",
                digest,
                note,
            )
            db.execute(
                "UPDATE designs SET record=? WHERE design_id=? AND revision=?",
                (record.model_dump_json(), design_id, revision),
            )
        return record

    def task(self, record: DesignRecord, panel: DesignPanel) -> ImageTask:
        brief = record.brief
        if brief.reference_replica:
            return compile_reference(record, panel).task
        if brief.suite:
            return compile_suite(record, panel).task
        return ImageTask(
            task_id=f"r{record.revision}-{panel.panel_id}",
            prompt=prompt_for(record, panel),
            reference_images=panel.reference_images,
            reference_sha256=[
                next(a.sha256 for a in record.assets if a.path == p) for p in panel.reference_images
            ]
            if record.reference_hash_binding
            else None,
            aspect_ratio=brief.aspect_ratio,
            resolution=brief.resolution,
            model=brief.model,
            api_format=brief.api_format,
            endpoint=brief.endpoint,
        )

    async def submit(
        self, design_id: str, revision: int, digest: str, panel_ids: list[str], authorize_paid: bool
    ) -> TaskPage:
        if not authorize_paid:
            raise BusinessError("本次绘图会收费；缺少明确收费授权，未提交任务。")
        if not 1 <= len(panel_ids) <= MAX_BATCH_ITEMS or len(set(panel_ids)) != len(panel_ids):
            raise BusinessError("每次明确选择1–20个不同panel_id。")
        # Only immutable local copies are used; no network while holding the design lock.
        with self.connect(write=True) as db:
            record = self.current(db, design_id, revision, digest)
            if record.approved_digest != digest:
                raise BusinessError("当前方案尚未取得用户确认。")
            panels = {p.panel_id: p for p in record.panels}
            if not set(panel_ids) <= panels.keys():
                raise BusinessError("包含不存在的panel_id；全批未提交。")
            selected_paths = {path for key in panel_ids for path in panels[key].reference_images}
            for asset in record.assets:
                if asset.path in selected_paths:
                    path = self.storage.safe_output(Path(asset.path))
                    try:
                        with path.open("rb") as stream:
                            data = stream.read(20 * MIB + 1)
                    except OSError:
                        raise BusinessError("冻结商品图不可读，未提交任务。") from None
                    if hashlib.sha256(data).hexdigest() != asset.sha256:
                        raise BusinessError("冻结商品图已更改；未提交任务，请重新审阅。")
                    decode_image(data)
            return await self.queue.submit(
                SCOPE, design_id, [self.task(record, panels[key]) for key in panel_ids]
            )

    def progress(self, design_id: str, revision: int | None = None) -> DesignProgress:
        record = self.get(design_id, revision)
        with self.connect() as db:
            has_reviews = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='replica_reviews'"
            ).fetchone()
            reviews = (
                [
                    ReplicaReview.model_validate_json(r[0])
                    for r in db.execute(
                        "SELECT record FROM replica_reviews WHERE design_id=? AND revision=? ORDER BY review_id",
                        (design_id, record.revision),
                    )
                ]
                if has_reviews
                else []
            )
        tasks: list[TaskResult] = []
        cursor = 0
        while True:
            page = self.queue.get(SCOPE, design_id, cursor=cursor)
            tasks.extend(t for t in page.tasks if t.task_id.startswith(f"r{record.revision}-"))
            if page.next_cursor is None:
                break
            cursor = page.next_cursor
        submitted = {t.task_id for t in tasks}
        return DesignProgress(
            design=record,
            thread_id=design_id,
            tasks=tasks,
            replica_reviews=reviews,
            unsubmitted_panel_ids=[
                p.panel_id
                for p in record.panels
                if f"r{record.revision}-{p.panel_id}" not in submitted
            ],
        )
