# v0.3.0 当前 Codex 会话真实绘图验收（2026-10-22）

本记录归档用户分三轮授权的单张主图、3张详情图及1次编辑、10项详情图验收。实际安装为正式 v0.3.0 / `c6121a7f142558aa53bc622505b4f1d1e17fcca2`，使用当前 Codex 会话的 MCP 工具，输出根目录为默认 `D:\MCP\zhenzhen-nanobanana-mcp\outputs`。测试商品是虚构、无品牌的白色马克杯，不宣称实际商品规格、认证或性能。

本次文档归档只读取已有证据与文件，没有新增收费请求、修改 Host 配置或 D 盘安装，也没有发布或修改 Release。原图、私有账本、完整提示词/工具响应、图片来源检查点和日志留在本机私有验收目录，不入库；本文只提供核对所需的测试身份、结果摘要、相对路径和 SHA256。

## 1. 身份、提交与查询

三轮共用 `checkpointer=codex-v030-paid-acceptance`；这是 SQLite 字符串命名空间，不是目录、认证凭据或供应商作业 ID。每个任务按 `(checkpointer, thread_id, task_id)` 唯一标识，`detail-001` 等编号在不同 thread 内互不混用。

| 标识 | thread_id | task_id | 模型 / 端点 | 提交返回 | 创建至完成 | 并发观察 |
| --- | --- | --- | --- | --- | --- | --- |
| S：单张主图 | `20261022-single-mug-01` | `main-mug-001` | gemini-nano-banana-2.1 / Generations | 92 ms | 28.798 s | 单项 |
| B：3张详情 | `20261022-batch3-edit-01` | `detail-001`、`detail-002`、`detail-003` | gemini-nano-banana-2.1 / Generations | 63 ms | 26.345 s | 3项 running |
| E：原图编辑 | `20261022-batch3-edit-01` | `edit-mug-001` | nano-banana-pro / Edits | 67 ms | 55.635 s | 单项 |
| T：10项详情 | `20261022-ten-details-01` | `detail-001` 至 `detail-010` | gemini-nano-banana-2.1 / Generations | 93 ms | 73.122 s | 峰值5项 running |

所有请求均使用 DALL·E 格式、1:1 比例和基础模型，没有显式像素路由或2k/4k变体。每轮调用 `submit_image_tasks` 后立即返回 `queued`，不等待出图；后续 `get_image_tasks` 查询观察到 `running`，最终15项均 `succeeded`、`file_integrity=verified`。耗时来自客户端提交计时与账本创建/完成时间，不是供应商性能基准。

3项批次一次登记并观察到3项同时 running；10项批次首次查询为5项 running、5项 queued，之后7项成功、3项 running，最终全部成功。两轮另以100 ms间隔只读 SQLite 采样，峰值分别为3和5，且并行 running 项的 `post_attempts` 各为1。此处证明本地队列并发状态，没有抓包或供应商内部调度遥测，不能扩展成全局长期并发上限的业务压测结论。

编辑以 S 的原主图绝对路径作参考，显式提供其 SHA256，准备阶段核对一致；使用 `/v1/images/edits` 的重复 `image` 文件字段及 `aspect_ratio`。结果保留白色马克杯外形并改为暖米色背景与浅木桌面，原图哈希不变。传输格式由对应版本源码契约核对，不将本次证据描述为完整 HTTP 抓包。

## 2. 自动落盘与图片校验

下表路径相对于安装根目录；文件只存在于本机输出目录，不随文档提交。15张均为1024×1024，每项恰好一张。收费执行后和原身份重放后分别核对文件存在、字节数、SHA256与Pillow解码/尺寸，均通过。S/B/E已逐张查看，T检查十图索引；未将特定平台审核、严格同SKU、所有细节视角或绘图质量认证为通过。

