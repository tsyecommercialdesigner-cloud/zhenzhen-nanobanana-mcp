"""Isolated fake credentials and zero-business-network stdio checks."""

import asyncio
import json
import os
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

TOOLS = {
    "list_models",
    "plan_ecommerce_images",
    "submit_image_tasks",
    "generate_images",
    "wait_image_tasks",
    "get_image_tasks",
    "cancel_image_tasks",
    "get_batch_result",
}


async def check(mode: str, temporary: Path):
    project = temporary / f"config-{mode}"
    project.mkdir()
    (project / ".env").write_text(
        "ZHENZHEN_NANOBANANA_API_KEY=smoke-test-not-real\n", encoding="utf-8"
    )
    unrelated = temporary / f"host-cwd-{mode}"
    unrelated.mkdir()
    (unrelated / ".env").write_text("ZHENZHEN_NANOBANANA_API_KEY=\n", encoding="utf-8")
    env = dict(os.environ)
    env["ZHENZHEN_NANOBANANA_API_KEY"] = (
        ""  # File precedence must win over even an invalid process value.
    )
    env["NANOBANANA_PROJECT_DIR"] = str(project)
    env["NANOBANANA_BASE_URL"] = "https://ai.t8star.org"
    env["NANOBANANA_TIMEOUT_SECONDS"] = "300"
    env["NANOBANANA_CONCURRENCY"] = "2"
    env["NANOBANANA_MAX_PENDING_TASKS"] = "200"
    if mode == "legacy":
        env["NANOBANANA_INPUT_DIRS"] = str(temporary / "input")
    else:
        env.pop("NANOBANANA_INPUT_DIRS", None)
    env["NANOBANANA_OUTPUT_DIR"] = str(temporary / mode)
    transport = StdioTransport(
        command=sys.executable,
        args=["-m", "zhenzhen_nanobanana_mcp"],
        env=env,
        cwd=str(unrelated),
        keep_alive=False,
    )
    async with Client(transport, mode=mode, timeout=30, init_timeout=30) as client:
        tools = await client.list_tools()
        assert {tool.name for tool in tools} == TOOLS
        assert all(tool.output_schema for tool in tools)
        catalog = await client.call_tool("list_models", {})
        assert not catalog.is_error
        assert catalog.structured_content["api_key_configured"] is True
        assert catalog.structured_content["local_file_access"] == "readable_files"
        assert catalog.structured_content["input_dirs"] == []
        assert len(catalog.structured_content["models"]) == 7
        assert catalog.structured_content["default_model"] == "gemini-nano-banana-2.1"
        assert catalog.structured_content["sync_generation"] is True
        for name in ("generate_images", "wait_image_tasks"):
            schema = next(tool for tool in tools if tool.name == name).input_schema
            assert schema["properties"]["wait_timeout_seconds"]["maximum"] == 1200
        missing_wait = await client.call_tool(
            "wait_image_tasks",
            {"checkpointer": "smoke", "thread_id": "validation", "task_ids": ["missing"]},
            raise_on_error=False,
        )
        assert missing_wait.is_error
        invalid_wait = await client.call_tool(
            "generate_images",
            {
                "checkpointer": "smoke",
                "thread_id": "validation",
                "tasks": [{"task_id": "never-submit", "prompt": "test"}],
                "wait_timeout_seconds": 0,
            },
            raise_on_error=False,
        )
        assert invalid_wait.is_error
        submit_tool = next(tool for tool in tools if tool.name == "submit_image_tasks")
        assert submit_tool.input_schema["properties"]["tasks"]["maxItems"] == 12
        assert catalog.structured_content["capabilities"]["nano-banana-pro"] == ["dalle"]
        assert catalog.structured_content["supported_endpoints"]["gemini-nano-banana-2.1"] == [
            "generations"
        ]
        plan = await client.call_tool(
            "plan_ecommerce_images",
            {
                "product_name": "棉麻收纳篮",
                "selling_points": ["棉麻材质"],
                "scene": "detail",
                "count": 6,
                "resolution": {"width": 1536, "height": 2048},
            },
        )
        assert len(plan.structured_content["items"]) == 6
        assert all(
            item["resolution"] == {"width": 1536, "height": 2048}
            for item in plan.structured_content["items"]
        )
        for resolution in ({"width": 0, "height": 1}, {"width": "2048", "height": 1}):
            invalid_resolution = await client.call_tool(
                "submit_image_tasks",
                {
                    "checkpointer": "smoke",
                    "thread_id": "validation",
                    "tasks": [
                        {
                            "task_id": "invalid-resolution",
                            "prompt": "test",
                            "resolution": resolution,
                        }
                    ],
                },
                raise_on_error=False,
            )
            assert invalid_resolution.is_error
        failed = await client.call_tool(
            "submit_image_tasks",
            {
                "checkpointer": "smoke",
            },
            raise_on_error=False,
        )
        assert failed.is_error
        invalid = await client.call_tool(
            "submit_image_tasks",
            {
                "checkpointer": "smoke",
                "thread_id": "validation",
                "tasks": [{"task_id": "invalid", "prompt": "test", "aspect_ratio": "7:9"}],
            },
            raise_on_error=False,
        )
        assert invalid.is_error
        unsupported = await client.call_tool(
            "submit_image_tasks",
            {
                "checkpointer": "smoke",
                "thread_id": "validation",
                "tasks": [
                    {
                        "task_id": "unsupported",
                        "prompt": "test",
                        "model": "nano-banana-pro",
                        "api_format": "gemini",
                    }
                ],
            },
            raise_on_error=False,
        )
        assert unsupported.is_error
        empty = await client.call_tool(
            "get_image_tasks", {"checkpointer": "smoke", "thread_id": "validation"}
        )
        assert empty.structured_content["tasks"] == []
        assert len(await client.list_prompts()) == 1
        assert len(await client.list_resources()) == 1
        resource = await client.read_resource("nanobanana://capabilities")
        assert "gemini-nano-banana-2.1" in resource[0].text
        prompt = await client.get_prompt("ecommerce_brief", {"product_name": "收纳篮"})
        assert prompt.messages
        return {
            "mode": mode,
            "protocol": client.session.protocol_version,
            "tools": sorted(TOOLS),
            "prompts": 1,
            "resources": 1,
            "business_network_calls": 0,
            "isolated_project_env": True,
        }


async def check_invalid_startup(temporary: Path):
    project = temporary / "invalid-config"
    project.mkdir()
    (project / ".env").write_text("ZHENZHEN_NANOBANANA_API_KEY=\n", encoding="utf-8")
    env = dict(os.environ)
    env["NANOBANANA_PROJECT_DIR"] = str(project)
    env["ZHENZHEN_NANOBANANA_API_KEY"] = "smoke-fallback-not-real"
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "zhenzhen_nanobanana_mcp",
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
    except TimeoutError:
        process.kill()
        await process.communicate()
        raise
    assert process.returncode == 2 and not stdout
    assert b"ZHENZHEN_NANOBANANA_API_KEY" in stderr and b"smoke-fallback-not-real" not in stderr
    return {"empty_file_key_startup_exit_code": 2, "fallback_blocked": True}


async def main_async():
    with tempfile.TemporaryDirectory(prefix="nanobanana-smoke-") as temp:
        results = [await check(mode, Path(temp)) for mode in ("auto", "legacy")]
        startup = await check_invalid_startup(Path(temp))
    print(
        json.dumps(
            {
                "status": "passed",
                "python": sys.version.split()[0],
                "fastmcp": version("fastmcp"),
                "mcp_sdk": version("mcp"),
                "checks": results,
                "invalid_startup": startup,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main_async())
