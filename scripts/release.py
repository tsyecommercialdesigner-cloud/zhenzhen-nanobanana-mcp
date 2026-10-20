"""Read-only GitHub release eligibility checks; publication belongs to the approved CD job."""

import json
import os
import re
import subprocess
import tomllib
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp"


def api(path, missing_ok=False):
    request = Request(
        f"https://api.github.com/repos/{REPOSITORY}/{path}",
        headers={
            "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        if missing_ok and error.code == 404:
            return None
        raise RuntimeError(f"GitHub eligibility request failed (HTTP {error.code})") from None


def select_ci(runs, sha, default):
    return next(
        (
            run
            for run in runs
            if run["head_sha"] == sha
            and run["head_branch"] == default
            and run["event"] == "push"
            and run["status"] == "completed"
            and run["conclusion"] == "success"
        ),
        None,
    )


def main():
    sha = os.environ["TARGET_SHA"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha) or os.environ.get("GITHUB_REPOSITORY") != REPOSITORY:
        raise SystemExit("Expected this repository and a complete lowercase Git SHA.")
    repository = api("")
    default = repository["default_branch"]
    if os.environ.get("GITHUB_REF") != f"refs/heads/{default}":
        raise SystemExit("Release workflow must run from the actual default branch.")
    environment = api("environments/release", missing_ok=True)
    if not environment or not any(
        rule.get("type") == "required_reviewers" and rule.get("reviewers")
        for rule in environment.get("protection_rules", [])
    ):
        raise SystemExit(
            "The release environment must exist and require reviewers before publishing."
        )
    subprocess.run(["git", "fetch", "origin", default], cwd=ROOT, check=True)
    subprocess.run(["git", "merge-base", "--is-ancestor", sha, "FETCH_HEAD"], cwd=ROOT, check=True)
    metadata = subprocess.check_output(
        ["git", "show", f"{sha}:pyproject.toml"], cwd=ROOT, text=True
    )
    version = tomllib.loads(metadata)["project"]["version"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit("This release flow supports final X.Y.Z versions.")
    tag = "v" + version
    if api(f"git/ref/tags/{tag}", missing_ok=True) or api(f"releases/tags/{tag}", missing_ok=True):
        raise SystemExit("Tag or release already exists; never overwrite a published version.")
    query = urlencode({"event": "push", "head_sha": sha, "per_page": 100})
    runs = api(f"actions/workflows/ci.yml/runs?{query}")["workflow_runs"]
    run = select_ci(runs, sha, default)
    if run is None:
        raise SystemExit("No successful default-branch CI run for the exact commit.")
    jobs = api(f"actions/runs/{run['id']}/jobs?per_page=100")["jobs"]
    if (
        not jobs
        or any(job["conclusion"] != "success" for job in jobs)
        or not any(job["name"] == "quality" for job in jobs)
    ):
        raise SystemExit("Required CI jobs are missing, skipped, or unsuccessful.")
    reports = ROOT / "test-reports"
    reports.mkdir(exist_ok=True)
    evidence = {"tag": tag, "version": version, "commit": sha, "ci_run": run["html_url"]}
    (reports / "release-eligibility.json").write_text(
        json.dumps(evidence, indent=2), encoding="utf-8"
    )
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(f"tag={tag}\n")
    print(json.dumps(evidence))


if __name__ == "__main__":
    main()
