# 实施任务

- [x] 检查真实凭据、只读连通性、公开商品/SKU资料，保留8屏规则，确认最新16次上限。
- [x] 实现手动收费预算/真实stdio验收脚本，6项无收费专项验证通过，含显式关闭数据库连接回归。
- [x] 生成完整方案，真实stdio执行1+15任务全部成功；16次POST、16张图SHA正确，重复提交无新增请求，导出/执行提示一致。
- [x] 观察全部16张真实图片并经MCP保存复核：7图Agent通过、9图需修订，不自动重画；脱敏证据见live-acceptance.json。
- [x] 本地11项门禁通过后提交8d5cca1并常规推送dev，创建[PR #19](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/pull/19)；当时授权止于创建PR、不合并发布，后续授权与实际合并结果见下节。

## 2026-10-22 后续审查与免费 Host 验收

- [x] 按维护者后续授权审查 PR #19 的 head 40ab2c0，未发现合并阻断项；本地11项检查与PR Windows CI通过，正常合并到 main aed8eb57。
- [x] 合入提交 Windows CI 39700127651 通过，165项测试与11阶段检查全部成功，保留必需quality门禁；未发布。
- [x] 独立目录 clone main 精确提交并锁定成员安装，协议发现21工具、9 Resources、6 Prompts；Codex app-server及DSH CLI均发现21工具，7类免费调用通过，没有收费提交。
- [x] 记录DSH最小profile图片投影限制：原始ImageContent保留并校验正确，Agent内容因缺附件存储/视觉路由降为提示文本，不记为看图验收通过。详细范围见[独立Host验收](../../docs/HOST-VALIDATION-PR19.md)。
- [ ] 如需验证DSH Agent实际看图，另在具备附件存储与视觉模型路由的隔离profile完成验证；不通过修改验收标准掩盖当前未覆盖项。
