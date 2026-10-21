# 仓库门禁与草稿发布

目标仓库：https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp ，默认分支main，候选集成分支dev。执行范围与六步标准见 [DELIVERY-PLAN.md](DELIVERY-PLAN.md)，任务状态唯一来源为 [002/tasks.md](../specs/002-github-distribution/tasks.md)。Windows是当前唯一CI平台；本服务公开6工具、1Prompt、1Resource。初始迁移保留远端README/LICENSE；用户随后授权重写README，现提供快速入门，MANUAL维护详细步骤，LICENSE继续保留。

## dev、PR与Windows CI

1. 先从实际main基线在GitHub创建dev，然后把本地审查通过的项目文件提交并快进推送到dev。本次已获创建dev及提交推送授权；不强推main，不把私有.env、图片、数据库、依赖环境或日志提交。
2. 锁定初始化 `uv sync --locked`，统一检查 `uv run --no-sync python scripts/check.py`。固定uv0.12.9、Python3.12.14、Windows x64；不宣称支持Linux验收，也不为满足旧计划删除Windows Junction测试。
3. CI在dev push、所有PR及默认分支push运行Windows的quality作业。包含格式、lint、类型、测试/覆盖率、文档、契约、秘密/依赖风险、构建、无收费stdio与独立安装。日志及coverage.xml保存在test-reports并上传14天；无路径过滤或允许失败继续。
4. 当前 [dev→main PR #1](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/pull/1) 使用 [main-pr-windows-quality规则集25471021](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/rules/25471021)。规则仅匹配refs/heads/main、active、bypass_actors为空，要求PR、全部评审讨论解决、严格跟随最新main基线，并绑定GitHub Actions（integration_id=15368）的必需quality；禁止强推和删除。

   用户于2026-10-20明确说明只有本人维护，并授权本Agent审查通过后合并。因此采用单人维护流程：GitHub required_approving_review_count=0、require_last_push_approval=false；审查结论与受审SHA写入PR review/comment，由维护者的直接授权允许合入。此AI审查不冒充第二个GitHub账号的APPROVED，也不是GitHub可自动强制验证的人工审批。保持PR、Windows CI和其他规则，不用--admin或添加绕过身份。多人维护时可经授权恢复独立账号审批；Windows CI及代码审查仍不代替真实Host/收费验收。

5. Token默认只读，PR无业务密钥，第三方Actions固定完整SHA，不执行高权限pull_request_target。开发分支通过不能代替最终main合入SHA的发布资格。

## Release只创建草稿

2026-10-21用户明确授权：审查本地改动，提交推送dev、创建PR，Windows CI和审查通过后合并，复验main并创建Release草稿；不正式公开。已建立release环境（id24873880407），required reviewer为唯一维护者tsyecommercialdesigner-cloud，prevent_self_review=false，允许其按直接授权完成正常审批；不是独立第二账号审查，也不使用管理员绕过。deployment branch policy仅允许main。

已建立active标签规则集release-tags-immutable（id25518329），匹配refs/tags/v*，禁止更新/删除、bypass_actors为空；不禁止首次创建，CD获release审批后创建新tag。现有资格脚本读取环境reviewer规则，缺少保护即停止。已配置门禁不等于已经执行工作流，具体run、tag、草稿及最终SHA以GitHub实际记录为准。

1. PR经评审及明确合入授权后合并，等待同一完整SHA在main的push CI全部成功。不得借用dev或合并前PR的结果。
2. 在默认分支手动触发Release workflow_dispatch，输入已合入SHA。受信任默认分支代码先验证40位小写SHA、默认分支祖先关系、该SHA成功的main push CI、quality及所有job成功、X.Y.Z版本及不存在的vX.Y.Z，再checkout目标、锁定安装并重跑检查。
3. verify只读，publish等待release环境审批才取得contents:write。此job名称沿用publish，但行为只创建不可覆盖的新tag与 **draft Release**，`gh release create --draft --verify-tag` 不正式公开Release；不会调用自动转公开命令。
4. 草稿使用同一verify产物：wheel/sdist、SHA256SUMS、release-eligibility.json及说明中的完整SHA、CI URL。tag在此阶段已经创建并可见，草稿Release不作为成员正式发行版；安装器明确拒绝draft/prerelease，不因tag存在跳过Release资格检查。不发布PyPI或远程部署。
5. 保留草稿URL，由维护者核对版本、tag指向、完整SHA、main CI、Host/收费验收记录、SHA256SUMS所覆盖的包哈希与验收JSON，确认无秘密或业务资料。核对通过并另获正式公开授权后，才在GitHub编辑该草稿并选择Publish release；不能在生成草稿的同一自动步骤直接公开。
6. 正式公开后从实际远端tag在独立目录clone，核对SHA、锁定无开发依赖安装及smoke，并追加发布证据。现阶段这些远端发布行为尚未执行；本地sdist安装不是正式发行证据。

如果tag已创建而草稿创建失败，停止并保留日志/产物，不重指tag。是否恢复同一产物的草稿或发布新版本需明确决定。不得为重跑而覆盖已发布tag/Release，人工最终公开也不得替换已核对资产。

## 回滚与旧安装

按MANUAL第5节保留.env/ACL、图片、tasks.sqlite3与batches.sqlite3，再切回已记录的SHA、安装该锁及复验协议。0.1不处理新任务队列，保留数据，勿用reset --hard、clean -fdx或删账本绕过问题。

main初始SHA ce7ce74a357782fcda820174c60a9c41090d7fa9只有README/LICENSE，不能当作可用MCP版本。目前README提供已通过CI的完整SHA试用路径；正式Release安装器仍拒绝草稿/缺失Release，tag存在也不改变这一点。本轮草稿创建授权不包含最终公开；门禁、CI、tag与草稿是否已生成按实际GitHub记录报告。
