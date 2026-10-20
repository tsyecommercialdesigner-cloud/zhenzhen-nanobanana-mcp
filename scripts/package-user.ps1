param([string]$DestinationDirectory)
$ErrorActionPreference = 'Stop'
$ProjectDir = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (!$DestinationDirectory) { $DestinationDirectory = Join-Path $ProjectDir 'output' }
$DestinationDirectory = [IO.Path]::GetFullPath($DestinationDirectory)
$PythonExe = Join-Path $ProjectDir '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $PythonExe -PathType Leaf)) { throw 'Run uv sync --locked first.' }

$Version = & $PythonExe -c "import sys,tomllib; from pathlib import Path; from importlib.metadata import version; p=tomllib.loads((Path(sys.argv[1])/'pyproject.toml').read_text(encoding='utf-8'))['project']; assert p['name']=='zhenzhen-nanobanana-mcp'; assert p['version']==version(p['name']), 'Installed metadata differs from source; run uv sync --locked'; print(p['version'])" $ProjectDir
if ($LASTEXITCODE -ne 0 -or !$Version) { throw 'Cannot read distribution version.' }
$ProjectName = 'zhenzhen-nanobanana-mcp'
$ZipPath = Join-Path $DestinationDirectory "$ProjectName-$Version-user.zip"
if (Test-Path -LiteralPath $ZipPath) { throw "Release already exists: $ZipPath" }
$Whitelist = Get-Content -LiteralPath (Join-Path $ProjectDir 'user-files.json') -Raw | ConvertFrom-Json
if ($Whitelist -isnot [array] -or $Whitelist.Count -eq 0) { throw 'Whitelist must be a nonempty array.' }
. (Join-Path $PSScriptRoot 'delivery-common.ps1')
$ResolvedFiles = @(Resolve-DeliveryFiles -ProjectDir $ProjectDir -Whitelist $Whitelist)

# Keep build cache outside the source tree. Preflight also avoids rebuilding when a ZIP exists.
$BuildCacheDir = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'zhenzhen-nanobanana-mcp\uv-build-cache'
& uv --cache-dir $BuildCacheDir build --directory $ProjectDir --no-build-isolation
if ($LASTEXITCODE -ne 0) { throw 'Application build failed.' }
New-Item -ItemType Directory -Path $DestinationDirectory -Force | Out-Null
$Stream = [IO.File]::Open($ZipPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
try {
  $Archive = [IO.Compression.ZipArchive]::new($Stream, [IO.Compression.ZipArchiveMode]::Create, $true)
  try {
    foreach ($File in $ResolvedFiles) {
      $ArchiveEntry = "$ProjectName/$($File.Entry)"
      [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($Archive, $File.Path, $ArchiveEntry) | Out-Null
    }
  } finally { $Archive.Dispose() }
} finally { $Stream.Dispose() }
$ReadArchive = [IO.Compression.ZipFile]::OpenRead($ZipPath)
try {
  $Actual = @($ReadArchive.Entries | ForEach-Object FullName)
  $Expected = @($Whitelist | ForEach-Object { "$ProjectName/$_" })
  if ($Actual.Count -ne $Expected.Count -or @(Compare-Object ($Expected | Sort-Object) ($Actual | Sort-Object)).Count -ne 0) {
    throw 'ZIP entries differ from whitelist.'
  }
} finally { $ReadArchive.Dispose() }
Write-Output $ZipPath
