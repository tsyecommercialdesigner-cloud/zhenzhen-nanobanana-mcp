# 手动真实收费验收

真实调用只在用户明确授权后执行，不属于CI或常规smoke。`scripts/live-ecommerce.py`固定验证同款5张主图、8屏详情、3张SKU，共16次上限；业务套图原有8屏下限不变。方案使用新版共享规范复刻流程，模型/接口由manifest明确指定，本手动脚本检查Gemini原生接口。

输入文件命名`manifest.json`，内容为build_reference_replica_prompts的完整参数，结构参考[示例](../examples/reference-replica.json)，调整为5+8+3并核实全部商品事实、素材、参考观察和SKU。所有真实资料、生成图、原响应和账本必须放在仓库之外。先给用户展示方案并取得对本次真实测试的授权，不能把CLI开关当作授权来源。

```text
uv run --no-sync python scripts/live-ecommerce.py execute --root /absolute/private/live-test --authorize-paid-test
```

脚本读取已有项目.env/进程密钥，按原凭据优先级校验；密钥不写入命令行、manifest或日志。MCP SDK默认过滤子进程环境，手动入口只显式转交本服务密钥、服务根地址和必要网络配置，不传GitHub凭据。当前云环境如需HTTPS_PROXY与SSL_CERT_FILE，在专用真实transport中明确使用且保留TLS校验，不改变业务默认网络边界。每次Provider请求使用独立transport，调用的仍是正式Provider适配器与任务队列。

HTTP发送前用SQLite事务预留次数，校验Idempotency-Key、固定设计/版本/任务、真实端点和HTTP提示与批准任务一致；单键仅1次、分类5/8/3、合计16。自动POST尝试设为1；超时或连接失败已预留次数不退款，不能删除预算、更改manifest、换任务编号或新目录来重画。先用第1张正式主图验证成功，再提交余下15张；不是另外增加探测调用。

完整流程通过真实stdio读取Resources/Prompt、看输入图、构造/导出、记录用户测试授权、提交/等待、查询结果和重复提交复用。记录全部16任务成功、每项一张图片、SHA验证、无未提交图、导出提示不变、复用不增加POST后，状态为execution_passed_pending_visual_review。还需Agent观察全部图片，以六维assessment保存逐图证据并向用户展示；流程跑通不等于图片已经可以上架。

输出根目录包含plan.json、progress.json、execution-summary.json、paid-budget.sqlite3及output下原任务/设计/图片。不要把真实图片、原响应、私有路径或账本放入Git或PR；只提交必要的脱敏数量/配置/结论及未覆盖项。未知收费状态不重发；失败时保留原记录并按实际证据报告，不为了通过测试额外收费。

自动化只对费用边界使用MockTransport：原提示校验、16次和分类型上限、持久重启、并发重复、响应不确定不再发送、无显式CLI授权拒绝，以及子进程密钥转交不混入其他凭据。

2026-10-21已执行一轮用户授权的5+8+3真实验收，完整结果见[验收记录](../specs/010-live-ecommerce-validation/verification.md)。16次POST全部完成16图，复用/复核未增加收费；7图Agent通过，9图标记需修订，未自动重画。规划时应把负向绘图约束放在requirements，Textual Contents只填写确实希望绘制的文案。
