# zhenzhen-nanobanana-mcp

用于家居日用百货电商绘图的本地 MCP Server：商品主图、详情页、场景图、营销海报和参考图编辑。Agent 一次可登记 1–12 项后台任务，立即得到持久化状态，后续查询图片路径；默认并发 4，图片自动保存到本机。生成和编辑会产生供应商费用。

参考图可直接使用本机可读图片绝对路径或公开 HTTP/HTTPS 图片直链，无需搬入 `input`。服务会检查图片内容、大小及网络地址；不自动上传店铺或保证平台审核通过。

## 安装版本与环境

成员使用已正式公开的 [v0.2.1](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/releases/tag/v0.2.1)，对应提交 `09501092c369e2a314df757eece5fa8d7a38e64e` 和[成功的 Windows CI](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39534145510)。默认目录 `D:\MCP\zhenzhen-nanobanana-mcp`；当前开发分支及文档更新不自动改变成员安装或已发布附件。

需要 Windows x64、Git、PowerShell 7、uv（已验证 `0.12.9`）。项目精确使用 Python `3.12.14`，由 uv 按锁定声明准备；FastMCP `4.1.0`、MCP SDK `2.3.0`。首次安装需访问 GitHub、Python 下载源和 PyPI；绘图及图片下载另需业务网络。Linux/macOS/WSL 尚未完成安装验收。

## 快速安装与配置

在 **PowerShell 7** 执行以下首次安装步骤。只创建父目录，clone 自动创建项目目录；已有安装请按[升级与迁移](MANUAL.md#5-启动排障)处理。

```powershell
$ErrorActionPreference = 'Stop'
$ProjectDir = 'D:\MCP\zhenzhen-nanobanana-mcp'
$ExpectedCommit = '09501092c369e2a314df757eece5fa8d7a38e64e'
if (Test-Path -LiteralPath $ProjectDir) { throw '目录已存在，请按手册更新，不能覆盖。' }
New-Item -ItemType Directory -Path (Split-Path -Parent $ProjectDir) -Force | Out-Null
git clone --branch v0.2.1 --single-branch 'https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp.git' $ProjectDir
if ($LASTEXITCODE -ne 0) { throw '仓库获取失败。' }
$ActualCommit = git -C $ProjectDir rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $ActualCommit -cne $ExpectedCommit) { throw '标签提交不匹配。' }
uv --directory $ProjectDir sync --locked --no-dev
if ($LASTEXITCODE -ne 0) { throw '运行依赖安装失败。' }
pwsh -NoProfile -File (Join-Path $ProjectDir 'scripts\smoke-test.ps1')
if ($LASTEXITCODE -ne 0) { throw '隔离协议检查失败。' }
$EnvPath = Join-Path $ProjectDir '.env'
if (!(Test-Path -LiteralPath $EnvPath)) {
  [IO.File]::Copy((Join-Path $ProjectDir '.env.example'), $EnvPath, $false)
}
Start-Process -FilePath 'notepad.exe' -ArgumentList ('"{0}"' -f $EnvPath) -ErrorAction Stop
```

在编辑器中填写 `ZHENZHEN_NANOBANANA_API_KEY=`，保存为 UTF-8；使用原始密钥，不加 `Bearer `，不写入共享命令或 Host 模板。仅当字段缺失时按 **项目 `.env` → 进程环境 → Windows 当前用户环境** 回退；空值、非法值、重复或解析错误会阻止启动。已有 `.env` 和业务数据在升级时保留。完整发布记录核验、权限和回滚步骤见[手册](MANUAL.md)。

协议检查使用隔离假配置，不产生绘图费用；通过后在所用 Host 合并服务配置。日常启动入口为：

```powershell
uv --directory 'D:\MCP\zhenzhen-nanobanana-mcp' run --no-sync python -m zhenzhen_nanobanana_mcp
if ($LASTEXITCODE -ne 0) { throw 'MCP 服务退出失败，请检查 stderr。' }
```

stdio 等待输入时没有普通输出属于正常状态。Host 负责启动子进程，无需同时手动常驻；启动不安装依赖或拉取代码。

## 选择客户端

| 客户端 | 配置入口 |
|---|---|
| Cherry Studio | [本地 JSON 模板](.mcp.json.example)，导入/填写后保存、启用并绑定助手 |
| Codex | [TOML 模板](templates/codex.config.toml.example)，合并到实际 Codex 配置后重载服务 |
| Claude Code | [项目 JSON 模板](templates/claude-code.mcp.json.example)，按所选项目作用域添加；Claude-3p 未作为已验证适配交付 |
| 原生 DSH / DSH App / Multica | [同一 YAML 模板](templates/dsh.patch.yml.example)，分别合并到 web / desktop / multica 的独立 patch |

完整的添加、备份、保存、启用、工具发现和权限步骤见[客户端配置](MANUAL.md#4-客户端配置)。DSH 章节按新规范提供三份 profile 的存在检查、唯一备份、打开命令与空列表/已有 patch 合并方式；不覆盖其他插件，不改共享 bundle。HTTP/代理配置不适用于本项目。

## 使用流程

1. 调用免费 `list_models` 核对配置，提供已核实的商品事实与参考图。
2. 用免费 `plan_ecommerce_images` 规划并审阅提示词；出图前确认收费授权。
3. 为每项提供稳定的 `(checkpointer, thread_id, task_id)`，一次 `submit_image_tasks` 登记任务。
4. 通过 `get_image_tasks` 查询同一身份，成功后使用返回的图片绝对路径。

相同身份与相同参数复用记录；参数冲突整组拒绝新增。`queued/preparing/running` 只表示尚未完成；`failed/unknown`、超时或取消不保证未收费，不自动换编号重试。防重范围为同一实际输出目录，保留 SQLite 与图片，不删除账本绕过幂等。其余工具为 `cancel_image_tasks` 和旧批次只读 `get_batch_result`；共 6 Tools、1 Prompt、1 Resource，详见[资源与参数](MANUAL.md#7-资源清单)。

默认模型 `gemini-nano-banana-2.1`，自动使用 DALL·E Generations；`nano-banana-pro` 仅 DALL·E，支持 Generations/Edits；Flash-lite 仅 Gemini/Chat。两个 banana 家族支持基础版及 `-2k/-4k`。显式分辨率长边 ≤1024 用基础版、≤2048 用 2k、>2048 用 4k；Flash-lite 不路由。此规则只选择模型，不保证精确输出像素，完整接口矩阵见手册。

## 验证与维护

[发布安装验收](docs/RELEASE-0.2.1-ACCEPTANCE.md)、[Host 免费验收](docs/HOST-VALIDATION.md)、[本机 D 盘迁移验收](docs/LOCAL-D-DRIVE-MIGRATION-ACCEPTANCE.md)及[10 项业务验收](docs/TEN-IMAGE-ACCEPTANCE.md)分别记录安装、协议、Host 与真实业务证据。当前 Codex 与 DSH CLI 隔离 profile 已有工具调用证据；DSH 三种完整私人 profile、Multica 集成、各 GUI、Bash/Zsh、全部模型/变体和真实故障恢复仍有未验证范围，不因更新文档视为通过。

维护者遵循分支 → PR → Windows CI → 评审 → 合并；发布单独授权，先创建草稿，核对后才公开。开发安装使用 `uv sync --locked`、检查使用 `uv run --no-sync python scripts/check.py`；成员只需锁定运行依赖。任务状态见[交付任务](specs/002-github-distribution/tasks.md)。

[完整手册](MANUAL.md) · [交付计划](docs/DELIVERY-PLAN.md) · [MIT 许可证](LICENSE)
