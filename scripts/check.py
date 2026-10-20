"""The same fail-closed quality gate locally and on GitHub Actions."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    os.chdir(ROOT)
    os.environ.setdefault(
        "UV_CACHE_DIR", str(Path(tempfile.gettempdir()) / "nanobanana-check-cache")
    )
    reports = ROOT / "test-reports"
    reports.mkdir(exist_ok=True)
    python = sys.executable
    steps = [
        ("format", [python, "-m", "ruff", "format", "--check", "src", "tests", "scripts"]),
        ("lint", [python, "-m", "ruff", "check", "src", "tests", "scripts"]),
        ("types", [python, "-m", "mypy"]),
        (
            "unit",
            [
                python,
                "-m",
                "coverage",
                "run",
                "--source=src",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
            ],
        ),
        ("coverage", [python, "-m", "coverage", "xml", "-o", str(reports / "coverage.xml")]),
        ("docs", [python, "scripts/check-docs.py"]),
        ("contracts", [python, "scripts/export-contracts.py", "--check"]),
        ("security", [python, "scripts/security-check.py"]),
        ("build", ["uv", "build", "--no-build-isolation"]),
        ("protocol", [python, "-m", "zhenzhen_nanobanana_mcp.smoke"]),
        ("member-install", [python, "scripts/verify-install.py"]),
    ]
    results = []
    for name, command in steps:
        print(f"Checking {name}...", flush=True)
        with (reports / f"{name}.log").open("w", encoding="utf-8") as stream:
            completed = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        results.append({"check": name, "exit_code": completed.returncode})
        (reports / "checks.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        if completed.returncode:
            print((reports / f"{name}.log").read_text(encoding="utf-8")[-12000:])
            raise SystemExit(completed.returncode)
    print("All required local checks passed. This is not evidence of a GitHub run or release.")


if __name__ == "__main__":
    main()
