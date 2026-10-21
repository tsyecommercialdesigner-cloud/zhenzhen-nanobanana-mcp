# zhenzhen-nanobanana-mcp

用于家居日用百货电商绘图的本地 MCP Server，支持商品主图、详情页、家居场景图、营销海报及参考图编辑。通过本地 stdio 接入 Host，使用 t8star 图像服务；图像生成与编辑会产生上游费用。

批量任务先写入本地 SQLite 并立即返回，Agent 后续查询结果，无需用一次工具调用等待整批渲染。图片自动保存到本机，参考图可直接使用可读取的本机绝对路径或公开 HTTP/HTTPS 图片 URL，无需搬到 input 文件夹。

## 当前状态

- 项目版本：`0.2.0`；Python `3.12.14`，uv `0.12.9`，FastMCP `4.1.0`，MCP SDK `2.3.0`。
- 已验证的源码提交：`728172caf5794a374dda4c418779d34cd372155d`，对应 [Windows CI](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39525493697) 成功。Windows 是当前安装和验收平台；未声明 Linux/macOS 已验收。
- 截至 2026-10-21，尚无正式 Release。下面提供该固定 CI 提交的试用安装；元数据版本不代表已有 `v0.2.0` 标签。正式发行后按[手册的 Release 安装流程](MANUAL.md#2-项目初始化)获取版本，不在启动时拉取最新 main。
- Codex app-server、DSH CLI 的工具发现及免费调用已验证；GUI、自主选工具和各 Host 完整私人配置不在该结论内，见 [Host 验收](docs/HOST-VALIDATION.md)。

## 快速安装与配置

需要 Git、PowerShell 7 和 uv 0.12.9；uv 根据项目版本文件安装/使用 Python 3.12.14。首次安装需访问 GitHub、Python 下载源和 PyPI。以下命令在 **PowerShell 7** 中执行，安装父目录需可写；已有目录请按[升级/迁移流程](MANUAL.md#5-启动排障)处理。

```powershell
$ErrorActionPreference = 'Stop'
$ProjectDir = 'C:\MCP\zhenzhen-nanobanana-mcp'
$ExpectedCommit = '728172caf5794a374dda4c418779d34cd372155d'
if (Test-Path -LiteralPath $ProjectDir) { throw '目录已存在，请按手册更新，不能覆盖安装。' }
New-Item -ItemType Directory -Path (Split-Path -Parent $ProjectDir) -Force | Out-Null
git clone --branch main --single-branch 'https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp.git' $ProjectDir
if ($LASTEXITCODE -ne 0) { throw '仓库获取失败。' }
git -C $ProjectDir checkout --detach $ExpectedCommit
if ($LASTEXITCODE -ne 0) { throw '固定提交不存在，停止安装。' }
$ActualCommit = git -C $ProjectDir rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $ActualCommit -cne $ExpectedCommit) { throw '提交核验失败。' }
uv --directory $ProjectDir sync --locked --no-dev
if ($LASTEXITCODE -ne 0) { throw '锁定依赖安装失败。' }
```

在同一个 PowerShell 会话中创建并打开项目私有 `.env`，保留已有文件：

```powershell
$EnvPath = Join-Path $ProjectDir '.env'
if (!(Test-Path -LiteralPath $EnvPath)) {
  [IO.File]::Copy((Join-Path $ProjectDir '.env.example'), $EnvPath, $false)
}
notepad.exe $EnvPath
```

在编辑器中填写 `ZHENZHEN_NANOBANANA_API_KEY=` 的值，保存为 UTF-8。使用原始密钥，不加 `Bearer `；不要把真实值写入共享命令、Host 模板或 Git。

服务固定读取实际项目根目录 `.env`，逐字段优先级为 **项目 .env → 进程环境 → Windows 当前用户环境**，统一使用 `ZHENZHEN_NANOBANANA_API_KEY`，旧名称不再读取。只有缺失才回退；空值、非法值、重复字段或文件解析失败会阻止启动。详细配置、权限和升级保留规则见[手册](MANUAL.md#1-环境准备)。

安装后先执行不收费的协议检查：

```powershell
pwsh -NoProfile -File (Join-Path $ProjectDir 'scripts\smoke-test.ps1')
if ($LASTEXITCODE -ne 0) { throw '协议检查失败。' }
```

smoke 使用隔离假配置，不调用绘图接口，也不证明真实密钥或上游业务可用。日常由 Host 使用下列入口启动，不安装、构建或升级依赖；手工运行 stdio 服务会等待协议输入：

```powershell
uv --directory 'C:\MCP\zhenzhen-nanobanana-mcp' run --no-sync python -m zhenzhen_nanobanana_mcp
```

## 接入客户端

完整添加、保存、启用、工具发现和排障步骤见 [MANUAL 第 4 节](MANUAL.md#4-客户端配置)，不要覆盖 Host 中已有的其它服务。

| Host | 配置模板 |
|---|---|
| Codex | [TOML](templates/codex.config.toml.example) |
| DSH / App | [profile YAML](templates/dsh.patch.yml.example) |
| Claude Code | [JSON](templates/claude-code.mcp.json.example) |
| Cherry Studio | [JSON](.mcp.json.example) |

模板使用 `C:\MCP\zhenzhen-nanobanana-mcp`；安装到其它位置时修改 `--directory` 的绝对路径。密钥由服务读取，默认不填入 Host 配置。

## 异步绘图工作流

公开 **6 个工具**，另提供 1 个 Prompt、1 个 Resource；详细参数和结构见[手册资源清单](MANUAL.md#7-资源清单)与[工具契约](specs/003-async-image-tasks/contracts/mcp.json)。

| 工具 | 用途 |
|---|---|
| `list_models` | 免费查看模型、接口限制、并发和配置状态 |
| `plan_ecommerce_images` | 免费生成待审阅的主图/详情页/场景/海报计划 |
| `submit_image_tasks` | 一次登记 1–12 项后台生成/编辑任务，立即返回；后台会收费 |
| `get_image_tasks` | 按原身份查询状态、结果和图片绝对路径，不重新提交 |
| `cancel_image_tasks` | 取消任务；已发送任务不保证远端停止或退款 |
| `get_batch_result` | 查询旧版 request_id 批次记录，不生成图片 |

先核实商品事实与计划，再为每项分配稳定的 `(checkpointer, thread_id, task_id)` 并提交。查询 `queued`、`preparing`、`running` 时继续查原身份；`succeeded` 后读取图片路径。相同身份和内容重放返回 `reused=true`，不同内容冲突拒绝，不能通过换ID盲目重试 `failed` 或 `unknown`。

默认并发为 **4**，可配置为 1–10；同一输出目录内的进程共享限额，单批 10 项不等于同时启动 10 个上游请求。默认输出为项目 `outputs/`，可通过 `NANOBANANA_OUTPUT_DIR` 配置绝对路径；所有共享账本的实例需保持相同并发配置。

## 模型与编辑

默认模型是 `gemini-nano-banana-2.1`；各模型的接口限制不同：

| 模型系列 | 可用格式 | DALL·E 端点 |
|---|---|---|
| `gemini-3.1-flash-lite-image` | Gemini、OpenAI Chat | 不支持 |
| `gemini-nano-banana-2.1` | Gemini、OpenAI Chat、DALL·E | Generations；参考图也走此端点，不走 Edits |
| `nano-banana-pro` | DALL·E | Generations、Edits |

后两系列各保留 `-2k`、`-4k` 变体。显式分辨率长边 ≤1024 使用基础版，1024＜长边≤2048 使用 2k，＞2048 使用 4k；Flash-lite 不做该映射。这是模型路由，不保证上游精确输出像素。

表中为当前接口契约；本轮真实收费验证覆盖基础 gemini-nano-banana-2.1 的 Generations 和基础 nano-banana-pro 的 Edits，其余模型、格式、参考图编码与分辨率变体未因此视为实测通过。

输入图片可直接使用本机可读取的绝对路径或公开 HTTP/HTTPS URL；服务仍校验格式、大小、像素、下载地址和路径安全边界。无法把“能读取参考图”当作商品真实性证明；只使用已确认的商品信息。

## 验证与维护

- 单张主图、3 项并发生成和一次本机参考图编辑及原身份重放已实测，见[单张验收](docs/SINGLE-IMAGE-ACCEPTANCE.md)、[小批量与编辑验收](docs/BATCH-EDIT-ACCEPTANCE.md)。
- [10 项详情页实测](docs/TEN-IMAGE-ACCEPTANCE.md)已通过：单次异步登记、并发峰值 4、结果查询和 10 图落盘，整批原身份重放未新增上游请求。默认模型未请求精确像素，上游返回格式/尺寸可能不同。完整状态见[交付任务](specs/002-github-distribution/tasks.md)。
- MCP 进程退出期间不执行任务。重启只恢复明确未发送的任务；可能已经发送的中断任务标记 `unknown`，不自动重发。防重仅在同一实际输出目录的账本内成立，不能承诺供应商网络侧 exactly-once。
- 维护者使用 `uv sync --locked`、`uv run --no-sync python scripts/check.py`，经 PR、必需 Windows CI 和审查合入；发布另行授权，先生成草稿，核对后才公开。更新保留成员 `.env`、权限与图片/SQLite，不清空安装目录。

使用与更新：[MANUAL](MANUAL.md) · 当前计划：[DELIVERY-PLAN](docs/DELIVERY-PLAN.md) · 工程规范：[ENGINEERING-GUIDE](docs/ENGINEERING-GUIDE.md) · 许可证：[MIT](LICENSE)
