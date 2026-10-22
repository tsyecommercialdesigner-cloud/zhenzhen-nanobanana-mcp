"""Durable local task queue. Never replay a request that might have reached the provider."""

import asyncio
import hashlib
import json
import logging
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

import httpx

from .config import BusinessError, Settings
from .media import MIB, MediaLoader, TransientDownloadError
from .integrity import digest_file, publish
from .limits import MAX_BATCH_ITEMS
from .models import (
    ImageTask,
    SavedImage,
    TaskPage,
    TaskResult,
    TaskWaitResult,
    resolve_api,
    route_model,
)
from .provider import Provider, SafeConnectFailure
from .service import BatchService

ACTIVE = ("queued", "preparing", "running", "recovering")
LEASE_SECONDS = 30
HEARTBEAT_SECONDS = 5
LOG = logging.getLogger(__name__)


async def durable_io(function, *args, **kwargs):
    """Keep blocking disk work off stdio's loop; drain it before releasing ownership."""
    pending = asyncio.create_task(asyncio.to_thread(function, *args, **kwargs))
    try:
        return await asyncio.shield(pending)
    except asyncio.CancelledError:
        await asyncio.gather(pending, return_exceptions=True)
        raise


class TaskQueue:
    def __init__(
        self,
        settings: Settings,
        provider: Provider | None = None,
        loader: MediaLoader | None = None,
    ):
        self.settings = settings
        self.storage = BatchService(settings, provider, loader)
        self.db_path = self.storage.safe_output(self.storage.root / "tasks.sqlite3")
        self.owner = uuid.uuid4().hex
        self.workers: list[asyncio.Task] = []
        self.heartbeat: asyncio.Task | None = None
        self.inflight: dict[int, asyncio.Task] = {}
        self.reconcile: set[int] = set()
        self.wake = asyncio.Event()
        self.started = False
        self.closing = False
        self.verified_files: dict[str, tuple] = {}
        self.schema_identity: tuple[int, int] | None = None
        self.wal_keeper: sqlite3.Connection | None = None

    @contextmanager
    def connect(self, readonly=False):
        if not readonly:
            self.storage.root.mkdir(parents=True, exist_ok=True)
        # Re-check links on every access, including after the first queue was created.
        path = self.storage.safe_output(self.db_path)
        db = None
        try:
            db = (
                sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=3)
                if readonly
                else sqlite3.connect(path, timeout=3)
            )
            db.row_factory = sqlite3.Row
            if not readonly:
                db.execute("PRAGMA synchronous=FULL")
                identity = (path.stat().st_dev, path.stat().st_ino)
                if self.schema_identity != identity:
                    # Concurrent first connections can race while switching an empty DB to WAL.
                    # Only retry this local setup, never a task body or a provider POST.
                    for attempt in range(8):
                        try:
                            if db.execute("PRAGMA journal_mode").fetchone()[0] != "wal":
                                db.execute("PRAGMA journal_mode=WAL")
                            break
                        except sqlite3.OperationalError as exc:
                            if "locked" not in str(exc).lower() or attempt == 7:
                                raise
                            time.sleep(0.02)
                    db.execute("BEGIN IMMEDIATE")
                    db.execute(
                        "CREATE TABLE IF NOT EXISTS task_owners (owner TEXT PRIMARY KEY, heartbeat REAL NOT NULL)"
                    )
                    db.execute("""CREATE TABLE IF NOT EXISTS image_tasks (
                        seq INTEGER PRIMARY KEY AUTOINCREMENT,
                        checkpointer TEXT NOT NULL, thread_id TEXT NOT NULL, task_id TEXT NOT NULL,
                        fingerprint TEXT NOT NULL, request TEXT NOT NULL, actual_model TEXT NOT NULL,
                        api_format TEXT NOT NULL, endpoint TEXT NOT NULL, state TEXT NOT NULL,
                        base_url TEXT NOT NULL,
                        owner TEXT, images TEXT NOT NULL DEFAULT '[]', error TEXT,
                        created REAL NOT NULL, updated REAL NOT NULL,
                        UNIQUE(checkpointer, thread_id, task_id))""")
                    columns = {column[1] for column in db.execute("PRAGMA table_info(image_tasks)")}
                    if "base_url" not in columns:
                        db.execute(
                            "ALTER TABLE image_tasks ADD COLUMN base_url TEXT NOT NULL DEFAULT ''"
                        )
                    additions = {
                        "provider_key": "TEXT NOT NULL DEFAULT ''",
                        "reference_hashes": "TEXT NOT NULL DEFAULT '[]'",
                        "input_paths": "TEXT NOT NULL DEFAULT '[]'",
                        "response_path": "TEXT NOT NULL DEFAULT ''",
                        "response_sha256": "TEXT NOT NULL DEFAULT ''",
                        "post_attempts": "INTEGER NOT NULL DEFAULT 0",
                        "recovery_attempts": "INTEGER NOT NULL DEFAULT 0",
                        "cycle_attempts": "INTEGER NOT NULL DEFAULT 0",
                        "safe_retry": "INTEGER NOT NULL DEFAULT 0",
                        "next_attempt": "REAL NOT NULL DEFAULT 0",
                        "repair_files": "INTEGER NOT NULL DEFAULT 0",
                    }
                    for column, declaration in additions.items():
                        if column not in columns:
                            db.execute(f"ALTER TABLE image_tasks ADD COLUMN {column} {declaration}")
                    db.execute(
                        "CREATE INDEX IF NOT EXISTS image_tasks_queue ON image_tasks(state,seq)"
                    )
                    db.commit()
                    self.schema_identity = identity
            with db:
                yield db
        except sqlite3.Error:
            raise BusinessError(
                "任务账本不可用或正在被占用；请查询原标识，不要盲目更换任务编号。"
            ) from None
        finally:
            if db is not None:
                db.close()

    def reap(self, db):
        stale = time.time() - LEASE_SECONDS
        db.execute(
            """UPDATE image_tasks SET state=CASE WHEN state='preparing' THEN 'queued' WHEN state='recovering' THEN 'recovering' ELSE 'unknown' END,
                   error=CASE WHEN state='preparing' THEN NULL WHEN state='recovering' THEN '进程中断，按已保存响应恢复图片，不重发绘图。' ELSE '工作进程中断，上游结果与费用不确定；未自动重发。' END,
                   owner=NULL, updated=? WHERE state IN ('preparing','running','unknown','recovering') AND owner IN
                   (SELECT owner FROM task_owners WHERE heartbeat < ?)""",
            (time.time(), stale),
        )
        db.execute("DELETE FROM task_owners WHERE heartbeat < ?", (stale,))

    async def start(self):
        if self.started:
            return
        self.started, self.closing = True, False
        if self.db_path.exists():
            self.ensure_workers()

    def ensure_workers(self):
        if self.workers:
            return
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self.reap(db)
            db.execute("INSERT OR REPLACE INTO task_owners VALUES (?,?)", (self.owner, time.time()))
        # Keep WAL open while workers live; short transactions must not each
        # become the last connection and checkpoint/delete the WAL on close.
        if self.wal_keeper is None:
            path = self.storage.safe_output(self.db_path)
            keeper = None
            try:
                keeper = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=3)
                keeper.execute("SELECT seq FROM image_tasks LIMIT 1").fetchall()
            except sqlite3.Error:
                if keeper is not None:
                    keeper.close()
                raise BusinessError(
                    "任务账本连接初始化失败；请查询原标识，不要重新提交。"
                ) from None
            self.wal_keeper = keeper
        self.heartbeat = asyncio.create_task(self.keep_alive())
        self.workers = [
            asyncio.create_task(self.worker()) for _ in range(self.settings.concurrency)
        ]

    async def keep_alive(self):
        while True:
            await asyncio.sleep(HEARTBEAT_SECONDS)
            try:
                with self.connect() as db:
                    # Losing a lease must not silently renew ownership of running requests.
                    renewed = db.execute(
                        "UPDATE task_owners SET heartbeat=? WHERE owner=?",
                        (time.time(), self.owner),
                    ).rowcount
                    if not renewed:
                        self.owner = uuid.uuid4().hex
                        db.execute(
                            "INSERT INTO task_owners VALUES (?,?)", (self.owner, time.time())
                        )
                    self.reap(db)
                    reconciled = list(self.reconcile)
                    for seq in reconciled:
                        db.execute(
                            "UPDATE image_tasks SET state='unknown',owner=NULL,error=?,updated=? WHERE seq=? AND owner=? AND state IN ('preparing','running','recovering','unknown')",
                            (
                                "任务账本写入曾失败，结果和费用不确定；未自动重发。",
                                time.time(),
                                seq,
                                self.owner,
                            ),
                        )
                # Remove repair intents only after the transaction committed.
                self.reconcile.difference_update(reconciled)
            except BusinessError:
                LOG.warning("任务心跳写入失败；暂停新的收费请求直到账本可用。")

    async def close(self):
        self.closing = True
        for task in self.workers:
            task.cancel()
        if self.heartbeat:
            self.heartbeat.cancel()
        try:
            await asyncio.gather(
                *self.workers, *([self.heartbeat] if self.heartbeat else []), return_exceptions=True
            )
            if self.db_path.exists() and self.workers:
                with self.connect() as db:
                    db.execute("UPDATE task_owners SET heartbeat=0 WHERE owner=?", (self.owner,))
                    self.reap(db)
        finally:
            if self.wal_keeper is not None:
                self.wal_keeper.close()
                self.wal_keeper = None
            self.workers = []
            self.heartbeat = None
            self.started = False

    def result(self, row, reused=False):
        keys = set(row.keys())

        def value(name, default):
            return row[name] if name in keys else default

        images = [SavedImage.model_validate(i) for i in json.loads(row["images"])]
        state, error, integrity = row["state"], row["error"], "not_checked"
        if state == "succeeded":
            try:
                if not images:
                    raise BusinessError("任务没有已保存图片。")
                for image in images:
                    path = self.storage.safe_output(Path(image.path))
                    stat = path.stat()
                    stamp = (
                        stat.st_size,
                        stat.st_mtime_ns,
                        stat.st_ctime_ns,
                        stat.st_ino,
                        image.sha256,
                    )
                    if self.verified_files.get(str(path)) != stamp:
                        if (
                            stat.st_size != image.bytes
                            or digest_file(path, 32 * MIB) != image.sha256
                        ):
                            raise BusinessError("图片大小或SHA256不匹配。")
                        self.verified_files[str(path)] = stamp
                integrity = "verified"
            except (OSError, BusinessError):
                state, integrity = "failed", "failed"
                error = "已生成结果文件缺失或SHA256不匹配；未重新出图，可用原响应修复。"
        return TaskResult(
            provider_idempotency_key=value("provider_key", "")
            or self.key_for(
                row["checkpointer"], row["thread_id"], row["task_id"], row["fingerprint"]
            ),
            reference_sha256=json.loads(value("reference_hashes", "[]")),
            post_attempts=value("post_attempts", 0),
            recovery_attempts=value("recovery_attempts", 0),
            safe_to_retry=bool(value("safe_retry", 0) or value("response_path", "")),
            file_integrity=integrity,
            checkpointer=row["checkpointer"],
            thread_id=row["thread_id"],
            task_id=row["task_id"],
            status=state,
            actual_model=row["actual_model"],
            api_format=row["api_format"],
            endpoint=row["endpoint"],
            images=images,
            error=error,
            created_at=row["created"],
            updated_at=row["updated"],
            reused=reused,
        )

    async def submit(self, checkpointer: str, thread_id: str, tasks: list[ImageTask]) -> TaskPage:
        if not 1 <= len(tasks) <= MAX_BATCH_ITEMS or len({task.task_id for task in tasks}) != len(
            tasks
        ):
            raise BusinessError("每次提交1–20项，task_id不可重复。")
        prepared = []
        for task in tasks:
            actual_model = route_model(task.model, task.resolution)
            try:
                api, endpoint = resolve_api(
                    actual_model, task.api_format, task.endpoint, bool(task.reference_images)
                )
            except ValueError as exc:
                raise BusinessError(str(exc)) from exc
            request = task.model_copy(
                update={"api_format": api, "endpoint": endpoint if api == "dalle" else "auto"}
            ).model_dump_json()
            canonical = json.dumps(
                {
                    "request": task.model_dump(
                        exclude={"reference_sha256"} if task.reference_sha256 is None else set()
                    ),
                    "model": actual_model,
                    "api": api,
                    "endpoint": endpoint,
                    "base_url": self.settings.base_url,
                },
                sort_keys=True,
                ensure_ascii=False,
            )
            prepared.append(
                (
                    task.task_id,
                    hashlib.sha256(canonical.encode()).hexdigest(),
                    request,
                    actual_model,
                    api,
                    endpoint,
                )
            )
        await self.start()
        rows, reused = [], set()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self.reap(db)
            for task_id, fingerprint, *_ in prepared:
                old = db.execute(
                    "SELECT * FROM image_tasks WHERE checkpointer=? AND thread_id=? AND task_id=?",
                    (checkpointer, thread_id, task_id),
                ).fetchone()
                if old is not None:
                    if old["fingerprint"] != fingerprint:
                        raise BusinessError(
                            "相同(checkpointer,thread_id,task_id)已绑定其他内容；全批未新增任务。"
                        )
                    reused.add(task_id)
            pending = db.execute(
                "SELECT count(*) FROM image_tasks WHERE state IN ('queued','preparing','running','recovering')"
            ).fetchone()[0]
            if pending + len(prepared) - len(reused) > self.settings.max_pending_tasks:
                raise BusinessError("任务队列容量已满；本次未新增任务，稍后用相同标识提交。")
            now = time.time()
            for task_id, fingerprint, request, model, api, endpoint in prepared:
                if task_id not in reused:
                    db.execute(
                        """INSERT INTO image_tasks(checkpointer,thread_id,task_id,fingerprint,request,
                               actual_model,api_format,endpoint,base_url,state,created,updated,provider_key) VALUES (?,?,?,?,?,?,?,?,?,'queued',?,?,?)""",
                        (
                            checkpointer,
                            thread_id,
                            task_id,
                            fingerprint,
                            request,
                            model,
                            api,
                            endpoint,
                            self.settings.base_url,
                            now,
                            now,
                            self.key_for(checkpointer, thread_id, task_id, fingerprint),
                        ),
                    )
                rows.append(
                    db.execute(
                        "SELECT * FROM image_tasks WHERE checkpointer=? AND thread_id=? AND task_id=?",
                        (checkpointer, thread_id, task_id),
                    ).fetchone()
                )
        self.ensure_workers()
        self.wake.set()
        return TaskPage(
            checkpointer=checkpointer,
            thread_id=thread_id,
            tasks=[self.result(row, row["task_id"] in reused) for row in rows],
        )

    def get(
        self,
        checkpointer: str,
        thread_id: str,
        task_ids: list[str] | None = None,
        cursor: int = 0,
        limit: int = 100,
    ) -> TaskPage:
        if not self.db_path.exists():
            if task_ids:
                raise BusinessError("未找到指定任务。")
            return TaskPage(checkpointer=checkpointer, thread_id=thread_id, tasks=[])
        with self.connect(readonly=True) as db:
            params = [checkpointer, thread_id, cursor]
            sql = "SELECT * FROM image_tasks WHERE checkpointer=? AND thread_id=? AND seq>?"
            if task_ids:
                sql += " AND task_id IN (" + ",".join("?" for _ in task_ids) + ")"
                params.extend(task_ids)
            rows = db.execute(sql + " ORDER BY seq LIMIT ?", [*params, limit + 1]).fetchall()
            if (
                task_ids
                and cursor == 0
                and limit >= len(set(task_ids))
                and len(rows) != len(set(task_ids))
            ):
                raise BusinessError("部分指定任务不存在于该checkpointer/thread_id；请核对标识。")
        return TaskPage(
            checkpointer=checkpointer,
            thread_id=thread_id,
            tasks=[self.result(row) for row in rows[:limit]],
            next_cursor=rows[limit - 1]["seq"] if len(rows) > limit else None,
        )

    async def wait(
        self,
        checkpointer: str,
        thread_id: str,
        task_ids: list[str],
        wait_timeout_seconds: float = 600,
    ) -> TaskWaitResult:
        """Wait on the shared ledger only. Never own, cancel or resubmit rendering work."""
        if not task_ids or len(task_ids) > 100 or len(set(task_ids)) != len(task_ids):
            raise BusinessError("等待需指定1–100个不重复的task_id。")
        if not 0 < wait_timeout_seconds <= 1200:
            raise BusinessError("等待时限必须大于0且不超过1200秒。")
        loop = asyncio.get_running_loop()
        deadline = loop.time() + wait_timeout_seconds
        while True:
            page = self.get(checkpointer, thread_id, task_ids, limit=100)
            if all(task.status not in ACTIVE for task in page.tasks):
                return TaskWaitResult(**page.model_dump())
            remaining = deadline - loop.time()
            if remaining <= 0:
                return TaskWaitResult(**page.model_dump(), wait_timed_out=True)
            # Workers belong to the server lifespan, not this tool call. Cancellation
            # propagates only through this sleep and cannot cancel provider requests.
            await asyncio.sleep(min(0.2, remaining))

    def cancel(self, checkpointer: str, thread_id: str, task_ids: list[str]) -> TaskPage:
        self.get(checkpointer, thread_id, task_ids)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            for task_id in task_ids:
                row = db.execute(
                    "SELECT * FROM image_tasks WHERE checkpointer=? AND thread_id=? AND task_id=?",
                    (checkpointer, thread_id, task_id),
                ).fetchone()
                if row["state"] in ACTIVE:
                    state = "unknown" if row["state"] == "running" else "cancelled"
                    error = (
                        "本地取消；上游可能已收费，未自动重发。"
                        if state == "unknown"
                        else "已停止原响应的图片恢复，绘图可能已收费。"
                        if row["state"] == "recovering"
                        else "已取消，未发起绘图请求。"
                    )
                    db.execute(
                        "UPDATE image_tasks SET state=?,error=?,updated=?,owner=CASE WHEN state IN ('running','recovering') THEN owner ELSE NULL END WHERE seq=?",
                        (state, error, time.time(), row["seq"]),
                    )
                    if row["seq"] in self.inflight:
                        self.inflight[row["seq"]].cancel()
        return self.get(checkpointer, thread_id, task_ids)

    def claim(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self.reap(db)
            owner = db.execute(
                "SELECT 1 FROM task_owners WHERE owner=? AND heartbeat>=?",
                (self.owner, time.time() - LEASE_SECONDS),
            ).fetchone()
            if owner is None:
                return None
            active = db.execute(
                "SELECT count(*) FROM image_tasks WHERE state IN ('preparing','running') OR (state IN ('unknown','recovering') AND owner IS NOT NULL)"
            ).fetchone()[0]
            if active >= self.settings.concurrency:
                return None
            row = db.execute(
                "SELECT * FROM image_tasks WHERE (state='queued' OR (state='recovering' AND owner IS NULL)) AND next_attempt<=? ORDER BY seq LIMIT 1",
                (time.time(),),
            ).fetchone()
            if row is not None:
                db.execute(
                    "UPDATE image_tasks SET state=CASE WHEN state='recovering' THEN 'recovering' ELSE 'preparing' END,owner=?,updated=? WHERE seq=?",
                    (self.owner, time.time(), row["seq"]),
                )
            return row

    def finish(self, seq, state, images=None, error=None, safe_retry=False):
        with self.connect() as db:
            db.execute(
                "UPDATE image_tasks SET state=?,images=?,error=?,safe_retry=?,updated=? WHERE seq=? AND owner=? AND state IN ('preparing','running','recovering')",
                (
                    state,
                    json.dumps(images or [], ensure_ascii=False),
                    error,
                    int(safe_retry),
                    time.time(),
                    seq,
                    self.owner,
                ),
            )

    @staticmethod
    def key_for(checkpointer, thread_id, task_id, fingerprint):
        return hashlib.sha256(
            json.dumps([checkpointer, thread_id, task_id, fingerprint], ensure_ascii=False).encode()
        ).hexdigest()

    async def checkpoint(self, row, sources):
        data = json.dumps(sources, ensure_ascii=False).encode()
        digest = hashlib.sha256(data).hexdigest()
        path = self.storage.safe_output(self.storage.root / "task-responses" / f"{digest}.json")
        await durable_io(publish, path, data)
        with self.connect() as db:
            changed = db.execute(
                "UPDATE image_tasks SET response_path=?,response_sha256=?,state='recovering',recovery_attempts=recovery_attempts+1,cycle_attempts=1,safe_retry=1,updated=? WHERE seq=? AND owner=? AND state='running' AND EXISTS(SELECT 1 FROM task_owners WHERE owner=? AND heartbeat>=?)",
                (
                    str(path),
                    digest,
                    time.time(),
                    row["seq"],
                    self.owner,
                    self.owner,
                    time.time() - LEASE_SECONDS,
                ),
            ).rowcount
        if not changed:
            raise BusinessError("任务已取消或租约失效；未继续处理结果。")

    def resume_sources(self, row):
        path = self.storage.safe_output(Path(row["response_path"]))
        if digest_file(path, 110 * MIB) != row["response_sha256"]:
            raise BusinessError("响应检查点SHA256不匹配，不能恢复或重发绘图。")
        return json.loads(path.read_text(encoding="utf-8"))

    async def prepare_inputs(self, row, task):
        frozen = json.loads(row["input_paths"])
        references = [await self.storage.loader.load(p) for p in (frozen or task.reference_images)]
        hashes = [ref.digest for ref in references]
        expected = json.loads(row["reference_hashes"]) if frozen else task.reference_sha256
        if expected is not None and hashes != expected:
            raise BusinessError("参考图SHA256不匹配；未发起绘图请求。")
        if sum(len(ref.data) for ref in references) > 40 * MIB:
            raise BusinessError("单项参考图总字节数超过40 MiB；未发起绘图请求。")
        paths = []
        for ref in references:
            path = self.storage.safe_output(
                self.storage.root / "task-inputs" / (ref.digest + ref.suffix)
            )
            await durable_io(publish, path, ref.data)
            paths.append(str(path))
        with self.connect() as db:
            db.execute(
                "UPDATE image_tasks SET reference_hashes=?,input_paths=? WHERE seq=? AND owner=? AND state='preparing'",
                (json.dumps(hashes), json.dumps(paths), row["seq"], self.owner),
            )
        return references

    def schedule_recovery(self, seq, images):
        with self.connect() as db:
            row = db.execute(
                "SELECT cycle_attempts FROM image_tasks WHERE seq=? AND owner=? AND state='recovering'",
                (seq, self.owner),
            ).fetchone()
            if row:
                attempts = row[0]
                state = "recovering" if attempts < self.settings.safe_attempts else "failed"
                db.execute(
                    "UPDATE image_tasks SET state=?,owner=NULL,images=?,safe_retry=1,next_attempt=?,error=?,updated=? WHERE seq=? AND owner=?",
                    (
                        state,
                        json.dumps(images),
                        time.time() + self.settings.retry_delay * 2 ** (attempts - 1),
                        "原响应的下载/落盘未完成；仅恢复原响应，不重新绘图。",
                        time.time(),
                        seq,
                        self.owner,
                    ),
                )

    async def execute(self, row):
        seq, dispatched = row["seq"], False
        checkpointed = bool(row["response_path"])
        images = json.loads(row["images"])
        try:
            if not checkpointed and row["base_url"] != self.settings.base_url:
                raise BusinessError(
                    "任务登记的服务地址与当前配置不同；未发起请求，请人工核对配置。"
                )
            task = ImageTask.model_validate_json(row["request"])
            async with asyncio.timeout(self.settings.timeout):
                if checkpointed:
                    sources = self.resume_sources(row)
                    with self.connect() as db:
                        db.execute(
                            "UPDATE image_tasks SET recovery_attempts=recovery_attempts+1,cycle_attempts=cycle_attempts+1 WHERE seq=? AND owner=? AND state='recovering'",
                            (seq, self.owner),
                        )
                    media = await self.storage.provider.collect(sources)
                else:
                    references = await self.prepare_inputs(row, task)
                    if not self.settings.api_key:
                        raise BusinessError("未配置API密钥；未发起绘图请求。")
                    with self.connect() as db:
                        changed = db.execute(
                            "UPDATE image_tasks SET state='running',post_attempts=post_attempts+1,safe_retry=0,updated=? WHERE seq=? AND owner=? AND state='preparing' AND EXISTS(SELECT 1 FROM task_owners WHERE owner=? AND heartbeat>=?)",
                            (time.time(), seq, self.owner, self.owner, time.time() - LEASE_SECONDS),
                        ).rowcount
                    if not changed:
                        return
                    first_attempt = True

                    def on_attempt():
                        nonlocal first_attempt
                        with self.connect() as db:
                            changed = db.execute(
                                "UPDATE image_tasks SET post_attempts=post_attempts+? WHERE seq=? AND owner=? AND state='running' AND EXISTS(SELECT 1 FROM task_owners WHERE owner=? AND heartbeat>=?)",
                                (
                                    0 if first_attempt else 1,
                                    seq,
                                    self.owner,
                                    self.owner,
                                    time.time() - LEASE_SECONDS,
                                ),
                            ).rowcount
                        first_attempt = False
                        if not changed:
                            raise BusinessError("任务已取消或租约失效；未发送新的绘图请求。")

                    async def on_response(sources):
                        nonlocal checkpointed
                        await self.checkpoint(row, sources)
                        checkpointed = True

                    task._provider_key = row["provider_key"] or self.key_for(
                        row["checkpointer"], row["thread_id"], row["task_id"], row["fingerprint"]
                    )
                    task._on_post_attempt, task._on_response = on_attempt, on_response
                    dispatched = True
                    media = await self.storage.provider.render(
                        task, references, row["actual_model"], row["api_format"]
                    )
                    if not checkpointed:
                        await on_response([m.data_url for m in media])
                with self.connect(readonly=True) as db:
                    if not db.execute(
                        "SELECT 1 FROM image_tasks WHERE seq=? AND owner=? AND state='recovering'",
                        (seq, self.owner),
                    ).fetchone():
                        return
                key = row["provider_key"] or self.key_for(
                    row["checkpointer"], row["thread_id"], row["task_id"], row["fingerprint"]
                )
                folder = self.storage.safe_output(
                    self.storage.root / uuid.uuid5(uuid.NAMESPACE_URL, key).hex
                )
                if not media or len(media) > 4 or len(media) < len(images):
                    raise BusinessError("原响应的图片数量无效或发生变化，不能替换已有结果。")
                for index, item in enumerate(media):
                    if index < len(images) and images[index]["sha256"] != item.digest:
                        raise BusinessError("原响应图片内容已改变，不能替换已有结果。")
                    path = self.storage.safe_output(folder / f"{index + 1:02}{item.suffix}")
                    await durable_io(publish, path, item.data, repair=bool(row["repair_files"]))
                    saved = SavedImage(
                        path=str(path),
                        mime_type=item.mime,
                        width=item.width,
                        height=item.height,
                        bytes=len(item.data),
                        sha256=item.digest,
                    ).model_dump()
                    if index < len(images):
                        images[index] = saved
                    else:
                        images.append(saved)
                self.finish(seq, "succeeded", images)
        except asyncio.CancelledError:
            self.finish(
                seq,
                "recovering" if checkpointed else "unknown" if dispatched else "queued",
                images,
                "本地等待中断；保留原响应/幂等键，不重发可能已收费请求。",
                safe_retry=checkpointed or not dispatched,
            )
            raise
        except SafeConnectFailure as exc:
            self.finish(seq, "failed", images, str(exc), safe_retry=True)
        except (httpx.HTTPError, TimeoutError, OSError, TransientDownloadError):
            if checkpointed:
                self.schedule_recovery(seq, images)
            else:
                self.finish(
                    seq,
                    "unknown" if dispatched else "failed",
                    images,
                    "请求超时/网络或文件失败；可能已发送的绘图未自动重发。",
                    safe_retry=not dispatched,
                )
        except BusinessError as exc:
            self.finish(seq, "failed", images, str(exc), safe_retry=checkpointed or not dispatched)
        except Exception:
            self.finish(
                seq,
                "failed",
                images,
                "任务处理失败；请查询原标识，不自动重发。",
                safe_retry=checkpointed or not dispatched,
            )
        finally:
            with self.connect() as db:
                db.execute(
                    "UPDATE image_tasks SET owner=NULL WHERE seq=? AND owner=? AND state NOT IN ('preparing','running','recovering')",
                    (seq, self.owner),
                )

    async def retry(self, checkpointer, thread_id, task_ids, repair_files=False):
        if not task_ids or len(task_ids) > MAX_BATCH_ITEMS or len(set(task_ids)) != len(task_ids):
            raise BusinessError("重试需1–20个不重复的原task_id。")
        self.get(checkpointer, thread_id, task_ids)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = [
                db.execute(
                    "SELECT * FROM image_tasks WHERE checkpointer=? AND thread_id=? AND task_id=?",
                    (checkpointer, thread_id, key),
                ).fetchone()
                for key in task_ids
            ]
            changes = []
            for row in rows:
                result = self.result(row)
                if row["state"] in ACTIVE or result.status == "succeeded":
                    continue
                if row["owner"] or not (row["response_path"] or row["safe_retry"]):
                    raise BusinessError(
                        "包含可能已收费且无可靠响应的任务，禁止重发；请按原标识核对。"
                    )
                if result.file_integrity == "failed" and not repair_files:
                    raise BusinessError(
                        "结果文件校验失败；修复需显式repair_files=True，原损坏文件会保留。"
                    )
                changes.append(row)
            pending = db.execute(
                "SELECT count(*) FROM image_tasks WHERE state IN ('queued','preparing','running','recovering')"
            ).fetchone()[0]
            if pending + len(changes) > self.settings.max_pending_tasks:
                raise BusinessError("重试会超出队列容量；本批未重排。")
            for row in changes:
                db.execute(
                    "UPDATE image_tasks SET state=?,owner=NULL,cycle_attempts=0,next_attempt=0,repair_files=?,error=NULL,updated=? WHERE seq=?",
                    (
                        "recovering" if row["response_path"] else "queued",
                        int(repair_files),
                        time.time(),
                        row["seq"],
                    ),
                )
        await self.start()
        self.ensure_workers()
        self.wake.set()
        return self.get(checkpointer, thread_id, task_ids)

    async def worker(self):
        while not self.closing:
            row = None
            try:
                row = self.claim()
                if row is None:
                    self.wake.clear()
                    try:
                        await asyncio.wait_for(self.wake.wait(), 0.2)
                    except TimeoutError:
                        pass
                    continue
                task = asyncio.create_task(self.execute(row))
                self.inflight[row["seq"]] = task
                try:
                    await task
                finally:
                    self.inflight.pop(row["seq"], None)
            except asyncio.CancelledError:
                if self.closing:
                    raise
            except Exception:
                if row is not None:
                    self.reconcile.add(row["seq"])
                LOG.warning("后台任务账本处理失败；未自动重发已发送请求。")
                await asyncio.sleep(0.5)