| 标识 | task_id | 格式 | 尺寸 | 字节 | 安装根相对路径 | SHA256 |
| --- | --- | --- | --- | --- | --- | --- |
| S | `main-mug-001` | PNG | 1024×1024 | 1056859 | `outputs/51df63d9dbc558e3a7e5696a0466da9c/01.png` | `1b429bc50a1f8e6f2acee9ebd1c879b802e0ac8f0da6a451c775541af8759372` |
| B | `detail-001` | PNG | 1024×1024 | 1047644 | `outputs/e9a216013b305470b7fdfe0aabfcd3fa/01.png` | `13e6babce499d00c0170cec9a85656b97c9172490c862ed7fd1b37aeca921de9` |
| B | `detail-002` | PNG | 1024×1024 | 1114500 | `outputs/822dfe55f0a25cb0b3afe3a1dddba4d4/01.png` | `449b8336c1e55dbf0674a0fc5fcaf8b6b78a0dc3611340f2bccf5acaa364439b` |
| B | `detail-003` | PNG | 1024×1024 | 975882 | `outputs/bd1f902b58065115b9109ce09656f3c5/01.png` | `9221bcc5ea44c3d2841138a68a6789ccb5fbe8f1b5937b4d4881c651680c256c` |
| E | `edit-mug-001` | JPEG | 1024×1024 | 490120 | `outputs/f5f627badc1451faa3af4afe88033ad3/01.jpg` | `efb3f78b6a1f7d2f05edf54287d8468a0a2892b8aec349610c9a3b7b0b479aa1` |
| T | `detail-001` | PNG | 1024×1024 | 886091 | `outputs/8207349d554057c68474d49c8bfc0b48/01.png` | `7f1998839cd12d357dfd90df35877261b2f11a515f789267c145a09737d0e892` |
| T | `detail-002` | PNG | 1024×1024 | 1013889 | `outputs/882f066430cf55f38d856c4fae645499/01.png` | `fd1fbce96cb4852e8e8701eb2add46b319b11a67c105553b438d81686aa75852` |
| T | `detail-003` | PNG | 1024×1024 | 1056310 | `outputs/222a851358df5c74ad01d3d65d64b85f/01.png` | `3aa09731227bde2e56f2aad336da1314b5fea12c5d19bbb7281e88749a544b8d` |
| T | `detail-004` | PNG | 1024×1024 | 981771 | `outputs/62ea7e36311554088844340211414206/01.png` | `62ec358da0049e935c2336431b249e89c8a74c5e86a48a278efcc3314ab3696e` |
| T | `detail-005` | PNG | 1024×1024 | 944927 | `outputs/da46057f379d5b699cbf70e038a4c978/01.png` | `cd5f9fd45a1e63555c2a2d908d08898644b09544ce79765192b84d6ae406cdb4` |
| T | `detail-006` | PNG | 1024×1024 | 984499 | `outputs/865448c168b2578697414c094cac569e/01.png` | `3d833b934428d7d45a997258130e1d2c6cb5ecd9f9f912e0d9d0ea980a145efd` |
| T | `detail-007` | PNG | 1024×1024 | 959758 | `outputs/444e7062888a5c23a2d87fed388ae6a5/01.png` | `6c1f3a45c293fe7955a7cabc9e8d1cdef337bd5c857787e099b1ef453004e388` |
| T | `detail-008` | PNG | 1024×1024 | 1065532 | `outputs/71264bc1d673518099e8fca12ad9c265/01.png` | `7fc5d21174ff189f550326563de84e554db06ea243784dd4c13fe0bff8598e09` |
| T | `detail-009` | PNG | 1024×1024 | 1111552 | `outputs/e3b9f65bd024535ab76ceff08ca4a14e/01.png` | `fdd50f72c26c263f588ca88d3bfeee9710a0374c299e149df07dec6eb75c24bc` |
| T | `detail-010` | PNG | 1024×1024 | 869553 | `outputs/725f8064386352a690d55d6bfce63ee1/01.png` | `f623e0137ac45d37f4d33273b5da35d6857f68cf055c01a6cfc7a8cd00629821` |

## 3. 同身份重放与费用边界

| 轮次 | 新任务数 | 重放前后 POST 计数 | 重放结果 |
| --- | --- | --- | --- |
| S | 1 | 1 → 1 | 原身份/完整参数重放，reused=true |
| B | 3 | 3 → 3 | 整批原样重放，3项均reused=true |
| E | 1 | 1 → 1 | 原身份/完整参数重放，reused=true |
| T | 10 | 10 → 10 | 整批原样重放，10项均reused=true |

各轮重放前后完整任务行、供应商幂等键、图片路径/字节/SHA256不变；每个新任务的 `post_attempts` 均为1。任务总数依次5→6→10→20（含5项原有历史任务），三轮合计仅新增15项及15次绘图POST尝试。此前历史任务完整记录保持一致。十项验收还复核此前28份私有验收文件及46个非账本输出文件摘要均未变。

POST计数是服务器在派发点持久化的尝试计数，本次说明重放没有新增本地上游绘图请求；未读取供应商账单或核对实际金额，也未独立验证供应商是否承诺 `Idempotency-Key` 去重或网络层 exactly-once。未知收费状态、故障注入及真实崩溃/重启恢复不在本轮范围，不换编号补画或自动重提。

### recovery_attempts 的解释纠正

