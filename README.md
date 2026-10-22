# zhenzhen-nanobanana-mcp

v0.3.1 面向家居日用电商，保留 **21 Tools、9 Resources、6 Prompts** 及同步/异步出图。本补丁修复队列热路径重复结构事务、阻塞 stdio 的持久文件写入和 Windows SQLite 文件占用；不改变公开工具、模型或收费防重契约。功能见[设计工作流](docs/ECOMMERCE-DESIGN.md)、[竞品复刻](docs/REFERENCE-REPLICA-UPGRADE.md)、[同款整套模板](docs/PRODUCT-SUITE.md)和[队列可靠性](docs/QUEUE-RELIABILITY.md)。

发布状态以[正式 Release](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/releases/tag/v0.3.1)及其资格记录为准；草稿或记录缺失时安装器停止。现用 D 盘安装仍为 v0.3.0，本次发布不自动更新它。原始验收证据、历史版本和图片保持不变。

用于家居日用百货电商绘图的本地 MCP Server：商品主图、详情页、场景图、营销海报和参考图编辑。Agent 一次可提交 1–20 项任务，选择异步立即返回，或同步等待完成并落盘后返回；默认并发 5，图片自动保存到本机。生成和编辑会产生供应商费用。

参考图可直接使用本机可读图片绝对路径或公开 HTTP/HTTPS 图片直链，无需搬入 `input`。服务会检查图片内容、大小及网络地址；不自动上传店铺或保证平台审核通过。

## 安装版本与环境

成员安装目标为 v0.3.1，默认目录 `D:\MCP\zhenzhen-nanobanana-mcp`。精确标签 SHA 与成功 main CI 来自正式附件 `release-eligibility.json`；下面的示例逐项核对，不猜测提交。本次修复的已验收代码基线为 `e0a80b53accce98ab8819e2812d871ceb23a1d7a`，它不作为本版最终发布标签的提交。

需要 Windows x64、Git、PowerShell 7、uv（已验证 `0.12.9`）。项目精确使用 Python `3.12.14`，由 uv 按锁定声明准备；FastMCP `4.1.0`、MCP SDK `2.3.0`。首次安装需访问 GitHub、Python 下载源和 PyPI；绘图及图片下载另需业务网络。Linux/macOS/WSL 尚未完成安装验收。

## 快速安装与配置

