# zhenzhen-nanobanana-mcp 交付与使用手册

本手册面向 v0.3.0：21 Tools、9 Resources、6 Prompts，包含同步/异步出图、[设计研讨与确认](docs/ECOMMERCE-DESIGN.md)、[共享规范竞品复刻](docs/REFERENCE-REPLICA-UPGRADE.md)、[同款整套提示词](docs/PRODUCT-SUITE.md)及[20项/5并发可靠队列](docs/QUEUE-RELIABILITY.md)。版本须以正式Release和release-eligibility.json核验；草稿阶段停止安装。

现用D盘安装仍为v0.2.2/8工具；本次发布不改动现用Host或安装。原最小DSH profile看图未通过的历史说明保留；独立CLI补齐附件与视觉模型路由后已通过[Agent实际看图](docs/DSH-VISION-HOST-VALIDATION.md)，Desktop GUI与现用完整profile仍未验收。历史[16图验收](specs/010-live-ecommerce-validation/verification.md)为7图Agent通过、9图需修订，不自动重画或等同全部可上架。安装概览见[README](README.md)，发布边界见[v0.3.0说明](docs/RELEASE-0.3.0.md)。

## 1. 环境准备

### 安装方式与版本

默认从[项目 GitHub 仓库](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp.git)取得正式发布标签，安装到 `D:\MCP\zhenzhen-nanobanana-mcp`。本项目只有本地 stdio 服务，没有已部署的 HTTP 服务或网关；不需要 Node.js、npm 或运行项目脚手架。开发仓库、成员安装和各客户端配置是独立位置，不会自动互相更新。

| 项目 | 本项目取值 |
|---|---|
| 项目目录、发行包、服务标识 | `zhenzhen-nanobanana-mcp`（23 字符） |
| Python 模块 | `zhenzhen_nanobanana_mcp` |
| 安装目标版本 | [v0.3.0](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/releases/tag/v0.3.0)，精确SHA与main CI以正式release-eligibility.json为准；草稿不可安装 |
| 运行环境 | Windows x64，PowerShell 7，Git；Python 精确 `3.12.14`，已验证 uv `0.12.9` |
| 框架与 SDK | FastMCP `4.1.0`、MCP SDK `2.3.0`，以项目锁文件为准 |
| 已验收协议 | `2026-07-28` 请求级元数据模式、兼容 `2025-11-25` 初始化握手模式 |
| Host 配置 | Cherry Studio、Codex、Claude Code；DSH 共用补丁适用于 web、desktop、multica 三种 profile，需逐份合并 |
| 实测边界 | v0.2.2已通过独立安装、双协议8工具及重启后当前Codex的免费历史查询；更早Codex app-server/DSH CLI隔离profile结果保留历史版本范围，不代表v0.2.2已在DSH复验。DSH三种私人profile完整配置、Multica集成、各GUI和Bash/Zsh执行均未因此视为验证通过 |

历史v0.2.2对应 [Windows CI39571818062](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39571818062) 及[发布安装验收](docs/RELEASE-0.2.2-ACCEPTANCE.md)。现用D盘升级和重启后当前Codex会话验收见[本机v0.2.2验收](docs/LOCAL-V0.2.2-UPGRADE-ACCEPTANCE.md)，更早迁移见[历史验收](docs/LOCAL-D-DRIVE-MIGRATION-ACCEPTANCE.md)。本手册按v0.3.0目标维护，不重写旧标签或Release附件；正式发布前不把开发分支作为默认成员安装来源。

首次安装需访问 GitHub、Python 下载源和 PyPI。公开仓库可 HTTPS clone；私有仓库访问使用成员自己的 Git 凭据管理机制，不在 URL 中写令牌。绘图另需可用的 `https://ai.t8star.org` 账号及模型权限；图片下载访问公开 HTTP/HTTPS 地址。未提供离线依赖包。业务 HTTP 客户端禁用环境代理并校验证书，包管理器的网络设置不能证明业务网络也可用。

### 配置与凭据

实际凭据文件是 `D:\MCP\zhenzhen-nanobanana-mcp\.env`；使用其他安装位置时是该项目实际根目录的 `.env`。不搜索 Host 工作目录或其父目录，不读取 `.env.example` 作为凭据。

