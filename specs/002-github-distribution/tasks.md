# 执行任务

本文件是本功能任务状态唯一来源，无任务数据库。

- [x] DOC01 2026-10-21按用户本地修订的MANUAL-WRITING-GUIDE重写README与交付手册：保持十节结构、正式v0.2.1/0950109/D盘安装及既有四模板；README收敛为快速入门。DSH章节覆盖web/desktop/multica，YAML前先检查全部文件、唯一相邻备份再打开，说明空列表/已有patch/同实例合并、DSH_HOME、宿主重启和权限边界；补充Claude双配置位置打开命令，Claude-3p仍非已验证适配。模板/JSON/TOML/YAML、相对链接、13段PowerShell语法、临时假profile的6份独立备份/原文不变及缺失profile无部分副作用检查通过；重写阶段未运行真实Host配置修改、收费调用、提交推送或发布；后续用户已授权连同修订指南提交dev、PR、Windows CI与审查后合并并复验合入CI，实际结果留在对应PR，不预填未来通过。用户已修改的指南按授权纳入本轮文档提交；三种完整DSH profile/Multica、GUI和Bash/Zsh运行未据此标为实测通过。

- [x] M01 2026-10-21现用服务从C盘0.1.0迁移至D:\MCP\zhenzhen-nanobanana-mcp的GitHub发布版v0.2.1（0950109）；.env仅升级密钥字段名且保留值/访问规则，保留10批次11图及防重指纹，映射新副本结果路径。Codex配置切换后用户重启，当前会话发现6工具、免费查询全部历史批次及逐文件核对通过；33个原始关键文件与备份未变。见docs/LOCAL-D-DRIVE-MIGRATION-ACCEPTANCE.md。
- [x] M02 2026-10-21追加授权的一次真实收费生成通过当前Codex会话完成：默认gemini-nano-banana-2.1、DALL·E Generations、单张白色马克杯，queued→running→succeeded，约25.39秒，PNG2048×2048，落盘D盘且解码/hash/视觉检查通过。只提交一次任务，不追加批量/编辑/重放或发布；未核对账单/全部网络POST，真实故障恢复仍未实测。
- [x] M03 本轮验收文档先以b409894提交推送dev，Windows CI39544644902通过后，按授权精确删除C盘旧安装及20261021-a3dba663迁移备份；旧虚拟环境权限不足经限定目录处理及UAC提权清理解决，两个目标确认不存在。删除后当前MCP查询10个旧批次及新任务全部成功，11张历史图片及新图hash/解码、两数据库完整性检查通过，D盘.env保留。其他验收目录/父目录未清理；实际清理结果补记提交，仅创建PR，不合并或发布。
- [x] M04 用户后续授权后PR #11合入23fe6062c491e0296e517e9793ee70fb9128d4b9；PR CI39544970155成功，main CI39545262939首轮隔离测试等待超时、同SHA未改代码/断言的第二轮11阶段及71测试成功，失败与复查记录留在PR。之后按明确授权删除两个无独有提交/无工作区占用的本地历史分支feature/async-image-tasks、migration/github-distribution；清理空备份父目录及独立v0.2.1临时验收目录，不扩大至其他私有资料。
- [x] M05 本地dev及远端dev均正常快进至main的23fe606，无强推；同步触发的Windows CI39549820598全部11阶段、71测试及秘密/依赖审计通过。核对时本地仅dev、远端main/dev同SHA，工作区干净；D盘运行副本仍为发布版v0.2.1（0950109），10批次及1新任务保留、两数据库完整性ok，Codex免费查询正常。详见docs/LOCAL-D-DRIVE-MIGRATION-ACCEPTANCE.md的后续归档；该对齐状态为本次新增文档提交前快照，本次归档PR/合入CI结果留在对应PR。不新增收费、不修改或发布Release，不补齐G06.5。

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

- [x] V021 2026-10-21版本同步为0.2.1，纳入D盘默认路径和最新验收文档，PR #8经审查及Windows CI后合入09501092c369e2a314df757eece5fa8d7a38e64e；同SHA main CI39534145510及受控CD39534393895成功，经release环境正常审批创建Release419087832草稿，四附件复核通过。原阶段仅建草稿、不收费，v0.2.0保持不变；后续公开按V021-PUB的新授权执行。

