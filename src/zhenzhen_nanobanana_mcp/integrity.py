"""Atomic verified files. Preserve mismatching output instead of overwriting it."""

import hashlib
import os
import uuid
from pathlib import Path

from .config import BusinessError


def digest_file(path: Path, limit: int) -> str:
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            count += len(block)
            if count > limit:
                raise BusinessError("文件超过已记录的大小上限。")
            digest.update(block)
    return digest.hexdigest()


def publish(path: Path, data: bytes, repair=False) -> None:
    """A complete, checked temp file becomes visible exclusively via an atomic link."""
    digest = hashlib.sha256(data).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            matches = digest_file(path, len(data)) == digest
        except BusinessError:
            matches = False
        if matches:
            return
        if not repair:
            raise BusinessError("输出文件SHA256不匹配；未覆盖。请核对后用repair_files显式修复。")
        path.rename(path.with_name(path.name + ".corrupt-" + uuid.uuid4().hex))
    temporary = path.with_name("." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if digest_file(temporary, len(data)) != digest:
            raise BusinessError("暂存文件SHA256校验失败，未发布输出。")
        try:
            os.link(temporary, path)
        except FileExistsError:
            if digest_file(path, len(data)) != digest:
                raise BusinessError("输出位置存在内容冲突；未覆盖已有文件。") from None
    finally:
        temporary.unlink(missing_ok=True)
