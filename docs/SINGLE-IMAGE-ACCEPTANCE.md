# 2026-10-21 单张收费验收

授权范围：用户明确要求先生成1张家居日用品主图，验证异步提交、查询、图片落盘及原身份重放；不做批量、编辑或发布。本记录只证明这一范围，不代表完整收费验收完成。

## 版本与环境

从实际GitHub main独立克隆`728172caf5794a374dda4c418779d34cd372155d`至`E:\temporarily-workspace\nanobanana-paid-single-20261021\zhenzhen-nanobanana-mcp`，锁定安装运行依赖，不使用旧聊天挂载的同步generate_images工具。使用实际FastMCP客户端连接新版stdio服务，发现6工具；从新字段`ZHENZHEN_NANOBANANA_API_KEY`读取真实凭据，不复制或输出值，不改现用Host配置。

使用独立HTTP观察启动器运行原版模块：仅记录POST方法、主机、路径、时间及状态码，不读取或记录凭据/请求头/响应内容，不替换上游响应。额外预算保护拒绝第二次POST；本次没有触发该保护，实际只产生一次POST尝试。代码、锁文件与正常上游请求/下载路径保持原版；该保护不能用于掩盖重复提交失败。

## 请求与结果

| 项目 | 实测 |
|---|---|
| 商品 | 虚构验收示意：单只无品牌白色陶瓷马克杯，纯白背景、柔和棚拍光、无文字/商标/水印/道具 |
| 模型 | gemini-nano-banana-2.1基础版，1:1，未请求高分辨率路由，无参考图 |
| 接口 | DALL·E格式，POST https://ai.t8star.org/v1/images/generations，HTTP200 |
| checkpointer | paid-single-acceptance-20261021 |
| thread_id | white-mug-main-001 |
| task_id | white-mug-001 |
| 初次提交 | 约0.328秒返回queued，reused=false，没有等待渲染完成 |
| 查询 | 约0.343/8.343/16.359秒为running，约24.390秒观察到succeeded |
| 图片 | 1张PNG，1024×1024，1,080,356字节；独立读取验证格式、像素和SHA256通过 |
| SHA256 | 9851e3831abd218ab47f64cecdf5d6ae0d3c87c7e7e019f46e26e99ad921e593 |

图片绝对路径：`E:\temporarily-workspace\nanobanana-paid-single-20261021\zhenzhen-nanobanana-mcp\outputs\0f3374c5a5ca4049896b277293f1347b\01.png`。视觉检查为单只白色杯子、白色背景与接触阴影，没有可见文字或品牌；这是示意商品，不作为真实商品尺寸、材质或认证的证明。

## 相同身份重放

成功后重新调用submit_image_tasks，使用磁盘保存的完全相同请求JSON和三元组，未更换ID或内容。返回succeeded、reused=true及同一图片路径/hash。等待8秒后，SQLite完整任务行快照（含seq、指纹、状态、图片、创建/更新时间）与重放前完全一致，image_tasks总行数仍为1。

观察日志在初次提交至重放后共记录1次绘图POST和1次HTTP200，未出现第二次尝试或预算保护阻断事件。因此本次重放没有再次提交上游；没有读取供应商账单后台，不能把本地HTTP证据表述为已核实具体扣款金额或供应商账务系统行为。

## 证据与后续范围

上述独立测试父目录保留request.json、initial-submit.json、queries.jsonl、final-task.json、replay.json、ledger-before-replay.json、ledger-after-replay.json、http-observer.jsonl、summary.json以及实际验收/观察启动脚本。真实凭据未落盘；提示词、图片和SQLite留在独立私有运行目录，不作为仓库产物提交。验收服务已退出，没有残留测试进程。

本轮未执行批量生成、编辑、10项并发、故障/重启恢复或发布；这些项目仍待单独授权。单元/隔离测试的故障覆盖不能替代对应真实收费验收。
