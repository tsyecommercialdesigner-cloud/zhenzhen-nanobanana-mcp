# 首版验证记录

## 2026-10-15：完全移除参考图目录白名单及网络URL支持（AC14/AC15）

用户进一步要求覆盖此前T15的可选白名单行为：完全忽略旧NANOBANANA_INPUT_DIRS及内部兼容roots参数，不检查参考图目录归属；旧变量无需删除，不修改用户环境。OS读取权限、普通文件、图片格式/字节/像素检查保留；输出位置和防覆盖规则不变。公开HTTP 80/HTTPS 443直链可作为参考图。

- `uv --cache-dir .cache/uv run --no-sync python -m unittest discover -s tests`退出0，40项通过。含旧目录配置（有效/空/非法）不生效、目录外文件/Windows目录联接可读、HTTP相对重定向与HTTPS图片、本地+网络三参考图同项MCP编辑、DNS端口选择、下载无密钥、404/非图片预检不收费；网络私有地址防护仍通过。
- 运行副本smoke退出0，2026-07-28与2025-11-25均通过。legacy模式故意传入旧目录配置，发现仍为readable_files/input_dirs=[]。开发契约重新导出、四手册模板同步、文档一致性、ruff检查均通过。
- C:\MCP运行环境使用MediaLoader真实下载 `https://raw.githubusercontent.com/python-pillow/Pillow/main/Tests/images/hopper.png` 成功：PNG，128×128，30605字节；不调用收费模型。HTTP与混合编辑使用受控上游验证，未额外收费实测。
- 源码/README/MANUAL/Codex模板已同步运行副本；保留.env、图片、数据库、Host实际配置、旧ZIP。服务进程重启并刷新工具发现后加载新规则。AC14/AC15通过；历史记录中的input/可选白名单是当时行为。

## 2026-10-15：原素材直接读取（AC14）

用户反馈默认input白名单不适合成员使用，改为默认读取本机账号可读图片绝对路径；显式NANOBANANA_INPUT_DIRS仍启用白名单，空/非法值报错。以下历史记录中的默认input限制为当时行为。

- `uv --cache-dir .cache/uv sync --locked`退出0，依赖未改；`uv --cache-dir .cache/uv run --no-sync python -m unittest discover -s tests`共38项通过。新增受控编辑用例从input外的中文带空格原素材路径读取，再直接使用outputs生成结果继续编辑；检查默认发现readable_files/input_dirs=[]、配置目录白名单、空项/相对目录报错、非图片/目录/缺失文件/相对路径拒绝、读取权限错误脱敏。原有白名单越界和Windows目录联接逃逸测试继续通过。
- `pwsh -NoProfile -File ./scripts/smoke-test.ps1`及C:\MCP运行副本对应绝对路径命令均退出0；2026-07-28验证默认访问模式，2025-11-25验证显式白名单模式；无收费API调用。
- 注册契约重新导出，check-docs及ruff检查通过；工具输入说明与服务instructions明确不必搬运input，手册示例改为原素材绝对路径。AC06（白名单模式）/AC14通过。
- 开发项目及运行副本同步config/media/models/server/smoke与README/MANUAL；未改用户Host/全局环境/凭据/输出或旧ZIP。已有进程需重启并刷新工具说明；此前显式设置的目录白名单仍按配置生效。本次编辑链路用受控上游验证，未额外收费实测。

## 2026-10-15：切换默认模型

按用户要求把 list_models.default_model 与 generate_images 默认值改为 gemini-nano-banana-2.1；显式选择其他模型仍有效，默认DALL·E不变。35项unittest通过，新增通过MCP省略model参数的受控出图检查，验证基础/2k/4k实际请求模型。注册契约重新导出、文档一致性与ruff检查退出0。开发项目与C:\MCP运行副本smoke均退出0，2026-07-28与2025-11-25发现默认值和工具schema默认值一致。不执行收费调用。运行副本只同步server.py、smoke.py、README.md、MANUAL.md，未改凭据、图片、账本或Host配置；已有Host服务进程须重启才能加载改动。

## 2026-10-15：模型变体与显式分辨率路由（AC01/AC13）

