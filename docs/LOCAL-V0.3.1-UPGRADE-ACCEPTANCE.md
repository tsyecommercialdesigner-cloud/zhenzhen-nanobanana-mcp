# v0.3.1 D盘升级与重启后Codex验收（2026-10-22）

## 版本与证据范围

按用户授权，将 `D:\MCP\zhenzhen-nanobanana-mcp` 从正式v0.3.0/c6121a7升级到正式v0.3.1/4ebc4872d164173246f008c2d0e912589c2a8ca8。发布准备经[PR #27](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/pull/27)合并，[main CI39734779191](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39734779191)通过170测试及11阶段；受控CD39735290473正常审批后建草稿，核对附件后[v0.3.1](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/releases/tag/v0.3.1)于2026-10-22T06:46:24Z公开，独立安装与双模式协议验收完成。

本报告归档已完成的升级及用户重启后当前Codex原生MCP调用结果。本轮整理不重新运行收费业务；发布版本、D盘安装提交及后续文档归档提交分别记录，不将文档提交当作现用安装版本。

## 升级及完整备份

升级前确认无queued/preparing/running/recovering任务，仅停止目标安装的uv/python进程树。完整旧版备份包含源码/.git、.venv、.env及ACL、任务账本和输出，共6175文件、150041599字节；逐文件大小和SHA256核对通过。v0.3.0升级前备份、此前v0.2.2备份均保留，私有路径不进入公共仓库。

核对正式标签与发布资格后，使用保留忽略文件的固定标签checkout及 `uv sync --locked --no-dev` 更新；仅本项目包0.3.0→0.3.1，依赖版本未升级。运行Python3.12.14、FastMCP4.1.0、MCP SDK2.3.0。原.env字节/ACL、安装根ACL、业务记录和输出保留；没有改写Host配置。

## 两个阶段的实际验证

| 项目 | 升级阶段独立stdio子进程 | 用户重启后当前Codex会话 |
|---|---|---|
| 发现 | auto/legacy双模式21工具、9资源、6提示；工具输入/输出schema与发布契约一致 | 原生工具集合21项，与契约一致，包含generate_images、wait_image_tasks |
| 调用来源 | 无关cwd、日常uv --no-sync入口，读取实际项目根.env | 当前Codex原生list_models、get_image_tasks、get_batch_result调用 |
| 配置能力 | 新进程v0.3.1确认 | configured=true、sync_generation=true；默认gemini-nano-banana-2.1，批量20、并发5 |
| 历史任务 | 20项，19成功、1原有失败 | 8组身份查询覆盖同20项；原失败正确保留isError，不重试 |
| 历史批次 | 10批次 | 10批次成功，reused=true，manifest可读 |
| 图片及输出 | 30张唯一图片与66个非SQLite输出核对 | 图片路径、存在性、字节数、SHA256、尺寸、Pillow解码及升级前指纹全部一致；66输出不变 |
| 数据及防新增 | 任务/批次业务记录及post_attempts不变 | 同样不变，无新增绘图请求；不是再次执行收费重放测试 |
| 同步能力边界 | 对已成功任务只读wait立即成功；外部连接尝试0 | 同步工具发现通过，未实际调用generate_images收费出图 |

升级阶段曾因停止旧进程而使当时Codex旧连接Transport closed，该阶段不能证明当前Host已刷新；原始记录保留。用户重启后原生发现和免费查询才补齐当前会话验证，不能覆盖或改写早期失败记录。隔离子进程的网络拦截仅用于测试，未修改Host配置。

## 配置摘要变化与保留

升级阶段已核对Host配置摘要一致。用户重启后发现Codex的config.toml摘要与升级前不同，记录的修改时间为北京时间2026-10-22 14:55:50.858610，变化来源未确认；本Agent未写入该文件，保留现状，没有回滚。只读核对当前MCP入口仍指向D盘并使用--no-sync，实际连接和查询通过。

因此不能表述为“所有Host配置字节不变”。原363个受保护文件中362个摘要不变，唯一已观察差异为上述配置；.env、安装ACL及已核对DSH配置不变。配置原文、私有路径、前后摘要留在私有证据，不提交公共仓库。

## 原始证据、边界与归档

升级前/安装后/查询后快照、完整备份清单和校验、停止进程记录、协议日志、网络拦截记录、当前会话原生工具返回、30图校验表、配置变化记录及最终verification.json均留在本机私有验收目录。重启后再次核对6175个备份文件完整，5个已有Release元数据和附件摘要未变。以前收费验收、独立发布安装和DSH实际看图原件保留。

此次升级、重启验证及文档归档均未新增收费调用；未修改Host配置或已有Release，未删除旧版备份、原始证据、私有资料或D盘任务数据。本报告不补齐真实故障恢复、供应商账单、全部模型出图、DSH Desktop GUI或原最小profile失败等历史未验证项。归档按dev→PR→Windows CI→审查合并执行；实际PR与合入SHA CI结果留在对应PR，本文不预写未来检查成功。
