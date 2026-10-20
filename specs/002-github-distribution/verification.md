# 2026-10-20 本地迁移验收

Windows x64、PowerShell7、uv0.12.9、Python3.12.14；业务FastMCP4.1.0/MCP SDK2.3.0未迁移。用户机器的.env、输出账本、Host配置及C:\MCP运行副本未修改。

## 实际检查

| 验收 | 结果与证据 |
|---|---|
| GH01 | 读取远端仓库，默认main，初始SHA ce7ce74a357782fcda820174c60a9c41090d7fa9仅README/LICENSE，无Release/CI/ruleset。本地关联origin、迁移分支migration/github-distribution，保留远端LICENSE及现有完整代码；没有提交/推送。新增文件使用intent-to-add供diff评审，不是提交。 |
| GH02 本地 | `uv --cache-dir .cache/uv sync --locked`及`uv --cache-dir .cache/uv run --no-sync python scripts/check.py`退出0。完整11阶段通过：format/lint/mypy、48项unittest/覆盖率、文档、注册契约、秘密/全组依赖、构建、stdio、独立成员安装。test-reports/checks.json、coverage.xml及各阶段日志为本机生成物，不进入Git。 |
| GH03 本地 | 独立临时目录从当前sdist解包，空专用缓存`uv sync --locked --no-dev`及重复安装均退出0。fastmcp来自临时.venv、mypy不存在，异cwd下私有测试.env覆盖进程假值；重装后.env字节与NTFS SDDL一致；两个真实子进程协议2026-07-28/2025-11-25通过，无收费业务联网。临时目录自动清理，开发环境保留。 |
| GH04 静态/隔离 | 两份workflow YAML解析及权限、完整SHA、受信任校验先于目标checkout、release环境门禁测试通过；release不接受错误SHA/分支/事件/CI结论，无评审环境直接失败。installer无Release时不创建目录；VerifyOnly处理二进制JSON验收资产并不安装。尚未执行GitHub实际工作流/发布。 |
| GH05 | MANUAL十节重写，仓库URL/Release状态/clone核验/锁定运行安装/启动/升级回滚/旧安装保留/四Host及可选ZIP一致。四模板逐字同步、JSON/TOML/YAML检查通过；全部PS脚本及手册11个PowerShell代码块离线解析通过，不修改用户配置。DSH按新版指南改为desktop/web，未声称实际Host已联调；Claude-3p不支持，配置清单明确不适用。 |
| GH06 | 正/反例git check-ignore通过，秘密、环境、UUID批次/账本、缓存/构建/报告被忽略，tests/fixtures、锁/指南/CI/规范/.env.example及outputs模板可跟踪。秘密候选扫描通过。源码包含LICENSE，无真实.env或业务数据；已有ZIP未改。 |

首次统一检查在依赖审计阶段遇到PyPI TLS连接超时，明确失败并停止；保留原因，未绕过。将读取超时设为60秒后重新检查通过。初始Pillow12.0.0有19项已知公告（例如PYSEC-2026-3493，修复版本12.3.0），按风险检查要求精确升级Pillow12.3.0并同步锁；其他业务依赖未升级。新增开发工具coverage7.10.6/mypy1.18.2/pip-audit2.9.0/PyYAML6.0.3。最后严格审计99个适用依赖，0已知漏洞、0跳过；不代表将来没有新公告。

第三方Actions通过官方仓库Release元数据、git ls-remote及action.yml核对，使用node24运行时：checkout v7.0.1=3d3c42e5aac5ba805825da76410c181273ba90b1；setup-uv v10.3.0=1c37ad07a6a961277cf70c0d37d6f313000f5884；upload-artifact v7.0.2=cf430e030ddbb5b0abf93d22962f4752f3646cd9；download-artifact v8.0.2=9000827ccba6bdab643e8b6fd33ac0654aef8333。更新这些pin后重新执行发行边界8项测试、文档及lint均通过；本地源安装不等于GitHub运行。

## 待授权及未验证

G06未完成：提交/推送迁移分支、创建PR、GitHub实际CI、独立评审/合入、分支与标签ruleset、release环境审批配置、首个正式Release及其实际远端tag clone验收。AGENTS要求“未经授权不提交、推送、合并或发布”，本次任务未明确授予这些操作。没有正式版本tag/SHA可写入安装说明，成员安装故意在无Release时停止。

完整Git版本切换升级/回滚、四Host新版本业务联调、Linux/macOS及真实收费出图未在本次验证；只验证了独立运行安装和测试.env重装保留，不把它们称为远端发布成功。该项目是本地stdio，服务端远程部署CD不适用；版本发布CD适用但尚未触发。

## 2026-10-20：用户修订及dev导入

用户明确CI只验Windows、公开6工具、先建Release草稿核对后再公开，并授权先从远端main建立dev，再提交推送本地完整项目；README/LICENSE采用main版本。远端dev先创建于ce7ce74a357782fcda820174c60a9c41090d7fa9，随后cb78329bcf6574144a763e39f2c18fb61db7d035上传69个新增文件；GitHub compare证实无README/LICENSE变化，main保持原SHA。六步计划位于docs/DELIVERY-PLAN.md。

