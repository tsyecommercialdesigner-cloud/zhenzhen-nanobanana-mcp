# 验证方案

选用Zippo官方HeatBank 9s的黑/银/蓝三个SKU，官方HeatBank 6 Pro真实握持照只用于参考干净背景、自然柔光与产品表现，不迁移其结构、防水等级或其他参数。源资料与生成图保存于/workspace/live-tests独立目录，不纳入Git。

人工编写并校验ReferenceReplicaBrief，保持8屏下限和16图目标。测试服务使用真实Provider适配器、真实MCP stdio与现有队列；仅在手动验收脚本中显式注入当前云环境出口代理transport及持久POST预算，不改变生产默认网络边界。选用本服务gemini-nano-banana-2.1的Gemini原生接口，结果预期为inline图片；未验证的其他实际模型/接口不宣称已验证。

收费计数在HTTP发送前以SQLite事务记录，任务身份必须属于批准的manifest，校验真实HTTP提示与队列批准内容。每键最多1次、分类5/8/3、总数16；safe_attempts=1，持久记录预留次数不退款，不自动重提。先提交1主图并查看是否成功，再提交余下15；查询/导出/复用检查不能新增收费。

scripts/live-ecommerce.py为显式授权的手动入口，CI仅对计数/拒绝/请求匹配用MockTransport测试。完成后记录真实任务/文件/调用/视觉复核与未覆盖项，跑全部本地门禁，再按用户条件授权提交dev并创建PR，等待实际CI结果，不合并或发布。