| 字段 | 必填/默认 | 读取来源与约束 |
|---|---|---|
| `ZHENZHEN_NANOBANANA_API_KEY` | 日常启动必填 | 项目 `.env` → 进程环境 → Windows 当前运行账号 `HKCU\Environment`；原始 ASCII 密钥，不加 `Bearer `，无内部空白/控制字符，无固定前缀要求 |
| `NANOBANANA_PROJECT_DIR` | 默认从源码布局定位 | 进程环境；非秘密绝对目录，特殊 wheel 布局需明确指定 |
| `NANOBANANA_BASE_URL` | `https://ai.t8star.org` | 进程环境；无路径/query/凭据的 HTTPS 服务根地址 |
| `NANOBANANA_OUTPUT_DIR` | 项目 `outputs/` | 进程环境；绝对路径，存放图片和 SQLite 账本 |
| `NANOBANANA_TIMEOUT_SECONDS` | `300` | 进程环境；1–600 秒，单任务准备、绘图与下载的整体限时 |
| `NANOBANANA_CONCURRENCY` | `5` | 进程环境；整数 1–20，同输出目录各实例设置一致 |
| `NANOBANANA_SAFE_ATTEMPTS` | `3` | 进程环境；1–5，安全阶段每轮最大尝试数 |
| `NANOBANANA_RETRY_DELAY_SECONDS` | `1` | 进程环境；0–30，指数退避基数秒 |
| `NANOBANANA_MAX_PENDING_TASKS` | `200` | 进程环境；整数 20–1000，限制 queued/preparing/running/recovering 项总数 |

只有密钥字段按上表逐来源回退，其余运行设置不从 `.env` 加载。旧密钥名称不再读取；`NANOBANANA_INPUT_DIRS` 已停用且被忽略，没有本地图片目录白名单。

只有文件/字段缺失才回退；已定义但空、非法、重复、文件不可读/语法错误/非 UTF-8 时立即失败，不使用低优先级旧值。文件最多 1 MiB，UTF-8 可含 BOM，使用锁定的 python-dotenv 底层解析且不展开变量。`${VAR}` 和 `$(command)` 是字面值，不执行。非 Windows 不读取 Windows 用户注册表。

`.env` 是明文私有资料，限制到实际服务账号及必要管理员可读写；升级保留内容和访问权限。不要对磁盘根目录递归改 ACL，也不要默认以管理员运行 MCP。修改配置后重启实际 MCP 子进程，再调用免费 `list_models` 核对；该工具仅报告配置是否加载，不返回密钥，也不证明供应商权限或余额正常。

## 2. 项目初始化

以下安装目标为v0.3.0，包含21工具及同步/异步、整套设计与参考复刻能力。仅在正式Release公开后执行。安装器核对正式Release、完整提交和CI，继续拒绝草稿、预发布或资格记录不匹配的版本；仅有标签不等于满足安装资格。

### 首次安装

先核对[正式 Release](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/releases/tag/v0.3.0)及其 `release-eligibility.json` 的标签、完整提交和 CI。下面在 PowerShell 7 运行：只创建父目录，由 clone 创建同名项目目录；目录已存在时改用第 5 节，不能覆盖。

```powershell
$ErrorActionPreference = 'Stop'
$ProjectDir = 'D:\MCP\zhenzhen-nanobanana-mcp'
$ReleaseTag = 'v0.3.0'
if (Test-Path -LiteralPath $ProjectDir) { throw '目录已存在，请使用升级或迁移流程。' }
New-Item -ItemType Directory -Path (Split-Path -Parent $ProjectDir) -Force | Out-Null
git clone --branch $ReleaseTag --single-branch 'https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp.git' $ProjectDir
if ($LASTEXITCODE -ne 0) { throw '仓库获取失败。' }
$ActualCommit = git -C $ProjectDir rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw '无法读取标签提交，停止安装。' }
$Evidence = & (Join-Path $ProjectDir 'scripts\install-from-github.ps1') -Tag $ReleaseTag -VerifyOnly
$ExpectedCommit = $Evidence.Commit
if ($ActualCommit -cne $ExpectedCommit -or $Evidence.Tag -cne $ReleaseTag) { throw '发布记录不匹配。' }
uv --directory $ProjectDir sync --locked --no-dev
if ($LASTEXITCODE -ne 0) { throw '运行依赖安装失败。' }
pwsh -NoProfile -File (Join-Path $ProjectDir 'scripts\smoke-test.ps1')
if ($LASTEXITCODE -ne 0) { throw '隔离协议检查失败。' }
```

`-VerifyOnly` 只读取正式 Release、验收附件和对应 main CI，核对 `quality` 成功，不安装、不写凭据；缺少记录、GitHub 限流或网络失败时停止，不回退 main。已有可信开发 checkout 的维护者也可使用其中的 `scripts/install-from-github.ps1 -Tag v0.3.0 -InstallRoot 'D:\MCP'` 完成同等检查和安装，不能在尚未取得源码时执行不存在的相对脚本。

detached HEAD 是固定发布标签安装的正常状态。依赖落在项目独立 `.venv`；`uv sync --locked --no-dev` 会准备运行环境，不删除锁、不用全局 pip、不重新 `uv init`。日常启动使用 `--no-sync`，不安装、构建或升级依赖。没有额外 Node 构建或必选 extra。

### 安全创建私有 .env

