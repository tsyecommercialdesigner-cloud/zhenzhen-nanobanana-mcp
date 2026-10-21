# 2026-10-21 本机 D 盘迁移与当前 Codex 会话验收

用户分阶段授权：安装发布版本并迁移本机服务，保留凭据、任务数据和旧目录备份；重启 Codex 后通过当前会话查询历史批次；最后追加一次真实收费生成，确认成功后归档、提交推送并清理旧目录和本次迁移备份。本文记录实际结果，不修改已发布版本、标签或附件。

## 安装、配置与数据迁移

- 从 GitHub 发布标签 v0.2.1 安装，HEAD 为 `09501092c369e2a314df757eece5fa8d7a38e64e`，使用正式安装器的默认路径 `D:\MCP\zhenzhen-nanobanana-mcp`，独立 `.venv`、锁定无开发依赖安装及双协议 smoke 通过。
- 旧安装为 `C:\MCP\zhenzhen-nanobanana-mcp`，版本 0.1.0、非 Git 目录。迁移前停止旧服务并建立完整目录快照，迁移 `input`、`outputs` 与 `.env`。旧安装没有 `tasks.sqlite3`，历史数据位于 `batches.sqlite3`；不把独立收费验收目录中的任务冒充本机历史任务。
- 原 `.env` 仅将密钥字段名改为 `ZHENZHEN_NANOBANANA_API_KEY`，值和其他内容保持，未输出密钥。新文件保留原访问规则，所有者为当前用户；未声称恢复原 Administrators 组所有者，也未修改磁盘根目录权限。
- 10 个历史批次全部成功，包含 11 张图片。原目录及完整快照的 33 个关键文件与迁移前清单逐个 SHA256 一致；新账本保留原 request_id 和防重指纹，数据库完整性检查通过。新副本数据库及结果清单中的 42 处图片/清单路径映射到 D 盘；原目录和快照未改写。
- Codex 用户配置仅修改本服务 stdio 条目及原生成工具策略对应项；日常入口为 `uv --directory D:\MCP\zhenzhen-nanobanana-mcp run --no-sync python -m zhenzhen_nanobanana_mcp`。其他服务配置解析值保持不变。

## 当前 Codex 会话的免费验收

迁移时先使用桌面附带的实际 Codex app-server 在隔离配置目录验收。用户随后重启 Codex；当前会话已发现全部 6 个公开工具，并实际调用 `list_models`，返回密钥已配置、默认模型 `gemini-nano-banana-2.1`、异步任务启用、输出目录位于 D 盘。进程路径也已切换至 D 盘 `.venv`。

通过当前会话调用 `get_batch_result` 查询下列全部旧编号，均返回 `succeeded`，不重新提交上游：

| request_id | 图片数 | outputs 下的结果目录 |
|---|---|---|
| ecom-main-green-20261019-01 | 1 | 81e3f6e6874d45aea85413ef65527fb2 |
| ecom-main-green-v2-20261019 | 2 | 604d3f5a7c05461fbc56b0f74568e2da |
| garbage-bag-main-01 | 1 | d07d6899e1e14211a5aa1b9661b87437 |
| krusty-krab-poster-gemini-20260611-01 | 1 | 8062eaf97b284e648f7fa9be567f6a10 |
| live-trial-20261014-191717 | 1 | af794b21b33f4dc782f2ee33dc9742e8 |
| mr-krabs-counting-coins-chat-20260611-01 | 1 | 03678fd7588e4faaafb322161c19dba9 |
| patrick-beach-20261015-091157 | 1 | ef6dbc211eb24c818e0f975652f0bd78 |
| spongebob-beach-sun-1014 | 1 | f20a1542800a4c19afa19f5a4041dad2 |
| spongebob-patrick-dinner-20260611-01 | 1 | 2f85f2910be343e9afddc0facdc6f12e |
| spongebob-patrick-sunset-20261015-092940 | 1 | 40a0afadaa83445ca5cbb408608d6a17 |

