# 20项任务、5并发及安全恢复

当前开发源码同步/异步/设计入口均支持单次1–20项，默认全局并发5，允许配置1–20，队列容量默认200（可配20–1000）。同一实际输出目录内各Host共享SQLite事务、任务记录与并发，需设置相同并发数；不同输出目录独立。当前共17 Tools、2 Resources、2 Prompts，新增retry_image_tasks；正式v0.2.2仍是旧8工具版本，尚未发布新版本或更新成员安装。

## 模型适配

全线使用以下三个模型家族，保留已有分辨率变体，不再把旧绘图模型作为导出目标：

| 家族 | API能力 | 已有变体 |
|---|---|---|
| gemini-3.1-flash-lite-image | Gemini、Chat；auto选择Gemini | 无2k/4k路由 |
| nano-banana-pro | DALL·E Generations/Edits；有参考图时auto选择Edits | -2k、-4k |
| gemini-nano-banana-2.1 | DALL·E Generations、Gemini、Chat；auto选择Generations | -2k、-4k |

list_models返回三个base_models及共7个可选标识。复刻的prompt_target兼容字段由服务器按brief.model和resolution归一，导出包含真实execution_model/api_format/endpoint、画幅及像素需求，和实际提交共用矩阵及提示编译器。三个模型保持同样的风格图/商品图角色控制结构；具体多图效果须实际验证。

## 重试按阶段执行

| 阶段 | 行为 |
|---|---|
| 参考读取与HTTP GET | 临时网络失败及GET的429/500/502/503/504进行有界指数退避；无效图片、私网URL、权限和hash不符直接报告 |
| 绘图连接建立 | 仅ConnectError/ConnectTimeout这类请求尚未发送的连接错误有限重试，Idempotency-Key不变 |
| 可能已发送POST | Read/Write超时、服务错误或无可靠响应，不自动重放；保留unknown/failed及原身份，先核对结果/费用 |
| 收到有效图片响应 | 先把原响应来源保存为本地检查点，核对SHA256并持久化recovering状态，再下载/落盘 |
| 下载或保存失败 | 只用原响应恢复，不发第二次绘图；进程中断后的recovering同样只继续原响应 |
| 输出校验失败 | 报告file_integrity=failed；显式repair_files=True后保留损坏文件并尝试从原响应修复，既有成功摘要仍须匹配 |

NANOBANANA_SAFE_ATTEMPTS默认3（可配1–5），NANOBANANA_RETRY_DELAY_SECONDS默认1秒（可配0–30），按1、2、4…倍退避；单任务超时仍约束每次执行。GET单次收集最多3次，原响应恢复最多3轮，因此默认最坏9次只读下载尝试；不会因此重发绘图。显式retry_image_tasks会开始新的有限安全恢复周期，累计attempts保留。没有隐式换模型、换编号或降级；供应商未承诺幂等语义时，发送Idempotency-Key本身不构成远端exactly-once或免重复计费保证。

响应检查点位于task-responses/，输入副本在task-inputs/，业务图仍在UUID目录。检查点与SQLite记录、图片和设计数据应一起保留；不删除账本绕过去重。检查点可能包含签名图片URL，作为私有业务资料保存，不把完整内容打印到日志。

## 幂等键与输入摘要

本地身份仍是(checkpointer, thread_id, task_id)，唯一约束和整批冲突事务继续有效。同一键、相同参数复用已有记录；任一内容冲突时全批不新增。旧请求未提供reference_sha256时，仍按旧字段集构建指纹，原账本增量加列，原成功/未知记录不自动重画。

provider_idempotency_key从身份及内容指纹派生并持久绑定，所有连接重试和安全恢复保持原键。post_attempts为请求尝试数，包含连接前失败，不能拿它推断已计费次数；recovery_attempts为原响应收集次数。safe_to_retry表示存在可安全恢复的原响应或确定未发送的阶段，不代表业务成功。

可选reference_sha256按reference_images顺序传入预期SHA256，数量必须一致。worker收费前校验实际内容并保存内容寻址副本及摘要，后续安全重试使用该副本。普通无预期hash输入在首次准备时固定实际内容；如果需要严格绑定先前看过的图，先inspect_design_images取得SHA再传入。新设计/复刻方案由服务自动绑定已批准的冻结图摘要，历史方案保留旧接口兼容。

## retry_image_tasks

接收原checkpointer/thread_id和1–20个不重复task_ids。正在进行或成功的项直接复用；可安全重试项重排原任务，不创建新身份。无可靠响应且可能已发出的项拒绝，本批任何非法/不安全项都会使全批不重排。

```json
{
  "checkpointer": "ecommerce-design",
  "thread_id": "basket-main",
  "task_ids": ["r1-p01", "r1-p02"],
  "repair_files": true
}
```

repair_files默认false，仅修复文件时明确置true。损坏文件移为原文件名.corrupt-UUID并保留；临时文件完整写入、fsync及SHA256核对后，通过原子创建发布，不覆盖已有不同内容。已有成功输出的SHA继续约束后续恢复，即使图片URL内容变化也不能悄悄接受替代图。缺失或变更的响应检查点直接失败，不发新绘图。

get_image_tasks、wait_image_tasks和重复提交会校验成功文件。校验使用内容摘要，并缓存文件inode/大小/mtime/ctime及预期hash；文件属性变化或新进程读取会重新计算。文件缺失/不符时返回failed/file_integrity=failed及原元数据，不伪装成功。该只读查询不自动修复文件或改写账本；明确重试后才安排恢复。失败中仍保留已落盘部分结果。

recovering是活跃状态，等待会继续；它表示已收到可靠图像响应并在恢复文件。queued/preparing可无发送地取消；running取消仍unknown，不能承诺供应商停止/退款；recovering取消停止本地恢复，绘图可能已收费。取消/关闭保持原幂等与响应记录，重启仅自动继续明确未发送或已有响应可安全恢复的阶段。

## SQLite实测与范围

本机测试3个独立进程共用一个输出目录，200个任务按20项批次登记，5个并发派发，200个文件全部hash核对，无重复/丢失，PRAGMA integrity_check=ok，WAL模式有效。另测5个同时等待的同步RPC及20项异步登记。实际运行数值见[007验证记录](../specs/007-queue-reliability/verification.md)。

SQLite只保存短事务元数据，大响应/图片位于文件系统，因此当前需求不需要额外数据库。实测采用本机小图与受控替身，不能推断真实供应商吞吐、8K图片下载速度或网络盘能力。SQLite必须在本机可靠磁盘使用；若未来出现跨机器写入或持续锁竞争，应基于相同任务协议评估开源免费的PostgreSQL，迁移需单独设计和验证。本次没有安装无必要的数据库服务。