在 **PowerShell 7** 执行以下首次安装步骤。只创建父目录，clone 自动创建项目目录；已有安装请按[升级与迁移](MANUAL.md#5-启动排障)处理。

```powershell
$ErrorActionPreference = 'Stop'
$ProjectDir = 'D:\MCP\zhenzhen-nanobanana-mcp'
if (Test-Path -LiteralPath $ProjectDir) { throw '目录已存在，请按手册更新，不能覆盖。' }
New-Item -ItemType Directory -Path (Split-Path -Parent $ProjectDir) -Force | Out-Null
git clone --branch v0.3.1 --single-branch 'https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp.git' $ProjectDir
if ($LASTEXITCODE -ne 0) { throw '仓库获取失败。' }
$Evidence = & (Join-Path $ProjectDir 'scripts\install-from-github.ps1') -Tag v0.3.1 -VerifyOnly
$ExpectedCommit = $Evidence.Commit
$ActualCommit = git -C $ProjectDir rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $ActualCommit -cne $ExpectedCommit -or $Evidence.Tag -cne 'v0.3.1') { throw '正式发布记录不匹配。' }
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

v0.3.1 提供 21 个工具，支持同步与异步出图，详见[资源与参数](MANUAL.md#7-资源清单)：

| 工具 | 用途 |
|---|---|
| `list_models` | 免费核对模型、配置与能力 |
| `plan_ecommerce_images` | 免费规划商品图提示词 |
| `generate_images` | 提交生成/编辑任务，等待完成并落盘后返回，会收费 |
| `submit_image_tasks` | 持久化后立即返回，后台并发生成/编辑，会收费 |
| `get_image_tasks` | 查询已有任务及图片路径 |
| `wait_image_tasks` | 只等待已有任务，不新增绘图请求 |
| `cancel_image_tasks` | 取消未发出的任务；已可能发出时标记不确定 |
| `get_batch_result` | 只读查询旧批次 |
| `retry_image_tasks` | 显式重试满足安全条件的已有任务；不确定收费状态不得盲目重提 |
| `inspect_design_images` | 免费读取本机或公开URL图片，交给Host观察 |
| `plan_ecommerce_design` | 免费保存版本化设计底稿，缺少信息时返回待补问题 |
| `confirm_ecommerce_design` | 记录用户对当前版本的确认，不代表收费授权 |
| `submit_ecommerce_design` | 提交已确认设计，须另提供收费授权 |
| `get_ecommerce_design` | 免费查询设计、已有任务及图片路径 |
| `plan_reference_replica` | 保存参考图拆解与逐图复刻方案 |
| `export_reference_replica` | 只读导出参考复刻提示词 |
| `review_reference_replica` | 记录Agent对已有结果图的复核，不自动重画 |
| `build_product_suite_prompts` | 免费构造主图、详情页、SKU共享规范方案 |
| `export_product_suite_prompts` | 只读导出已校验的整套提示词 |
| `build_reference_replica_prompts` | 免费构造共享规范竞品复刻方案 |
| `export_validated_reference_replica` | 只读导出已校验的竞品复刻提示词 |

1. 调用免费 `list_models` 核对配置，提供已核实的商品事实与参考图。
2. 用免费 `plan_ecommerce_images` 规划并审阅提示词；出图前确认收费授权。
3. 为每项提供稳定的 `(checkpointer, thread_id, task_id)`，选择异步 `submit_image_tasks` 立即登记，或同步 `generate_images` 等待本组完成、图片落盘后返回。
4. 异步任务用 `get_image_tasks` 立即查询；已有任务也可用 `wait_image_tasks` 等待，成功后使用返回的图片绝对路径。

同步生成/等待的 `wait_timeout_seconds` 默认600，严格整数1–1200秒，包含排队时间；Host工具超时应更长并预留传输开销。等待超时返回 `isError=true`、`wait_timed_out=true` 及当前状态和已完成图片，只结束此次等待，后台继续。客户端取消也不主动取消队列任务，按原身份继续等待或查询，不能换编号重提；如果Host关闭整个MCP进程，仍受原有恢复规则约束。

相同身份与相同参数跨同步/异步入口复用记录；参数冲突整组拒绝新增。`queued/preparing/running` 只表示尚未完成；`failed/unknown`、超时或取消不保证未收费，不自动换编号重试。防重范围为同一实际输出目录，保留 SQLite 与图片，不删除账本绕过幂等。此外提供6 Prompts、9 Resources；完整名称与设计流程见手册及对应专题文档。

默认模型 `gemini-nano-banana-2.1`，自动使用 DALL·E Generations；`nano-banana-pro` 仅 DALL·E，支持 Generations/Edits；Flash-lite 仅 Gemini/Chat。两个 banana 家族支持基础版及 `-2k/-4k`。显式分辨率长边 ≤1024 用基础版、≤2048 用 2k、>2048 用 4k；Flash-lite 不路由。此规则只选择模型，不保证精确输出像素，完整接口矩阵见手册。

## 验证与维护

[21工具隔离Host验收](docs/HOST-VALIDATION-PR19.md)与[DSH Agent实际看图](docs/DSH-VISION-HOST-VALIDATION.md)记录真实Host后端验证。原最小DSH profile因缺附件/视觉路由未通过看图；补齐后使用codeproxy-anthropic / claude-sonnet-5-5完成CLI Agent识图，Desktop GUI仍未验证。

历史[16图业务验收](specs/010-live-ecommerce-validation/verification.md)只证明相应模型/接口的流程和文件校验，7图Agent通过、9图需修订，不等于全部可上架。新版本发布说明及当前边界见[v0.3.1](docs/RELEASE-0.3.1.md)；旧[v0.2.2安装验收](docs/RELEASE-0.2.2-ACCEPTANCE.md)与[D盘记录](docs/LOCAL-V0.2.2-UPGRADE-ACCEPTANCE.md)保留原范围。全部模型/变体、真实故障恢复及Desktop GUI不因发布而视为通过。

维护者遵循分支 → PR → Windows CI → 评审 → 合并；发布单独授权，先创建草稿，核对后才公开。开发安装使用 `uv sync --locked`、检查使用 `uv run --no-sync python scripts/check.py`；成员只需锁定运行依赖。任务状态见[交付任务](specs/002-github-distribution/tasks.md)。

[完整手册](MANUAL.md) · [交付计划](docs/DELIVERY-PLAN.md) · [MIT 许可证](LICENSE)
