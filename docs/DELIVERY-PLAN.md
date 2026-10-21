# 六步交付计划（2026-10-20修订）

适用本仓库0.2.0、本地stdio、Windows x64、Python3.12.14与uv。按用户修订，CI只验Windows，公开6个工具，Release先建草稿，人工核对后才正式公开。执行状态统一记在 [002任务](../specs/002-github-distribution/tasks.md)，本文件维护步骤及标准，不重复维护进度。

| 步骤 | 要做什么 | 完成标准 |
|---|---|---|
| 1. 提交前审查 | 刷新远端main，对照源码、测试、文档、流水线；检查秘密与私有资料。README.md和LICENSE放弃本地修改，以远端main为准。 | 明确提交清单，两文件与main的Git内容一致，秘密/本地生成物不提交。 |
| 2. 创建dev并上传候选代码 | 先在GitHub从最新main创建dev，再将已审查本地项目内容提交并快进推送到dev；通过后续dev→main PR申请合入。 | 远端dev先指向main基线，再包含完整项目提交；main保持原状，无强推。PR另行按授权创建。 |
| 3. 远端Windows CI与门禁 | 在dev push、PR和main合入提交上运行Windows quality：测试、构建、协议、安装及安全检查；失败先修复，落实main必需检查与评审。 | Windows quality通过，门禁在远端实际启用；不声称验证Linux。 |
| 4. 真实Host联调 | 在独立测试目录安装同一候选SHA，先Codex再DSH；发现6工具、调用免费规划和查询，不改现用服务。 | 两Host可发现实际工具并执行免费调用，记录Host版本、SHA及结果；命令行协议通过不能代替应用联调。 |
| 5. 小规模收费验收 | 预算和具体调用获准后先1张，再小批量及编辑；原(checkpointer,thread_id,task_id)重放不得新增提交，最后按预算验证10项；不对unknown盲目重试。 | 图片保存、队列恢复、防重及费用边界有真实记录，保留未确定项。当前没有执行此阶段的费用授权或预算。 |
| 6. 评审、合并、草稿及公开 | 评审通过且获合入授权后合并dev→main；等待合入SHA的Windows CI，审批后运行Release工作流，只创建草稿。核对版本、SHA、tag、资产哈希、CI及Host/收费验收后，再经明确授权公开。 | 已验证的Release先为draft=true；核对与最终公开是独立人工步骤，正式版公开后复验远端安装。 |

当前工具清单：`list_models`、`plan_ecommerce_images`、`submit_image_tasks`、`get_image_tasks`、`cancel_image_tasks`、`get_batch_result`，另有1 Prompt及1 Resource。11是工程检查阶段数，不是工具数；不新增占位工具。

“本地所有内容”指审查后应入库的源码、测试、锁文件、规范、手册、模板及流水线；`.env`、凭据、业务图片/SQLite、.venv、缓存、dist、ZIP和检查日志仍留本机并由.gitignore排除。默认分支保持main，dev是候选集成分支，不能将dev的CI代替最终main合入SHA的发布资格。

已获授权的范围包括修订计划/草稿流程、恢复远端README/LICENSE、创建dev及提交推送；用户后续另行授权了dev→main PR、Windows CI及main合并门禁。用户说明仅本人维护，授权本Agent代码审查通过后合并PR；采用审查结论留在PR、GitHub人工批准数为0的单人维护流程，同时保留必需Windows CI和其他main规则。2026-10-21用户进一步授权统一密钥字段后，在独立目录安装main并按Codex→DSH进行6工具发现及免费调用验证；不覆盖现用Host服务。收费调用及发布仍按后续阶段授权，不触发草稿或正式发布。具体完成状态见002/tasks.md。
