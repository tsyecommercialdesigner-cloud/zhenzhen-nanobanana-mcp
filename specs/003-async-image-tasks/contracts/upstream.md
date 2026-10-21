# 当前上游与本地任务契约（0.2.0）

后续[004同步入口](../../004-sync-image-tools/spec.md)复用此上游映射与共享账本，不增加供应商端点或重试。当前mcp.json注册快照已包含开发版generate_images/wait_image_tasks；本文原异步协议和发布版本历史保留。

来源：[新 API 文档](../../../docs/API-ENDPOINT.md)，2026-10-20；四个分辨率变体按用户确认继承基础模型限制。001 旧契约仅保留历史。底层仍为同步绘图 API，异步队列由本地 MCP 实现，无供应商 task/job 查询端点。

| 基础模型及其变体 | Gemini | Chat | Generations | Edits |
|---|---|---|---|---|
| gemini-3.1-flash-lite-image | 是 | 是 | 否 | 否 |
| nano-banana-pro / -2k / -4k | 否 | 否 | 是 | 是 |
| gemini-nano-banana-2.1 / -2k / -4k | 是 | 是 | 是 | 否 |

自动路由 Flash-lite→Gemini，其余→DALL·E；pro 有参考图时选择 Edits，其余 DALL·E 走 Generations。显式端点约束同表，不支持组合整批拒绝。显式像素长边≤1024基础版、≤2048为2k、其余4k，Flash-lite忽略；只替换模型名，不发送 size 或分辨率参数。

默认基地址 `https://ai.t8star.org`；绘图 POST 使用 Bearer 原始密钥，无自动重试、不跟随重定向。下载使用独立、无认证且禁环境代理的客户端。密钥不写入账本。

| 请求 | 映射 |
|---|---|
| POST /v1/images/generations | JSON model、prompt、aspect_ratio、response_format=url；有参考图时 image 为原始 base64 字符串数组 |
| POST /v1/images/edits | multipart model、prompt、aspect_ratio、response_format=url；所有参考文件重复 image 字段，无 image[]；无文件也发送 multipart |
| POST /v1/chat/completions | model、messages[{role:user,content:文字}]；有参考图时改为 text + image_url(data URL) 数组 |
| POST /v1beta/models/{actual_model}:generateContent | contents[{role:user,parts:[text, inlineData{mimeType,data}...]}]，不强加 generationConfig |

Chat/Gemini 在文字中添加“画面比例：X”，不发送文档未确认的比例配置；不承诺像素尺寸。Gemini/Chat 多模态与 Generations 参考图编码是保留的兼容映射，新文档未提供完整收费验证证据。四变体亦未在本次实测。

响应：DALL·E data[].url（兼容 b64_json）；Gemini candidates[].content.parts[].inlineData/inline_data.data；Chat 明确 Markdown 图片或 image_url 图片字段。纯文本不作成功图片。下载/解码后验证内容、字节/像素/数量，保存 UUID 路径与 SHA256。HTTP、业务错误或无效响应返回 failed；网络或超时若已进入发送阶段返回 unknown。任何失败不表示免费，不自动重试。

本地工具结构详见 [mcp.json](mcp.json)。提交 1–12 项，事务内按三元组与规范化请求/实际路由/上游地址指纹防重。相同参数返回 reused；冲突/容量超限整次无新增。返回排队状态后由 lifespan worker 执行，共享账本限流；不使用 SDK 原生 MCP Tasks 扩展或 LangGraph。

任务状态 queued→preparing→running→succeeded/failed/unknown；取消未发出任务为 cancelled，可能已发出为 unknown。running 在发 POST 前持久化，宁可保守报告 unknown 也不回放可能收费请求。owner 心跳每5秒，租约30秒；过期 preparing 恢复 queued，running 变 unknown。旧 owner 发送前及保存前校验所有权，不覆盖被取消/接管记录。若跨 Host 取消仍在执行的本地等待，该所有者退出前或租约过期前继续占用并发槽。

服务停止期间不运行任务；重启只恢复未发出任务。改上游根地址后不执行之前在其他地址登记的 queued 任务。相同输出目录须使用相同并发配置，数据库仅在本机文件系统共享；不同输出目录无共同防重记录。无法保证供应商网络侧 exactly-once，也无法自动恢复未收到的供应商响应。

验证采用 MockTransport、gate/barrier、故障注入、SQLite 多实例/线程与真实 stdio fake provider；本次无收费调用。API 文档所引用 validation 原始报告未随仓库提供，未视为新增现场业务/账单证据。
