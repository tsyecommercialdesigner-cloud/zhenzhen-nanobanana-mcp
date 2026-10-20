"""Reject secret-bearing source files and audit the complete pinned dependency export."""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    r"\bAKIA[0-9A-Z]{16}\b",
    r"\bgh[pousr]_[A-Za-z0-9]{36,}\b",
    r"\bgithub_pat_[A-Za-z0-9_]{60,}\b",
    r"\bsk-[A-Za-z0-9_-]{24,}\b",
]


def candidate_paths():
    output = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT
    )
    return sorted(set(output.decode("utf-8").rstrip("\0").split("\0")))


def scan():
    problems = []
    for relative in candidate_paths():
        path = ROOT / relative
        if not path.is_file():
            continue
        name = path.name.lower()
        if (
            (name.startswith(".env") or ".env." in name or name.endswith(".env"))
            and relative != ".env.example"
        ) or name.endswith((".pem", ".key")):
            problems.append((relative, "private file name"))
            continue
        data = path.read_bytes()
        if b"\0" in data:
            continue
        text = data.decode("utf-8", errors="replace")
        if any(re.search(pattern, text) for pattern in PATTERNS):
            problems.append((relative, "credential pattern"))
        if relative == ".env.example":
            values = [
                line for line in text.splitlines() if line.strip() and not line.startswith("#")
            ]
            if values != ["NANOBANANA_API_KEY="]:
                problems.append((relative, "nonempty or unexpected credential template"))
    if problems:
        for path, reason in problems:
            print(f"Rejected {path}: {reason}", file=sys.stderr)
        raise SystemExit(1)
    print("Source credential scan passed (known patterns and prohibited file names).")


def main():
    reports = ROOT / "test-reports"
    reports.mkdir(exist_ok=True)
    scan()
    requirements = reports / "audit-requirements.txt"
    subprocess.run(
        [
            "uv",
            "export",
            "--locked",
            "--all-groups",
            "--no-emit-project",
            "--no-hashes",
            "--format",
            "requirements-txt",
            "--output-file",
            str(requirements),
        ],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    audit = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip_audit",
            "--no-deps",
            "--disable-pip",
            "--strict",
            "--progress-spinner",
            "off",
            "--timeout",
            "60",
            "-r",
            str(requirements),
            "-f",
            "json",
            "-o",
            str(reports / "dependency-audit.json"),
        ],
        cwd=ROOT,
    )
    if audit.returncode:
        raise SystemExit(audit.returncode)
    (reports / "security.json").write_text(
        json.dumps({"credential_scan": "passed", "audit": "passed"}), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
