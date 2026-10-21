# 执行任务

本文件是本功能任务状态唯一来源，无任务数据库。

- [x] G01 阅读规范、远端仓库与本地事实，关联本地迁移分支（无提交/推送）。
- [x] G02 实现本地/CI统一检查、秘密/依赖检查、干净运行安装和受控发布校验。
- [x] G03 添加PR/default CI、批准发布CD与维护者门禁指引（远端设置待G06）。
- [x] G04 重写GitHub获取/安装/迁移/更新/回滚手册和README，同步元数据及跟踪边界。
- [x] G05 执行本地检查、安装/权限保留验收、记录通过/失败/未验证项。
- [ ] G06 按修订的六步计划交付；2026-10-20用户已授权恢复main的README/LICENSE、创建远端dev并提交推送源码。后续用户已授权PR、Windows CI和main合并门禁；用户随后说明单人维护，已授权本Agent审查通过后合并PR。2026-10-21分阶段授权独立Host免费验证、单张主图、3张详情页与1次编辑、10项详情页及相同身份重放；本轮另授权重写README。故障恢复仍未授权/未实测；同日后续已明确授权并完成正式公开及发布版独立安装，见G06.6。
  - [x] G06.1 提交前审查；按用户修订只验Windows及6工具，秘密/私有数据排除。
  - [x] G06.2 先从main基线ce7ce74在远端创建dev；恢复README/LICENSE后以cb78329提交并推送69个新增项目文件，远端对比证实两文件无变化、main未移动。
  - [x] G06.3 创建dev→main PR #1，PR Windows quality运行39413479488通过；启用并读取验证main规则集25471021，必需quality/GitHub Actions、最新基线、讨论解决、禁止强推/删除且无绕过。用户后续授权单人维护改为人工批准数0，由本Agent审查并在PR留记录；最终PR检查及是否合并以GitHub实时结果为准。
  - [x] G06.4 2026-10-21从GitHub独立安装main的91af94c，按Codex app-server→DSH CLI隔离profile顺序发现6工具并完成免费调用及错误返回验证。实际Host后端通过，未验证GUI、Agent自主选工具、现用DSH完整profile；见docs/HOST-VALIDATION.md。无收费调用或发布。
  - [ ] G06.5 2026-10-21单张主图、3项并发详情页、1次原图编辑及重放通过（docs/SINGLE-IMAGE-ACCEPTANCE.md、docs/BATCH-EDIT-ACCEPTANCE.md）；随后新增授权的10项详情页也已通过异步登记、并发峰值4、全部落盘与原身份重放防重（docs/TEN-IMAGE-ACCEPTANCE.md），10次上游POST未增加。真实故障/重启恢复仍未授权/未实测，不能勾选整个阶段；本轮10项验收已完成。
  - [x] G06.6 2026-10-21依次完成PR #4及发布修复PR #5/#6的审查、Windows CI和正常合并；main同SHA CI及受控CD39530083752成功，经release环境正常审批创建草稿。用户随后明确授权核对后正式公开及远端安装，现v0.2.0已公开，标签66555d72742cf54b98bd3dc4c57a94d3a98d7818不变，四附件和哈希通过。正式Release安装器在独立目录从GitHub标签clone、空缓存锁定无开发依赖安装、双模式stdio及6工具契约/免费调用验收通过，新增收费调用0；见docs/RELEASE-ACCEPTANCE.md。G06.5真实故障恢复仍未实测，因此不勾选整个G06。

六步内容与验收标准见 docs/DELIVERY-PLAN.md；本文件是状态唯一来源。

- [x] K01 2026-10-21全部凭据来源统一为ZHENZHEN_NANOBANANA_API_KEY，旧名不回退；源码、模板、文档与回归同步，69测试及11阶段通过。PR #2合入91af94c，main CI39524783398成功，已继续并完成G06.4限定范围。

- [x] R01 2026-10-21按用户新授权重写README，取代先前保持初始化README的限制；保留LICENSE。README给出功能、已通过CI的固定SHA试用安装、统一密钥字段、无同步安装的启动入口、Host模板、6工具/模型矩阵及验收边界；MANUAL同步当前main与未发布状态，文档检查通过。交付与草稿范围按G06.6执行。

- [x] D01 2026-10-21按用户新指示将默认安装目录仅改盘符为D:\MCP\zhenzhen-nanobanana-mcp，安装脚本父目录D:\MCP、四Host模板及README/MANUAL同步；明确v0.2.0旧脚本显式传入InstallRoot，历史路径和发行物不改。PowerShell AST确认默认值与目录深度，README/MANUAL共15段PowerShell示例解析通过，四模板路径一致；本地11阶段、71测试、构建、协议及独立安装通过。真实D盘目录安装/现用Host迁移未执行，无收费调用；本轮用户已授权推送dev、PR、CI与审查通过后合并，远端执行结果以对应PR及合入SHA CI为准，不触发发布。

- [ ] V021 2026-10-21已获用户授权将包/模块/锁版本更新为0.2.1，纳入D盘默认路径和最新验收文档；经dev→PR→Windows CI及审查合并、同SHA main CI后正常审批创建草稿。暂不正式公开、不新增收费调用；v0.2.0保持不变。候选说明见docs/RELEASE-0.2.1.md，精确SHA/run/草稿与验收结论以GitHub记录为准，未完成前不预填成功。
