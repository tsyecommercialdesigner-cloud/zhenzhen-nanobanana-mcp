"""No-network stdio fixture: render waits for a test-controlled file, never calls an API."""

import asyncio
import io
import hashlib
import sys
import os
from pathlib import Path

from PIL import Image

from zhenzhen_nanobanana_mcp.config import BusinessError, Settings
from zhenzhen_nanobanana_mcp.media import decode_image
from zhenzhen_nanobanana_mcp.server import create_server
from zhenzhen_nanobanana_mcp.tasks import TaskQueue


def main():
    root = Path(sys.argv[1])
    (root / f"process-{os.getpid()}.pid").write_text(str(os.getpid()), encoding="ascii")
    settings = Settings(
        api_key="stdio-fixture-not-real", output_dir=root / "output", timeout=10, concurrency=2
    )
    queue = TaskQueue(settings)

    async def render(spec, *args):
        posts = root / "fake-posts"
        posts.mkdir(exist_ok=True)
        # Exclusive per-task marker makes any duplicate cross-process dispatch observable.
        with (posts / hashlib.sha256(spec.task_id.encode()).hexdigest()).open("x") as marker:
            marker.write("fake provider entered")
        if spec.prompt == "fail":
            raise BusinessError("fixture upstream failure")
        while not (root / "release-gate").exists():
            await asyncio.sleep(0.02)
        data = io.BytesIO()
        Image.new("RGB", (16, 16), "blue").save(data, format="PNG")
        return [decode_image(data.getvalue())]

    queue.storage.provider.render = render
    create_server(settings, queue=queue).run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