导入前重新执行统一11阶段，68项测试通过，99项适用依赖0已知漏洞/0跳过；无收费调用，独立安装保留测试.env和NTFS权限。工作流新增dev push CI及--draft发布，增加草稿安装拒绝/发布边界检查；README被用户指定保留，详细Release链接验证移到MANUAL。

首次上传的远端CI与Release工作流在解析阶段失败、jobs为空：ci第22行及release第31行的作业级env不允许runner.temp。实际失败链接分别为 https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39412075880 和 https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39412077017 。已按GitHub官方context availability规则将缓存初始化移至runner步骤，用RUNNER_TEMP写入GITHUB_ENV，并增加job env禁止runner上下文的回归检查。保留首次失败证据，不把本地YAML解析通过当成远端工作流通过。修复后实际CI以GitHub运行结果为准；未触发草稿或正式发布。

修复上下文后的dev提交1c3cd7991284eb5fc22e9a7c5bcc3cb42e9d1baf已正常进入Windows quality。运行 https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39412342771 的前10阶段通过，最后member-install因临时路径含RUNNER~1短名、断言直接比较短名与服务解析后的长名而失败。本机GetShortPathNameW复现：原始Path不等而resolve后相同。verify-install改为先规范化临时根目录，并将所有路径断言按resolve后的真实位置验证、附具名错误，未移除凭据/项目根/.venv隔离/mypy缺失/ACL保留检查。强制子进程TEMP/TMP使用真实8.3别名后重跑空缓存独立安装及两个stdio协议成功（exit0，business_calls0）。后续远端CI需以修复提交实际运行结果确认，不借用前一SHA结果。

## 2026-10-20：PR #1及实际main合并门禁

用户明确授权创建dev→main PR、落实Windows CI与合并门禁，要求不合并、不发布。创建普通OPEN PR https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/pull/1 ，head=dev、base=main、初始head SHA=3bfa17d43aa7cd06a7131fc5e8eba86b919b68cd；已关联当前Codex任务。原dev push CI运行39412877780成功，新的pull_request事件Windows quality运行 https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39413479488 同样成功，不拿dev push结果冒充PR运行。

远端创建并启用规则集25471021，名称main-pr-windows-quality，链接 https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/rules/25471021 。条件仅refs/heads/main；enforcement=active、bypass_actors=[]。实际规则包含deletion、non_fast_forward、pull_request、required_status_checks：至少1批准、推送后撤销旧批准、最新推送需其他账号批准、所有评审讨论解决；必需quality绑定GitHub Actions app/integration 15368，strict_required_status_checks_policy=true。

已读取rulesets/25471021、rules/branches/main及branches/main进行只读核验，main.protected=true、实际四项规则均来自该ruleset；rules/branches/dev为空。CI成功后PR仍OPEN、mergeStateStatus=BLOCKED、reviewDecision=REVIEW_REQUIRED、autoMergeRequest=null，证明当前仍受评审门禁约束。没有通过试推main、试合并、删分支等写操作测试门禁，没有添加管理员或机器人绕过。仓库协作者目前只有PR作者一个，需另一个有权限账号完成独立审批；未邀请或私信他人，未降低评审数量。

main仍为ce7ce74a357782fcda820174c60a9c41090d7fa9，README/LICENSE与main一致；未配置/触发Release或收费验收。以上是此验证时点的实际PR与规则状态，后续文档提交会正常重跑dev/PR CI，最终head结果以PR实时检查为准，不预填未来SHA的成功结论。

## 2026-10-20：单人维护审查与合入授权

用户说明本仓库只有本人维护，并明确授权本Agent审查通过后合并PR #1；未授权发布。审查读取当前源码、相关spec/plan/contracts、模型与API矩阵、SQLite原子幂等/owner租约/取消/未知状态、参考图URL与本地路径边界、固定.env解析、stdio错误语义、测试、Windows CI及草稿Release资格检查，未发现阻塞当前源码合入的缺陷。受审业务实现与38885540c0f7b93fcbb6bfab8574b9a06eb4ca66一致，本轮变更仅同步单人维护政策及审查记录，不新增或更改绘图业务逻辑。最终合并须等待这些文档更新对应的PR Windows CI成功并将精确受审SHA写入PR review/comment。

既有PR Windows CI运行39413894145、dev push运行39413887898均在该实现基线上成功，包含68项测试、协议和独立安装等11阶段；原始上游validation资料、真实Codex/DSH及收费验收仍未验证。审查结论仅允许源码集成，不据此宣称完整业务交付或正式发行。未使用第二账号、未虚构独立APPROVED。

由于GitHub不能让PR作者批准自己的PR，按用户直接授权将本仓库改为单人维护：规则集25471021保留active、PR、strict GitHub Actions quality、讨论解决、禁强推/删除和空bypass列表；仅required_approving_review_count改0、require_last_push_approval改false。此调整是已授权的治理政策修订，不通过--admin跳过CI或添加临时绕过身份。正常合并须绑定已审SHA，PR真实合并状态及最终main SHA以GitHub记录为准，不在待合并提交中预填未来合入SHA。Release工作流不触发。
