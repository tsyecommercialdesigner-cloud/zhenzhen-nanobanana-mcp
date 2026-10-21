"""Persistent batch ledger and independently saved image results."""

import asyncio
import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

import httpx

from .config import BusinessError, Settings
from .media import MIB, MediaLoader
from .models import (
    ApiFormat,
    BatchResult,
    ImageSpec,
    ItemResult,
    ModelName,
    SavedImage,
    route_model,
)
from .provider import Provider
from .limits import MAX_BATCH_ITEMS


class BatchService:
    def __init__(
        self,
        settings: Settings,
        provider: Provider | None = None,
        loader: MediaLoader | None = None,
    ):
        self.settings = settings
        self.loader = loader or MediaLoader(
            settings.input_dirs,
            settings.timeout,
            safe_attempts=settings.safe_attempts,
            retry_delay=settings.retry_delay,
        )
        self.provider = provider or Provider(settings, self.loader)
        self.semaphore = asyncio.Semaphore(settings.concurrency)
        self.root = settings.output_dir.resolve()

    def safe_output(self, path: Path) -> Path:
        resolved = path.resolve()
        if not resolved.is_relative_to(self.root):
            raise BusinessError("输出路径越过已配置目录。")
        return resolved

    @contextmanager
    def connect(self, readonly: bool = False):
        if not readonly:
            self.root.mkdir(parents=True, exist_ok=True)
        db = self.safe_output(self.root / "batches.sqlite3")
        if readonly and not db.exists():
            raise BusinessError("未找到该请求编号。")
        connection = (
            sqlite3.connect(db.as_uri() + "?mode=ro", uri=True, timeout=5)
            if readonly
            else sqlite3.connect(db, timeout=5)
        )
        try:
            with connection:
                if not readonly:
                    connection.execute(
                        "CREATE TABLE IF NOT EXISTS batches ("
                        "request_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, "
                        "result TEXT NOT NULL)"
                    )
                yield connection
        finally:
            connection.close()

    def get(self, request_id: str) -> BatchResult:
        with self.connect(readonly=True) as db:
            row = db.execute(
                "SELECT result FROM batches WHERE request_id = ?", (request_id,)
            ).fetchone()
        if not row:
            raise BusinessError("未找到该请求编号。")
        result = BatchResult.model_validate_json(row[0])
        for item in result.items:
            if item.actual_model is None:
                item.actual_model = result.model
        result.reused = True
        if result.status == "running":
            result.warning = "批次正在运行或曾被中断；请勿更换编号盲目重发，先核对已有结果和费用。"
        return result

    def existing(self, request_id: str, fingerprint: str) -> BatchResult | None:
        if not self.safe_output(self.root / "batches.sqlite3").exists():
            return None
        with self.connect(readonly=True) as db:
            row = db.execute(
                "SELECT fingerprint, result FROM batches WHERE request_id = ?", (request_id,)
            ).fetchone()
        if row:
            if row[0] != fingerprint:
                raise BusinessError("请求编号已绑定其他参数；拒绝重复提交。")
            result = self.get(request_id)
            if result.status == "running":
                raise BusinessError(
                    "请求已登记，正在运行或被中断；使用 get_batch_result 查询，不自动重发。"
                )
            return result
        return None

    def persist(self, result: BatchResult):
        manifest = self.safe_output(Path(result.manifest_path))
        encoded = result.model_dump_json(indent=2)
        # The database is the authoritative recovery record if writing the manifest fails.
        with self.connect() as db:
            db.execute(
                "UPDATE batches SET result = ? WHERE request_id = ?", (encoded, result.request_id)
            )
        temporary = self.safe_output(manifest.with_name(f".{uuid.uuid4().hex}.tmp"))
        with temporary.open("x", encoding="utf-8") as stream:
            stream.write(encoded)
        temporary.replace(manifest)

    async def run(
        self,
        request_id: str,
        specs: list[ImageSpec],
        model: ModelName,
        api_format: ApiFormat,
        progress=None,
    ) -> BatchResult:
        if not 1 <= len(specs) <= MAX_BATCH_ITEMS:
            raise BusinessError("批次必须有 1–20 项。")
        canonical = json.dumps(
            {
                "items": [s.model_dump(exclude_none=True) for s in specs],
                "model": model,
                "api_format": api_format,
                "base_url": self.settings.base_url,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        fingerprint = hashlib.sha256(canonical.encode()).hexdigest()
        previous = self.existing(request_id, fingerprint)
        if previous:
            return previous
        if not self.settings.api_key:
            raise BusinessError("未配置 ZHENZHEN_NANOBANANA_API_KEY；未发起收费请求。")
        references, loaded = [], {}
        # Preflight the entire batch before any billable POST. Keep repeated inputs in one snapshot.
        try:
            async with asyncio.timeout(self.settings.timeout):
                for spec in specs:
                    refs = []
                    for value in spec.reference_images:
                        if value not in loaded:
                            loaded[value] = await self.loader.load(value)
                            if sum(len(ref.data) for ref in loaded.values()) > 80 * MIB:
                                raise BusinessError("批次不同参考图总字节数超过 80 MiB。")
                        refs.append(loaded[value])
                    if sum(len(ref.data) for ref in refs) > 40 * MIB:
                        raise BusinessError("单项参考图总字节数超过 40 MiB。")
                    references.append(refs)
        except (httpx.HTTPError, TimeoutError) as exc:
            raise BusinessError("参考图准备失败或超时；未发起收费请求。") from exc

        batch_id = uuid.uuid4().hex
        folder = self.safe_output(self.root / batch_id)
        result = BatchResult(
            request_id=request_id,
            batch_id=batch_id,
            model=model,
            api_format=api_format,
            status="running",
            items=[
                ItemResult(
                    index=i,
                    operation="edit" if refs else "generate",
                    actual_model=route_model(model, specs[i].resolution),
                )
                for i, refs in enumerate(references)
            ],
            manifest_path=str(folder / "manifest.json"),
        )
        with self.connect() as db:
            try:
                db.execute(
                    "INSERT INTO batches VALUES (?, ?, ?)",
                    (request_id, fingerprint, result.model_dump_json()),
                )
            except sqlite3.IntegrityError:
                # Another Host may have claimed this ID during preflight.
                claimed = self.existing(request_id, fingerprint)
                if claimed is None:
                    raise BusinessError("请求登记状态异常；请查询原编号，不自动重发。")
                return claimed

        completed = 0

        async def run_item(index: int):
            nonlocal completed
            item = result.items[index]
            async with self.semaphore:
                try:
                    item.status = "running"
                    self.persist(result)
                    actual_model = item.actual_model
                    if actual_model is None:
                        raise BusinessError("缺少本项实际模型；未发起收费请求。")
                    async with asyncio.timeout(self.settings.timeout):
                        images = await self.provider.render(
                            specs[index], references[index], actual_model, api_format
                        )
                        for number, media in enumerate(images):
                            path = self.safe_output(
                                folder / f"{index + 1:02}_{number + 1:02}{media.suffix}"
                            )
                            with path.open("xb") as stream:
                                stream.write(media.data)
                            item.images.append(
                                SavedImage(
                                    path=str(path),
                                    mime_type=media.mime,
                                    width=media.width,
                                    height=media.height,
                                    bytes=len(media.data),
                                    sha256=media.digest,
                                )
                            )
                    item.status = "succeeded"
                except (httpx.TimeoutException, TimeoutError):
                    item.status = "failed"
                    item.error = "绘图或下载超时；上游可能已收费，未自动重试。"
                except BusinessError as exc:
                    item.status, item.error = "failed", str(exc)
                except httpx.HTTPError:
                    item.status, item.error = "failed", "绘图/下载网络失败；未自动重试。"
                except Exception:
                    item.status, item.error = "failed", "绘图结果处理或保存失败；未自动重试。"
                self.persist(result)
                completed += 1
                if progress:
                    try:
                        await progress(completed, len(specs))
                    except Exception:
                        pass  # A disconnected progress channel must not rerun a billable call.

        tasks = []
        try:
            folder.mkdir(exist_ok=False)
            self.persist(result)
            # Only image hashes are persisted; reference bytes and prompts remain in memory.
            snapshot = self.safe_output(folder / "reference-hashes.json")
            with snapshot.open("x", encoding="utf-8") as stream:
                json.dump([[r.digest for r in refs] for refs in references], stream, indent=2)
            tasks = [asyncio.create_task(run_item(i)) for i in range(len(specs))]
            await asyncio.gather(*tasks)
            successes = sum(item.status == "succeeded" for item in result.items)
            result.status = (
                "succeeded" if successes == len(specs) else "partial" if successes else "failed"
            )
            self.persist(result)
            return result
        except asyncio.CancelledError:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            for item in result.items:
                if item.status in ("pending", "running"):
                    item.status = "cancelled"
                    item.error = "本地等待已取消；远端可能已收费，未自动重试。"
            result.status = "cancelled"
            result.warning = "取消本地等待不保证上游停止或退款。"
            self.persist(result)
            raise
        except Exception as exc:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            for item in result.items:
                if item.status in ("pending", "running"):
                    item.status, item.error = "failed", "批次处理失败；使用结果工具查询已保存图片。"
            result.status = "failed"
            try:
                self.persist(result)
            except Exception:
                pass
            raise BusinessError("批次处理失败；请求编号已登记，未自动重发，请查询结果。") from exc
