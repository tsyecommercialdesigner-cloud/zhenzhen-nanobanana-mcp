# zhenzhen-nanobanana-mcp 使用手册

## 1. 环境准备

成员从GitHub的已验证Release获取源码后，本服务在本机运行，通过 stdio 由客户端启动，面向家居日用百货电商绘图。Windows 运行命令使用 PowerShell 7；Bash/Zsh 注册流程另见第 4 节。远程 HTTP 托管、网关、OAuth、Node.js 初始化均不适用。

| 项目 | 实际值/验证范围 |
|---|---|
| 项目目录 / 发行包 / 服务名 | `zhenzhen-nanobanana-mcp`，服务名无小数点、23 字符，满足本机 DSH 1–32 字符约束 |
| 导入模块 / 入口 | `zhenzhen_nanobanana_mcp` / `python -m zhenzhen_nanobanana_mcp` |
| 本地安装目录 | `D:\MCP\zhenzhen-nanobanana-mcp` |
| Python / 包管理 | 精确 `3.12.14` / 开发机 uv `0.12.9`，依赖由 `uv.lock` 锁定 |
| 框架 / 底层 SDK | `fastmcp==4.1.0` / `mcp==2.3.0`；采用 FastMCP 是用户指定的项目例外 |
| MCP 协议 | 子进程检查通过 `2026-07-28` 请求元数据模式和 `2025-11-25` 初始化握手模式；其他旧版本未测试 |
| Host | Cherry Studio、Codex、Claude Code、DSH 模板；Codex CLI 0.153.0、Claude Code 2.1.258、DSH 0.2.0-rc.2 已核对帮助/schema；Codex app-server、DSH CLI 隔离 profile 的 6 工具发现及免费调用已验证，四个 GUI 业务联调未验证 |
| 系统 | Windows x64 + Python 3.12.14 已测；Bash/Zsh 示例为 POSIX 路径，Linux/macOS/WSL 未实测 |

安装前需Git（使用`git --version`核对）及PowerShell7，公开仓库HTTPS访问无需GitHub令牌。联网初始化从 PyPI 下载锁定依赖，绘图联网访问 `https://ai.t8star.org`，图片下载访问公开 HTTP/HTTPS 地址。无离线缓存交付。uv 遵从其网络/注册表配置；业务 httpx 禁用环境代理，遵从系统 TLS 校验，不能通过关闭 TLS 来排障。

| 环境变量 | 必填 | 默认/用途 |
|---|---|---|
| `ZHENZHEN_NANOBANANA_API_KEY` | 日常启动必填 | 服务读取项目 `.env`；原始 ASCII 密钥，无内部空白/控制字符，不含 `Bearer `，不要求固定前缀 |
| `NANOBANANA_PROJECT_DIR` | 否 | 非秘密项目绝对目录；默认从已验证 src 布局定位，特殊 wheel 安装布局需显式指定；其它运行设置仍从进程环境读取 |
| `NANOBANANA_BASE_URL` | 否 | `https://ai.t8star.org`；HTTPS 服务根地址，无路径/query/凭据；属于操作员信任配置 |
| `NANOBANANA_INPUT_DIRS` | 已停用 | 旧配置被忽略，不再限制本地图片目录，无需修改已有Host配置即可解除白名单 |
| `NANOBANANA_OUTPUT_DIR` | 否 | 项目 `outputs`；绝对路径，不随 Host 工作目录改变 |
| `NANOBANANA_TIMEOUT_SECONDS` | 否 | `300`；1–600，每任务参考图准备、上游绘图及图片下载的整体限时 |
| `NANOBANANA_MAX_PENDING_TASKS` | 否 | `200`；整数 12–1000，共享账本中 queued/preparing/running 的容量上限 |
| `NANOBANANA_CONCURRENCY` | 否 | `4`；整数 1–10，同一输出目录的多个服务进程共享并发上限，所有 Host 应采用相同配置 |

实际私有文件为 `D:\MCP\zhenzhen-nanobanana-mcp\.env`；开发时为实际开发项目根目录 `.env`。服务显式定位，不搜索 Host 工作目录/父目录，不把 `.env.example` 当运行凭据。文件仅解析 `ZHENZHEN_NANOBANANA_API_KEY` 凭据字段，不导入 `os.environ`；其它非秘密设置仍从进程环境读取。

2026-10-21起，所有凭据来源统一使用上述新名称，旧名称不再读取。升级已有安装时，只重命名私有 `.env` 中的密钥字段，保留值、其它内容及权限；若使用环境变量回退，在对应来源配置新名称并重启服务。不把旧字段静默当作新字段，也不自动删除用户的其它环境变量。

优先级是 **项目 `.env` → 进程环境 → Windows 当前运行账号 HKCU\Environment**。只有文件/字段缺失才回退；字段已定义但空/非法、重复、文件不可读/非 UTF-8/语法错误均拒绝启动，不使用旧密钥。兼容来源中已定义但空/非法也立即失败；全部缺失退出 2。Windows 回退只读当前账号，不访问机器/其他账号或写注册表；非 Windows 仅兼容进程环境。

解析器锁定 `python-dotenv==1.2.4`，采用不展开变量的底层解析；文件 UTF-8（可含 BOM），最多 1 MiB。支持注释、单双引号及解析器转义；未加引号时空白后的 `#` 是注释，紧邻值的 `#` 保留。`${VAR}`、`$(command)` 是字面数据，不执行。密钥拒绝控制字符、非 ASCII、内部空白和完整 Bearer 前缀，约束来自请求头，不虚构供应商密钥前缀。

初始化见第 2 节。默认不创建全局变量、不删除已有旧变量。文件修改后重启实际 MCP 服务子进程，不承诺热加载；启动后 `list_models.api_key_configured` 表示配置是否成功。错误只给字段名/来源/原因，不输出值、文件内容或请求头。真实 `.env` 与秘密备份禁止进入 Git/ZIP。

## 2. 项目初始化

**正式发布状态（2026-10-21）**：[v0.2.0](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/releases/tag/v0.2.0)已正式公开，标签提交`66555d72742cf54b98bd3dc4c57a94d3a98d7818`通过[Windows CI39529835229](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39529835229)，从GitHub发布标签的独立安装及无收费协议验收已通过，见[发布验收](docs/RELEASE-ACCEPTANCE.md)。不要把远端初始提交`ce7ce74a357782fcda820174c60a9c41090d7fa9`当作MCP版本。