逐项验证 10 份 `manifest.json` 可读取且 request_id 匹配；11 张图片的绝对路径均在新 `outputs` 内，读取、解码、像素尺寸、文件大小、SHA256 全部通过，与旧目录及备份图片一致。此前免费历史核对未触发收费；本轮清理前再次通过当前 MCP 查询全部批次成功。

## 当前会话的一次真实收费生成

免费规划后仅调用一次 `submit_image_tasks`，一个任务；后续只调用 `get_image_tasks`，未重放提交、改编号重试或追加批量/编辑。

| 项目 | 结果 |
|---|---|
| 内容 | 虚构验收示意：单只无品牌白色陶瓷马克杯，白背景、柔和棚拍光、无文字/商标/水印 |
| checkpointer | d-drive-migration-acceptance-20261021 |
| thread_id | current-codex-session-20261021 |
| task_id | white-mug-main-001 |
| 实际模型 / 格式 / 端点 | gemini-nano-banana-2.1 / dalle / generations |
| 参数 | 1:1，无参考图，未指定 resolution，未触发高分辨率模型路由 |
| 生命周期 | 初次约 0.3 秒返回 queued、reused=false；查询观察到 running，再到 succeeded；账本时间差约 25.39 秒 |
| 文件 | `D:\MCP\zhenzhen-nanobanana-mcp\outputs\1e0a1ced960944a0a7a13e3e70a1ec28\01.png` |
| 图片 | PNG，2048×2048，4,095,158 字节，读取/解码/尺寸/哈希校验通过 |
| SHA256 | fada6840fc105f8633a26628ebcf59234d823c2755cc106daffe992c6bf20cba |

视觉检查为单只白色杯子，杯体/把手完整，白背景和自然阴影，无可见品牌或文字。该图仅为虚构商品示意，不证明真实商品材质或性能；基础模型实际输出 2048 像素不等于请求使用了 2k 变体。

本轮仅证明当前 Codex→D 盘安装→真实供应商→图片保存/查询链路成功。没有独立 HTTP 观察器或供应商账单核对，不能由一次工具提交推导具体扣费金额或声称验证全部网络请求次数；也未新增防重重放、真实故障恢复、其他模型或编辑实测。`list_models.upstream_verified` 是原版静态能力说明，不因本次单场景成功而改写源码。G06.5 的真实故障恢复继续保留未完成。

## 归档与清理边界

仅提交脱敏验收文档及任务/验证记录，不提交 `.env`、Codex 私有配置、图片、SQLite、完整备份或原始运行日志。版本仍为 0.2.1，不运行发布流程。

文档与任务先以 `b409894412ce56b5908b51fbfa7647d8b0caadb8` 提交推送至 dev；该提交的 [Windows CI39544644902](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39544644902) 成功。之后按用户授权删除 `C:\MCP\zhenzhen-nanobanana-mcp` 和 `D:\MCP-backups\zhenzhen-nanobanana-mcp\20261021-a3dba663`。清理前核对原文件及 D 盘迁移结果，精确解析路径且确认两个目录及其子项均无目录联接/符号链接；未发现 C 盘旧安装进程。

首次删除因旧虚拟环境中 Administrators 所有的目录拒绝访问而停止；仅对旧安装根目录添加当前用户可继承的完全控制规则，子项权限仍不足，随后通过 Windows UAC 提权运行精确路径清理脚本完成删除。没有修改磁盘根目录或现用安装的权限。两个目标目录已确认不存在；本次备份中的旧凭据副本、旧 Codex 配置及完整旧环境随之删除，不能再引用为可回滚备份。其他安装、独立验收目录、父目录及开发仓库均不在删除范围。

删除后再次通过当前 MCP 查询全部 10 个历史批次和本轮新任务，均返回 succeeded；11 张历史图片及新图的读取、解码与 SHA256 复核通过，`batches.sqlite3`、`tasks.sqlite3` 完整性检查均为 ok，现用 D 盘 `.env` 仍存在。清理未引发新的收费提交。最终补记实际结果单独提交；仅创建 dev→main PR 供正常 CI/评审，不合并或发布。
