"""Static template checks; do not expand or print real credentials."""

import json
import re
import tomllib
from pathlib import Path

import yaml

root = Path(__file__).resolve().parents[1]
text = (root / "MANUAL.md").read_text(encoding="utf-8")
for block in re.findall(r"```json\n(.*?)\n```", text, re.DOTALL):
    json.loads(block)
for match in re.finditer(r"<!-- template:([^>]+) -->\n\n```\w+\n(.*?)\n```", text, re.DOTALL):
    assert match.group(2) == (root / match.group(1)).read_text(encoding="utf-8").rstrip()
for filename in (".mcp.json.example", "templates/claude-code.mcp.json.example"):
    data = json.loads((root / filename).read_text(encoding="utf-8"))
    entry = data["mcpServers"]["zhenzhen-nanobanana-mcp"]
    assert "cwd" not in entry and "env" not in entry and entry["command"] == "uv"
config = tomllib.loads((root / "templates/codex.config.toml.example").read_text(encoding="utf-8"))
assert (
    "ZHENZHEN_NANOBANANA_API_KEY"
    not in config["mcp_servers"]["zhenzhen-nanobanana-mcp"]["env_vars"]
)
assert "env" not in data["mcpServers"]["zhenzhen-nanobanana-mcp"]
assert (root / ".env.example").read_text(encoding="utf-8").splitlines()[
    -1
] == "ZHENZHEN_NANOBANANA_API_KEY="


class InertLoader(yaml.SafeLoader):
    pass


InertLoader.add_constructor(
    "tag:yaml.org,2002:js",
    lambda loader, node: {
        "__jsExpr": loader.construct_scalar(node),
    },
)
patch = yaml.load(
    (root / "templates/dsh.patch.yml.example").read_text(encoding="utf-8"), Loader=InertLoader
)
entry = patch[0]["insert"][0]
assert entry["name"] == "@deepseek-ai/dsh-mcp-client"
assert "env" not in entry["config"]
assert len(entry["config"]["serverName"]) <= 32
schema_path = root / ".cache/dsh-schema.json"
if schema_path.exists():
    from jsonschema import Draft202012Validator

    schema = json.loads(schema_path.read_text(encoding="utf-8-sig"))
    local_schema = {"$defs": schema["$defs"], "$ref": "#/$defs/config98"}
    errors = list(Draft202012Validator(local_schema).iter_errors(entry["config"]))
    assert not errors, [error.message for error in errors]
assert len(re.findall(r"^## \d+\.", text, re.MULTILINE)) == 10
repository_url = "https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp.git"
assert repository_url in text
for required in (
    "git clone --branch",
    "release-eligibility.json",
    "ExpectedCommit",
    "--no-overwrite-ignore",
    "## 5. 启动排障",
):
    assert required in text, required
# README was rewritten by explicit user request; its quickstart must agree with the manual.
readme = (root / "README.md").read_text(encoding="utf-8")
for required in (
    "MANUAL.md",
    "ZHENZHEN_NANOBANANA_API_KEY",
    "sync --locked --no-dev",
    "run --no-sync",
    "submit_image_tasks",
    "get_image_tasks",
    "checkpointer, thread_id, task_id",
):
    assert required in readme, required
assert re.search(r"\b[0-9a-f]{40}\b", readme), "README needs a full verified commit SHA"
for target in re.findall(r"\]\(([^)]+)\)", readme):
    if "://" not in target and not target.startswith("#"):
        assert (root / target.split("#", 1)[0]).is_file(), target
assert "https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/releases" in text
for entry in json.loads((root / "user-files.json").read_text(encoding="utf-8")):
    assert (root / entry).is_file(), entry
print("JSON/TOML/inert YAML, manual templates, ten sections and delivery inputs passed.")
