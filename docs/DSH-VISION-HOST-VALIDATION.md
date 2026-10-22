# DSH 附件与 Agent 实际看图验收（2026-10-22）

## 结果与范围

在独立目录补齐附件存储与视觉模型路由后，实际 DSH CLI Agent 看图链路通过。使用本机 Desktop profile 的 `codeproxy-anthropic / claude-sonnet-5-5`，经真实 Agent loop 自主调用 MCP `inspect_design_images`，收到 ImageContent 后向代理商发送图片并完成识别。发生两次模型 POST，均为 HTTP 200；无绘图生成/编辑请求，没有创建图像任务。

此前[PR #19 免费 Host 验收](HOST-VALIDATION-PR19.md)中最小 profile 的 `image unavailable` 是当时真实结果，保留不改写；本记录补充新的附件及模型路由条件。此次证明隔离 CLI Agent 的图片投影、请求序列化和简单视觉识别，不证明 Desktop GUI 实际操作、现用完整 profile 或电商图片质量验收。

## 隔离配置

- 测试根：`E:\temporarily-workspace\nanobanana-dsh-vision-20261022`；使用独立 DSH_HOME、vision-check profile、会话和附件对象目录。
- 复用此前独立 MCP 安装，源码提交 `aed8eb57b50ba13319600fbf0559a391f8ab5bc1`；不是 D 盘现用安装或已发布 v0.2.2 标签。stdio 以 `uv --directory <独立项目> run --no-sync python -m zhenzhen_nanobanana_mcp` 启动，仍用无真实权限的绘图假密钥。
- DSH CLI 与相关插件为本机已安装的 0.2.1-rc.2；启用实际 llm、session、session-projection、agent、agent-loop、system-prompt、tools、llm-pi-ai、attachment-local 和 mcp-client。不替换模型或 MCP 响应。
- 仅从 Desktop profile 提取 codeproxy-anthropic 配置，保留 `anthropic-messages`、`https://codeproxy.dev` 和目标模型；模型明确声明 text/image 输入。
- 仅将该代理商所需凭据从本机凭据存储读取到子进程环境，不复制完整凭据存储、不将密钥写入测试 profile 或日志。保留环境变量引用名，移除继承的绘图密钥及项目/输出目录覆盖。
- 复用 Desktop 当前 Anthropic schema 根约束修复补丁的隔离副本；副本及其日志均位于测试根，未改动 Desktop 原补丁或现用配置。此配置依赖明确记录，不扩大为所有 DSH 版本的必需条件。
- Agent 仅可见 inspect_design_images，并加执行 guard；不暴露绘图工具或文件、shell 工具。模型 HTTP 探针只记录路由、图片数量/哈希和状态，不记录授权头；最多允许两次模型 POST，未发生自动重试。

## 预检与实际识图

预检不调用模型：以真实 Agent 身份执行旧色块和新测试图的 MCP 读取，两者均得到 text/image 内容，模型请求数 0，图片进入独立附件存储。由此确认已消除最小 profile 缺附件存储/视觉路由导致的文本占位。

实际测试图为本地 Pillow 生成的 1000×800 图形 fixture：四个区域随机排列蓝色圆、黄色方块、绿色五角星和红色三角形，中央含随机六位数字。隐藏答案清单仅供模型结束后的断言使用，未进入用户提示、系统提示或工具结果；提示只提供中性文件路径、需返回的字段和颜色/形状词表。

| 阶段 | 实际证据 |
|---|---|
| 第一次模型请求 | `/v1/messages`，model=claude-sonnet-5-5，无图片；唯一工具为 MCP inspect_design_images；HTTP 200 |
| Agent 工具调用 | 会话记录真实 tool/call、tool/result；工具结果的面向 Agent 内容为 text/image |
| 第二次模型请求 | 同路由，携带 1 张 PNG，12497 字节；HTTP 200；请求图片 SHA256 与本地源图一致 |
| 最终识别 | 左上 blue/circle、右上 yellow/square、左下 green/star、右下 red/triangle，中央数字 968325；全部与隐藏清单精确一致 |

会话以正常 turn/end 收尾，进程退出 0。模型推理调用共 2 次；不将“无收费绘图调用”描述成“没有模型调用”。只验证代理商请求中的模型标识，不独立证明其后端模型来源。

## 原始图片、附件与保护核对

| 图片 | SHA256 |
|---|---|
| 旧 32×32 色块，保留副本 prior-fixture-mug.png | f848ef4591d475390ad9c052e2d284b1abf2cbcc199bfd0cd3292cd283d0b1a1 |
| 新图 visual-input.png | 6de8939702b0963c460f4dafa077612b7c65f00a31c374471ad69850acd1b2c5 |

旧验收原文件与证据未覆盖；测试副本与旧原图一致。两个附件对象按内容哈希存入独立 `dsh-home/attachments/v1/objects/`，逐一读回校验一致；新图实际模型请求的图片字节哈希也一致。保留 fixture、隐藏答案和原始会话/请求校验证据，不只保存成功结论。

前后逐文件指纹核对：现用 Desktop cordis.yml、cordis.patch.yml、package.json、pnpm-lock.yaml、凭据存储、Codex config.toml 及 D 盘 MCP .env 均未变化。原始报告、日志和测试配置已与实际凭据值比对，未发现密钥泄露。独立 MCP 仍没有 outputs/tasks.sqlite3。测试子进程已退出，未修改现用 Host 配置、更新 D 盘安装、删除旧证据或进行 Release。

证据均保留在上述独立测试根：run.py、vision-probe.mjs、preflight-report.json、vision-report.json、verified-summary.json、image-hashes.json、expected.json、原图/附件对象、隔离 profile 及日志。原始证据仅留本地，不随本次归档提交；仓库文档只记录脱敏结果。后续提交、评审与合入检查由归档 PR 追踪，不重新执行模型或绘图调用。
