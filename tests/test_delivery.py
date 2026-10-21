import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class DeliveryTests(unittest.TestCase):
    def test_whitelist_guards(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix="nanobanana-whitelist-") as directory:
            fixture = Path(directory)
            (fixture / "file.txt").write_text("public", encoding="utf-8")
            script = fixture / "check.ps1"
            # Paths are passed as structured command arguments; no interpolated shell code.
            script.write_text(
                """param([string]$Helper,[string]$Fixture)
$ErrorActionPreference = 'Stop'
. $Helper
$ok = @(Resolve-DeliveryFiles -ProjectDir $Fixture -Whitelist @('file.txt'))
if ($ok.Count -ne 1) { throw 'Valid file rejected' }
foreach ($bad in @(@('file.txt','file.txt'), @('../file.txt'), @('missing.txt'),
    @('.env'), @('docs/dev.md'), @('C:/private.txt'), @('file.txt:stream'))) {
  $rejected = $false
  try { Resolve-DeliveryFiles -ProjectDir $Fixture -Whitelist $bad | Out-Null }
  catch { $rejected = $true }
  if (!$rejected) { throw 'Invalid whitelist accepted' }
}
$Target = Join-Path $Fixture 'target'
New-Item -ItemType Directory -Path $Target | Out-Null
[IO.File]::WriteAllText((Join-Path $Target 'file.txt'), 'public')
$LinkType = if ($IsWindows) { 'Junction' } else { 'SymbolicLink' }
New-Item -ItemType $LinkType -Path (Join-Path $Fixture 'link') -Target $Target | Out-Null
$rejected = $false
try { Resolve-DeliveryFiles -ProjectDir $Fixture -Whitelist @('link/file.txt') | Out-Null }
catch { $rejected = $true }
if (!$rejected) { throw 'Junction whitelist accepted' }
[IO.File]::WriteAllText((Join-Path $Fixture '.env.example'), "ZHENZHEN_NANOBANANA_API_KEY=`n")
Resolve-DeliveryFiles -ProjectDir $Fixture -Whitelist @('.env.example') | Out-Null
[IO.File]::WriteAllText((Join-Path $Fixture '.env.example'), "ZHENZHEN_NANOBANANA_API_KEY=must-not-package`n")
$rejected = $false
try { Resolve-DeliveryFiles -ProjectDir $Fixture -Whitelist @('.env.example') | Out-Null }
catch { $rejected = $true }
if (!$rejected) { throw 'Populated env template accepted' }
Write-Output 'Seven invalid whitelists rejected; valid file accepted.'
""",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    shutil.which("pwsh"),
                    "-NoProfile",
                    "-File",
                    str(script),
                    "-Helper",
                    str(root / "scripts/delivery-common.ps1"),
                    "-Fixture",
                    str(fixture),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