安装及隔离协议检查不需要真实密钥。准备连接 Host 前，在本机编辑器填写项目 `.env`；下面只创建空模板，已有文件保持不变，命令不包含真实密钥：

```powershell
$ErrorActionPreference = 'Stop'
$ProjectDir = 'D:\MCP\zhenzhen-nanobanana-mcp'
$EnvPath = Join-Path $ProjectDir '.env'
if (Test-Path -LiteralPath $EnvPath) {
  Write-Host '保留已有 .env，只手工合并必要字段。'
} else {
  [IO.File]::Copy((Join-Path $ProjectDir '.env.example'), $EnvPath, $false)
}
Start-Process -FilePath 'notepad.exe' -ArgumentList ('"{0}"' -f $EnvPath) -ErrorAction Stop
```

在编辑器中填写 `ZHENZHEN_NANOBANANA_API_KEY=` 的值并以 UTF-8 保存，再按第 1 节核对文件访问权限。空值模板不能启动日常服务；如确需兼容环境来源，须明确移除文件中的字段，不能留空。升级旧配置时只重命名密钥字段，保留密钥值、其他内容及权限，不自动删除用户环境变量。不要把密钥写进 Host JSON/TOML、共享命令或 Git。

## 3. 可用性测试

成员可从任意 PowerShell 工作目录运行实际交付脚本：

```powershell
pwsh -NoProfile -File 'D:\MCP\zhenzhen-nanobanana-mcp\scripts\smoke-test.ps1'
if ($LASTEXITCODE -ne 0) { throw 'MCP 协议检查失败，请查看 stderr。' }
```

脚本使用该安装的 `.venv`，在临时目录准备无真实权限的假凭据，从无关 cwd 启动真实 stdio 子进程；不读取成员 `.env`，不提交有效绘图请求。每请求/启动限时 30 秒，成功返回 JSON `status: passed`、退出 0；失败非零并在 stderr 提供诊断。测试空密钥实例预期退出 2，stdout 无额外输出。

覆盖两种已声明协议、v0.3.0的21 Tools/6 Prompts/9 Resources、免费计划/查询、输入错误及配置失败。协议成功不等于当前 Host 已加载真实配置，更不证明真实绘图或所有模型可用。配置客户端后，在该 Host 中调用 `list_models`，核对模型、密钥状态、输出目录及sync_generation=true，再做免费计划/历史查询；没有出图授权时停在这里。

| 证据类别 | 已有结果与边界 |
|---|---|
| 单元/契约及受控替身 | 幂等、并发、取消/恢复和上游格式映射；[异步验收](specs/003-async-image-tasks/verification.md)、[同步验收](specs/004-sync-image-tools/verification.md)及v0.2.2发布后的10项同步专项测试，不能冒充真实供应商效果 |
| 发布安装/协议 | [v0.2.2 安装验收](docs/RELEASE-0.2.2-ACCEPTANCE.md)，Windows、锁定无开发依赖、stdio 与免费能力 |
| Host | [隔离 Host 验收](docs/HOST-VALIDATION.md)和[v0.2.2 D盘升级/重启后当前Codex验收](docs/LOCAL-V0.2.2-UPGRADE-ACCEPTANCE.md)：8工具发现、只读等待、5任务/10批次及15图片核对；DSH三种完整私人profile/Multica及真实Host长等待出图仍未验证 |
| 历史收费业务 | [单张](docs/SINGLE-IMAGE-ACCEPTANCE.md)、[小批量/编辑](docs/BATCH-EDIT-ACCEPTANCE.md)、[10 项](docs/TEN-IMAGE-ACCEPTANCE.md)与迁移后单张；不因改手册重复执行，不覆盖所有模型/格式/变体或真实故障恢复 |

开发者才需 `uv sync --locked` 和 `uv run --no-sync python scripts/check.py`。Linux/macOS/WSL 安装及 Bash/Zsh 示例没有本轮实测结论；POSIX 目录需自行对应，不能在 Git Bash 中粘贴 PowerShell 语法。

## 4. 客户端配置

| 六项配置清单 | 本项目交付 |
|---|---|
| 本地 MCP JSON | 根目录 `.mcp.json.example`，供 Cherry Studio JSON 导入/字段映射；服务自行读取项目 `.env` |
| HTTP/代理 Host JSON | 不适用：本项目仅 stdio，未部署 Cherry Studio Proxy/HTTP 网关 |
| Codex TOML | `templates/codex.config.toml.example` |
| Claude Code JSON | `templates/claude-code.mcp.json.example`，项目作用域 |
| DSH profile YAML | `templates/dsh.patch.yml.example`，web、desktop、multica 三种 profile 共用 |
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

### Claude Code / Claude-3p 配置位置

