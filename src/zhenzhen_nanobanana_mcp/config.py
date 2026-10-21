"""Explicit project .env credentials with fail-closed, field-level fallback."""

import io
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from dotenv.parser import parse_stream

PROJECT_ROOT = Path(__file__).resolve().parents[2]
API_KEY_FIELD = "ZHENZHEN_NANOBANANA_API_KEY"


class BusinessError(Exception):
    """Only explicitly safe messages cross the MCP boundary."""


def resolve_project_root() -> Path:
    """Use the known src layout or an explicit nonsecret absolute override; never search cwd."""
    if "NANOBANANA_PROJECT_DIR" in os.environ:
        root = Path(os.environ["NANOBANANA_PROJECT_DIR"])
        if not root.is_absolute() or not root.is_dir():
            raise BusinessError("NANOBANANA_PROJECT_DIR 必须为存在的项目绝对目录。")
        return root.resolve()
    if (
        Path(__file__).resolve().parent.parent.name != "src"
        or not (PROJECT_ROOT / "pyproject.toml").is_file()
    ):
        raise BusinessError("无法从安装布局确定项目目录；请设置 NANOBANANA_PROJECT_DIR 绝对路径。")
    return PROJECT_ROOT


def read_project_key(path: Path) -> tuple[bool, str | None]:
    """Return presence separately from value. Parser bindings are never logged/interpolated."""
    try:
        with path.open("rb") as stream:
            raw = stream.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise BusinessError("项目 .env 超过 1 MiB 解析限制。")
        text = raw.decode("utf-8-sig")
    except FileNotFoundError:
        # A broken symlink is an existing, unreadable configuration, not a missing file.
        if path.is_symlink():
            raise BusinessError("项目 .env 无法读取；不回退其他密钥。") from None
        return False, None
    except (OSError, UnicodeError):
        raise BusinessError("项目 .env 无法读取或不是 UTF-8；不回退其他密钥。") from None
    present, value = False, None
    for binding in parse_stream(io.StringIO(text)):
        if binding.error:
            raise BusinessError("项目 .env 存在语法错误；不回退其他密钥。")
        if binding.key == API_KEY_FIELD:
            if present:
                raise BusinessError(f"项目 .env 重复定义 {API_KEY_FIELD}；不回退其他密钥。")
            present, value = True, binding.value
    return present, value


def read_windows_user_value(name: str = API_KEY_FIELD) -> str | None:
    """Read only the current account's HKCU Environment; never change registry values."""
    if sys.platform != "win32":
        return None
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ) as key:
            value, kind = winreg.QueryValueEx(key, name)
        if kind not in (winreg.REG_SZ, winreg.REG_EXPAND_SZ) or not isinstance(value, str):
            raise BusinessError(f"Windows 当前用户环境中的 {name} 必须为字符串。")
        return value  # Do not expand references or inspect machine/other-user stores.
    except FileNotFoundError:
        return None
    except OSError:
        raise BusinessError(f"无法读取 Windows 当前用户环境中的 {name}。") from None


def validate_api_key(value: str | None, source: str) -> str:
    if value is None or not value.strip():
        raise BusinessError(f"{source} 的 {API_KEY_FIELD} 为空；不回退其他密钥。")
    if any(ord(c) < 32 or ord(c) > 126 for c in value):
        raise BusinessError(
            f"{source} 的 {API_KEY_FIELD} 格式无效；密钥不可含控制字符或非 ASCII 字符。"
        )
    value = value.strip()
    # Constraints come from the ASCII Authorization header transport, not an invented key prefix.
    if value.lower().startswith("bearer ") or any(ord(c) < 33 or ord(c) > 126 for c in value):
        raise BusinessError(
            f"{source} 的 {API_KEY_FIELD} 格式无效；应填写无空白的原始 ASCII 密钥。"
        )
    return value


def load_api_key(project_dir: Path) -> str:
    present, value = read_project_key(project_dir / ".env")
    if present:
        return validate_api_key(value, "项目 .env")
    if API_KEY_FIELD in os.environ:
        return validate_api_key(os.environ[API_KEY_FIELD], "进程环境")
    value = read_windows_user_value()
    if value is not None:
        return validate_api_key(value, "Windows 当前用户环境")
    raise BusinessError(f"缺少 {API_KEY_FIELD}；请在项目 .env 中配置，服务未启动。")


@dataclass(frozen=True)
class Settings:
    api_key: str = field(default="", repr=False)
    base_url: str = "https://ai.t8star.org"
    input_dirs: tuple[Path, ...] = ()  # Deprecated compatibility field; no access restriction.
    output_dir: Path = PROJECT_ROOT / "outputs"
    timeout: float = 300
    concurrency: int = 4
    max_pending_tasks: int = 200
    project_dir: Path = PROJECT_ROOT

    def __post_init__(self):
        url = urlsplit(self.base_url)
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
            or url.path not in ("", "/")
        ):
            raise BusinessError("NANOBANANA_BASE_URL 必须是无路径/凭据的 HTTPS 服务根地址。")
        if not 1 <= self.timeout <= 600 or not 1 <= self.concurrency <= 10:
            raise BusinessError("TIMEOUT_SECONDS 必须在 1–600 内，CONCURRENCY 必须在 1–10 内。")
        if not 12 <= self.max_pending_tasks <= 1000:
            raise BusinessError("MAX_PENDING_TASKS 必须在 12–1000 内。")
        if not self.output_dir.is_absolute():
            raise BusinessError("输出目录必须为绝对路径。")

    @classmethod
    def from_env(cls):
        try:
            project_dir = resolve_project_root()
            api_key = load_api_key(project_dir)
            return cls(
                api_key=api_key,
                base_url=os.environ.get("NANOBANANA_BASE_URL", "https://ai.t8star.org").rstrip("/"),
                output_dir=Path(
                    os.environ.get("NANOBANANA_OUTPUT_DIR", str(project_dir / "outputs"))
                ),
                timeout=float(os.environ.get("NANOBANANA_TIMEOUT_SECONDS", "300")),
                concurrency=int(os.environ.get("NANOBANANA_CONCURRENCY", "4")),
                max_pending_tasks=int(os.environ.get("NANOBANANA_MAX_PENDING_TASKS", "200")),
                project_dir=project_dir,
            )
        except (ValueError, OverflowError) as exc:
            raise BusinessError("环境配置数值不合法。") from exc