- `uv --cache-dir .cache/uv sync --locked` 退出0，依赖与锁文件未改。
- `uv --cache-dir .cache/uv run --no-sync python -m unittest discover -s tests`：34项通过，退出0。七模型×三格式×生成/编辑共42项上游映射；覆盖无尺寸、1024/1025/2047/2048/2049/4096与横竖图、变体直选、flash-lite不路由、非法尺寸、免费计划保留、混合批次逐项实际模型、输出schema、改变尺寸编号冲突、旧账本读取与旧指纹防重。另验证路由结果传入三种格式的生成/编辑调用。全部业务请求为受控替身。
- `pwsh -NoProfile -File ./scripts/smoke-test.ps1` 退出0：真实stdio子进程auto=2026-07-28、legacy=2025-11-25均通过；七模型发现、带尺寸免费计划及非法尺寸拒绝通过；收费业务联网0。
- `uv --cache-dir .cache/uv run --no-sync python scripts/export-contracts.py`、`python scripts/check-docs.py`、`ruff check src tests` 均退出0（后两者同样由 uv run --no-sync 执行），注册契约已重新导出，四Host模板一致性与十节结构通过。
- AC01/AC13通过。新增四变体的真实上游收费调用与更新后实际Host联调未验证；本次不发布成员ZIP、不替换旧ZIP、不修改C:\MCP运行副本或用户Host配置。重启开发副本可加载新功能，现有运行副本需按手册升级源码/包后重启。

## 2026-10-15：ZIP 自带项目顶层目录（AC12）

用户明确要求的新结构覆盖通用平铺ZIP默认，仅本项目适用；以下历史2026-10-14检查记录保留原当时的结构说明。

- 实际打包命令：`pwsh -NoProfile -File scripts/package-user.ps1 -DestinationDirectory .cache/folder-layout-audit-20261015`，退出0。21个文件条目全部且仅带 `zhenzhen-nanobanana-mcp/` 前缀，与添加同一前缀的白名单精确一致；点开头空值模板仍保留，真实.env不收录。
- 验证命令：`uv --cache-dir .cache/uv run --no-sync python scripts/verify-delivery.py .cache/folder-layout-audit-20261015/zhenzhen-nanobanana-mcp-0.1.0-user.zip`，退出0。解压前模拟MCP父目录内不存在项目文件夹，解压自动创建项目目录；直接找到pyproject.toml，没有第二层同名嵌套。
- 独立临时目录/空缓存联网 `uv sync --locked --no-dev` 通过，成员stdio协议2026-07-28与2025-11-25均通过；升级重新解压到父目录后原.env字节及NTFS ACL保持一致。没有收费业务请求。
- 旧包拒绝覆盖及SHA-256保留通过；运行白名单保护测试、文档一致性检查、修改脚本lint均通过。结果详见 `.cache/verification/delivery.json`。默认output中的旧包未替换，额外包仅用于临时验收。
- AC12通过。安装说明已改为把新包解压到C:\MCP，顶层文件夹自动形成；通用docs指南未修改。

日期：2026-10-14（Asia/Shanghai）。工作目录为本项目；Python 3.12.14，uv 0.12.9，FastMCP 4.1.0，底层 MCP SDK 2.3.0，stdio。本记录不包含真实凭据。

## 已通过

| 检查 | 命令/证据 | 结果 |
|---|---|---|
| 锁定环境 | `uv --cache-dir .cache/uv sync --locked`；`uv --cache-dir .cache/uv lock --check` | 退出0，独立 .venv；本机默认 C:\uv\cache 拒绝访问，改用项目专用缓存，未删除开发环境 |
| 行为测试 | `uv run --no-sync python -m unittest discover -s tests` | 29 项测试通过；含12项凭据加载测试以及3模型×3格式×2操作的18个映射场景 |
| 风格检查 | `uv run --no-sync ruff check src tests scripts`；`ruff format --check src tests scripts` | 退出0 |
| 注册契约 | `uv run --no-sync python scripts/export-contracts.py` | 4 Tools、1 Prompt、1 Resource，schema 与实现同时生成 |
| 协议子进程 | `pwsh -NoProfile -File '.\scripts\smoke-test.ps1'` | 退出0；auto=2026-07-28、legacy=2025-11-25；从含诱导.env的不同cwd启动，使用隔离项目假配置，不读取成员密钥；空文件密钥启动退出2、阻止环境回退、stdout为空；业务联网0 |
| 文档与模板 | `uv run --no-sync python scripts/check-docs.py` | JSON/TOML/惰性YAML通过，4模板与MANUAL一致，十节齐全，DSH插件局部schema通过 |
| 构建/临时打包 | `pwsh -NoProfile -File scripts/package-user.ps1 -DestinationDirectory .cache/env-policy-audit` | 退出0；wheel/sdist通过，21个ZIP条目精确白名单，新增空密钥.env.example、无真实.env/副本；未生成默认output成员发行包 |
| 白名单拒绝 | `tests/test_delivery.py` | 7类非法列表及真实Windows目录联接拒绝；空.env.example允许、填入测试值的示例拒绝，不泄露值 |
| 旧包保护 | `scripts/verify-delivery.py` 内实际再次调用打包入口 | 非0拒绝Release already exists；原ZIP SHA-256不变，元数据源版本与已安装版本一致 |
| 隔离交付 | `uv run --no-sync python scripts/verify-delivery.py .cache/env-policy-audit/zhenzhen-nanobanana-mcp-0.1.0-user.zip` | 独立临时目录、空缓存锁定安装退出0；两种协议通过；成员默认src根目录.env覆盖不同进程值，从无关cwd加载；升级重复解压保留.env原字节和NTFS SDDL；清理临时安装、保留开发环境 |
| 凭据规则 | `tests/test_config.py` | 文件优先、缺失逐级回退、空/非法/重复/语法/UTF8/读取权限失败不回退、字面变量不展开、错误脱敏、不同cwd、Windows HKCU只读适配器测试通过；实际当前用户随机不存在字段读取通过，无注册表写入；非Windows分支以mock platform验证 |