按指南先给出同时打开两个配置位置的快捷命令；只打开已存在的文件，缺失时提示初始化。Claude-3p 尚未纳入本项目已验证 Host，列出路径不代表它已适配；本节只交付 Claude Code 项目作用域 JSON，不将两个客户端的整份配置互换。编辑前为实际要修改的文件创建私有备份，仅合并目标服务，保留无关配置。

```powershell
$ErrorActionPreference = 'Stop'
$ConfigFiles = @(
  (Join-Path $env:USERPROFILE '.claude.json')
  (Join-Path $env:LOCALAPPDATA 'Claude-3p\claude_desktop_config.json')
)
foreach ($ConfigFile in $ConfigFiles) {
  if (Test-Path -LiteralPath $ConfigFile -PathType Leaf) {
    Start-Process -FilePath 'notepad.exe' -ArgumentList ('"{0}"' -f $ConfigFile) -ErrorAction Stop
  } else {
    Write-Warning "配置文件不存在，请先按对应客户端流程初始化：$ConfigFile"
  }
}
```

`.claude.json` 是 Claude Code 用户状态/配置位置，不能用下方项目 `.mcp.json` 整体覆盖。下方 CLI 明确使用 `--scope project`，应在想启用 MCP 的工作项目中运行，不要求该工作项目就是 MCP Server 安装目录。

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

### DSH：原生、App 与 Multica

同一 stdio YAML 补丁分别合并到三个独立 profile，不修改共享 bundle。仅使用部分客户端时，从下方 `$Profiles` 删除不适用项；不存在的 profile 应先在对应客户端初始化，不能创建空文件冒充初始化。

| 使用方 | profile | 默认 patch 位置（当前用户目录下） |
|---|---|---|
| 原生 DSH | `web` | `.dsh\profiles\web\cordis.patch.yml` |
| DSH App | `desktop` | `.dsh\profiles\desktop\cordis.patch.yml` |
| Multica 中的 DSH | `multica` | `.dsh\profiles\multica\cordis.patch.yml` |

优先使用当前终端非空白的 `DSH_HOME`，否则取当前用户 `.dsh`。客户端另设运行目录时先调整 `$DshRoot`。以下 PowerShell 7 命令先确认所有目标文件存在，之后为每份文件创建不覆盖的唯一相邻备份，最后打开；它不添加插件、不改写 patch，也不启动客户端：

```powershell
$ErrorActionPreference = 'Stop'
$DshRoot = if ([string]::IsNullOrWhiteSpace($env:DSH_HOME)) {
  Join-Path $env:USERPROFILE '.dsh'
} else {
  $env:DSH_HOME
}
$Profiles = @('web', 'desktop', 'multica')
$PatchFiles = @($Profiles | ForEach-Object {
  Join-Path $DshRoot "profiles\$_\cordis.patch.yml"
})
foreach ($PatchFile in $PatchFiles) {
  if (!(Test-Path -LiteralPath $PatchFile -PathType Leaf)) {
    throw "配置不存在，请先初始化对应客户端或核对 DSH_HOME：$PatchFile"
  }
}
foreach ($PatchFile in $PatchFiles) {
  $BackupPath = '{0}.{1}.bak' -f $PatchFile, ([guid]::NewGuid().ToString('N'))
  [IO.File]::Copy($PatchFile, $BackupPath, $false)
  Write-Host "备份：$BackupPath"
}
foreach ($PatchFile in $PatchFiles) {
  Start-Process -FilePath 'notepad.exe' -ArgumentList ('"{0}"' -f $PatchFile) -ErrorAction Stop
}
```

备份含私有配置，只留本机并保留访问限制。编辑器中逐份处理：

1. 文件只有顶层空列表 `[]`：以完整 YAML 模板替换。
2. 文件已有 patch：将下面的 `- insert:` 作为同一顶层列表条目追加，保留原有插件、缩进、注释和 `!!js`，不要另加顶层 `[]` 或嵌套完整列表。
3. 若同一 MCP 实例已存在，就地合并它，不重复插入；保留其他实例。新增实例使用不冲突的唯一 ID，本模板为 `mcp-zhenzhen-nanobanana`。

插件为 `@deepseek-ai/dsh-mcp-client`，本项目既有 DSH `0.2.0-rc.2` 局部 schema 验证记录确认 stdio、1–32 字符服务名和 `toolCallTimeoutMs`。下面是三种 profile 共用的后端配置；不含密钥或 JavaScript 凭据表达式。各客户端实际安装的插件版本与 schema 不一致时先核对，不盲目合并。已有 web Loader 节点错误与本补丁分别处理；不宣称整个私人 profile 通过。

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

保存后分别在原生 DSH、App、Multica 中按实际版本重新加载所选 profile 或重启对应 DSH 运行实例；不凭空指定尚未核实的 GUI 按钮。检查补丁加载日志、v0.3.0的21个工具发现，以及工具权限预设：先允许免费计划/查询，generate_images与submit_image_tasks的收费提交权限由使用者决定。App 或 Multica 可能由宿主管理运行时，不假定全局 `dsh.exe` 与其内置运行时版本相同。

