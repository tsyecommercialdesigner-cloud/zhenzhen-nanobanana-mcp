# 2026-10-21 十项详情页收费验收

用户明确授权本轮10项详情页生成、批量异步提交、并发、结果查询、落盘及原身份重放；暂不发布。沿用已通过CI的main `728172caf5794a374dda4c418779d34cd372155d`独立运行安装，未改跟踪源码或现用Host配置。凭据从`ZHENZHEN_NANOBANANA_API_KEY`正常读取，不输出或复制真实值。

## 提交与执行

- 一次submit_image_tasks登记10项，约0.406秒返回；初次均queued、reused=false。模型为gemini-nano-banana-2.1基础版，DALL·E Generations，1:1，无参考图、无显式分辨率。内容为虚构白色陶瓷马克杯的10个电商详情构图，不声明容量、认证、价格或功效。
- 使用默认并发上限4，查询同时最多4项running；真实HTTP请求观察峰值4，没有把一次登记10项误称为同时10路。排队任务随槽位释放逐步执行。
- 按原身份每8秒查询，提交后约80.625秒观察到10项全部succeeded；各项有独立图片路径。POST `/v1/images/generations`共10次，全部HTTP200，无自动重试。
- 9张1024×1024 PNG，1张2048×2048 JPEG（第4项）；格式、像素、字节数及SHA256均独立读取校验通过。所有任务仍使用基础模型，第4项的格式/尺寸来自上游响应，不是本地自动路由到2k版，也不构成精确分辨率保证。

## 原身份重放

checkpointer=`paid-ten-acceptance-20261021`，thread_id=`mug-details-ten`，task_id=`mug-detail-01`至`mug-detail-10`。完整请求在首次RPC前保存，提交尝试标记也先落盘；不使用新ID重试不确定请求。

10项成功后，使用保存的完全相同请求和身份整批重放，10项均reused=true且图片路径/hash不变。重放后等待8秒，SQLite完整任务行快照（seq、三元组、指纹、状态、图片及创建/更新时间）前后完全一致，总任务行数仍为10。真实HTTP POST尝试计数为10→10，没有额外生成请求。

观察器运行原版MCP入口并转发真实请求，不伪造上游响应；仅记录方法/主机/路径、非秘密Content-Type、时点、状态码与重叠数，不记录认证头、密钥或图片请求体。预算保护只允许本轮10次Generations，禁止额外POST或Edits；保护未触发，防重结论不是靠拦截重复请求得到。没有核对供应商账单后台或具体扣款金额。

## 文件清单

独立证据根：`E:\temporarily-workspace\nanobanana-paid-ten-20261021`；下表路径相对于其outputs目录。原图、SQLite、请求及日志均留本机，不进入Git。

| task_id | 像素 | 图片相对路径 | 字节数 | SHA256 |
|---|---|---|---:|---|
| mug-detail-01 | 1024×1024 | 29423bef246f4622872e979265e9e210/01.png | 867339 | 185289c3a1b25a528a5e9867b03a43d1501a941aece15d04f047fce5c52ee534 |
| mug-detail-02 | 1024×1024 | 86d80e70290d4836ae98acf48d22ffd6/01.png | 1117573 | b72a9b12194d03c578ef4e834ffa18d6e330d72432e854e0911a7f2a8e8ad8fe |
| mug-detail-03 | 1024×1024 | 026fb5c1bbc9437e85a510ea53ce9b1a/01.png | 1000007 | e314e129fd2979420613df7a91802cb2e89e7189cc90c9a00b6c9b6b432d8543 |
| mug-detail-04 | 2048×2048 | b12e9665d4d3427985506fcfbd83a97e/01.jpg | 1997864 | 100df6eecd475ad3427030181df3ba03de10edeb6f4104976d0d38797f732a7d |
| mug-detail-05 | 1024×1024 | c92e3dd8c01d467d9b38075ae53d0d15/01.png | 1241742 | 6b7c3cc75e94534a92cc69cd01748466b139cd5dc35da6998373db161ab529ec |
| mug-detail-06 | 1024×1024 | 93c2aa31c6e04ef29ea3626a6ed80253/01.png | 1221922 | 21c94c831839133a8a3dc63a8f45554130996dd8de570d06f8e6c31182cdd77c |
| mug-detail-07 | 1024×1024 | 065f7ced60784d7db1ea303805d57b33/01.png | 1207816 | b6535cc5dad01c63b3044fe28a3e0f8fc47d262bb989cf66c61d5513d0452472 |
| mug-detail-08 | 1024×1024 | 977b53787ab34e258b1456af988fe8c2/01.png | 1330252 | 4f726babd655386d5cf7f98cd69b24e26eb2a6b6ba14b80f06a657a7752394ab |
| mug-detail-09 | 1024×1024 | f31047d1c6c14467b3883094bc5c44f3/01.png | 946283 | 7551ef0e3b8e9f9519a820ac5f3a6f6065a50687226d5461a977df9f89cf33b8 |
| mug-detail-10 | 1024×1024 | 17ec8162b1ca4a3b877dd21e5561b143/01.png | 1354518 | 4bad43578328e79e00369fe44a3bee33c94e04bc5adaf5fb44101c180738c964 |

证据根保留ten-request.json、ten-submit.json、ten-queries.jsonl、ten-final.json、ten-replay.json、两份账本快照、http-observer.jsonl、summary.json及实际验收脚本。images.md提供全部原图链接，contact-sheet.jpg为只读预览拼图，原图未更改；已查看10图预览，不能把示意生成当作真实商品一致性证明。

## 范围

本轮未发布，也未执行额外编辑、其它模型/接口/变体、故障注入/重启恢复、取消或GUI测试。验收服务正常退出，无残留测试进程。本记录初次写入时README及验收文档仍为本地工作树变更；后续提交、CI、合并与草稿创建按新的阶段授权执行，不将本次业务验收当作远端发布证据。
