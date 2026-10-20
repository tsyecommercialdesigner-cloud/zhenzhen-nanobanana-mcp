# Requires PowerShell 7. Isolated fake credentials only; no billable operation is used.
$ErrorActionPreference = 'Stop'
$ProjectDir = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$PythonExe = Join-Path $ProjectDir '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
  throw 'Python environment missing. Run uv sync --locked --no-dev first.'
}
& $PythonExe -m zhenzhen_nanobanana_mcp.smoke
if ($LASTEXITCODE -ne 0) { throw 'MCP stdio protocol check failed.' }