新版源码已通过独立DSH CLI的21工具发现与免费调用，补齐附件/视觉路由后Agent实际看图也通过，详见docs/DSH-VISION-HOST-VALIDATION.md。原最小profile看图未通过的历史结论保留；三种完整profile、Multica、Desktop GUI与Host Prompt/Resource桥接仍未因此视为通过。工具发现不代表绘图业务验收。

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

需要其他已初始化 profile 时将 `web` 改为 `desktop` 或 `multica`；此命令只用于相应 CLI 运行时，不替代 App/Multica 宿主的启动流程。`--patch` 只影响本次启动；已合并持久 profile 后不要同时加载同一临时补丁。本机 `dsh --help` 没有 `mcp add`，不要发明该命令。九种 Shell 示例覆盖完整；本轮只重新核对安装 CLI 的帮助，未执行真实注册或加载私人 profile；Bash/Zsh、App/Multica 仍未实测。

## 5. 启动排障

### 日常启动

```powershell
uv --directory 'D:\MCP\zhenzhen-nanobanana-mcp' run --no-sync python -m zhenzhen_nanobanana_mcp
```

启动只复用已有环境，不拉取代码、不安装或升级。stdio等待协议输入无普通输出是正常现象，stdout仅协议，日志stderr。配置失败退出2；修改.env或程序后重启Host管理的实际MCP子进程。先查Host日志、`Get-Command uv`、绝对路径与`.venv\Scripts\python.exe`，再运行第3节协议检查；不能用删锁/浮动升级修复。

### 已有Git安装的升级与回滚

先在 Host 停用该 MCP 并等待当前业务结束，记录当前 SHA；收费任务失败/中断先按原三元组查询，旧批次按 request_id 查询，不因升级重发。停止所有使用同一输出目录的服务后备份，再执行版本切换。下方以正式公开后的标签v0.3.0为目标；脚本检查发布记录/CI，并对本地改动或冲突停止。保留 .env、NTFS ACL、outputs 及 SQLite 账本；备份放私有目录，不进入 Git。锁定安装不会覆盖 .env。

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
$TargetTag = 'v0.3.0'
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
| [Releases](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/releases) | v0.3.0正式公开后作为安装目标；包含正式tag、完整SHA、CI链接、安装验收记录、sdist/wheel及SHA256SUMS |
| `.github/workflows/ci.yml` | dev push、PR及默认分支push的Windows quality检查，Python3.12.14、uv0.12.9 |
| `.github/workflows/release.yml` | 默认分支手动发起，要求同SHA CI成功并重新验收，通过release环境批准后发tag及草稿Release，核对并另获授权后人工公开；不部署远程服务 |
| `scripts/check.py` | 本地与CI统一格式、lint、类型、测试/覆盖率、文档、契约、秘密/依赖、构建、协议及独立运行安装检查 |
| `scripts/install-from-github.ps1` | 核对真实Release/CI并clone安装；`-VerifyOnly`供升级核对 |
| `specs/002-github-distribution/` | 本次迁移的需求、方案、任务及验证边界；门禁设置说明见`docs/RELEASE.md` |
| 本机生成内容 | `.venv`、缓存、dist、test-reports、私有.env和UUID批次图片/账本不进入Git；outputs正式模板仍可跟踪 |

源码安装不要求成员下载wheel或ZIP。开发人员在dev分支提交/推送候选代码后，按授权创建dev→main PR；GitHub分支保护要求必需`quality`与评审，release环境要求审批及标签保护。门禁及受控发布流程见[发布说明](docs/RELEASE.md)，v0.2.2的实际发布/安装证据见[验收报告](docs/RELEASE-0.2.2-ACCEPTANCE.md)。发布需独立授权；本次v0.3.0已获发布授权，先按受控流程生成草稿并核对，再正式公开。六步计划见 docs/DELIVERY-PLAN.md。

### 可选ZIP（仅按明确需要）

仅保留旧成员明确需要时的补充分发：`pwsh -NoProfile -File './scripts/package-user.ps1'`，白名单`user-files.json`，当前版本元数据对应输出`output/zhenzhen-nanobanana-mcp-0.3.0-user.zip`（本轮不生成或发布）；已有包拒绝覆盖，可显式指定`-DestinationDirectory`。ZIP只有一个`zhenzhen-nanobanana-mcp/`顶层目录，解压到父目录即可。它不携带.env/依赖环境/开发资料/业务图片，也不能代替GitHub CI与正式版本。完整可选验收仍由`verify-delivery.py`执行，本次不额外发布成员ZIP。

## 7. 资源清单

