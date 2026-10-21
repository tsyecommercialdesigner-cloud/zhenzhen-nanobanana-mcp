# v0.2.2 D盘升级与重启后Codex会话验收

2026-10-21，用户先授权归档正式发布验收，再更新D盘现用安装；随后重启Codex并授权当前会话免费查询历史任务/批次。现授权归档本次升级及会话验收，经dev→PR→Windows CI与审查→合并，并复验实际main合入提交CI后，删除本次升级备份。不新增收费调用，不运行Release流程，不修改已有发行版本。

## 版本与前置归档

- [v0.2.2正式发布安装验收](RELEASE-0.2.2-ACCEPTANCE.md)已由[PR #16](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/pull/16)归档，main合入SHA为`698921e1e355a7fd7db7ab69381b689a0b9c96fe`；[main CI39579530071](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39579530071)11阶段及81项测试通过。
- 现用目录`D:\MCP\zhenzhen-nanobanana-mcp`从v0.2.1/09501092c369e2a314df757eece5fa8d7a38e64e更新到正式v0.2.2/d831573e659bc2a8bf45689d6c1a0b9ce585e5cd。运行安装固定已公开标签，不把后续文档归档提交回写到发行标签。
- 更新前确认5项任务均已终态，无queued/preparing/running；停止指向该目录的MCP uv/python子进程，未关闭Host应用或修改其配置。

## 升级、备份及数据保留

备份位于`D:\MCP-backups\zhenzhen-nanobanana-mcp\v021-before-v022-20261021-698921e1`，包含原源码/.git、.env及原ACL、outputs账本和历史图片；不复制.venv或缓存。首次复制NTFS安全信息因权限不足而在checkout前停止；改用数据复制并单独保留备份.env原ACL，验证备份后才切换版本，没有调整系统级或源安装ACL。

按正式Release资格记录核对目标SHA，fetch v0.2.2后以`git switch --detach --no-overwrite-ignore refs/tags/v0.2.2`切换，执行`uv --directory D:\MCP\zhenzhen-nanobanana-mcp sync --locked --no-dev`及已发布smoke脚本，均退出0。模块及发行元数据均0.2.2；Python3.12.14、FastMCP4.1.0、MCP SDK2.3.0保持锁定。

| 对象 | 升级后验证 |
|---|---|
| .env | 字节哈希与NTFS ACL均与升级前一致，未将真实值写入证据或Git |
| tasks.sqlite3 | 5任务（4成功、1原有失败），完整业务记录逻辑摘要不变，integrity_check=ok |
| batches.sqlite3 | 10历史批次，完整记录逻辑摘要不变，integrity_check=ok |
| outputs | 35个非账本输出文件，逐项路径、大小和SHA256保持 |
| 历史图片 | 通过结果引用核对15张唯一图片，均位于现用D盘outputs且文件/哈希可读 |

新启动的日常uv --directory/--no-sync stdio连接在2026-07-28与2025-11-25兼容模式均发现8 Tools、1 Prompt、1 Resource，工具输入/输出schema与发布契约一致。免费查询全部历史任务/批次，并使用只读wait_image_tasks取得原终态。该追加协议过程启用外部联网拦截，业务联网尝试0、有效绘图提交0、收费调用0。

## 重启后的当前Codex会话

更新停止旧服务后，重启前当前会话的旧transport返回Transport closed；这一结果没有被新进程的协议成功掩盖。用户明确告知已重启后，再通过当前会话实际提供的MCP工具调用验证：

| 实际发现工具 | 当前会话覆盖 |
|---|---|
| list_models | 免费调用成功，output_dir指向现用D盘outputs，sync_generation=true，最长等待1200秒，默认模型gemini-nano-banana-2.1 |
| generate_images | 成功发现；未调用，避免新增收费请求 |
| wait_image_tasks | 对一个已成功任务只读等待成功，wait_timed_out=false、status=succeeded |
| submit_image_tasks | 成功发现，未调用 |
| get_image_tasks | 实际查询5历史任务，4成功和1原有失败；失败保留isError=true，没有重试 |
| get_batch_result | 实际查询10历史批次，均为succeeded |
| cancel_image_tasks | 成功发现，未调用 |
| plan_ecommerce_images | 成功发现，本次会话未调用 |

当前会话返回的15张唯一图片逐一验证绝对路径在现用D盘outputs下、文件存在、SHA256及图像尺寸匹配，并用Pillow检查图像可解析。再次核对全部35个输出文件及两个账本的业务记录摘要，均与升级前一致。安装元数据/模块版本为0.2.2、HEAD为正式标签完整SHA，结合当前会话的8工具发现及sync_generation确认新版已生效。

同步生成的实际等待/编辑/超时/防重仍以[正式发布隔离验收](RELEASE-0.2.2-ACCEPTANCE.md)的受控替身证据为准，本次真实会话没有调用generate_images，不声称新增收费绘图或真实Host长等待业务已验收。此次也没有新增DSH GUI验收或全部模型/格式/变体实测。

## 证据归档与备份清理边界

升级原始证据保留在`D:\MCP-v022-upgrade-20261021-698921e1`，包括backup-verification.json、runtime-before/after快照、data-preservation.json、runtime-protocol-verification.json、final-verification.json及辅助脚本/日志。当前会话证据为工作区忽略目录`.cache/v022-current-session-verification.json`，另留副本在上述证据目录。秘密、私有数据库、图片和原始日志不进入Git。

本次归档的PR、受审SHA、Windows CI与main合入SHA/CI及最终删除结果记录在对应PR；不在提交前预填未来成功。只有main合入提交CI通过且再次确认现用安装、配置和历史数据正常，才删除上述唯一升级备份目录。删除前核对绝对路径、非reparse point及其与现用安装的隔离；不删除现用D盘安装、任务数据、独立发布验收目录或升级证据目录，也不以本次授权清理其它文件。已有v0.2.0/v0.2.1/v0.2.2的标签、说明和附件不变，不运行Release工作流。
