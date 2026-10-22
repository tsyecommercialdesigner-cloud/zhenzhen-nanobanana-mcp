# v0.3.0 D盘安装升级验收（2026-10-22）

## 目标与授权

用户授权更新现用D盘安装，不新增收费调用、不修改现用Host配置或已有Release。将 `D:\MCP\zhenzhen-nanobanana-mcp` 从正式v0.2.2 / `d831573e659bc2a8bf45689d6c1a0b9ce585e5cd` 更新到正式v0.3.0 / `c6121a7f142558aa53bc622505b4f1d1e17fcca2`。发布资格由正式Release附件及成功main CI核对；不把后续文档归档提交当成安装版本。

升级前源码工作区干净，任务账本为4项成功、1项原有失败，无queued/preparing/running/recovering；另有10历史批次和35个非账本输出文件。仅停止指向该目录的MCP uv/python子进程，没有关闭Host或修改其配置。源目录ACL不变。

## 备份与安装

升级前v0.2.2备份保留在本机私有备份目录；完整路径只留本地验收证据，不进入公共文档。

包含原源码/.git、.env及其ACL、任务/批次账本和历史输出，不复制可重建的.venv/缓存。仅新备份目录采用私有权限，原.env字节与ACL分别校验一致；备份两个账本integrity_check=ok，业务摘要及35个输出文件哈希与原安装一致。验证备份后才fetch标签并以 `git switch --detach --no-overwrite-ignore refs/tags/v0.3.0` 更新，未清空安装或覆盖私有数据。

执行 `uv --directory D:\MCP\zhenzhen-nanobanana-mcp sync --locked --no-dev`，只将本项目包从0.2.2更新到0.3.0；运行版本/发行元数据均为0.3.0，Python3.12.14、FastMCP4.1.0、MCP SDK2.3.0。已发布smoke脚本退出0，双协议发现21 Tools、9 Resources、6 Prompts。

## 现用数据与追加免费协议验收

另从无关cwd，以日常uv/--no-sync入口启动新stdio子进程；读取实际D盘项目根.env，cwd中的空.env不影响定位。子进程仅允许回环连接，外部连接/DNS均拦截并计数，不触发绘图工具。两种协议均核对工具输入/输出schema与发布契约完全一致，免费查询和只读等待通过。

| 项目 | 结果 |
|---|---|
| .env与ACL | 升级前后字节SHA256、NTFS SDDL一致 |
| 已核对Host配置 | Codex配置及存在的DSH web/desktop/multica patch指纹一致，没有改写配置 |
| tasks.sqlite3 | 5项，4成功/1原有失败；失败正确保留isError，不重试 |
| batches.sqlite3 | 10批次，免费查询全部成功 |
| 数据迁移 | 新版可添加内部列；按升级前原有业务列比较完整记录摘要，均一致，integrity_check=ok；不把动态owner/heartbeat视为不可变化的业务数据 |
| 输出与图片 | 全部35个非账本输出文件路径/大小/哈希一致；15张唯一结果图片均在现用D盘outputs，哈希、尺寸与Pillow解析通过 |
| 等待 | 对已成功任务调用wait_image_tasks立即返回成功，wait_timed_out=false，不生成新任务 |
| 网络及收费 | 外部联网尝试0，收费调用0；没有调用submit/generate/retry或设计收费提交 |

追加验收后的再次快照确认所有原业务记录、文件和配置保持一致。所有已有Release的正文/资产摘要未变化；未运行Release或修改其内容。首次本地验收探针误按批次顶层images取值后中止，已按既有BatchResult.items[].images契约修正；失败日志保留，不改服务器或业务数据，后续双协议完整检查通过。

## 当前会话与保留范围

升级阶段只证明D盘安装及新stdio进程已是v0.3.0，不等于当时Codex会话已刷新工具缓存。旧MCP连接因升级停止，当时重启后的当前会话发现/调用尚未验证；后续当前Codex会话已发现21工具、免费查询及单张/3项并发/编辑/10项收费验收完成，详见[当前会话验收](LIVE-V0.3.0-ACCEPTANCE.md)。用户报告DSH重启后连接恢复单独注明来源，不扩展为Desktop GUI实测。原最小profile未通过与独立CLI看图通过的历史边界不变。

升级证据保留在本机私有验收目录：停止进程清单、备份验证、升级日志、前/后及查询后快照、schema/历史图片/网络拦截协议记录与final-verification.json。备份、此前独立发布验收及DSH原始看图证据全部保留，未经后续授权不删除。此次仅将脱敏报告与任务状态通过dev/PR归档，不提交私有配置、原始账本、日志或图片，不修改现用D盘安装。
