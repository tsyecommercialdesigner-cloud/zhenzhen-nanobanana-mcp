# 新API与异步批量图像任务

后续范围：用户追加的[004同步工具](../004-sync-image-tools/spec.md)允许保留异步工具并新增可选同步入口，取代本功能最初“不公开同步generate_images”的入口限制。其余003上游、三元组、并发和防重契约保持；旧版request_id同步签名不恢复。

依据：用户升级要求及docs/API-ENDPOINT.md（2026-10-20更新）；用户已确认保留四个2k/4k变体，继承基础模型接口限制；checkpointer为SQLite命名空间，不引入LangGraph。

## 范围与场景

Agent一轮提交1–12个任务（含10图详情页），立即得到任务标识和持久化状态，不等待上游绘图。使用(checkpointer,thread_id,task_id)唯一标识，每项有独立提示、模型、比例、参考图和接口；通过后续工具查询结果/保存路径，支持分页和取消未发出的任务。

保留已有固定.env读取、本地任意可读参考图/公开HTTP(S)输入、自动保存及旧request_id结果查询。旧同步generate_images不再公开，避免Agent继续用同步出图；批次新接口是有版本变更的契约，不把旧批次编号当成新task_id。

## API能力

Flash-lite支持Gemini/Chat，不支持DALL·E；nano-banana-pro及其变体仅支持DALL·E Generations/Edits；gemini-nano-banana-2.1及其变体支持Gemini/Chat/DALL·E Generations，不支持Edits。自动接口选择：Flash-lite→Gemini，其余→DALL·E。DALL·E请求response_format=url，Edits重复image文件字段；gemini-nano的参考图走Generations的image字符串数组，不错误调用Edits。Gemini与Chat的无参考图请求使用文档最小文本形式；既有多模态编码作为未实测的兼容映射保留并在发现/文档说明，不保证模型编辑效果。保持用户确认的显式分辨率路由，不新增上游size参数。

## 验收

| ID | 标准 |
|---|---|
| AT01 | 模型/格式/端点矩阵及四变体准确；不支持组合在提交时全批拒绝，不发POST。 |
| AT02 | 正确URL、multipart重复image、Generations image数组、Chat文本及Gemini文本/图片响应解析；纯文本/业务失败不当作图片成功。 |
| AT03 | 单次10项提交无需等待渲染；有限后台并发执行；同输出目录多实例通过事务抢占，任务只执行一次，并发上限在共享账本内执行。 |
| AT04 | 三元组唯一，同内容返回已有任务，不同内容冲突；整个提交事务原子，任一冲突不插入其他新任务；并发同ID/查询不重复POST。 |
| AT05 | 持久化队列/结果，重启可继续尚未发出的任务；已可能收费的running任务中断标unknown，不自动重试。关闭/取消不丢成功结果，不保证远端退款。 |
| AT06 | 按命名空间/会话/任务查询及分页；queued/running等状态查询成功返回，业务失败failed/unknown是isError；结果含实际模型、接口、端点、图片尺寸/hash/路径。 |
| AT07 | 参考图预检在后台且在POST前，错误/超限无收费；队列容量及并发可配置，满时原子拒绝；queued可取消，running取消返回不确定。 |
| AT08 | 实际MCP两个协议子进程发现、免费规划、非法输入及异步任务生命周期可验证；CI无收费调用，单元/故障/重启验证不能称为上游实测。 |
| AT09 | 更新手册/契约/版本/配置及可选运行清单；不改用户Host、运行副本、凭据、既有账本或执行收费探针。 |

不能承诺网络故障下远端exactly-once或自动找回未收到的供应商结果；供应商无异步任务ID/查询端点，本地task_id不是供应商job ID。MCP主进程关闭期间不后台执行；重启后只恢复明确未发送的任务。checkpointer分区不是多用户认证边界。
