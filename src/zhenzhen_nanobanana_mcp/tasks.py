"""Durable local task queue. Never replay a request that might have reached the provider."""

import asyncio
import hashlib
import json
import logging
import sqlite3
import time
import uuid
from contextlib import contextmanager

import httpx

from .config import BusinessError, Settings
from .media import MIB, MediaLoader
from .models import (
    ImageTask,
    SavedImage,
    TaskPage,
    TaskResult,
    TaskWaitResult,
    resolve_api,
    route_model,
)
from .provider import Provider
from .service import BatchService

ACTIVE = ("queued", "preparing", "running")
LEASE_SECONDS = 30
HEARTBEAT_SECONDS = 5
LOG = logging.getLogger(__name__)


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

    @contextmanager
    def connect(self, readonly=False):
        if not readonly:
            self.storage.root.mkdir(parents=True, exist_ok=True)
        # Re-check links on every access, including after the first queue was created.
        path = self.storage.safe_output(self.db_path)
        db = None
        try:
            db = (
                sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)
                if readonly
                else sqlite3.connect(path, timeout=1)
            )
            db.row_factory = sqlite3.Row
            if not readonly:
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
                db.execute("PRAGMA synchronous=FULL")
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
                db.execute("CREATE INDEX IF NOT EXISTS image_tasks_queue ON image_tasks(state,seq)")
                db.commit()
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
            """UPDATE image_tasks SET state=CASE WHEN state='preparing' THEN 'queued' ELSE 'unknown' END,
                   error=CASE WHEN state='preparing' THEN NULL ELSE '工作进程中断，上游结果与费用不确定；未自动重发。' END,
                   owner=NULL, updated=? WHERE state IN ('preparing','running','unknown') AND owner IN
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
                            "UPDATE image_tasks SET state='unknown',owner=NULL,error=?,updated=? WHERE seq=? AND owner=? AND state IN ('preparing','running','unknown')",
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
        await asyncio.gather(
            *self.workers, *([self.heartbeat] if self.heartbeat else []), return_exceptions=True
        )
        if self.db_path.exists() and self.workers:
            with self.connect() as db:
                db.execute("UPDATE task_owners SET heartbeat=0 WHERE owner=?", (self.owner,))
                self.reap(db)
        self.workers = []
        self.heartbeat = None
        self.started = False

    def result(self, row, reused=False):
        return TaskResult(
            checkpointer=row["checkpointer"],
            thread_id=row["thread_id"],
            task_id=row["task_id"],
            status=row["state"],
            actual_model=row["actual_model"],
            api_format=row["api_format"],
            endpoint=row["endpoint"],
            images=json.loads(row["images"]),
            error=row["error"],
            created_at=row["created"],
            updated_at=row["updated"],
            reused=reused,
        )

    async def submit(self, checkpointer: str, thread_id: str, tasks: list[ImageTask]) -> TaskPage:
        if not 1 <= len(tasks) <= 12 or len({task.task_id for task in tasks}) != len(tasks):
            raise BusinessError("每次提交1–12项，task_id不可重复。")
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
                    "request": task.model_dump(),
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
                "SELECT count(*) FROM image_tasks WHERE state IN ('queued','preparing','running')"
            ).fetchone()[0]
            if pending + len(prepared) - len(reused) > self.settings.max_pending_tasks:
                raise BusinessError("任务队列容量已满；本次未新增任务，稍后用相同标识提交。")
            now = time.time()
            for task_id, fingerprint, request, model, api, endpoint in prepared:
                if task_id not in reused:
                    db.execute(
                        """INSERT INTO image_tasks(checkpointer,thread_id,task_id,fingerprint,request,
                               actual_model,api_format,endpoint,base_url,state,created,updated) VALUES (?,?,?,?,?,?,?,?,?,'queued',?,?)""",
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
                        else "已取消，未发起绘图请求。"
                    )
                    db.execute(
                        "UPDATE image_tasks SET state=?,error=?,updated=?,owner=CASE WHEN state='running' THEN owner ELSE NULL END WHERE seq=?",
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
                "SELECT count(*) FROM image_tasks WHERE state IN ('preparing','running') OR (state='unknown' AND owner IS NOT NULL)"
            ).fetchone()[0]
            if active >= self.settings.concurrency:
                return None
            row = db.execute(
                "SELECT * FROM image_tasks WHERE state='queued' ORDER BY seq LIMIT 1"
            ).fetchone()
            if row is not None:
                db.execute(
                    "UPDATE image_tasks SET state='preparing',owner=?,updated=? WHERE seq=?",
                    (self.owner, time.time(), row["seq"]),
                )
            return row

    def finish(self, seq, state, images=None, error=None):
        with self.connect() as db:
            db.execute(
                "UPDATE image_tasks SET state=?,images=?,error=?,updated=? WHERE seq=? AND owner=? AND state IN ('preparing','running')",
                (
                    state,
                    json.dumps(images or [], ensure_ascii=False),
                    error,
                    time.time(),
                    seq,
                    self.owner,
                ),
            )

    async def execute(self, row):
        seq = row["seq"]
        dispatched = False
        images = []
        try:
            if row["base_url"] != self.settings.base_url:
                raise BusinessError(
                    "任务登记的服务地址与当前配置不同；未发起请求，请人工核对配置。"
                )
            task = ImageTask.model_validate_json(row["request"])
            async with asyncio.timeout(self.settings.timeout):
                references = [
                    await self.storage.loader.load(value) for value in task.reference_images
                ]
                if sum(len(ref.data) for ref in references) > 40 * MIB:
                    raise BusinessError("单项参考图总字节数超过40 MiB；未发起绘图请求。")
                if not self.settings.api_key:
                    raise BusinessError("未配置API密钥；未发起绘图请求。")
                with self.connect() as db:
                    changed = db.execute(
                        """UPDATE image_tasks SET state='running',updated=? WHERE seq=? AND owner=?
                        AND state='preparing' AND EXISTS(SELECT 1 FROM task_owners WHERE owner=? AND heartbeat>=?)""",
                        (time.time(), seq, self.owner, self.owner, time.time() - LEASE_SECONDS),
                    ).rowcount
                if not changed:
                    return
                dispatched = True
                media = await self.storage.provider.render(
                    task, references, row["actual_model"], row["api_format"]
                )
                with self.connect(readonly=True) as db:
                    still_owned = db.execute(
                        "SELECT 1 FROM image_tasks WHERE seq=? AND owner=? AND state='running'",
                        (seq, self.owner),
                    ).fetchone()
                if not still_owned:
                    return
                folder = self.storage.safe_output(self.storage.root / uuid.uuid4().hex)
                folder.mkdir(exist_ok=False)
                for index, item in enumerate(media):
                    path = self.storage.safe_output(folder / f"{index + 1:02}{item.suffix}")
                    with path.open("xb") as stream:
                        stream.write(item.data)
                    images.append(
                        SavedImage(
                            path=str(path),
                            mime_type=item.mime,
                            width=item.width,
                            height=item.height,
                            bytes=len(item.data),
                            sha256=item.digest,
                        ).model_dump()
                    )
                self.finish(seq, "succeeded", images)
        except asyncio.CancelledError:
            self.finish(
                seq,
                "unknown" if dispatched else "queued",
                images,
                "等待中断，上游结果和费用不确定；未自动重发。" if dispatched else None,
            )
            raise
        except (httpx.HTTPError, TimeoutError):
            self.finish(
                seq,
                "unknown" if dispatched else "failed",
                images,
                "请求或下载超时/网络失败；上游可能已收费，未自动重发。"
                if dispatched
                else "参考图准备超时/网络失败，未发起绘图请求。",
            )
        except BusinessError as exc:
            self.finish(seq, "failed", images, str(exc))
        except Exception:
            self.finish(seq, "failed", images, "任务处理或保存失败；请查询原标识，不自动重发。")
        finally:
            # Another Host may cancel a running call. Keep its slot until the original
            # local waiter really exits (or its owner lease expires).
            with self.connect() as db:
                db.execute(
                    "UPDATE image_tasks SET owner=NULL WHERE seq=? AND owner=? AND state NOT IN ('preparing','running')",
                    (seq, self.owner),
                )

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
