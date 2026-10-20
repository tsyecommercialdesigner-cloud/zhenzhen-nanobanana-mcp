"""Install the actual user ZIP with an empty dedicated cache, then run member smoke."""

import json
import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
archive = (
    Path(sys.argv[1]).resolve()
    if len(sys.argv) > 1
    else root / f".cache/package-audit/zhenzhen-nanobanana-mcp-{version}-user.zip"
)
whitelist = json.loads((root / "user-files.json").read_text(encoding="utf-8"))
project_name = "zhenzhen-nanobanana-mcp"
prefix = project_name + "/"
expected_entries = [prefix + path for path in whitelist]
before = hashlib.sha256(archive.read_bytes()).hexdigest()
refusal = subprocess.run(
    [
        shutil.which("pwsh"),
        "-NoProfile",
        "-File",
        str(root / "scripts/package-user.ps1"),
        "-DestinationDirectory",
        str(archive.parent),
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=60,
)
assert refusal.returncode != 0 and "Release already exists" in refusal.stderr
assert hashlib.sha256(archive.read_bytes()).hexdigest() == before
print("Existing ZIP overwrite rejected; original SHA-256 unchanged.", flush=True)
with zipfile.ZipFile(archive) as source:
    assert sorted(source.namelist()) == sorted(expected_entries)
    assert len(source.namelist()) == len(set(source.namelist()))
    assert prefix + ".env" not in source.namelist()
    assert (
        source.read(prefix + ".env.example").decode("utf-8").splitlines()[-1]
        == "NANOBANANA_API_KEY="
    )
with tarfile.open(root / f"dist/zhenzhen_nanobanana_mcp-{version}.tar.gz") as source:
    names = source.getnames()
    assert not any(
        set(Path(name).parts) & {".cache", ".venv", "outputs", "input"} for name in names
    )
    assert not any(
        Path(name).name.startswith(".env") and Path(name).name != ".env.example" for name in names
    )

with tempfile.TemporaryDirectory(prefix="nanobanana-delivery-") as temporary:
    audit_root = Path(temporary).resolve()
    assert audit_root.is_relative_to(Path(tempfile.gettempdir()).resolve())
    install_parent = audit_root / "MCP"
    project = install_parent / project_name
    cache = audit_root / "empty-uv-cache"
    install_parent.mkdir()
    assert not project.exists()
    assert not cache.exists()
    with zipfile.ZipFile(archive) as source:
        for name in source.namelist():
            assert (install_parent / name).resolve().is_relative_to(project)
        source.extractall(install_parent)
    assert project.is_dir() and (project / "pyproject.toml").is_file()
    assert not (project / project_name).exists()
    private_env = project / ".env"
    private_env.write_text("NANOBANANA_API_KEY=upgrade-test-not-real\n", encoding="utf-8")
    acl_script = audit_root / "read-acl.ps1"
    acl_script.write_text(
        "param([string]$Target)\n(Get-Acl -LiteralPath $Target).Sddl\n", encoding="utf-8"
    )

    def acl():
        return subprocess.run(
            [
                shutil.which("pwsh"),
                "-NoProfile",
                "-File",
                str(acl_script),
                "-Target",
                str(private_env),
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        ).stdout

    before_content, before_acl = private_env.read_bytes(), acl()
    with zipfile.ZipFile(archive) as source:
        source.extractall(
            install_parent
        )  # Simulate upgrading program files into an existing installation.
    assert private_env.read_bytes() == before_content and acl() == before_acl
    print("Upgrade preserved existing .env content and NTFS ACL.", flush=True)
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env.pop("NANOBANANA_PROJECT_DIR", None)
    env["NANOBANANA_API_KEY"] = "environment-not-real"
    env["NANOBANANA_BASE_URL"] = "https://ai.t8star.org"
    env["NANOBANANA_INPUT_DIRS"] = str(project / "input")
    env["NANOBANANA_OUTPUT_DIR"] = str(project / "outputs")
    env["NANOBANANA_TIMEOUT_SECONDS"] = "300"
    env["NANOBANANA_CONCURRENCY"] = "2"
    env["UV_PROJECT_ENVIRONMENT"] = str(project / ".venv")
    command = [
        "uv",
        "--cache-dir",
        str(cache),
        "--directory",
        str(project),
        "sync",
        "--locked",
        "--no-dev",
    ]
    install = subprocess.run(
        command,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    if install.returncode:
        print(install.stderr[-6000:], file=sys.stderr)
        raise SystemExit(install.returncode)
    print("Empty-cache locked member installation passed.", flush=True)
    python = project / ".venv/Scripts/python.exe"
    probe = subprocess.run(
        [str(python), "-c", "import fastmcp; print(fastmcp.__file__)"],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    assert Path(probe.stdout.strip()).is_relative_to(project / ".venv")
    subprocess.run(
        [
            str(python),
            "-c",
            "import sys; from pathlib import Path; from zhenzhen_nanobanana_mcp.config import Settings; "
            "s=Settings.from_env(); assert s.api_key=='upgrade-test-not-real'; "
            "assert s.project_dir==Path(sys.argv[1]); print('Member project .env loading passed.')",
            str(project),
        ],
        cwd=audit_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    smoke = subprocess.run(
        [shutil.which("pwsh"), "-NoProfile", "-File", str(project / "scripts/smoke-test.ps1")],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )
    if smoke.returncode:
        print(smoke.stderr[-6000:], file=sys.stderr)
        raise SystemExit(smoke.returncode)
    result = {
        "status": "passed",
        "zip_entries": len(whitelist),
        "archive_top_level_directory": project_name,
        "project_directory_created_by_extraction": True,
        "cache_initially_empty": True,
        "install_exit_code": install.returncode,
        "smoke_exit_code": smoke.returncode,
        "existing_env_content_preserved": True,
        "existing_env_acl_preserved": True,
        "member_project_env_overrides_process": True,
        "member_smoke": json.loads(smoke.stdout),
    }
target = root / ".cache/verification/delivery.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
