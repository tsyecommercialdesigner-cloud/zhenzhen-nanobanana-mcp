# 技术方案

FastMCP4.1.0已有lifespan接口已核对；保留SDK/锁定运行依赖，版本升0.2.0。新增SQLite TaskQueue，不引入调度/Agent框架。独立tasks.sqlite3避免改写旧batches.sqlite3。SQLite WAL、BEGIN IMMEDIATE、唯一三元组和内容指纹提供批量原子提交与跨进程抢占。请求JSON仅存私有运行账本，不存API密钥；重复任务不重新下载已变更参考图。

每服务实例lifespan启动有限worker和heartbeat；共享数据库内按preparing/running计数执行并发限制。queued→preparing（只准备参考图）→running（可能已经发送）→succeeded/failed/unknown。每次状态更新限定owner，发送前持久化running；owner心跳超时后preparing恢复queued、running转unknown。正常关闭也按该规则恢复，绝不自动重发可能收费请求；独立实例失去所有权后不能发送/覆盖状态。

提交仅做schema/支持矩阵/指纹及容量检查，持久化后立即返回，不读取文件/请求上游；每任务worker预检参考图总量，有限并发POST+下载保存，事务提交结果。文件输出由不可猜测UUID生成，不用用户ID拼路径；保留现有输出路径边界。queued取消立即生效；preparing取消后owner CAS阻止发出；running取消只停止本地等待并标unknown，其他实例运行时也不能自动再发。

公开submit_image_tasks/get_image_tasks/cancel_image_tasks，保留list_models/plan_ecommerce_images/get_batch_result以及Prompt/Resource。不公开同步generate_images；旧BatchService仅保留内部测试/历史读取兼容。查询分页游标是数据库递增序号，scope条件固定，不返回提示词或参考图URL。状态running/queued是正常查询，不包装业务失败为成功。

测试使用gate/barrier替身证实工具调用先返回、10项并发、混合结果、跨实例抢占/同ID冲突原子性、重启queued恢复与running未知、取消CAS/容量/分页/进程关闭；所有适用API组合与非法组合分别验证。stdio smoke只注册/发现/免费调用；额外本地fake provider集成检验真实MCP协议的提交/查询。同步最新版手册及开发CI。GitHub提交/推送及发布按002/tasks.md与六步交付计划的阶段授权执行，不改C:\MCP运行副本。
