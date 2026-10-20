function Resolve-DeliveryFiles {
  param([Parameter(Mandatory)][string]$ProjectDir, [Parameter(Mandatory)][object[]]$Whitelist)
  $ProjectDir = [IO.Path]::GetFullPath($ProjectDir)
  if ($Whitelist.Count -eq 0) { throw 'Whitelist must be nonempty.' }
  $Seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
  $ResolvedFiles = [Collections.Generic.List[object]]::new()
  $DeniedSegment = '(^|/)(\.git|\.venv|\.cache|node_modules|output|outputs|input|tests|specs|docs|\.specify|\.agents|\.claude|\.codex|\.beads)(/|$)'
  foreach ($Entry in $Whitelist) {
    if ($Entry -isnot [string] -or !$Entry -or $Entry.Contains('\') -or
        [IO.Path]::IsPathRooted($Entry) -or $Entry -match '(^|/)\.{1,2}(/|$)' -or
        $Entry -match '[:\x00-\x1F]' -or $Entry -match '//|/$') { throw "Invalid relative entry: $Entry" }
    if ($Entry -match $DeniedSegment -or ($Entry -ne '.env.example' -and $Entry -match '(^|/)(AGENTS\.md|CLAUDE\.md|CONVENTIONS\.md|.*\.env.*|\.mcp\.json|\.cherrystudiomcpproxy\.mcp\.json|.*\.(log|sqlite3|pem|key))$')) {
      throw "Forbidden delivery entry: $Entry"
    }
    if (!$Seen.Add($Entry)) { throw "Duplicate entry: $Entry" }
    $FullPath = [IO.Path]::GetFullPath((Join-Path $ProjectDir $Entry))
    if (!$FullPath.StartsWith($ProjectDir + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
      throw "Entry escapes project: $Entry"
    }
    $Item = Get-Item -LiteralPath $FullPath -Force -ErrorAction Stop
    if ($Item.PSIsContainer) { throw "Whitelist requires exact files: $Entry" }
    $Cursor = $Item
    while ($Cursor.FullName -ne $ProjectDir) {
      if ($Cursor.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse entry: $Entry" }
      $Cursor = Get-Item -LiteralPath ([IO.Path]::GetDirectoryName($Cursor.FullName)) -Force
    }
    if ($Entry -eq '.env.example') {
      $Count = 0
      $TemplateText = [IO.File]::ReadAllText($FullPath, [Text.UTF8Encoding]::new($false, $true))
      foreach ($Line in ($TemplateText -split '\r?\n')) {
        if ($Line -match '^\s*(#.*)?$') { continue }
        if ($Line -notmatch '^NANOBANANA_API_KEY=\s*$') { throw 'Unsafe .env.example: only an empty API key field is allowed.' }
        $Count++
      }
      if ($Count -ne 1) { throw 'Unsafe .env.example: API key field must occur exactly once.' }
    }
    $ResolvedFiles.Add(@{ Entry = $Entry; Path = $FullPath })
  }
  return $ResolvedFiles.ToArray()
}