v0.3.0提供21 Tools、6 Prompts、9 Resources，无资源模板；契约从注册信息导出至 `specs/003-async-image-tasks/contracts/mcp.json`。同步/异步共用持久队列，设计确认与收费授权分开，历史批次查询保留；升级后须让Host重新发现工具。v0.2.2旧安装保持8工具，不能用旧安装验证新版发现结果。

| Tool | 输入 | 输出/副作用 |
|---|---|---|
| `list_models` | 无 | 模型/接口/端点矩阵、默认值、配置与上限；不联网，不显示密钥 |
| `plan_ecommerce_images` | 商品事实和绘图要求，见下方 | `ImagePlan`，免费，不读取参考图 |
| `generate_images` | 三元组、tasks；可选wait_timeout_seconds | 提交并等待本组终态；成功时图片已落盘，会收费 |
| `wait_image_tasks` | 三元组中的checkpointer/thread_id、必填task_ids；可选wait_timeout_seconds | 只等待已有任务，无新提交 |
| `submit_image_tasks` | `checkpointer`、`thread_id`、`tasks` | 先持久化，再立即返回 `TaskPage`；后台收费出图及保存文件 |
| `get_image_tasks` | `checkpointer`、`thread_id`；可选 `task_ids`、`cursor`、`limit` | `TaskPage`，查询已有状态，不重发绘图请求 |
| `cancel_image_tasks` | `checkpointer`、`thread_id`、`task_ids` | `TaskPage`；取消未发出的任务，已可能发出则标记 unknown |
| `get_batch_result` | 历史 `request_id` | 旧 `BatchResult`；只读旧账本，不重新出图 |
| `retry_image_tasks` | 以工具JSON schema及对应专题为准 | 显式重试满足安全条件的已有任务；不确定收费状态不得盲目重提 |
| `inspect_design_images` | 以工具JSON schema及对应专题为准 | 免费读取本机或公开URL图片，交给Host观察 |
| `plan_ecommerce_design` | 以工具JSON schema及对应专题为准 | 免费保存版本化设计底稿，缺少信息时返回待补问题 |
| `confirm_ecommerce_design` | 以工具JSON schema及对应专题为准 | 记录用户对当前版本的确认，不代表收费授权 |
| `submit_ecommerce_design` | 以工具JSON schema及对应专题为准 | 提交已确认设计，须另提供收费授权 |
| `get_ecommerce_design` | 以工具JSON schema及对应专题为准 | 免费查询设计、已有任务及图片路径 |
| `plan_reference_replica` | 以工具JSON schema及对应专题为准 | 保存参考图拆解与逐图复刻方案 |
| `export_reference_replica` | 以工具JSON schema及对应专题为准 | 只读导出参考复刻提示词 |
| `review_reference_replica` | 以工具JSON schema及对应专题为准 | 记录Agent对已有结果图的复核，不自动重画 |
| `build_product_suite_prompts` | 以工具JSON schema及对应专题为准 | 免费构造主图、详情页、SKU共享规范方案 |
| `export_product_suite_prompts` | 以工具JSON schema及对应专题为准 | 只读导出已校验的整套提示词 |
| `build_reference_replica_prompts` | 以工具JSON schema及对应专题为准 | 免费构造共享规范竞品复刻方案 |
| `export_validated_reference_replica` | 以工具JSON schema及对应专题为准 | 只读导出已校验的竞品复刻提示词 |

`checkpointer`、`thread_id`、`task_id` 均为去除两端空白后的 1–128 字符字符串，不允许控制字符。`checkpointer` 是本地 SQLite 的字符串命名空间，无需额外框架；它不是认证凭据。`thread_id` 由调用 Agent 稳定提供，并非服务自动读取 Host 会话编号。`task_id` 表示一张计划图的稳定业务编号。标识不用于拼接文件路径。

`tasks` 每次 1–20 项，每项独立模型及参数；同次 task_id 不可重复，未知字段拒绝：

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
| recovering | 已有可靠响应，正在下载/落盘或按原响应恢复，不重新出图 |
| succeeded | 通过真实图片内容校验并保存 |
| failed | 预检、上游业务、响应或保存失败；查看 error，不推定未收费 |
| unknown | 中断/网络问题导致结果和费用不确定；禁止自动重发 |
| cancelled | 请求发出前已取消 |

queued/preparing/running/recovering 是正常查询状态，返回 MCP isError=false，不表示图片已生成。返回页含 failed/unknown/cancelled 则 isError=true，仍保留该页完整结构化结果。参数或账本错误也按 MCP 错误处理；单项失败不阻止其余任务完成。