- [x] V021-PUB 2026-10-21用户另行授权核对后正式公开及独立安装/协议验收。v0.2.1于2026-10-21T02:52:58Z公开，四附件及标签不变；在D盘独立目录从GitHub正式标签clone、空缓存锁定无开发依赖安装通过，确认默认D:\MCP\zhenzhen-nanobanana-mcp及四模板、最新验收文档与发行物一致。双模式stdio、6工具契约及免费调用、配置/ACL保留通过，有效绘图提交和新增收费调用均0；v0.2.0元数据、标签及附件不变。见docs/RELEASE-0.2.1-ACCEPTANCE.md，不据此补齐G06.5故障恢复。

- [x] V030 2026-10-22用户授权先将本地/远端dev快进到main 856e362并核对同步Windows CI，再发布v0.3.0。版本、锁、README/MANUAL和发布说明按21工具/9 Resources/6 Prompts同步，经dev→PR→CI与审查→合并及同SHA main CI后受控创建草稿，核对再公开并独立验收。原最小DSH profile未通过、Desktop GUI未验证及历史业务证据全部保留；无新增收费调用，不更新现用Host/D盘安装，不修改旧Release。

  - 完成：PR #23合入c6121a7f142558aa53bc622505b4f1d1e17fcca2，main CI39711818265与最终dev同步CI39711828294通过；受控CD39712366288经正常release环境审批创建草稿，四附件核对后v0.3.0于北京时间10:46:29公开。正式标签在E盘独立目录安装，双协议21 Tools/9 Resources/6 Prompts及免费检查通过；旧Release和原始证据指纹不变，发布验收时现用D盘仍v0.2.2，无新增收费调用。见docs/RELEASE-0.3.0-ACCEPTANCE.md；公开后记录已通过V030-ARCHIVE归档，不修改已发布标签。

- [x] V030-UPGRADE 2026-10-22按用户授权将D:\MCP\zhenzhen-nanobanana-mcp从v0.2.2/d831573升级至正式v0.3.0/c6121a7。先确认无活动任务、停止目标MCP进程并验证私有备份，再固定标签checkout和锁定无开发依赖安装；smoke与额外禁止外部网络的双协议21工具/9资源/6提示检查通过。原.env/ACL、Host配置、5任务（4成功1原失败）、10批次及35文件摘要不变，15张图片哈希/尺寸/解析通过；无新增收费调用或Release修改。备份和原始证据保留；后续当前Codex会话已发现21工具并完成V030-LIVE。见docs/LOCAL-V0.3.0-UPGRADE-ACCEPTANCE.md。

- [x] V030-LIVE 2026-10-22用户分阶段授权后，当前Codex会话依次完成1张主图、3张详情图、原图1次nano-banana-pro编辑及10项详情图，共15张新图片。异步提交92/63/67/93ms返回，3项和10项批次账本/MCP查询并发峰值分别3/5；15张1024×1024图片的字节/尺寸/解码/SHA256与原身份重放通过。重放POST计数分别1→1、3→3、1→1、10→10，任务/供应商键/图片不变；全账本5→6→10→20，历史记录保留。recovery_attempts=1是正常响应检查点也会增加的字段，不据此宣称故障恢复通过；供应商账单、GUI、全模型/变体等未验证项保持。见docs/LIVE-V0.3.0-ACCEPTANCE.md。DSH恢复连接为用户提供结果，Host配置观察按轮次记录；收费执行后仅脱敏归档，不新增收费或Release。

- [x] V030-ARCHIVE 2026-10-22完成三份v0.3.0验收报告、002/003/007验证记录与本文件的脱敏归档：15行图片表及身份/重放/时间线/链接与凭据/私有路径检查通过。提交d6bbf6146bdaa89a2247176d419470ae20f96383经PR #24审查，dev CI39722278653和PR CI39722308337成功后正常合入main的861277c0f4517ad8f6869cf8b0ea2b85d5fe5720；同SHA main CI39722870001成功，三轮均165测试/11阶段通过。20条现用任务及128个受保护文件、D盘安装和既有Release保持不变，无新增收费调用。远端结果见docs/LIVE-V0.3.0-ACCEPTANCE.md第5节。

- [x] V030-DEV-SYNC 2026-10-22按用户授权将本地和远端dev从d6bbf61正常快进至main的861277c0f4517ad8f6869cf8b0ea2b85d5fe5720，无新提交/文件差异/强推；同步结束时本地dev、origin/dev、origin/main及实际远端main/dev同SHA，ahead/behind=0/0、工作区干净。同步触发的dev push CI39723976626精确HEAD核对成功，165测试、11阶段通过；20条现用任务、128文件、4个已有Release及D盘v0.3.0/c6121a7不变。原始证据和私有资料保留，无收费、Host修改或Release。该完成状态为后续文档归档前快照，不预填承载本条的新PR及未来合入CI状态；实际结果留在对应PR。
