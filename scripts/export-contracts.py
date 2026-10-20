"""Regenerate JSON contracts from actual registered MCP components (no business calls)."""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

from fastmcp import Client

from zhenzhen_nanobanana_mcp.server import create_server
from zhenzhen_nanobanana_mcp.config import Settings


async def main():
    # Lifespan may resume queued tasks, so even discovery must use an empty private output.
    with tempfile.TemporaryDirectory(prefix="nanobanana-contract-") as directory:
        settings = Settings(api_key="contract-export-not-real", output_dir=Path(directory))
        async with Client(create_server(settings)) as client:
            contract = {
                "tools": [
                    t.model_dump(mode="json", by_alias=True) for t in await client.list_tools()
                ],
                "prompts": [
                    p.model_dump(mode="json", by_alias=True) for p in await client.list_prompts()
                ],
                "resources": [
                    r.model_dump(mode="json", by_alias=True) for r in await client.list_resources()
                ],
            }
    target = Path(__file__).resolve().parents[1] / "specs/003-async-image-tasks/contracts/mcp.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(contract, ensure_ascii=False, indent=2) + "\n"
    if "--check" in sys.argv:
        if target.read_text(encoding="utf-8") != encoded:
            raise SystemExit("Registered MCP contract differs; regenerate and review it.")
    else:
        target.write_text(encoded, encoding="utf-8")
    print(target)


if __name__ == "__main__":
    asyncio.run(main())