实际 v0.3.0 的 `TaskQueue.checkpoint()` 在正常保存上游响应时也会进入 recovering 并递增 `recovery_attempts`。因此本轮各项值为1，不能据此声称发生过一次下载故障、重试或崩溃恢复。此前本机单张和小批量记录的相关推断以本节纠正，原始文件不覆盖；出图、落盘、POST计数和重放结论不变。

## 4. Host、保留范围与未验证项

当前 Codex 会话已发现21个工具，免费 `list_models` 返回默认模型、20项单次上限和共享并发5；本记录的收费提交/查询也均通过当前会话执行。S轮验收期间 Codex 配置整体文件哈希变化，执行过程没有写入该文件，变化来源未确认，因此不宣称该轮整个配置文件保持一致；DSH三份profile哈希一致。B/E与T轮核对的Codex及DSH配置哈希全部一致，均无Host配置写入。

用户另行报告DSH重启后已连接21工具、远程图片检查和免费规划成功；这是用户提供的结果，不替代本轮独立的Desktop GUI或Agent视觉路由实测。保留[原最小profile看图未通过](HOST-VALIDATION-PR19.md)与[独立CLI视觉路由通过](DSH-VISION-HOST-VALIDATION.md)的历史边界，完整Desktop GUI仍未验证。

原始请求/查询、账本快照、队列采样、图片与来源检查点（可能含临时签名URL）仅保存在本机私有证据目录，未提交图片、SQLite、配置正文、提示词原件、签名URL或密钥。源码/依赖/版本/Host模板/发布流水线在本次归档中不变；现用D盘安装仍固定v0.3.0发布提交，本轮归档不升级安装。

本记录不补齐全模型/变体、同步出图、长期负载、真实故障恢复、平台审核、供应商账单或GUI等未验证项。发布与升级历史分别见[正式发布验收](RELEASE-0.3.0-ACCEPTANCE.md)和[D盘升级验收](LOCAL-V0.3.0-UPGRADE-ACCEPTANCE.md)。本轮文档检查与dev→PR→Windows CI→审查合并的最终结果以对应PR及精确合入提交CI记录为准，不预填未来通过。

## 5. 验收归档完成后的 dev 快进同步

本节记录2026-10-22已完成的归档及分支同步快照，区分此前真实绘图、本节无收费同步和后续文档归档；后续新增文档提交会产生新HEAD，不要求分支永远固定在本节SHA。

此前验收文档提交 `d6bbf6146bdaa89a2247176d419470ae20f96383` 经[PR #24](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/pull/24)审查与必需Windows quality通过，正常合入main的 `861277c0f4517ad8f6869cf8b0ea2b85d5fe5720`，再核对该合入提交CI成功；没有管理员绕过或Release操作。随后按用户授权执行本地 `git merge --ff-only origin/main` 与普通 `git push origin dev`，从d6bbf61快进到861277c，没有新建提交、改文件、强推或删除分支。

| 阶段 | 分支 / 事件 | 精确提交 | Windows CI |
| --- | --- | --- | --- |
| 验收文档推送 | dev / push | `d6bbf6146bdaa89a2247176d419470ae20f96383` | [39722278653](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39722278653) 成功 |
| 验收文档PR | dev / pull_request | `d6bbf6146bdaa89a2247176d419470ae20f96383` | [39722308337](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39722308337) 成功 |
| 合入提交复验 | main / push | `861277c0f4517ad8f6869cf8b0ea2b85d5fe5720` | [39722870001](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39722870001) 成功 |
| dev快进同步 | dev / push | `861277c0f4517ad8f6869cf8b0ea2b85d5fe5720` | [39723976626](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39723976626) 成功 |

四轮CI的报告均核对为165项测试、11个阶段全部通过。同步轮明确核对事件为push、分支为dev、HEAD为861277c；使用该轮自己的报告，不复用main检查替代同步验证。同步结束时本地dev、origin/dev、origin/main及远端实际main/dev均为861277c，领先/落后0/0，工作区干净。

同步前后只读快照核对20条现用任务完整记录、128个受保护文件（包括原始验收材料、输出、凭据文件和已核对Host配置）均不变；D盘安装仍固定正式v0.3.0的 `c6121a7f142558aa53bc622505b4f1d1e17fcca2`，不随开发分支移动。4个既有Release的发布记录/附件摘要不变，没有新增Release工作流或收费绘图调用。原始图片、账本、备份和私有证据继续保留，完整快照、CI报告及本机报告解析说明只留本机忽略目录，不入库。

本节所述同步已完成；本节文档的后续dev→PR→Windows CI→审查合并及合入CI结果，以承载本节的实际PR和精确提交运行记录为准，不预填未来成功。
