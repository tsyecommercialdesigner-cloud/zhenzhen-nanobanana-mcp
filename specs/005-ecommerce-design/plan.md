# 技术方案

保留依赖和现有队列，新增 design_models.py（严格结构）、design.py（分类型故事板、原图冻结、SQLite 版本记录、审批和队列桥接）、design_tools.py（MCP 注册）。server.py 注册新模块并更新 Host 指引。

免费 inspect_design_images 复用 MediaLoader 的格式、大小、URL/SSRF 校验，返回图片内容供 Host 观察。plan_ecommerce_design 收集完整 brief、对标分析或用户选择无参考的理由，完整后冻结实际商品图并生成三类差异化故事板；不把竞品图片当作商品身份参考。Host 可提交有事实引用的逐图修改，所有改动生成新版本。没有新增语言/视觉模型调用，也不从图片推断不可见的参数。

设计数据位于已配置输出目录的 designs/，通过现有 safe_output 防止链接逃逸。SQLite 使用独立事务、期望版本和完整内容 SHA256，保留旧版本。批准记录完整摘要；提交时核对当前版本/摘要、收费授权及冻结图片内容，再复用 TaskQueue.submit。提交期间短事务保护当前版本，使用独立任务数据库，不持有数据库锁等待网络。稳定标识 ecommerce-design / design_id / r{revision}-{panel_id}，每次最多 12 项，结果与现有 get/wait/cancel 互查。

测试覆盖缺失信息、参考取舍、三类内容、SKU 图绑定、来源引用、改稿/过期审批、图片变更、持久化、竞争版本、多批/重复提交、错误返回及落盘。现有完整门禁保留；链接夹具在Windows创建Junction，在Linux创建真实SymbolicLink，保留相同读取与安全断言。项目未提供 .specify/memory/constitution.md，沿用现有 specs 结构，不初始化 spec-kit。
