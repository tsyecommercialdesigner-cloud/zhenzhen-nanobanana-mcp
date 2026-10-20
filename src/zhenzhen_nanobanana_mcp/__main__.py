import logging
import sys

from .config import BusinessError
from .server import create_server


def main():
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    try:
        create_server().run(transport="stdio", show_banner=False)
    except BusinessError as exc:
        print(f"配置错误：{exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