当前开发候选版本为0.2.1，纳入D盘默认路径及最新验收文档；本轮仅获准创建Release草稿，不能作为正式成员发行版安装。公开前仍按下面流程获取已正式公开的v0.2.0，旧版脚本的路径例外见下段；[0.2.1候选说明](docs/RELEASE-0.2.1.md)记录范围与验证边界。未来正式公开须另获授权，不修改既有v0.2.0。

本项目按用户约定将默认安装目录改为`D:\MCP\zhenzhen-nanobanana-mcp`，与本次同步的手册指南一致，仅变更盘符；不搬迁已有安装或修改现用Host配置。下面流程和[README快速安装](README.md#快速安装与配置)均使用D盘。已发布v0.2.0文件、标签及附件不变，旧版安装脚本仍须显式传入`-InstallRoot 'D:\MCP'`，其Host模板也须按第4节调整路径。下面的发布验证在没有正式Release时仍明确停止，不回退main；升级前保留`.env`与私有图片/账本。

仓库：https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp.git 。正式版本与验收记录从 [Releases](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/releases) 取得；[CI](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/workflows/ci.yml) 与发布记录必须对应同一完整SHA。仓库公开，HTTPS clone无需密钥；不要把GitHub令牌放入URL。以后改为私有时使用自己的SSH或Git凭据管理器授权，业务API密钥不能用于Git认证。

### 首次安装：取正式标签并核验完整提交

需要Git、PowerShell7、uv0.12.9，uv按`.python-version`使用Python3.12.14。只创建安装父目录，clone自动创建项目目录；不能覆盖已有安装。以下PowerShell流程使用真实Release返回的tag和完整SHA，不从包版本推测标签：

```powershell
$ErrorActionPreference = 'Stop'
$Repository = 'tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp'
$ApiRoot = "https://api.github.com/repos/$Repository"
$RepositoryUrl = "https://github.com/$Repository.git"
$ProjectDir = 'D:\MCP\zhenzhen-nanobanana-mcp'
if (Test-Path -LiteralPath $ProjectDir) { throw '目录已存在，改用第5节升级/旧安装迁移流程。' }
try { $Release = Invoke-RestMethod "$ApiRoot/releases/latest" }
catch { throw '尚无正式Release或GitHub访问失败；停止安装，不回退main。' }
$ReleaseTag = $Release.tag_name
if ($Release.draft -or $Release.prerelease -or $ReleaseTag -cnotmatch '^v[0-9]+\.[0-9]+\.[0-9]+$') { throw '不是可安装的正式版本。' }
$Assets = @($Release.assets | Where-Object { $_.name -eq 'release-eligibility.json' })
if ($Assets.Count -ne 1) { throw '缺少发布验收记录。' }
$EvidenceBody = (Invoke-WebRequest $Assets[0].browser_download_url).Content
if ($EvidenceBody -is [byte[]]) { $EvidenceBody = [Text.Encoding]::UTF8.GetString($EvidenceBody) }
$Evidence = ConvertFrom-Json -InputObject $EvidenceBody
$ExpectedCommit = $Evidence.commit
if ($ExpectedCommit -cnotmatch '^[0-9a-f]{40}$' -or $Evidence.tag -cne $ReleaseTag -or $Evidence.version -cne $ReleaseTag.Substring(1)) { throw '标签/版本/SHA记录不一致。' }
$CiPattern = '^https://github\.com/' + [regex]::Escape($Repository) + '/actions/runs/([0-9]+)$'
if ($Evidence.ci_run -cnotmatch $CiPattern) { throw 'CI链接不是本仓库。' }
$CiRunId = $Matches[1]
$Ci = Invoke-RestMethod "$ApiRoot/actions/runs/$CiRunId"
$Repo = Invoke-RestMethod $ApiRoot
if ($Ci.status -ne 'completed' -or $Ci.conclusion -ne 'success' -or $Ci.head_sha -cne $ExpectedCommit -or $Ci.event -ne 'push' -or $Ci.head_branch -cne $Repo.default_branch -or $Ci.path -ne '.github/workflows/ci.yml') { throw '目标提交CI未通过。' }
$Jobs = Invoke-RestMethod "$ApiRoot/actions/runs/$CiRunId/jobs?per_page=100"
if (!@($Jobs.jobs | Where-Object { $_.name -eq 'quality' -and $_.conclusion -eq 'success' }).Count -or @($Jobs.jobs | Where-Object { $_.conclusion -ne 'success' }).Count) { throw '必需任务未全部通过。' }
New-Item -ItemType Directory -Path 'D:\MCP' -Force | Out-Null
git clone --branch $ReleaseTag --single-branch $RepositoryUrl $ProjectDir
if ($LASTEXITCODE -ne 0) { throw 'clone失败，停止安装。' }
$ActualCommit = git -C $ProjectDir rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $ActualCommit -cne $ExpectedCommit) { throw '安装提交与发布记录不一致。' }
Write-Host "安装版本：$ReleaseTag，提交：$ActualCommit"
uv --directory $ProjectDir sync --locked --no-dev
if ($LASTEXITCODE -ne 0) { throw '运行依赖安装失败，停止启动。' }
pwsh -NoProfile -File (Join-Path $ProjectDir 'scripts\smoke-test.ps1')
if ($LASTEXITCODE -ne 0) { throw '协议检查失败。' }
```

clone标签后detached HEAD是固定版本的正常状态。不要重新`uv init`、删除锁或使用全局pip。无Node构建或extra；Python安装会构建本项目所需的editable元数据，日常启动不执行安装/构建。首次初始化需联网访问GitHub、Python下载源和锁定包源；失败停止，不自动升级。

维护者已有完整开发checkout时，也可运行 `pwsh -NoProfile -File './scripts/install-from-github.ps1' -InstallRoot 'D:\MCP'`，其执行同等发布验证、clone、无开发依赖安装及协议检查；`-Tag`选择Releases中的实际标签，`-InstallRoot`只指定安装父目录，新版省略时也为D盘。`-VerifyOnly`只返回经过API核验的Tag/Commit/CI，不安装。不要从未知来源复制或未审阅即执行远程脚本。普通成员可直接使用上面的完整流程。

首次配置，只复制并打开空值模板，不把密钥写入共享命令/历史；已有文件保留：

```powershell
$ErrorActionPreference = 'Stop'
$ProjectDir = 'D:\MCP\zhenzhen-nanobanana-mcp'
$EnvPath = Join-Path $ProjectDir '.env'
$EnvExamplePath = Join-Path $ProjectDir '.env.example'
if (Test-Path -LiteralPath $EnvPath) {
  Write-Host '保留已有 .env，请检查需要更新的字段。'
} else {
  if (!(Test-Path -LiteralPath $EnvExamplePath -PathType Leaf)) { throw '缺少 .env.example。' }
  [IO.File]::Copy($EnvExamplePath, $EnvPath, $false)
}
notepad.exe $EnvPath
if ($LASTEXITCODE -ne 0) { throw '无法打开 .env，请使用本地文本编辑器。' }
```

在本地编辑器中将 `ZHENZHEN_NANOBANANA_API_KEY=` 空值填为原始服务密钥，UTF-8 保存。空模板不能直接启动日常服务；如确需兼容旧环境来源，应明确移除文件中的字段，不能留空。文件是明文，需限制读取权限。以下 NTFS ACL 示例用于自己拥有的文件，限定当前运行账号、SYSTEM 和 Administrators；服务账号不同时替换当前账号 SID，权限不足由文件所有者处理，不默认要求管理员运行 MCP：

```powershell
$ErrorActionPreference = 'Stop'
$EnvPath = 'D:\MCP\zhenzhen-nanobanana-mcp\.env'
$TaskSid = [Security.Principal.WindowsIdentity]::GetCurrent().User
$TaskAcl = Get-Acl -LiteralPath $EnvPath
$TaskAcl.SetAccessRuleProtection($true, $false)
foreach ($Rule in $TaskAcl.GetAccessRules($true, $false, [Security.Principal.SecurityIdentifier])) {
  $TaskAcl.RemoveAccessRuleSpecific($Rule)
}
foreach ($Sid in @($TaskSid.Value, 'S-1-5-18', 'S-1-5-32-544')) {
  $Identity = [Security.Principal.SecurityIdentifier]::new($Sid)
  $Rule = [Security.AccessControl.FileSystemAccessRule]::new($Identity, 'FullControl', 'Allow')
  $TaskAcl.AddAccessRule($Rule)
}
Set-Acl -LiteralPath $EnvPath -AclObject $TaskAcl
(Get-Acl -LiteralPath $EnvPath).Access | Format-Table IdentityReference, FileSystemRights, AccessControlType, IsInherited
```

检查不应包含 Everyone/无关账号。POSIX 安全复制空模板并在本地编辑器填写后执行 `chmod 600 "$HOME/MCP/zhenzhen-nanobanana-mcp/.env"`，保留已有文件。上述命令供使用者执行；开发验证不操作你的真实文件或 ACL。


开发初始化为`uv sync --locked`，然后运行`uv run --no-sync python scripts/check.py`。成员只安装`--no-dev`即可运行，测试、类型及审计工具仅在开发组。成员不执行测试套件或安装Node依赖。

Bash/Zsh/WSL使用者：该版本成员安装验收以Windows为主，POSIX尚未实测。先从Release核对实际标签/完整SHA和CI，再用自己的POSIX绝对目录clone并执行`uv sync --locked --no-dev`；不要照搬Windows路径。第4节保留对应Host CLI示例及其未实测范围。

## 3. 可用性测试

项目根目录运行：

```powershell
pwsh -NoProfile -File '.\scripts\smoke-test.ps1'
if ($LASTEXITCODE -ne 0) { throw '协议检查失败。' }
```

脚本使用项目 `.venv\Scripts\python.exe`，在临时配置目录写入无真实权限的假凭据，显式定位该目录，从另一个含诱导 `.env` 的 Host cwd 启动两个真实 stdio 服务进程。验证两种协议、6 Tools/1 Prompt/1 Resource、免费计划/空任务查询、缺少参数/非法比例/非法接口的 isError；另验证空文件密钥实例退出 2、stdout 为空、不回退不同环境值且不泄露值。每个请求/启动限时 30 秒，预期 JSON `status: passed`、退出 0；预期拒绝日志在 stderr。

POSIX 环境可直接执行 `uv --directory "$HOME/MCP/zhenzhen-nanobanana-mcp" run --no-sync python -m zhenzhen_nanobanana_mcp.smoke`；该脚本的 Windows PowerShell 包装不适用于 POSIX。

smoke 不读取成员真实 `.env`，不需要真实密钥，使用隔离假配置/临时输出，不调用合法的收费绘图请求。开发统一检查执行 `uv run --no-sync python scripts/check.py`；仅行为测试可执行 `uv run --no-sync python -m unittest discover -s tests`，需开发依赖；受控样例覆盖新文档支持矩阵的 28 种模型/格式/参考图组合及非法组合、分辨率边界、10 项后台任务、共享并发、幂等、重启与取消；额外 fake provider 子进程测试通过真实 stdio 提交和查询任务。这不等于真实上游或 Host 业务成功，证据见 `specs/003-async-image-tasks/verification.md`。

## 4. 客户端配置

| 六项配置清单 | 本项目交付 |
|---|---|
| 本地 MCP JSON | 根目录 `.mcp.json.example`，供 Cherry Studio JSON 导入/字段映射；服务自行读取项目 `.env` |
| HTTP/代理 Host JSON | 不适用：本项目仅 stdio，未部署 Cherry Studio Proxy/HTTP 网关 |
| Codex TOML | `templates/codex.config.toml.example` |
| Claude Code JSON | `templates/claude-code.mcp.json.example`，项目作用域 |
| DSH profile YAML | `templates/dsh.patch.yml.example`，web 与 desktop 共用 |
| CLI 注册 | 下方 Codex、Claude Code、DSH × PowerShell/Bash/Zsh；未运行真实用户配置修改 |

所有模板服务名一致，无 `cwd`，用 `uv --directory` 定位。后端服务自己读取 `.env`，Host 默认不设置密钥 env/变量展开；手册内模板与文件逐字同步，JSON 严格解析。Codex 的 env_vars 只允许转发非秘密运行设置。

### Cherry Studio

在设置 → MCP 服务器中添加/导入以下 JSON，或逐项填写名称、类型 stdio、命令、参数；先在服务项目 `.env` 填好密钥，保存后启用服务器，检查工具发现，再在目标助手/对话启用工具。不同版本按钮位置可能不同，本机 GUI 未核对。配置出错时检查服务自己的 `.env`，不用在 Host 填后端密钥。新提交立即返回，模板保留 1800 秒工具超时兼容值，无需用一次长调用等待出图。

<!-- template:.mcp.json.example -->

```json
{
  "mcpServers": {
    "zhenzhen-nanobanana-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "D:\\MCP\\zhenzhen-nanobanana-mcp",
        "run",
        "--no-sync",
        "python",
        "-m",
        "zhenzhen_nanobanana_mcp"
      ]
    }
  }
}
```
<!-- end-template -->

### Codex

将服务表合并到 `~/.codex/config.toml` 或项目 `.codex/config.toml`，保留其它配置，同名表编辑已有项。密钥由服务 `.env` 加载，env_vars 仅转发可选非秘密设置，不填写秘密。保存并重启服务/Codex，在 MCP 设置或 `/mcp` 检查工具；`codex mcp get zhenzhen-nanobanana-mcp` 查询注册。语法依据 [Codex 官方 MCP 文档](https://developers.openai.com/codex/mcp)。

<!-- template:templates/codex.config.toml.example -->

```toml
[mcp_servers.zhenzhen-nanobanana-mcp]
command = "uv"
args = [
  "--directory",
  "D:\\MCP\\zhenzhen-nanobanana-mcp",
  "run",
  "--no-sync",
  "python",
  "-m",
  "zhenzhen_nanobanana_mcp",
]
env_vars = [
  "NANOBANANA_PROJECT_DIR",
  "NANOBANANA_BASE_URL",
  "NANOBANANA_OUTPUT_DIR",
  "NANOBANANA_TIMEOUT_SECONDS",
  "NANOBANANA_CONCURRENCY",
  "NANOBANANA_MAX_PENDING_TASKS",
]
startup_timeout_sec = 30
tool_timeout_sec = 1800
```
<!-- end-template -->

CLI 注册只生成基础启动配置；注册后手工合并上述 `env_vars` 和超时，不通过 `--env KEY=真实值` 把秘密写入共享命令。PowerShell（用户配置作用域）：

```powershell
codex mcp add zhenzhen-nanobanana-mcp -- uv --directory 'D:\MCP\zhenzhen-nanobanana-mcp' run --no-sync python -m zhenzhen_nanobanana_mcp
if ($LASTEXITCODE -ne 0) { throw 'Codex 注册失败。' }
codex mcp get zhenzhen-nanobanana-mcp
if ($LASTEXITCODE -ne 0) { throw 'Codex 配置查询失败。' }
```

Bash：

```bash
codex mcp add zhenzhen-nanobanana-mcp -- uv --directory "$HOME/MCP/zhenzhen-nanobanana-mcp" run --no-sync python -m zhenzhen_nanobanana_mcp || exit 1
codex mcp get zhenzhen-nanobanana-mcp || exit 1
```

Zsh：

```zsh
codex mcp add zhenzhen-nanobanana-mcp -- uv --directory "$HOME/MCP/zhenzhen-nanobanana-mcp" run --no-sync python -m zhenzhen_nanobanana_mcp || exit 1
codex mcp get zhenzhen-nanobanana-mcp || exit 1
```

### Claude Code

Claude-3p未纳入本项目兼容范围，没有已核实的配置路径/schema，双客户端同时打开配置步骤不适用；不能把Claude Code模板直接当作其适配声明。

合并到当前开发项目 `.mcp.json`，保留无关服务器；这是 Claude Code 项目作用域模板。默认不传密钥 env、不展开凭据变量，服务独立读取自己的 `.env`。保存并重启 Claude Code，按项目 MCP 信任提示启用，再用 `/mcp` 检查连接/工具权限。参数依据 [Claude Code 官方文档](https://code.claude.com/docs/en/mcp)及本机 CLI 帮助。

<!-- template:templates/claude-code.mcp.json.example -->

```json
{
  "mcpServers": {
    "zhenzhen-nanobanana-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory",
        "D:\\MCP\\zhenzhen-nanobanana-mcp",
        "run",
        "--no-sync",
        "python",
        "-m",
        "zhenzhen_nanobanana_mcp"
      ],
      "timeout": 1800000
    }
  }
}
```
<!-- end-template -->

PowerShell：

```powershell
claude mcp add --scope project --transport stdio zhenzhen-nanobanana-mcp -- uv --directory 'D:\MCP\zhenzhen-nanobanana-mcp' run --no-sync python -m zhenzhen_nanobanana_mcp
if ($LASTEXITCODE -ne 0) { throw 'Claude Code 注册失败。' }
claude mcp get zhenzhen-nanobanana-mcp
if ($LASTEXITCODE -ne 0) { throw 'Claude Code 配置查询失败。' }
```

Bash：

```bash
claude mcp add --scope project --transport stdio zhenzhen-nanobanana-mcp -- uv --directory "$HOME/MCP/zhenzhen-nanobanana-mcp" run --no-sync python -m zhenzhen_nanobanana_mcp || exit 1
claude mcp get zhenzhen-nanobanana-mcp || exit 1
```

Zsh：

```zsh
claude mcp add --scope project --transport stdio zhenzhen-nanobanana-mcp -- uv --directory "$HOME/MCP/zhenzhen-nanobanana-mcp" run --no-sync python -m zhenzhen_nanobanana_mcp || exit 1
claude mcp get zhenzhen-nanobanana-mcp || exit 1
```

注册后在项目 JSON 合并 `timeout: 1800000`，不用增加密钥 env。本机入口是 `claude.exe`；其他 Windows 包装脚本吞掉 `--` 时先核对 `Get-Command claude` 与相应 `.cmd --help`。配置查询不等于绘图业务成功。

### DSH / App（desktop）

核对本机 DSH `0.2.0-rc.2` schema：插件 `@deepseek-ai/dsh-mcp-client`，stdio，`serverName` 匹配 `^[A-Za-z0-9_-]{1,32}$`，支持 `toolCallTimeoutMs`。本模板关闭自动重连以减少中断时自动恢复的歧义；服务自身也不重发收费请求。当前 web profile 的 schema 导出报告已有无关 Loader 节点错误，本模板只做局部 schema 验证，不宣称完整 profile 通过。

共用补丁如下。默认不包含密钥 env 或 `!!js` 凭据表达式，服务自己读取项目 `.env`。2026-10-21已验证本机DSH CLI隔离profile加载实际MCP桥接插件、发现6工具并免费调用；未验证现用web/desktop完整profile或GUI。Codex app-server也已通过同范围验收，详情见[Host验收记录](docs/HOST-VALIDATION.md)。

<!-- template:templates/dsh.patch.yml.example -->

```yaml
- insert:
    - id: mcp-zhenzhen-nanobanana
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        transport: stdio
        serverName: zhenzhen-nanobanana-mcp
        command: uv
        args:
          - --directory
          - 'D:\MCP\zhenzhen-nanobanana-mcp'
          - run
          - --no-sync
          - python
          - -m
          - zhenzhen_nanobanana_mcp
        toolCallTimeoutMs: 1800000
        failOnStartupError: true
        reconnect:
          enabled: false
```
<!-- end-template -->

两个独立 profile 路径：

- `C:\Users\<windows_user>\.dsh\profiles\web\cordis.patch.yml`
- `C:\Users\<windows_user>\.dsh\profiles\desktop\cordis.patch.yml`

`<windows_user>` 是实际登录用户，不需要管理员；若设置了 DSH_HOME，以它为根目录。只编辑当前使用的 profile，不修改共享 bundle。完整备份/打开步骤（只使用一个 profile 时删去另一项）：

```powershell
$ErrorActionPreference = 'Stop'
$DshRoot = if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $env:USERPROFILE '.dsh' }
foreach ($ProfileName in @('web', 'desktop')) {
  $PatchPath = Join-Path $DshRoot "profiles\$ProfileName\cordis.patch.yml"
  if (!(Test-Path -LiteralPath $PatchPath -PathType Leaf)) { throw "Profile 未初始化：$ProfileName" }
  $BackupPath = "$PatchPath.$([guid]::NewGuid().ToString('N')).bak"
  Copy-Item -LiteralPath $PatchPath -Destination $BackupPath -ErrorAction Stop
  notepad.exe $PatchPath
}
```

若原内容为 `[]`，用模板替换空列表；若已有补丁，把模板的 `- insert:` 块追加为同级列表项，保留已有条目，确保 `mcp-zhenzhen-nanobanana` ID 唯一。已有同名实例时更新它，不再插入。保存并重启对应 web/App（desktop） DSH 运行进程，检查 MCP 工具发现，并在工具权限预设中允许计划/查询工具；收费工具权限按使用者决定。Prompt/Resource 在原生服务发现成功，但 DSH/App（desktop） 是否桥接它们尚未验证。

也可先临时加载补丁。PowerShell：

```powershell
dsh --profile web --patch 'D:\MCP\zhenzhen-nanobanana-mcp\templates\dsh.patch.yml.example'
if ($LASTEXITCODE -ne 0) { throw 'DSH 启动失败。' }
```

Bash（先把模板内的 Windows 安装目录改成真实 POSIX 绝对路径）：

```bash
dsh --profile web --patch "$HOME/MCP/zhenzhen-nanobanana-mcp/templates/dsh.patch.yml.example" || exit 1
```

Zsh：

```zsh
dsh --profile web --patch "$HOME/MCP/zhenzhen-nanobanana-mcp/templates/dsh.patch.yml.example" || exit 1
```

需要 App（desktop） 时将 `web` 改为 `desktop`。`--patch` 只影响本次启动；已合并持久 profile 后不要同时加载同一临时补丁。本机 `dsh --help` 没有 `mcp add`，不要发明该命令。九种 Shell 示例覆盖完整；只核对 PowerShell 下的 CLI 帮助/DSH 局部 schema，实际注册与 Bash/Zsh 执行均未验证。

## 5. 启动排障

### 日常启动

```powershell
uv --directory 'D:\MCP\zhenzhen-nanobanana-mcp' run --no-sync python -m zhenzhen_nanobanana_mcp
```

启动只复用已有环境，不拉取代码、不安装或升级。stdio等待协议输入无普通输出是正常现象，stdout仅协议，日志stderr。配置失败退出2；修改.env或程序后重启Host管理的实际MCP子进程。先查Host日志、`Get-Command uv`、绝对路径与`.venv\Scripts\python.exe`，再运行第3节协议检查；不能用删锁/浮动升级修复。

### 已有Git安装的升级与回滚

先在 Host 停用该 MCP 并等待当前业务结束，记录当前 SHA；收费任务失败/中断先按原三元组查询，旧批次按 request_id 查询，不因升级重发。停止所有使用同一输出目录的服务后备份，再执行版本切换。下方 Read-Host 输入从 Releases 取得的真实目标标签；脚本检查发布记录/CI，并对本地改动或冲突停止。保留 .env、NTFS ACL、outputs 及 SQLite 账本；备份放私有目录，不进入 Git。锁定安装不会覆盖 .env。

```powershell
$ErrorActionPreference = 'Stop'
$ProjectDir = 'D:\MCP\zhenzhen-nanobanana-mcp'
$ExpectedOrigin = 'https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp.git'
$Origin = git -C $ProjectDir remote get-url origin
if ($LASTEXITCODE -ne 0 -or $Origin -cne $ExpectedOrigin) { throw 'origin不匹配，先核对仓库来源。' }
$Changes = git -C $ProjectDir status --porcelain
if ($LASTEXITCODE -ne 0 -or $Changes) { throw 'Git工作区有改动或无法读取，先保留并处理。' }
$PreviousCommit = git -C $ProjectDir rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw '无法记录更新前版本。' }
Write-Host "回滚用提交：$PreviousCommit"
$TargetTag = Read-Host '输入Releases中要安装的正式标签'
$Evidence = & (Join-Path $ProjectDir 'scripts\install-from-github.ps1') -Tag $TargetTag -VerifyOnly
$ExpectedCommit = $Evidence.Commit
git -C $ProjectDir fetch origin tag $TargetTag
if ($LASTEXITCODE -ne 0) { throw '目标标签获取失败。' }
$FetchedCommit = git -C $ProjectDir rev-parse "refs/tags/$TargetTag^{commit}"
if ($LASTEXITCODE -ne 0 -or $FetchedCommit -cne $ExpectedCommit) { throw '标签指向不匹配。' }
git -C $ProjectDir switch --detach --no-overwrite-ignore "refs/tags/$TargetTag"
if ($LASTEXITCODE -ne 0) { throw '版本切换失败；保留现状。' }
uv --directory $ProjectDir sync --locked --no-dev
if ($LASTEXITCODE -ne 0) { throw '安装失败，不启动服务；按记录的SHA回滚。' }
pwsh -NoProfile -File (Join-Path $ProjectDir 'scripts\smoke-test.ps1')
if ($LASTEXITCODE -ne 0) { throw '协议复验失败，不启用服务。' }
```

验证成功再启用Host。若失败，在无源码冲突的同一终端执行下方回滚；新终端先把`$PreviousCommit`设置为先前记录的完整SHA，不能猜测。不要`reset --hard`或`clean -fdx`，不要删除整个环境；源码有改动先保留处理。

```powershell
git -C $ProjectDir switch --detach --no-overwrite-ignore $PreviousCommit
if ($LASTEXITCODE -ne 0) { throw '回滚代码失败。' }
uv --directory $ProjectDir sync --locked --no-dev
if ($LASTEXITCODE -ne 0) { throw '回滚依赖失败。' }
pwsh -NoProfile -File (Join-Path $ProjectDir 'scripts\smoke-test.ps1')
if ($LASTEXITCODE -ne 0) { throw '回滚协议复验失败。' }
```

0.2.0 保留原 batches.sqlite3，另建 tasks.sqlite3。回滚到 0.1 不会执行或查询新任务；回滚前处理/取消未发出的新任务并保留新账本，之后重新升级可能继续其中 queued 项。不要删除账本来绕过幂等；未来有数据迁移时按发布说明的兼容范围回滚。

### 原复制目录或ZIP安装如何迁移

旧目录没有`.git`时，不在其中直接`git pull`，不把远端克隆覆盖旧目录。先停用旧服务；保持旧目录完整，在另一个父目录（例如`D:\MCP-Git`）按第2节clone同名项目目录并安装/验证。确认新目录没有.env/outputs后，把旧.env用`Copy-Item -LiteralPath`复制到新项目并核对/保留其原NTFS ACL，私有outputs和SQLite账本在服务停止后整体复制；目标已存在则停止，不能合并覆盖。不要复制旧.venv、缓存或日志。新路径需要同步修改Host中`--directory`；原Host私有配置先备份、只改这个服务。检验新进程加载同一私有配置及原请求可查询后再启用；旧目录保留作回滚。迁移私有数据涉及成员实际路径，必须先核实，本文不自动执行。

## 6. 文件清单

| 来源/内容 | 用途 |
|---|---|
| [GitHub仓库](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp) | 默认成员来源；`src/`、元数据/锁/运行时、LICENSE、安全模板、scripts、测试、规范及手册随clone取得 |
| [Releases](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/releases) | 正式tag、完整SHA、CI链接、安装验收记录、sdist/wheel及SHA256SUMS；迁移时尚无正式版 |
| `.github/workflows/ci.yml` | dev push、PR及默认分支push的Windows quality检查，Python3.12.14、uv0.12.9 |
| `.github/workflows/release.yml` | 默认分支手动发起，要求同SHA CI成功并重新验收，通过release环境批准后发tag及草稿Release，核对并另获授权后人工公开；不部署远程服务 |
| `scripts/check.py` | 本地与CI统一格式、lint、类型、测试/覆盖率、文档、契约、秘密/依赖、构建、协议及独立运行安装检查 |
| `scripts/install-from-github.ps1` | 核对真实Release/CI并clone安装；`-VerifyOnly`供升级核对 |
| `specs/002-github-distribution/` | 本次迁移的需求、方案、任务及验证边界；门禁设置说明见`docs/RELEASE.md` |
| 本机生成内容 | `.venv`、缓存、dist、test-reports、私有.env和UUID批次图片/账本不进入Git；outputs正式模板仍可跟踪 |

源码安装不要求成员下载wheel或ZIP。开发人员在dev分支提交/推送候选代码后，按授权创建dev→main PR；GitHub分支保护需必需`quality`与评审，release环境需审批及标签保护。工作流文件已准备不等于远端门禁已启用；当前dev上传范围已获授权，门禁、PR、实际CI及首发按阶段落实，不编造运行成功。六步计划见 docs/DELIVERY-PLAN.md。

### 可选ZIP

仅保留旧成员明确需要时的补充分发：`pwsh -NoProfile -File './scripts/package-user.ps1'`，白名单`user-files.json`，当前元数据对应输出`output/zhenzhen-nanobanana-mcp-0.2.1-user.zip`（本轮不生成或发布）；已有包拒绝覆盖，可显式指定`-DestinationDirectory`。ZIP只有一个`zhenzhen-nanobanana-mcp/`顶层目录，解压到父目录即可。它不携带.env/依赖环境/开发资料/业务图片，也不能代替GitHub CI与正式版本。完整可选验收仍由`verify-delivery.py`执行，本次不额外发布成员ZIP。

## 7. 资源清单

实际发现：6 Tools、1 Prompt、1 Resource，无资源模板。JSON schema 从注册信息导出到 `specs/003-async-image-tasks/contracts/mcp.json`。0.2.0 用异步工具替代原 `generate_images`，升级后让 Host 重新发现工具；历史结果查询保留。

| Tool | 输入 | 输出/副作用 |
|---|---|---|
| `list_models` | 无 | 模型/接口/端点矩阵、默认值、配置与上限；不联网，不显示密钥 |
| `plan_ecommerce_images` | 商品事实和绘图要求，见下方 | `ImagePlan`，免费，不读取参考图 |
| `submit_image_tasks` | `checkpointer`、`thread_id`、`tasks` | 先持久化，再立即返回 `TaskPage`；后台收费出图及保存文件 |
| `get_image_tasks` | `checkpointer`、`thread_id`；可选 `task_ids`、`cursor`、`limit` | `TaskPage`，查询已有状态，不重发绘图请求 |
| `cancel_image_tasks` | `checkpointer`、`thread_id`、`task_ids` | `TaskPage`；取消未发出的任务，已可能发出则标记 unknown |
| `get_batch_result` | 历史 `request_id` | 旧 `BatchResult`；只读旧账本，不重新出图 |

`checkpointer`、`thread_id`、`task_id` 均为去除两端空白后的 1–128 字符字符串，不允许控制字符。`checkpointer` 是本地 SQLite 的字符串命名空间，无需额外框架；它不是认证凭据。`thread_id` 由调用 Agent 稳定提供，并非服务自动读取 Host 会话编号。`task_id` 表示一张计划图的稳定业务编号。标识不用于拼接文件路径。

`tasks` 每次 1–12 项，每项独立模型及参数；同次 task_id 不可重复，未知字段拒绝：

| 字段 | 类型/默认 | 限制 |
|---|---|---|
| `task_id` | string，必填 | 在 checkpointer + thread_id 下唯一 |
| `prompt` | string，必填 | 1–8000 字符非空完整提示词 |
| `model` | `gemini-nano-banana-2.1` | 七个模型枚举，见下表 |
| `api_format` | `auto` | `auto`、`dalle`、`chat`、`gemini` |
| `endpoint` | `auto` | `auto`、`generations`、`edits`；后两项仅适用于 dalle |
| `aspect_ratio` | `1:1` | 4:3、3:4、16:9、9:16、2:3、3:2、1:1、4:5、5:4、21:9 |
| `resolution` | null | 可选 `{ "width": 1536, "height": 2048 }`，必填正整数宽高，拒绝浮点/布尔值/字符串 |
| `reference_images` | `[]` | 最多 4 个本机图片绝对路径或公开 HTTP/HTTPS 图片 URL，每个最多 4096 字符 |

| 模型家族 | 支持格式 | DALL·E 端点 | auto 选择 |
|---|---|---|---|
| `gemini-3.1-flash-lite-image` | gemini、chat | 不支持 | gemini |
| `nano-banana-pro`、`nano-banana-pro-2k`、`nano-banana-pro-4k` | dalle | generations、edits | 无参考图 generations，有参考图 edits |
| `gemini-nano-banana-2.1`、`gemini-nano-banana-2.1-2k`、`gemini-nano-banana-2.1-4k` | dalle、gemini、chat | 仅 generations | dalle / generations，参考图通过 image 数组传入 |

基础模型矩阵依据新 `docs/API-ENDPOINT.md`；四个变体按用户确认继承基础模型限制，未独立收费验证。nano-banana-pro 显式 edits 即使没有参考图也发送 multipart。其余不支持的格式/端点组合在整次提交前拒绝，不会静默换模型或失败后切接口。

两组 banana 模型按每项显式 resolution 长边选档：≤1024px 基础版；1024px＜长边≤2048px 用 -2k；＞2048px 用 -4k，2048px 恰好使用 2k。flash-lite 保持原模型。无 resolution 时保持所选模型；有尺寸时按模型家族重新选档。此字段只选模型，不传 size/width/height、不自动缩放、不保证精确输出尺寸。DALL·E 传 aspect_ratio；Gemini/Chat 将比例写入提示词，属于效果要求，不保证像素比例。

`TaskPage` 包含 checkpointer、thread_id、tasks 和 next_cursor。每条任务结果包含三元组、status、actual_model、api_format、endpoint、images、error、created_at、updated_at 和 reused。时间为 Unix 秒数；images 每项包含本机绝对 path、mime_type、width、height、bytes、sha256，不返回大块 base64。查询默认 limit=100，允许 1–100；cursor 默认 0，把 next_cursor 传入下一页，null 表示本页结束。task_ids 可选 1–100 项，省略时查询该命名空间/会话全部任务；续页需保持相同筛选条件。

| status | 含义/处理 |
|---|---|
| queued | 已持久化，等待 worker |
| preparing | 仅准备参考图；尚未发送绘图请求 |
| running | 发送前已写账本，上游可能已经收到请求 |
| succeeded | 通过真实图片内容校验并保存 |
| failed | 预检、上游业务、响应或保存失败；查看 error，不推定未收费 |
| unknown | 中断/网络问题导致结果和费用不确定；禁止自动重发 |
| cancelled | 请求发出前已取消 |

queued/preparing/running 是正常查询状态，返回 MCP isError=false，不表示图片已生成。返回页含 failed/unknown/cancelled 则 isError=true，仍保留该页完整结构化结果。参数或账本错误也按 MCP 错误处理；单项失败不阻止其余任务完成。

免费 `plan_ecommerce_images` 参数：product_name 必填 1–200 字符；selling_points 必填数组，最多 20 项、每项 1–500 字符，可为空；scene=main/detail/scene/poster，默认 main；count=1–12，默认 1；aspect_ratio 默认 1:1；resolution 可选；reference_images 最多 4 项，仅保留引用；requirements 最多 2000 字符、copy_text 最多 1000 字符，默认空。返回 items 含 ImageSpec；提交前逐项添加稳定 task_id，可选模型和接口。

Prompt `ecommerce_brief` 接收必填 string product_name，指导先补充事实、免费规划，再授权出图。Resource `nanobanana://capabilities` 是无参数 JSON 文本，公开模型/格式矩阵、任务操作、三元组及本地 stdio 能力，不联网、不读取私有文件；精确端点矩阵见 list_models。

## 8. 功能说明

把真实商品 PNG/JPEG/WebP 的本机绝对路径（如 `E:\商品素材\收纳篮.png`）或公开图片 URL 交给 Agent。先调用 list_models 确认配置，免费规划详情页：

```json
{
  "product_name": "棉麻收纳篮",
  "selling_points": ["棉麻面料", "可折叠收纳"],
  "scene": "detail",
  "count": 10,
  "aspect_ratio": "3:4"
}
```

审阅 items 的商品事实及提示词后，一轮 submit_image_tasks 可以提交全部 10 项。以下是两项的可用参数示例；10 项时继续添加 detail-03 至 detail-10，每项提供自己的 prompt，数组上限 12：

```json
{
  "checkpointer": "shop-design",
  "thread_id": "basket-detail-20261020",
  "tasks": [
    {
      "task_id": "detail-01",
      "prompt": "制作棉麻收纳篮详情开篇场景；保留参考图的形状、颜色及材质，不添加未提供的配件或文字。",
      "model": "nano-banana-pro",
      "aspect_ratio": "3:4",
      "reference_images": ["E:\\商品素材\\收纳篮.png"]
    },
    {
      "task_id": "detail-02",
      "prompt": "极简暖色家居收纳主题背景，留出卖点文案区域，不画具体商品，不添加文字。",
      "aspect_ratio": "3:4",
      "resolution": {"width": 1536, "height": 2048}
    }
  ]
}
```

提交只做参数、接口矩阵、容量及幂等检查，SQLite 落盘后返回，参考图读取/下载在后台发生。第一项自动走 nano-banana-pro Edits，第二项走 gemini-nano-banana-2.1-2k Generations。Agent 不需要等待全部图像生成，可以继续其他工作，之后 get_image_tasks：

```json
{
  "checkpointer": "shop-design",
  "thread_id": "basket-detail-20261020",
  "task_ids": ["detail-01", "detail-02"]
}
```

也可省略 task_ids 分页列出会话任务；先以 cursor=0、limit=10 查询，再传返回的 next_cursor。根据状态适度查询，避免紧密循环。图片保存在 `outputs/<UUID>/01.png` 等路径，真实扩展名由内容决定，文件不覆盖。新结果以 tasks.sqlite3 为权威记录，无新 manifest.json；原 batches.sqlite3 和旧 manifest 保留给 get_batch_result。

幂等键是 `(checkpointer, thread_id, task_id)`，有效范围是同一个输出目录的共享账本。相同键、相同参数复用已有状态与结果；更改 prompt、参考地址、模型、格式、端点、尺寸或服务根地址会冲突。任一冲突使本次整组不插入其他新项；已有任务仍继续。默认值与 auto 选择在提交时记录，参考图内容在 worker 准备阶段读取；相同路径之后变更文件不会使旧任务重跑。更换输出目录或删除账本会失去该范围的防重记录，勿把它当作重试方式。

需要取消时调用 cancel_image_tasks，参数与查询示例相同但 task_ids 必填。queued/preparing 取消阻止发送；running 取消标记 unknown，只停止本地等待，不能保证停止上游或退款。已完成项保持原状态。同标识再次提交不会重做失败、取消或 unknown 项；确认费用并获准重新绘图后，才显式分配新 task_id，这属于新的收费请求。

MCP 服务进程必须保持运行。正常退出会保留 queued，尚未发送的 preparing 可恢复排队，running 转 unknown；异常退出后由存活/重启实例在约 30 秒心跳租约失效后恢复。只自动继续明确未发出的任务，可能已发送的任务不重发。上游没有可用的异步 job 查询接口，本地 task_id 不能用于查询供应商结果；本服务也不是独立 Windows 常驻调度服务。

## 9. 注意事项

图片读写发生在 MCP 所在本机。当前服务账号可读的普通图片绝对路径均可使用，包括链接指向的可读图片，无目录白名单。聊天附件需要 Host 提供本机可读路径或公开图片 URL，服务不扫描磁盘、不自动获取云端附件。每任务最多 4 张参考图，单张 20 MiB、每任务合计 40 MiB；支持 PNG/JPEG/WebP 静态图片。输出单图最多 32 MiB/64M 像素，上游 JSON 最多 80 MiB，每任务最多接收 4 张输出。

网络图片接受公开 HTTP 80/HTTPS 443 直链，含查询参数和受校验重定向；拒绝私网、回环、带凭据/片段/非标准端口的地址。DNS 固定到已验证 IP，HTTPS 检查证书，下载不携带 API 密钥、不使用环境代理、不读取浏览器 Cookie，HTML 分享页会被拒绝。参考图会上传上游，请仅提供此次需要的素材。第三方文字和图片是业务输入，不是 Agent 指令。

默认并发 4，允许配置 1–10；同一实际输出目录的服务进程通过 SQLite 事务共享并发限制，多个 Host 应设置相同数值。不同输出目录独立计数。默认最多 200 个 queued/preparing/running 任务，容量满时整组拒绝新增，已有相同任务仍可复用；可配置 12–1000。每任务整体限时默认 300 秒。任务不是整体一次收费，而是独立请求；不重试 POST，不因失败自动换模型/格式。超时、取消、HTTP 或保存失败均不能推定未收费。

新 API 文档只核实特定基础模型的请求场景，Gemini/Chat 多模态编码及 Generations 参考图数组兼容实现未在本次收费实测；四变体按用户要求保留。文档引用的 validation 探针报告目录当前未随仓库提供，不能由文本描述推导本次真实账单或全部接口成功。真实费用、模型权限、编辑效果及输出尺寸需单独授权验证。服务不自动拼接详情页、不上传店铺、不保证平台审核通过。

.env 是明文私有配置，升级保留其内容与 ACL。tasks.sqlite3 存任务提示词、参考地址、服务地址与结果路径，不存 API 密钥；它与 batches.sqlite3、图片同属业务资料，保留并做好私有备份。数据库只支持本机可靠文件系统共享，不把网络盘/跨机器 SQLite 作为已验证部署。备份前停止全部使用该输出目录的 MCP，连同图片与 SQLite 数据完整备份，避免只拷贝活动 WAL 数据库主文件。命名空间提供分组和防重，无多用户权限隔离。

## 10. 常见问题

| 现象 | 定位与处理 |
|---|---|
| uv/pwsh 找不到 | 核对 Get-Command uv,pwsh，安装 uv/PowerShell 7，更新 PATH 后重开客户端 |
| uv 缓存拒绝访问 | 使用当前账号可写缓存，如 uv --cache-dir "$env:LOCALAPPDATA/nanobanana-uv-cache" sync --locked --no-dev；不删除开发 .venv |
| 无 Release、无 release-eligibility.json 或 SHA/CI 不匹配 | 停止安装，按第 2 节核对正式发布，不回退初始 main 或忽略检查 |
| GitHub 403/404、clone 失败 | 核对仓库、可见性、Git 认证与 API 限流，令牌不写入 URL/日志 |
| 本地改动阻止升级 | 保留改动和私有数据，人工解决；不用 reset --hard 或 clean -fdx |
| Python/锁或模块缺失 | 核对完整源码、3.12.14、pyproject.toml 与 uv.lock，再 uv sync --locked --no-dev，不删锁/升级依赖 |
| .env 空、错误或权限不足 | 检查实际项目根 UTF-8 文件；空值、重复和非法值不能回退，运行账号需有读取权限 |
| 修改后仍旧行为 | 重启实际 MCP 并重新发现工具，list_models 应有 async_tasks 和 capabilities；仅改开发目录不会更新 D:/MCP 副本 |
| generate_images 不存在 | 0.2.0 已改为 submit_image_tasks + get_image_tasks，历史 request_id 仍用 get_batch_result |
| 提交成功却没有图片 | queued/preparing/running 表示已登记，之后查询任务；failed/unknown 查看 error，勿自动换编号 |
| 不支持所选格式/端点 | 按第 7 节矩阵或 list_models 选择；flash-lite 不支持 dalle，pro 仅 dalle，gemini-nano 不支持 edits |
| 三元组冲突 | 同键已绑定其他参数，本次无新增；查询旧任务，只有明确的新收费业务才用新编号 |
| unknown 或服务退出后未完成 | 上游可能已收费；保留原标识和账本核对结果，不自动重试；重启只恢复未发出的排队任务 |
| 队列容量已满/账本被占用 | 查询现有任务和输出盘权限，容量释放后用相同标识提交；不要删除数据库或创建新编号绕过 |
| 配置的服务地址改变 | 旧排队任务拒绝在不同上游执行，核对配置；保持原地址可在执行前恢复，已失败项不会自动重做 |
| 参考图拒绝/TLS失败 | 检查服务机器路径、账号权限、静态图片/大小、公开标准端口直链和证书；不关闭 TLS、不向下载头加入密钥 |
| Host 等待超时 | 新提交不等待绘图，重新连接后查询原三元组；停止全部 MCP 进程会暂停队列 |
| DSH 名称/补丁报错 | 服务名无点、长度≤32、ID 唯一，编辑 profile 补丁而非 bundle；无关 Loader 错误独立修复 |
| 无 Prompt/Resource 界面 | Host 能力不同，工具发现不等于三类能力全部联调 |
| stdout 杂项、脚本或 Bash 语法错误 | 日志只写 stderr；PowerShell 代码须在 pwsh 执行，相对路径按终端当前目录解析 |
| 可选 ZIP 同名包已存在 | 脚本拒绝覆盖，保留旧包或显式选择新目标目录 |

隔离测试、真实 stdio、Host 联调与收费业务验证分别记录，未验证项不会因文档更新视为通过。
