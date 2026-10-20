"""Empty-cache source installation; fake config only, never touch a member installation."""

import json
import os
import subprocess
import tarfile
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(args, **kwargs):
    return subprocess.run(args, check=True, timeout=300, **kwargs)


def main():
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    archive = ROOT / "dist" / f"zhenzhen_nanobanana_mcp-{version}.tar.gz"
    with tempfile.TemporaryDirectory(prefix="nanobanana-source-install-") as directory:
        temporary = Path(directory)
        with tarfile.open(archive) as source:
            for member in source.getmembers():
                target = (temporary / member.name).resolve()
                if (
                    not target.is_relative_to(temporary.resolve())
                    or member.issym()
                    or member.islnk()
                ):
                    raise ValueError("Unsafe source archive entry")
                if (
                    Path(member.name).name.startswith(".env")
                    and Path(member.name).name != ".env.example"
                ):
                    raise ValueError("Private configuration in source archive")
            source.extractall(temporary, filter="data")
        project = temporary / f"zhenzhen_nanobanana_mcp-{version}"
        assert (project / "pyproject.toml").is_file()
        private = project / ".env"
        private.write_text("NANOBANANA_API_KEY=install-check-not-real\n", encoding="utf-8")
        before = private.read_bytes()
        acl_args = [
            "pwsh",
            "-NoProfile",
            "-Command",
            "& { param($p) (Get-Acl -LiteralPath $p).Sddl }",
            str(private),
        ]
        before_acl = (
            subprocess.check_output(acl_args) if os.name == "nt" else private.stat().st_mode
        )
        env = dict(os.environ)
        for name in (
            "PYTHONPATH",
            "PYTHONHOME",
            "VIRTUAL_ENV",
            "UV_PROJECT_ENVIRONMENT",
            "NANOBANANA_PROJECT_DIR",
        ):
            env.pop(name, None)
        env["UV_PROJECT_ENVIRONMENT"] = str(project / ".venv")
        env["NANOBANANA_API_KEY"] = "different-process-not-real"
        env["NANOBANANA_BASE_URL"] = "https://ai.t8star.org"
        env["NANOBANANA_OUTPUT_DIR"] = str(project / "outputs")
        env["NANOBANANA_CONCURRENCY"] = "4"
        env["NANOBANANA_MAX_PENDING_TASKS"] = "200"
        env["NANOBANANA_TIMEOUT_SECONDS"] = "300"
        command = [
            "uv",
            "--cache-dir",
            str(temporary / "empty-cache"),
            "--directory",
            str(project),
            "sync",
            "--locked",
            "--no-dev",
        ]
        run(command, env=env)
        python = project / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")
        probe = (
            "from pathlib import Path; import sys, fastmcp, importlib.util; "
            "from zhenzhen_nanobanana_mcp.config import Settings; s=Settings.from_env(); "
            "assert s.api_key=='install-check-not-real'; assert s.project_dir==Path(sys.argv[1]); "
            "assert Path(fastmcp.__file__).is_relative_to(Path(sys.argv[1])/'.venv'); "
            "assert importlib.util.find_spec('mypy') is None"
        )
        run([str(python), "-c", probe, str(project)], env=env, cwd=temporary)
        # Equivalent to updating/reinstalling the locked runtime in an existing clone.
        run(command, env=env)
        after_acl = subprocess.check_output(acl_args) if os.name == "nt" else private.stat().st_mode
        assert private.read_bytes() == before and before_acl == after_acl
        run([str(python), "-m", "zhenzhen_nanobanana_mcp.smoke"], env=env, cwd=temporary)
    print(
        json.dumps(
            {
                "source_install": "passed",
                "empty_cache": True,
                "dev_dependencies_absent": True,
                "env_content_and_permissions_preserved": True,
                "business_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
