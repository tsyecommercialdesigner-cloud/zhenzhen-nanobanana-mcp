# 执行任务

本文件是本功能任务状态唯一来源，无任务数据库。

- [x] G01 阅读规范、远端仓库与本地事实，关联本地迁移分支（无提交/推送）。
- [x] G02 实现本地/CI统一检查、秘密/依赖检查、干净运行安装和受控发布校验。
- [x] G03 添加PR/default CI、批准发布CD与维护者门禁指引（远端设置待G06）。
- [x] G04 重写GitHub获取/安装/迁移/更新/回滚手册和README，同步元数据及跟踪边界。
- [x] G05 执行本地检查、安装/权限保留验收、记录通过/失败/未验证项。
- [ ] G06 按修订的六步计划交付；2026-10-20用户已授权恢复main的README/LICENSE、创建远端dev并提交推送源码。后续用户已授权PR、Windows CI和main合并门禁；用户随后说明单人维护，已授权本Agent审查通过后合并PR。2026-10-21分阶段授权独立Host免费验证、单张主图、3张详情页与1次编辑、10项详情页及相同身份重放；本轮另授权重写README。故障恢复及正式公开仍待后续授权；本轮已授权创建草稿。
  - [x] G06.1 提交前审查；按用户修订只验Windows及6工具，秘密/私有数据排除。
  - [x] G06.2 先从main基线ce7ce74在远端创建dev；恢复README/LICENSE后以cb78329提交并推送69个新增项目文件，远端对比证实两文件无变化、main未移动。
  - [x] G06.3 创建dev→main PR #1，PR Windows quality运行39413479488通过；启用并读取验证main规则集25471021，必需quality/GitHub Actions、最新基线、讨论解决、禁止强推/删除且无绕过。用户后续授权单人维护改为人工批准数0，由本Agent审查并在PR留记录；最终PR检查及是否合并以GitHub实时结果为准。
  - [x] G06.4 2026-10-21从GitHub独立安装main的91af94c，按Codex app-server→DSH CLI隔离profile顺序发现6工具并完成免费调用及错误返回验证。实际Host后端通过，未验证GUI、Agent自主选工具、现用DSH完整profile；见docs/HOST-VALIDATION.md。无收费调用或发布。
  - [ ] G06.5 2026-10-21单张主图、3项并发详情页、1次原图编辑及重放通过（docs/SINGLE-IMAGE-ACCEPTANCE.md、docs/BATCH-EDIT-ACCEPTANCE.md）；随后新增授权的10项详情页也已通过异步登记、并发峰值4、全部落盘与原身份重放防重（docs/TEN-IMAGE-ACCEPTANCE.md），10次上游POST未增加。真实故障/重启恢复仍未授权/未实测，不能勾选整个阶段；本轮10项验收已完成。
  - [ ] G06.6 2026-10-21已明确授权本轮审查、提交/推送dev、PR、Windows CI通过后合并及创建Release草稿。需复验main同SHA CI并走release环境正常审批；正式公开及正式版安装仍未授权，不能因创建草稿勾选整个发布阶段。精确PR/run/tag/草稿和最终SHA以GitHub记录为准，不在待合入提交中预填未来成功状态。

六步内容与验收标准见 docs/DELIVERY-PLAN.md；本文件是状态唯一来源。

- [x] K01 2026-10-21全部凭据来源统一为ZHENZHEN_NANOBANANA_API_KEY，旧名不回退；源码、模板、文档与回归同步，69测试及11阶段通过。PR #2合入91af94c，main CI39524783398成功，已继续并完成G06.4限定范围。

- [x] R01 2026-10-21按用户新授权重写README，取代先前保持初始化README的限制；保留LICENSE。README给出功能、已通过CI的固定SHA试用安装、统一密钥字段、无同步安装的启动入口、Host模板、6工具/模型矩阵及验收边界；MANUAL同步当前main与未发布状态，文档检查通过。交付与草稿范围按G06.6执行。