免费 `plan_ecommerce_images` 参数：product_name 必填 1–200 字符；selling_points 必填数组，最多 20 项、每项 1–500 字符，可为空；scene=main/detail/scene/poster，默认 main；count=1–20，默认 1；aspect_ratio 默认 1:1；resolution 可选；reference_images 最多 4 项，仅保留引用；requirements 最多 2000 字符、copy_text 最多 1000 字符，默认空。返回 items 含 ImageSpec；提交前逐项添加稳定 task_id，可选模型和接口。

Prompt `ecommerce_brief` 接收必填 string product_name，指导先补充事实、免费规划，再授权出图。Resource `nanobanana://capabilities` 是无参数 JSON 文本，公开模型/格式矩阵、任务操作、三元组及本地 stdio 能力，不联网、不读取私有文件；精确端点矩阵见 list_models。

### 同步生成与只读等待（v0.2.2）

`generate_images` 接收与 `submit_image_tasks` 完全相同的 checkpointer、thread_id、tasks；参考图非空时仍按原矩阵编辑，模型和分辨率路由不变。一次同步调用可等待1–20项全部进入终态，仍按共享账本并发限额执行；不是串行逐图调用。没有wait_timeout_seconds参与任务指纹，跨入口重放同一身份和内容不重复出图。

`wait_image_tasks` 不接收tasks或提示词，不提交上游。必须提供同一命名空间/会话内1–100个已存在且不重复的task_ids，不支持空集合、错误会话或缺失任务，也无分页。两种等待工具均额外接收wait_timeout_seconds：严格整数1–1200、默认600秒；从本次开始等待计算，包含排队时间，不改变每项原有绘图超时。

返回 `TaskWaitResult`：原TaskPage的全部字段加布尔 `wait_timed_out`。全部成功才isError=false，返回已落盘图片；若全部终态但含failed/unknown/cancelled，则isError=true、wait_timed_out=false，保留全部成功和失败结果。到期仍有活跃项时isError=true、wait_timed_out=true，保留当前状态和已完成图片，不能把部分结果视为整组成功。

等待到期/客户端取消只结束本次等待，不触发队列取消、状态改写或重复收费；继续用get_image_tasks查询或wait_image_tasks等待原身份。需要主动取消时仍用cancel_image_tasks。若Host结束整个MCP进程，后台无法继续执行，按原生命周期恢复规则处理。Host工具时限应大于等待时限并留传输余量；现模板1800秒，等待最大1200秒。不要因Host超时而自动重新分配任务ID。

以下是同步生成参数示例（会收费，仅在明确授权后调用）：

```json
{
  "checkpointer": "shop-design",
  "thread_id": "mug-main",
  "tasks": [
    {
      "task_id": "main-01",
      "prompt": "虚构商品示意：单只无品牌白色马克杯，白背景，无文字，无水印。",
      "aspect_ratio": "1:1"
    }
  ],
  "wait_timeout_seconds": 600
}
```

继续等待只调用wait_image_tasks，参数如下，不再传绘图任务：

```json
{
  "checkpointer": "shop-design",
  "thread_id": "mug-main",
  "task_ids": [
    "main-01"
  ],
  "wait_timeout_seconds": 600
}
```

### 设计工作流的发现与使用

先inspect看图，plan/build保存底稿，与用户研讨并confirm当前revision/digest；submit_ecommerce_design另需authorize_paid。缺商品事实先补充，竞品仅作构图/风格参考，不能迁移其参数。预览/导出与执行提示一致，结果复核不自动重画。retry仅按[恢复边界](docs/QUEUE-RELIABILITY.md)显式操作，不确定收费状态不盲目重提。

Prompts：`reference_replication_brief`、`product_suite_brief`、`product_suite_review`、`reference_replica_brief`、`reference_replica_review`、`ecommerce_brief`。

Resources：`nanobanana://reference-replication`、`nanobanana://templates/product-suite`、`nanobanana://templates/styles`、`nanobanana://templates/main`、`nanobanana://templates/detail`、`nanobanana://templates/sku`、`nanobanana://templates/reference-replica`、`nanobanana://templates/reference-analysis`、`nanobanana://capabilities`。完整输入字段、错误和返回schema以工具发现契约为准。

## 8. 功能说明

把真实商品 PNG/JPEG/WebP 的本机绝对路径（如 `E:\商品素材\收纳篮.png`）或公开图片 URL 交给 Agent。先调用 list_models 确认配置，免费规划详情页：

```json
{
  "product_name": "棉麻收纳篮",
  "selling_points": [
    "棉麻面料",
    "可折叠收纳"
  ],
  "scene": "detail",
  "count": 10,
  "aspect_ratio": "3:4"
}
```

