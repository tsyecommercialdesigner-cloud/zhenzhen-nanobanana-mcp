import contextlib
import importlib.util
import io
import json
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DistributionTests(unittest.TestCase):
    def test_release_requests_canonical_repository_and_nested_urls(self):
        module = script("release")
        base = f"https://api.github.com/repos/{module.REPOSITORY}"
        with patch.dict(module.os.environ, {"GH_TOKEN": "fake-test-token"}):
            for path in ("", "environments/release", "actions/workflows/ci.yml/runs?per_page=100"):
                with patch.object(module, "urlopen") as open_request:
                    open_request.return_value.__enter__.return_value = io.BytesIO(b"{}")
                    self.assertEqual(module.api(path), {})
                    request = open_request.call_args.args[0]
                    self.assertEqual(request.full_url, base + (f"/{path}" if path else ""))
                    self.assertEqual(open_request.call_args.kwargs["timeout"], 30)

    def test_ci_security_and_release_boundary(self):
        for name in ("ci", "release"):
            data = yaml.load(
                (ROOT / f".github/workflows/{name}.yml").read_text(), Loader=yaml.BaseLoader
            )
            self.assertEqual(data["permissions"], {"contents": "read"})
            self.assertNotIn("pull_request_target", data["on"])
            for job in data["jobs"].values():
                # GitHub resolves job env before a runner exists; runner.temp here rejects the YAML.
                self.assertNotIn("runner.", json.dumps(job.get("env", {})))
                for step in job["steps"]:
                    if "uses" in step:
                        self.assertRegex(step["uses"], r"^[\w-]+/[\w-]+@[a-f0-9]{40}$")
                    self.assertNotIn("continue-on-error", step)
        release = yaml.load(
            (ROOT / ".github/workflows/release.yml").read_text(), Loader=yaml.BaseLoader
        )
        self.assertEqual(release["jobs"]["publish"]["environment"], "release")
        self.assertEqual(release["jobs"]["publish"]["permissions"], {"contents": "write"})
        publish_commands = [s.get("run", "") for s in release["jobs"]["publish"]["steps"]]
        creation = [
            shlex.split(line)
            for command in publish_commands
            for line in command.splitlines()
            if line.strip().startswith("gh release create ")
        ]
        self.assertEqual(len(creation), 1)
        self.assertIn("--draft", creation[0])
        self.assertTrue(all("gh release edit" not in command for command in publish_commands))
        ci = yaml.load((ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
        self.assertEqual(ci["jobs"]["quality"]["runs-on"], "windows-latest")
        self.assertIn("refs/heads/dev", ci["jobs"]["quality"]["if"])
        steps = release["jobs"]["verify"]["steps"]
        first_checkout = next(s for s in steps if s.get("uses", "").startswith("actions/checkout@"))
        self.assertEqual(first_checkout["with"]["ref"], "${{ github.sha }}")
        self.assertLess(
            next(i for i, s in enumerate(steps) if s.get("id") == "eligibility"),
            next(
                i
                for i, s in enumerate(steps)
                if s.get("with", {}).get("ref") == "${{ inputs.commit_sha }}"
            ),
        )

    def test_release_ci_requires_exact_default_branch_commit(self):
        module = script("release")
        good = {
            "head_sha": "a" * 40,
            "head_branch": "main",
            "event": "push",
            "status": "completed",
            "conclusion": "success",
        }
        self.assertIs(module.select_ci([good], "a" * 40, "main"), good)
        for field, value in (
            ("head_sha", "b" * 40),
            ("head_branch", "feature"),
            ("event", "pull_request"),
            ("conclusion", "skipped"),
            ("status", "in_progress"),
        ):
            self.assertIsNone(module.select_ci([{**good, field: value}], "a" * 40, "main"))

    def test_ignore_positive_and_negative_examples(self):
        ignored = [
            ".env",
            ".env.backup",
            "keys/private.env",
            ".venv/x",
            ".cache/x",
            "dist/x",
            "test-reports/unit.log",
            "outputs/batches.sqlite3",
            "outputs/" + "a" * 32 + "/01_01.png",
        ]
        public = [
            "tests/test_distribution.py",
            "tests/fixtures/sample.json",
            "uv.lock",
            ".github/workflows/ci.yml",
            ".env.example",
            "docs/ENGINEERING-GUIDE.md",
            "specs/002-github-distribution/spec.md",
            "outputs/README.md",
            "outputs/templates/poster.json",
        ]
        for path in ignored + public:
            result = subprocess.run(
                ["git", "check-ignore", "--no-index", "-q", "--", path], cwd=ROOT
            )
            self.assertEqual(result.returncode, 0 if path in ignored else 1, path)

    def test_release_refuses_unprotected_environment(self):
        module = script("release")
        with patch.dict(
            module.os.environ,
            {
                "TARGET_SHA": "a" * 40,
                "GITHUB_REPOSITORY": module.REPOSITORY,
                "GITHUB_REF": "refs/heads/main",
            },
        ):
            for environment in (None, {"protection_rules": []}):
                with patch.object(
                    module, "api", side_effect=[{"default_branch": "main"}, environment]
                ):
                    with self.assertRaisesRegex(SystemExit, "require reviewers"):
                        module.main()

    def test_secret_scan_rejects_files_and_values_without_printing_values(self):
        module = script("security-check")
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            secret = "ghp_" + "x" * 40
            for name, text in (
                ("private.env", "private-not-real"),
                ("source.py", secret),
                (".env.example", "ZHENZHEN_NANOBANANA_API_KEY=private-not-real"),
            ):
                (fixture / name).write_text(text, encoding="utf-8")
                output = io.StringIO()
                with (
                    patch.object(module, "ROOT", fixture),
                    patch.object(module, "candidate_paths", return_value=[name]),
                ):
                    with contextlib.redirect_stderr(output), self.assertRaises(SystemExit):
                        module.scan()
                self.assertNotIn(secret, output.getvalue())
                self.assertNotIn("private-not-real", output.getvalue())
            (fixture / ".env.example").write_text(
                "ZHENZHEN_NANOBANANA_API_KEY=\n", encoding="utf-8"
            )
            with (
                patch.object(module, "ROOT", fixture),
                patch.object(module, "candidate_paths", return_value=[".env.example"]),
            ):
                module.scan()

    def test_installer_has_safe_no_release_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            test = Path(directory) / "check.ps1"
            test.write_text(
                "param($Installer,$Destination)\n"
                "function Invoke-RestMethod { throw 'No release fixture' }\n"
                "try { & $Installer -InstallRoot $Destination; throw 'Unexpected success' }\n"
                "catch { if ($_.Exception.Message -notlike '*停止安装*') { throw } }\n"
                "if (Test-Path -LiteralPath (Join-Path $Destination 'zhenzhen-nanobanana-mcp')) { throw 'Created an install without release evidence' }\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    "pwsh",
                    "-NoProfile",
                    "-File",
                    str(test),
                    str(ROOT / "scripts/install-from-github.ps1"),
                    directory,
                ],
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr.decode(errors="replace"))

    def test_repository_metadata_and_member_license(self):
        self.assertIn("LICENSE", json.loads((ROOT / "user-files.json").read_text()))
        origin = subprocess.check_output(
            ["git", "remote", "get-url", "origin"], cwd=ROOT, text=True
        ).strip()
        self.assertEqual(
            origin.removesuffix(".git"),
            "https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp",
        )

    def test_verify_only_release_evidence_in_binary_json_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            test = Path(directory) / "verify.ps1"
            test.write_text(
                r"""param($Installer,$Destination)
$ErrorActionPreference = 'Stop'
$global:FixtureSha = 'a' * 40
function Invoke-RestMethod {
  param($Uri,$Headers)
  if ($Uri -like '*/releases/latest') {
    return @{tag_name='v0.1.0';draft=$false;prerelease=$false;assets=@(@{name='release-eligibility.json';browser_download_url='https://example.test/evidence'})}
  }
  if ($Uri -like '*/actions/runs/7/jobs*') { return @{jobs=@(@{name='quality';conclusion='success'})} }
  if ($Uri -like '*/actions/runs/7') { return @{status='completed';conclusion='success';head_sha=$global:FixtureSha;head_branch='main';event='push';path='.github/workflows/ci.yml'} }
  return @{default_branch='main'}
}
function Invoke-WebRequest {
  param($Uri)
  $Body = @{tag='v0.1.0';version='0.1.0';commit=$global:FixtureSha;ci_run='https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/7'} | ConvertTo-Json
  return @{Content=[Text.Encoding]::UTF8.GetBytes($Body)}
}
$Result = & $Installer -VerifyOnly -InstallRoot $Destination
if ($Result.Tag -cne 'v0.1.0' -or $Result.Commit -cne $global:FixtureSha) { throw 'Invalid evidence result' }
if (Test-Path -LiteralPath (Join-Path $Destination 'zhenzhen-nanobanana-mcp')) { throw 'VerifyOnly wrote an installation' }
""",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    "pwsh",
                    "-NoProfile",
                    "-File",
                    str(test),
                    str(ROOT / "scripts/install-from-github.ps1"),
                    directory,
                ],
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr.decode(errors="replace"))

    def test_installer_refuses_draft_before_download_or_install(self):
        with tempfile.TemporaryDirectory() as directory:
            test = Path(directory) / "draft.ps1"
            test.write_text(
                r"""param($Installer,$Destination)
$ErrorActionPreference = 'Stop'
function Invoke-RestMethod {
  param($Uri,$Headers)
  return @{tag_name='v0.2.0';draft=$true;prerelease=$false;assets=@()}
}
function Invoke-WebRequest { throw 'must not download a draft asset' }
$rejected = $false
try { & $Installer -InstallRoot $Destination }
catch {
  if ($_.Exception.Message -notmatch '不能安装草稿') { throw }
  $rejected = $true
}
if (!$rejected) { throw 'Draft accepted' }
if (Test-Path -LiteralPath (Join-Path $Destination 'zhenzhen-nanobanana-mcp')) {
  throw 'Draft created an installation'
}
""",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    "pwsh",
                    "-NoProfile",
                    "-File",
                    str(test),
                    str(ROOT / "scripts/install-from-github.ps1"),
                    directory,
                ],
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr.decode(errors="replace"))
