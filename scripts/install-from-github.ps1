# Clone a real, CI-verified release. Does not write credentials or modify existing installs.
param(
  [string]$Tag = '',
  [string]$InstallRoot = 'C:\MCP',
  [switch]$VerifyOnly
)
$ErrorActionPreference = 'Stop'
$Repository = 'tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp'
$RepositoryUrl = "https://github.com/$Repository.git"
$ApiRoot = "https://api.github.com/repos/$Repository"
$ProjectDir = Join-Path ([IO.Path]::GetFullPath($InstallRoot)) 'zhenzhen-nanobanana-mcp'
if (!$VerifyOnly -and (Test-Path -LiteralPath $ProjectDir)) { throw '安装目录已存在，请按手册升级或迁移，不能覆盖。' }
if ($Tag -and $Tag -cnotmatch '^v[0-9]+\.[0-9]+\.[0-9]+$') { throw '发布标签必须为 vX.Y.Z。' }
$Headers = @{ Accept = 'application/vnd.github+json'; 'X-GitHub-Api-Version' = '2022-11-28' }
$Endpoint = if ($Tag) { "$ApiRoot/releases/tags/$Tag" } else { "$ApiRoot/releases/latest" }
try { $Release = Invoke-RestMethod -Uri $Endpoint -Headers $Headers }
catch { throw '无法取得正式Release；仓库尚未发布、GitHub限流或网络不可用。停止安装，不回退到main。' }
if ($Release.draft -or $Release.prerelease) { throw '不能安装草稿或预发布版本。' }
$Tag = $Release.tag_name
if ($Tag -cnotmatch '^v[0-9]+\.[0-9]+\.[0-9]+$') { throw 'Release标签格式不支持。' }
$Asset = @($Release.assets | Where-Object { $_.name -eq 'release-eligibility.json' })
if ($Asset.Count -ne 1) { throw 'Release缺少唯一的CI/提交验收记录，停止安装。' }
$EvidenceBody = (Invoke-WebRequest -Uri $Asset[0].browser_download_url).Content
if ($EvidenceBody -is [byte[]]) { $EvidenceBody = [Text.Encoding]::UTF8.GetString($EvidenceBody) }
$Evidence = ConvertFrom-Json -InputObject $EvidenceBody
if ($Evidence.tag -cne $Tag -or $Evidence.commit -cnotmatch '^[0-9a-f]{40}$' -or $Evidence.version -cne $Tag.Substring(1)) {
  throw 'Release验收记录的标签、版本或完整SHA不匹配。'
}
$CiPattern = '^https://github\.com/' + [regex]::Escape($Repository) + '/actions/runs/([0-9]+)$'
if ($Evidence.ci_run -cnotmatch $CiPattern) { throw '验收记录不是本仓库CI。' }
$RunId = $Matches[1]
$Ci = Invoke-RestMethod -Uri "$ApiRoot/actions/runs/$RunId" -Headers $Headers
$Repo = Invoke-RestMethod -Uri $ApiRoot -Headers $Headers
if ($Ci.status -ne 'completed' -or $Ci.conclusion -ne 'success' -or $Ci.head_sha -cne $Evidence.commit -or
    $Ci.head_branch -cne $Repo.default_branch -or $Ci.event -ne 'push' -or $Ci.path -ne '.github/workflows/ci.yml') {
  throw '目标提交没有已通过的默认分支CI，停止安装。'
}
$Jobs = Invoke-RestMethod -Uri "$ApiRoot/actions/runs/$RunId/jobs?per_page=100" -Headers $Headers
if (!@($Jobs.jobs | Where-Object { $_.name -eq 'quality' -and $_.conclusion -eq 'success' }).Count -or
    @($Jobs.jobs | Where-Object { $_.conclusion -ne 'success' }).Count) { throw '必需CI任务未全部通过。' }
if ($VerifyOnly) {
  [pscustomobject]@{ Tag = $Tag; Commit = $Evidence.commit; CI = $Evidence.ci_run }
  return
}
New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
git clone --branch $Tag --single-branch $RepositoryUrl $ProjectDir
if ($LASTEXITCODE -ne 0) { throw '仓库获取失败，停止安装；保留现状供排查。' }
$ActualSha = git -C $ProjectDir rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $ActualSha -cne $Evidence.commit) { throw 'clone提交与发布验收记录不一致。' }
uv --directory $ProjectDir sync --locked --no-dev
if ($LASTEXITCODE -ne 0) { throw '锁定运行依赖安装失败，停止启动。' }
pwsh -NoProfile -File (Join-Path $ProjectDir 'scripts\smoke-test.ps1')
if ($LASTEXITCODE -ne 0) { throw '协议检查失败，停止配置Host。' }
[pscustomobject]@{ ProjectDir = $ProjectDir; Tag = $Tag; Commit = $ActualSha; CI = $Evidence.ci_run } | Format-List
Write-Host '下一步：按MANUAL.md保留或创建项目.env，填写私有密钥，再配置Host。'
