# PR #19 合并与独立 Host 免费验收（2026-10-22）

## 提交、审查及 CI

[PR #19](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/pull/19) 已正常合并。审查 head 为 `40ab2c0c50f560b14493d674a16ec7b5cfae32ed`，合入 main 为 `aed8eb57b50ba13319600fbf0559a391f8ab5bc1`。本轮审查覆盖设计确认与收费授权分离、稳定任务身份、防重、连接失败重试边界、响应检查点恢复、引用图与结果文件哈希、SQLite 并发租约，以及契约、测试和文档，未发现阻止合并的问题。

本机 `uv run --no-sync python scripts/check.py` 的 11 项必需检查通过。PR Windows CI 39691947207 / dev CI 39691940457 通过；合入提交的 [Windows CI 39700127651](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39700127651) 也通过，165 项测试及 11 阶段检查全部成功。必需 `quality` 门禁与 PR 规则保持 active，未使用管理员绕过或强推。

远端 PR 负载证据：3 进程、200 项、峰值并发 5、重复分发 0、200 个输出校验成功、SQLite integrity 为 ok。此项为隔离测试，不是新增真实供应商调用。历史 16 图记录仍为 7 项 Agent 通过、9 项需修订，本轮没有重画，也不将其描述为整体视觉验收通过。

## 独立安装与协议

从实际 GitHub 仓库 clone main 到以下专用父目录，并核对完整 SHA 与上述合入提交相同：

`E:\temporarily-workspace\nanobanana-host-validation-20261022-pr19-aed8eb57`

项目位于父目录下 `zhenzhen-nanobanana-mcp`。使用新专用 uv-cache 执行 `uv --directory <项目> sync --locked --no-dev`，Python 3.12.14、uv 0.12.9，包来自独立 .venv；没有更新现用安装。项目根 .env 仅含无真实权限的测试值，不复制用户凭据。Host 启动使用 `run --no-sync`，移除继承的 NANOBANANA_* 及真实密钥字段。

独立运行 `python -m zhenzhen_nanobanana_mcp.smoke` 通过：FastMCP 4.1.0、MCP SDK 2.3.0，自动协商协议 2026-07-28 与兼容协议 2025-11-25 均发现 21 工具、9 Resources、6 Prompts；受控业务网络计数为 0，空文件密钥拒绝回退检查通过。这是 SDK 协议验证，Resources/Prompts 不冒充两种 Host 的桥接验收。

源码包元数据仍为 0.2.2；本次测试对象以 main 完整提交唯一标识，不能等同已发布 v0.2.2 标签或现用 8 工具安装。

## 实际 Host 验证

按 Codex → DSH 顺序执行，未启动模型推理或绘图请求。

| Host | 实际入口 | 工具与免费调用 |
|---|---|---|
| Codex CLI 0.153.0 app-server | 独立 CODEX_HOME/config.toml；stdio JSON-RPC initialize、临时 thread/start、mcpServerStatus/list、mcpServer/tool/call | 21 工具与契约精确一致，7 类免费调用通过；返回原始 ImageContent |
| DSH 0.2.1-rc.2 CLI | 已安装 CLI，独立 DSH_HOME/profile；实际 system-prompt/tools/mcp-client 插件，通过 ctx.tools.execute 调用 | 21 工具与契约精确一致，7 类免费调用通过；进程退出 0；图片投影限制见下文 |

Codex 调用方式按本机版本生成的 JSON Schema 及 [官方 app-server 文档](https://learn.chatgpt.com/docs/app-server) 核对，没有用 Python MCP 客户端替代 Host。

| 免费调用 | 两 Host 的结果 |
|---|---|
| list_models | 7 个模型、默认 gemini-nano-banana-2.1、批次上限 20、共享输出目录并发 5，output_dir 位于独立目录；配置成功仅代表假密钥存在 |
| plan_ecommerce_images | count=20，返回 20 项详情页计划，无出图提交 |
| get_image_tasks | 隔离身份查询返回空 tasks，非错误 |
| get_batch_result | 不存在的批次正确返回 isError=true，未伪装成功 |
| inspect_design_images | 32×32 本地合成测试色块，尺寸、原始图像字节与 SHA256 验证成功；此图仅作传输 fixture，不是商品视觉判断 |
| plan_ecommerce_design | 分 Host 保存测试草稿 revision=1，正确返回 needs_input、7 个问题、空 panels；不批准设计、不提交任务 |
| get_ecommerce_design | 返回相应草稿，空任务，不触发恢复或重提 |

**DSH Agent 看图未验证通过：** 最小 profile 未挂载附件存储，也未配置活动视觉模型路由。此次图片投影返回 `image unavailable` 文本；原始 MCP ImageContent 与 structuredContent 仍保留在结果 value，原图哈希一致。本机 dsh-mcp-client 源码要求附件存储和已确认 image 输入能力的模型路由。该结果证明工具与原始数据桥接可用，不证明 DSH Agent 能看到图；完整视觉 profile、GUI、模型自主选工具及语义观察均未验证。未为解决此项而修改用户现用 DSH 配置或导入真实模型凭据。

## 数据保护与证据

测试前后现用 `D:\MCP\zhenzhen-nanobanana-mcp\.env` 与 Codex config.toml 指纹一致，现用任务数 5、批次数 10，35 个非数据库输出文件逐一 SHA256 一致。运行中的 owner/heartbeat 属于动态租约，不作为数据库字节不变的依据；观察到 owner 行数 5→6，未删除或修改其记录。独立 Codex 工具库存仅包含 nanobanana-host-check，未加载现用 MCP。

独立项目仅产生 outputs/designs/designs.sqlite3，没有 outputs/tasks.sqlite3，没有供应商任务和生成图片。Host 子进程已退出；不删除测试证据、私有资料或现用数据。未新增收费调用，未更新 D 盘现用安装，未创建、修改或发布 Release。

证据保存在上述专用父目录：protocol-result.json、Codex 库存/结果/RPC 日志、DSH 结果/profile/日志、verified-summary.json、文件指纹和业务数据数量基线。CI 证据在工作区忽略目录 `.cache/pr19-main-ci-evidence/`。这些本地日志与假配置不入库。

## 后续补充

2026-10-22 在新的独立目录补齐附件存储，并使用 Desktop profile 的 codeproxy-anthropic / claude-sonnet-5-5，完成实际 DSH CLI Agent 看图验证；见[附件与视觉路由验收](DSH-VISION-HOST-VALIDATION.md)。原最小 profile 未验证通过的历史结论保持不变；新增结果不代表 Desktop GUI 已验收。