审阅 items 的商品事实及提示词后，一轮 submit_image_tasks 可以提交全部 10 项。以下是两项的可用参数示例；10 项时继续添加 detail-03 至 detail-10，每项提供自己的 prompt，数组上限 20：

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
      "reference_images": [
        "E:\\商品素材\\收纳篮.png"
      ]
    },
    {
      "task_id": "detail-02",
      "prompt": "极简暖色家居收纳主题背景，留出卖点文案区域，不画具体商品，不添加文字。",
      "aspect_ratio": "3:4",
      "resolution": {
        "width": 1536,
        "height": 2048
      }
    }
  ]
}
```

提交只做参数、接口矩阵、容量及幂等检查，SQLite 落盘后返回，参考图读取/下载在后台发生。第一项自动走 nano-banana-pro Edits，第二项走 gemini-nano-banana-2.1-2k Generations。Agent 不需要等待全部图像生成，可以继续其他工作，之后 get_image_tasks：

```json
{
  "checkpointer": "shop-design",
  "thread_id": "basket-detail-20261020",
  "task_ids": [
    "detail-01",
    "detail-02"
  ]
}
```

也可省略 task_ids 分页列出会话任务；先以 cursor=0、limit=10 查询，再传返回的 next_cursor。根据状态适度查询，避免紧密循环。图片保存在 `outputs/<UUID>/01.png` 等路径，真实扩展名由内容决定，文件不覆盖。新结果以 tasks.sqlite3 为权威记录，无新 manifest.json；原 batches.sqlite3 和旧 manifest 保留给 get_batch_result。

幂等键是 `(checkpointer, thread_id, task_id)`，有效范围是同一个输出目录的共享账本。相同键、相同参数复用已有状态与结果；更改 prompt、参考地址/预期hash、模型、格式、端点、尺寸或服务根地址会冲突。任一冲突使本次整组不插入其他新项；已有任务仍继续。worker准备时核对可选reference_sha256并冻结内容；后续安全重试使用冻结图。相同路径之后变更文件不会使旧任务重画。供应商键及输出SHA校验、原响应恢复见[可靠性说明](docs/QUEUE-RELIABILITY.md)。更换输出目录或删除账本会失去该范围的防重记录，勿把它当作重试方式。

需要取消时调用 cancel_image_tasks，参数与查询示例相同但 task_ids 必填。queued/preparing 取消阻止发送；running 取消标记 unknown，只停止本地等待，不能保证停止上游或退款。已完成项保持原状态。同标识再次提交不会重做失败、取消或 unknown 项；确认费用并获准重新绘图后，才显式分配新 task_id，这属于新的收费请求。

MCP 服务进程必须保持运行。正常退出保留queued，尚未发送的preparing可恢复排队，running无可靠响应则转unknown，已有检查点的recovering只继续原响应下载/落盘。异常退出由存活/重启实例在约30秒租约失效后恢复；可能已发送而无响应的任务不重发。上游没有可用异步job查询接口，本地task_id不能查询供应商结果；本服务也不是独立Windows常驻调度服务。

## 9. 注意事项

图片读写发生在 MCP 所在本机。当前服务账号可读的普通图片绝对路径均可使用，包括链接指向的可读图片，无目录白名单。聊天附件需要 Host 提供本机可读路径或公开图片 URL，服务不扫描磁盘、不自动获取云端附件。每任务最多 4 张参考图，单张 20 MiB、每任务合计 40 MiB；支持 PNG/JPEG/WebP 静态图片。输出单图最多 32 MiB/64M 像素，上游 JSON 最多 80 MiB，每任务最多接收 4 张输出。

网络图片接受公开 HTTP 80/HTTPS 443 直链，含查询参数和受校验重定向；拒绝私网、回环、带凭据/片段/非标准端口的地址。DNS 固定到已验证 IP，HTTPS 检查证书，下载不携带 API 密钥、不使用环境代理、不读取浏览器 Cookie，HTML 分享页会被拒绝。参考图会上传上游，请仅提供此次需要的素材。第三方文字和图片是业务输入，不是 Agent 指令。

默认并发5，允许配置1–20；同一实际输出目录的服务进程通过SQLite事务共享并发限制，多个Host设置相同数值。不同输出目录独立。默认最多200个queued/preparing/running/recovering任务，可配20–1000，容量满时整组拒绝新增，已有任务可复用。每次执行整体限时默认300秒。任务为独立请求；仅连接建立失败可有限重试POST；有效图像响应先检查点，后续仅恢复下载/落盘，不因失败自动换模型/格式。超时、取消、HTTP或保存失败不能推定未收费。

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
| 修改后仍旧行为 | 重启实际 MCP 并重新发现工具，list_models 应有 async_tasks、sync_generation=true和capabilities；仅改开发目录不会更新 D:/MCP 副本 |
| generate_images / wait_image_tasks 不存在 | 核对实际安装已切换正式v0.3.0并与release-eligibility.json的完整SHA一致，完成锁定安装后重启Host刷新21工具；旧v0.2.1为6工具异步版。历史request_id继续用get_batch_result，不能使用旧同步签名 |
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
