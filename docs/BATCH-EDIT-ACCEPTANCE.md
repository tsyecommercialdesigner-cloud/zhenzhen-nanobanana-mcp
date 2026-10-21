# 2026-10-21 三张详情页与单次编辑收费验收

用户在首张验收后，另行授权3张详情页生成、一次原马克杯主图编辑及相同身份重放；明确不做10项测试或发布。沿用已通过CI的main `728172caf5794a374dda4c418779d34cd372155d`独立运行安装，Git跟踪源码无修改，不使用旧版同步工具，不改现用Host或私有凭据。

## 实际调用与结果

实际FastMCP客户端连接新版stdio，设置独立输出目录`E:\temporarily-workspace\nanobanana-paid-batch-edit-20261021\outputs`及并发3。先调用免费规划工具，然后一次submit_image_tasks提交3项，每8秒查询原身份。全部成功并重放验证后，才提交唯一一次编辑；没有自动重试收费请求。

| 项目 | 三张详情页生成 | 一次编辑 |
|---|---|---|
| 模型 | gemini-nano-banana-2.1基础版 | nano-banana-pro基础版 |
| 接口 | DALL·E JSON /v1/images/generations | DALL·E multipart/form-data /v1/images/edits |
| 输入 | 同一虚构白色陶瓷马克杯的全貌、细节、家居书桌场景；无参考图/文字/品牌声明 | 首张已生成的马克杯主图本机绝对路径；杯身/把手外表面改鼠尾草绿，杯内保持白色 |
| 提交返回 | 约0.438秒，三项均queued | 约0.375秒，queued |
| 查询成功 | 提交后约32.531秒三项全部succeeded | 提交后约40.469秒succeeded |
| 并发证据 | 查询同时3项running；3个真实HTTP POST重叠，观察峰值3 | 在生成验收通过后单独执行 |
| 文件 | 三张1024×1024 PNG，各自字节数/像素/格式/SHA256通过 | 一张1024×1024 PNG，字节数/像素/格式/SHA256通过 |
| 原身份重放 | 三项均reused=true，图片/任务行不变，POST计数3→3 | reused=true，图片/任务行不变，POST计数4→4 |

共有checkpointer：`paid-batch-edit-acceptance-20261021`。

- 生成thread_id=`mug-details-three`，task_id依次为`mug-detail-01`、`mug-detail-02`、`mug-detail-03`。
- 编辑thread_id=`mug-edit-single`，task_id=`mug-sage-edit-01`。
- 所有重放使用磁盘保存的相同请求内容和三元组，未换ID。每阶段重放后等待8秒，SQLite完整任务行快照（含seq、指纹、图片、状态与创建/更新时间）不变；最终独立账本为4项。

## 图片与视觉检查

以下路径均相对于独立输出目录，业务图片不进入Git：

| 结果 | 相对路径 | 字节数 | SHA256 |
|---|---|---:|---|
| 全貌 | d1d767c1b8c34639a6d1b824014fef87/01.png | 877378 | 4f7d6692f5b070550b05a3fbeb04c0e40c6343ff7a6b75c62eca65ac27d4325f |
| 细节 | cd1d3723a5874c67b2d32d2242b5cfab/01.png | 1067377 | 23075cc435d0d8737705342344ca08f331a9f47654cb5fdbc9362798a010c097 |
| 场景 | c4a727007f814a5f8982432573c7978f/01.png | 1303668 | 69f34dd0442b201e52b19c5db1e65f3d644fb680b5e99fc50e78f23ca3eaf747 |
| 编辑 | 7f4dc84013fa43f9a5569db318370b9e/01.png | 1048374 | 6aea1784484dd12d1165153fc7116ed8f5e5923fad149d5417115e78f95324ac |

四张均已目视查看。生成分别呈现完整杯子、杯口/把手近景、窗边书桌场景；编辑图保留原图单杯形状、构图、白色背景与阴影，外表面变绿、杯内保持白色，没有可见文字/品牌。前三张是无参考图的独立示意生成，不证明真实商品一致性、规格或认证。

编辑输入为[首张验收](SINGLE-IMAGE-ACCEPTANCE.md)的01.png，调用前后SHA256仍为`9851e3831abd218ab47f64cecdf5d6ae0d3c87c7e7e019f46e26e99ad921e593`；原图未覆盖。

## 请求观察与边界

独立HTTP观察器不替换真实网络响应、不记录密钥/请求头/图片请求体，仅记录POST主机/路径、非秘密Content-Type、时点、状态码及重叠数量。预算保护只允许3次Generations和1次Edits；本轮没有触发保护，观察到恰好4次POST，全部HTTP200。两阶段重放后均无新增POST尝试；不是通过拦截重复请求来伪装防重通过。未核对供应商账单后台或具体扣款金额。

独立测试父目录保留两阶段request/submit/queries/final/replay、重放前后账本快照、http-observer.jsonl、summary.json及实际脚本。任务请求、图片和SQLite均留本机；真实密钥未输出或复制。服务已正常退出，无残留验收进程。

本轮未执行10项、故障/重启恢复、取消、其余模型/接口/分辨率变体、GUI或发布；已通过的小批量与编辑不能替代这些项目。
