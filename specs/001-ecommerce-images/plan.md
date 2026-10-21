# 技术方案

## 指定约束与原则检查

- 使用用户指定 `fastmcp`，而非项目约定的默认官方 SDK `MCPServer` 服务类；FastMCP 的底层 MCP SDK 版本由 `uv.lock` 锁定并单独记录。该例外只适用于本项目。
- Python 精确锁定 3.12.14；hatchling + `src/zhenzhen_nanobanana_mcp/`；stdio 模块入口；不新增 Node 项目、不修改 Host 私有配置。
- 不安装或模拟 spec-kit 工具。采用 `spec.md`、`plan.md`、`tasks.md` 与契约文件维护本任务。
- 服务显式读取项目 `.env` 的 `ZHENZHEN_NANOBANANA_API_KEY`，文件优先，仅缺失时回退进程及 Windows 当前账号 HKCU Environment；启动缺失/空值/非法时失败，日志 stderr。python-dotenv 1.2.4 为直接运行依赖，使用 parse_stream 检查错误及重复，不调用环境导入/变量展开 API。启动与工具调用不安装依赖。
- 根目录来自已验证 `src/<module>/` 布局及 pyproject 标记，不搜索 cwd/父目录；不同安装布局允许明确非秘密绝对路径 `NANOBANANA_PROJECT_DIR`，无法判断布局时要求指定，不从 .venv 路径猜测。输入/输出默认目录与该项目根目录一致。

## 结构

`models.py`：输入/输出 schema 与模型枚举；`config.py`：环境配置；`media.py`：输入边界、HTTP(S) 固定解析 IP 下载、图片验证；`provider.py`：三种 API 格式及结果解析；`service.py`：SQLite 防重账本、批量执行及保存；`server.py`：工具/提示/资源注册；`smoke.py`：无收费协议检查。

## 调用与持久化

默认模型按2026-10-15用户要求切换为 `gemini-nano-banana-2.1`，同步 list_models、generate_images 参数默认值及注册契约。已有批次保存的模型不变；旧编号重交若省略模型导致参数变化，仍按现有规则报冲突，应查询结果或明确原模型，不自动重发。

计划工具只生成提示词和 `ImageSpec`。批量工具要求显式 `request_id`，1–12 项，参考图出现即编辑。收费前校验所有输入；SQLite 的唯一主键在事务中登记提交参数指纹（提示词、参考图地址/路径、模型/格式和服务地址）。输入图片内容摘要另存快照；重复编号返回原快照结果，不重新下载/读取已变更的参考图。逐项结果写数据库及独立图片文件；取消时终止本地未完成协程，清单标记 cancelled，但远端取消与退款不保证。进程崩溃留下 running，查询可返回现有结果而重交被拒绝。更换编号会产生新请求及费用。

单进程 semaphore 限制出图并发 2；每项含上游与下载整体 timeout；所有 POST 不重试。服务不后台轮询，批量工具等待完成并报告 progress；Host tool timeout 应设为 1800 秒。客户端超时/取消后通过结果工具读取现有状态。

## 分辨率路由（2026-10-15）

Resolution 严格正整数宽高用于逐项纯函数路由，七项模型枚举应用到所有工具 schema。批次 model 保留用户选择，ItemResult.actual_model 保存路由结果；历史缺失字段查询时补齐基础批次模型。未指定 resolution 的输入指纹省略 null，保持旧请求指纹兼容；显式尺寸进入指纹防止相同编号改变请求。Provider 三个适配器保持原请求字段，仅收到路由后的模型（Gemini 使用模型 URL 段）。模型变体直选无尺寸时保留，有尺寸时重新选档；不添加上游分辨率参数、推断提示词尺寸或改变比例。同步导出契约、发现/计划 smoke、边界/历史账本/42项适配器测试及使用文档；不调用收费上游验收。

## 媒体安全

按用户进一步要求，完全移除参考图目录白名单，覆盖此前T15方案。Settings.input_dirs及MediaLoader的roots参数仅兼容旧调用、不执行目录限制；不再读取NANOBANANA_INPUT_DIRS，旧值无论有效、为空或相对路径均忽略。发现固定readable_files/input_dirs=[]。本地普通文件经OS权限和图片校验；目录联接不按位置拦截。HTTP/HTTPS图片URL在80/443端口下载，DNS固定及每跳公网校验保留，下载不携带密钥、不使用环境代理；无需新增依赖。输出仍由服务器生成路径并防止越界/覆盖，不改变输出权限。Agent需取得服务机器可访问的实际绝对路径或图片直链。

## 验证与交付

2026-10-15 用户明确要求 ZIP 自带项目文件夹：本项目采用单一 `zhenzhen-nanobanana-mcp/` 顶层目录，解压至 `C:\MCP` 自动创建项目安装目录。此选择覆盖通用指南“ZIP根部即安装内容”的默认，只适用于本项目，不修改通用规范。白名单仍按项目内相对路径维护，归档与校验统一添加该前缀；隔离安装将包解压至模拟MCP父目录，验证无额外嵌套、旧.env及ACL保留。

Windows 打包脚本按自身路径定位项目，构建缓存固定在用户 LocalAppData 项目专用目录（源码树外）；元数据、ZIP存在检查与白名单检查先于构建。手册分别区分 PowerShell/Git Bash/Zsh 语法及启动时工作目录；无关 cwd 使用脚本绝对路径，现有包拒绝覆盖。

unittest + httpx.MockTransport 覆盖成功、映射、超时、业务失败、防重、取消和边界；FastMCP Client 连接真实服务子进程验证协议、schema 与 `isError`。从注册信息导出准确 schema 用于契约和手册。四个 Host 模板使用已查证语法；无需认证的 smoke 不模拟真实联网业务。`package-user.ps1` 按明确白名单 ZIP，隔离目录/专用空缓存安装后 smoke。验证结果归档于 `verification.md`，任务清单只在验证后勾选。
