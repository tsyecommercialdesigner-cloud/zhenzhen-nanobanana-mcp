"""Bounded image decoding and public HTTP(S) download with DNS pinning."""

import asyncio
import base64
import binascii
import hashlib
import io
import ipaddress
import socket
import warnings
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx
from PIL import Image, UnidentifiedImageError

from .config import BusinessError
from .limits import SAFE_ATTEMPTS, RETRY_DELAY

MIB = 1024 * 1024


class TransientDownloadError(BusinessError):
    """A read-only GET failed transiently; retry never generates another image."""


MAX_INPUT_BYTES = 20 * MIB
MAX_OUTPUT_BYTES = 32 * MIB
MAX_PIXELS = 64_000_000
IMAGE_TYPES = {
    "PNG": ("image/png", ".png"),
    "JPEG": ("image/jpeg", ".jpg"),
    "WEBP": ("image/webp", ".webp"),
}


@dataclass(frozen=True)
class Media:
    data: bytes
    mime: str
    suffix: str
    width: int
    height: int

    @property
    def b64(self):
        return base64.b64encode(self.data).decode("ascii")

    @property
    def data_url(self):
        return f"data:{self.mime};base64,{self.b64}"

    @property
    def digest(self):
        return hashlib.sha256(self.data).hexdigest()


def decode_image(data: bytes, limit: int = MAX_OUTPUT_BYTES) -> Media:
    if not data or len(data) > limit:
        raise BusinessError("图片为空或超过字节限制。")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                fmt = image.format
                width, height = image.size
                if fmt not in IMAGE_TYPES or width * height > MAX_PIXELS:
                    raise BusinessError("仅支持 PNG/JPEG/WebP，图片不可超过 64M 像素。")
                image.verify()
            # verify() alone does not decode all raster formats.
            with Image.open(io.BytesIO(data)) as image:
                if getattr(image, "n_frames", 1) != 1:
                    raise BusinessError("不支持动画图片。")
                image.load()
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise BusinessError("图片内容无法安全解码。") from exc
    mime, suffix = IMAGE_TYPES[fmt]
    return Media(data, mime, suffix, width, height)


def decode_b64(value: str) -> bytes:
    if value.startswith("data:"):
        header, sep, value = value.partition(",")
        if not sep or not header.startswith("data:image/") or not header.endswith(";base64"):
            raise BusinessError("图片 data URL 格式无效。")
    if len(value) > ((MAX_OUTPUT_BYTES + 2) // 3) * 4:
        raise BusinessError("base64 图片超过字节限制。")
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise BusinessError("上游 base64 图片无效。") from exc


def validate_image_url(url: str):
    try:
        parts = urlsplit(url)
        if (
            parts.scheme not in ("http", "https")
            or not parts.hostname
            or parts.username
            or parts.password
            or parts.port not in (None, 80 if parts.scheme == "http" else 443)
            or parts.fragment
        ):
            raise BusinessError(
                "图片 URL 必须为无凭据、无片段的公开 HTTP/HTTPS 地址，端口为 80/443。"
            )
        if "%" in parts.hostname:
            raise BusinessError("不允许带作用域的 URL 主机。")
        return parts
    except ValueError as exc:
        raise BusinessError("图片 URL 格式无效。") from exc


async def public_ip(host: str, port: int = 443) -> str:
    try:
        addresses = await asyncio.get_running_loop().getaddrinfo(
            host,
            port,
            type=socket.SOCK_STREAM,
        )
        ips = [a[4][0] for a in addresses]
        if not ips or any(
            not ipaddress.ip_address(ip).is_global or ipaddress.ip_address(ip).is_multicast
            for ip in ips
        ):
            raise BusinessError("拒绝访问非公网图片地址。")
        return ips[0]
    except (OSError, ValueError) as exc:
        raise BusinessError("无法解析图片地址。") from exc


async def bounded_read(response: httpx.Response, limit: int) -> bytes:
    try:
        length = response.headers.get("content-length")
        if length is not None and int(length) > limit:
            raise BusinessError("上游响应超过字节限制。")
    except ValueError as exc:
        raise BusinessError("上游响应长度无效。") from exc
    data = bytearray()
    async for part in response.aiter_bytes():
        if len(data) + len(part) > limit:
            raise BusinessError("上游响应超过字节限制。")
        data.extend(part)
    return bytes(data)


class MediaLoader:
    def __init__(
        self,
        roots: tuple[Path, ...],
        timeout: float,
        transport: httpx.AsyncBaseTransport | None = None,
        safe_attempts: int = SAFE_ATTEMPTS,
        retry_delay: float = RETRY_DELAY,
    ):
        # The former roots argument is accepted for compatibility, never used to restrict files.
        self.timeout = timeout
        self.transport = transport
        self.safe_attempts, self.retry_delay = safe_attempts, retry_delay

    async def download(self, url: str, limit: int = MAX_OUTPUT_BYTES) -> bytes:
        async with asyncio.timeout(self.timeout):
            for attempt in range(self.safe_attempts):
                try:
                    return await self.download_once(url, limit)
                except (httpx.HTTPError, TimeoutError, TransientDownloadError):
                    if attempt + 1 == self.safe_attempts:
                        raise
                    await asyncio.sleep(self.retry_delay * 2**attempt)
        raise BusinessError("图片下载未完成。")

    async def download_once(self, url: str, limit: int) -> bytes:
        async with asyncio.timeout(self.timeout):
            async with httpx.AsyncClient(
                trust_env=False, timeout=self.timeout, transport=self.transport
            ) as client:
                for _ in range(4):
                    parts = validate_image_url(url)
                    ip = await public_ip(parts.hostname, 80 if parts.scheme == "http" else 443)
                    pinned = httpx.URL(url).copy_with(host=ip)
                    # httpcore connects to the vetted IP but verifies TLS against the original host.
                    async with client.stream(
                        "GET",
                        pinned,
                        headers={"Host": parts.netloc},
                        extensions={"sni_hostname": parts.hostname},
                    ) as response:
                        if response.status_code in (301, 302, 303, 307, 308):
                            location = response.headers.get("location")
                            if not location:
                                raise BusinessError("图片重定向缺少地址。")
                            url = urljoin(url, location)
                            continue
                        if response.status_code in (429, 500, 502, 503, 504):
                            raise TransientDownloadError(
                                f"图片下载暂时失败（HTTP {response.status_code}）。"
                            )
                        if response.status_code != 200:
                            raise BusinessError(f"图片下载失败（HTTP {response.status_code}）。")
                        return await bounded_read(response, limit)
                raise BusinessError("图片重定向次数过多。")

    async def load(self, value: str) -> Media:
        if value.lower().startswith(("https://", "http://")):
            return decode_image(await self.download(value, MAX_INPUT_BYTES), MAX_INPUT_BYTES)
        path = Path(value)
        if not path.is_absolute():
            raise BusinessError("参考图必须为本机图片绝对路径或公开 HTTP/HTTPS URL。")
        try:
            path = path.resolve(strict=True)
            if not path.is_file():
                raise BusinessError("参考图路径必须指向普通图片文件。")
            with path.open("rb") as stream:
                data = stream.read(MAX_INPUT_BYTES + 1)
            return decode_image(data, MAX_INPUT_BYTES)
        except OSError as exc:
            raise BusinessError("无法读取参考图。") from exc
