"""Independent process load worker; all image rendering is an isolated fake."""

import asyncio
import io
import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from PIL import Image

from zhenzhen_nanobanana_mcp.config import Settings
from zhenzhen_nanobanana_mcp.media import decode_image
from zhenzhen_nanobanana_mcp.tasks import TaskQueue


async def main():
    root = Path(sys.argv[1])
    queue = TaskQueue(
        Settings(
            api_key="load-fixture-not-real",
            output_dir=root / "output",
            concurrency=5,
            retry_delay=0.01,
        )
    )
    data = io.BytesIO()
    Image.new("RGB", (16, 16), "blue").save(data, format="PNG")
    media = decode_image(data.getvalue())

    def change_active(delta):
        with closing(sqlite3.connect(root / "metrics.sqlite3", timeout=5)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("UPDATE metrics SET active=active+?", (delta,))
            db.execute("UPDATE metrics SET peak=MAX(peak,active)")

    async def render(spec, *args):
        while not (root / "go").exists():
            await asyncio.sleep(0.01)
        with (root / "posts" / spec.task_id).open("x") as stream:
            stream.write(str(os.getpid()))
        change_active(1)
        try:
            await asyncio.sleep(0.02)
            return [media]
        finally:
            change_active(-1)

    queue.storage.provider.render = render
    await queue.start()
    (root / f"ready-{os.getpid()}").touch()
    try:
        while not (root / "stop").exists():
            await asyncio.sleep(0.02)
    finally:
        await queue.close()


if __name__ == "__main__":
    asyncio.run(main())