## 验收关联

| 标识 | 状态 | 证据与边界 |
|---|---|---|
| AC01 | 通过 | schema枚举、模型/格式发现、未知模型/非法比例拒绝测试 |
| AC02 | 通过 | 免费六项详情计划、已提供事实/未知尺寸提示；输出视觉效果尚未验证 |
| AC03 | 受控映射通过；上游未验证 | 18条映射、multipart image/image[]、aspect_ratio，Chat/Gemini结构测试；未测试真实提供商 |
| AC04 | 通过（受控图片） | 实际PNG保存、绝对路径、SHA-256、清单、成功/部分失败/失败状态 |
| AC05 | 通过 | 持久账本跨服务实例复用、参数冲突、重复并发claim、取消后不重发；路径相同内容变更复用原快照 |
| AC06 | 通过（受控边界） | 目录越界、真实Windows Junction逃逸、无效图片、非公网/多播DNS、恶意重定向、固定IP/SNI/Host/下载无认证、响应字节/base64长度/像素限制及schema验证；真实公网TLS/CDN场景未验证 |
| AC07 | 通过（受控上游） | HTTP失败/显式业务错误/空图片/base64无效、超时无重试、取消保留已完成图片；partial结果MCP isError且schema有效 |
| AC08 | 通过 | 真实stdio两种协议；不是端口/进程启动检查 |
| AC09 | 静态通过；实际Host未验证 | 四模板、九种Shell示例、CLI帮助/DSH插件schema；既有DSH profile整体错误单列，未修改 |
| AC10 | 通过（当前临时交付） | 21条白名单精确ZIP、隔离空缓存安装与协议；默认只提供开发项目与打包能力 |
| AC11 | 通过（隔离测试） | 严格.env优先/错误不回退、无cwd搜索、日志不包含测试值；空模板打包、非空拒绝；升级配置字节和实际NTFS ACL均保留，不操作成员真实文件/全局环境 |

## 未验证与不适用

- 无真实密钥/收费请求：没有验证模型权限、真实响应、费用、失败不扣费、视觉质量/商品一致性/中文字效果。三个模型/三种格式能力来自用户声明，实际映射兼容性待上游联调。
- 编辑示例 files 为空；标准 image/image[] 和编辑 response_format 参数的真实接受情况尚待验证。
- Cherry Studio、Codex、Claude Code、DSH GUI运行与业务联调，以及Bash/Zsh实际注册均未验证；没有修改用户Host配置。
- 当前无Git仓库、spec-kit安装或任务数据库；分支/PR不适用。Remote HTTP/Origin/OAuth/网关/Node/离线分发不适用。
- sdist显式包含开发源码/规范/测试等资料，成员ZIP单独白名单；构建缓存已迁移至用户LocalAppData的项目专用目录，源码内缓存警告已消除。此前构建也已检查tar条目不包含.cache/.venv/input/outputs。

## 打包 Shell 与工作目录修正（2026-10-14）

用户报告的 Git Bash 语法错误来自 PowerShell if 被 Bash 解析，首次 ZIP 已生成；PowerShell 7.6.7 的脚本参数错误来自从用户主目录用相对路径，脚本尚未启动。MANUAL 第6节现分别给出先进入项目目录的 PowerShell/Git Bash/Zsh 代码块及 PowerShell 任意 cwd 绝对路径调用；Zsh 未实测，不宣称通过。

实际使用本机 `E:\Program Files\Git\bin\bash.exe`（非 WSL bash）和 PowerShell 7 验证，证据 `.cache/packaging-shell-results.json`：

- Git Bash 从项目根目录调用实际脚本，退出0；PowerShell 从独立临时无关 cwd 通过脚本绝对路径调用，退出0。
- 两份临时 ZIP 的21个条目均精确对应 user-files.json；无 `cache directory` 或 Bash 语法警告。
- 重复 Git Bash 调用返回非0、`Release already exists`，在构建前拒绝；用户已有默认 output ZIP 的 SHA-256 未变。
- 构建缓存改为 `%LOCALAPPDATA%\zhenzhen-nanobanana-mcp\uv-build-cache`；不删除或迁移已有开发缓存，不修改用户凭据、Host配置、旧ZIP或开发环境。文档静态检查退出0。

上述差异保持可见，不通过降低需求或改写规范宣称完成真实业务验证。
