# 上游映射契约

> 历史 0.1 设计：当前 API 矩阵及异步工具已由 [003 规范](../../003-async-image-tasks/contracts/upstream.md) 取代。保留下方内容供历史追溯，不代表当前能力。

基地址默认 `https://ai.t8star.org`；POST 统一 `Authorization: Bearer <服务加载的原始密钥>`，密钥从项目 `.env` 优先、仅缺失时兼容进程/Windows 当前用户环境。不跟随重定向、不自动重试。下载图片使用独立无认证客户端。

模型枚举为 spec.md 中用户指定的七个名称（含四个2k/4k变体）。每项可选 resolution.width/height 的长边≤1024选择基础版，1024<长边≤2048选择2k，>2048选择4k；flash-lite忽略路由。无显式尺寸保持所选模型；有尺寸时从所选模型家族重新选档。路由只替换下面的 model（Gemini 的 URL 模型段），不发送 resolution/size/width/height，不承诺精确输出尺寸。比例为需求的十项枚举。批量每项独立请求，不发送未声明的 `n`/任务参数。

| 格式/操作 | 方法与路由 | 请求 |
|---|---|---|
| DALL·E 生成 | POST `/v1/images/generations` | JSON：model, prompt, aspect_ratio, response_format=b64_json |
| DALL·E 编辑 | POST `/v1/images/edits` | multipart：上述四个字符串字段；单图文件 image、多图 image[]；不手动设置 Content-Type，httpx 生成 boundary |
| OpenAI Chat 生成/编辑 | POST `/v1/chat/completions` | JSON：model, messages=[{role:user,content:[{type:text,text:prompt},参考图 image_url data URL...]}], aspect_ratio |
| Gemini 生成/编辑 | POST `/v1beta/models/{实际模型}:generateContent` | JSON：contents=[{role:user,parts:[{text:prompt},参考图 inlineData:{mimeType,data}...]}], generationConfig:{responseModalities:[TEXT,IMAGE],imageConfig:{aspectRatio}} |

用户确认编辑 `size` 也被转成 `aspect_ratio`，本实现直接传 aspect_ratio。DALL·E 生成字段来自原本仓库 API 文档；编辑表单与路由来自用户示例，file field 和 response_format 支持仍需上游验证。Chat/Gemini 映射使用对应标准形式加项目比例要求，贞贞实际兼容性未验证。

响应只接受明确图片字段：DALL·E `data[].b64_json/url`；Gemini `candidates[].content.parts[].inlineData/inline_data.data`；Chat 图片 content block、message.images[].image_url 或明确 Markdown 图片。纯文字不是成功图片。解码/下载后使用真实内容验证，不根据返回 URL 后缀确定扩展名。

HTTP 非200、JSON无效、显式 error、没有图片、超过 4 张/项、无效图片、下载/字节/像素限制错误均为工具执行失败；不回传上游原始错误或密钥。成功或部分成功输出按 `mcp.json` 的 BatchResult schema。

验证以 MockTransport 可复现样例为证据，当前未获得授权/凭据执行真实收费调用；不得从受控样例推导余额、费率、真实响应结构或失败不收费承诺。
