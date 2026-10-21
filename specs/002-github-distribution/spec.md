# GitHub 源码分发迁移

依据：2026-10-20 用户提供的仓库及更新后的 AGENTS.md、两份指南。业务工具、模型、协议与凭据读取行为不变。

## 目标与场景

成员从 https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp.git 获取已发布、CI通过的固定版本，安装锁定运行依赖，再由本机Host启动stdio。维护者通过PR、CI和受控Release发布，ZIP仅保留既有可选工具。旧复制/ZIP安装不能直接当作Git工作区更新，迁移时保留私有.env、ACL及outputs账本。

## 验收

| ID | 可测试标准 |
|---|---|
| GH01 | origin准确，本地迁移分支保留已有代码和远端LICENSE；未授权不提交、推送、修改远端门禁或发布。 |
| GH02 | PR及默认分支push运行锁定安装、格式/lint/类型、40项既有行为测试、构建、秘密与依赖检查、无收费协议检查；失败非零。 |
| GH03 | 干净源码安装无需开发依赖，独立空缓存安装和协议通过；测试.env更新前后字节/ACL不变，不借用开发.venv。 |
| GH04 | 受控CD只允许默认分支工作流和已通过该分支CI的完整SHA，校验版本/tag/来源，拒绝覆盖旧Release，发布记录含SHA/CI/校验摘要；远程部署不适用。 |
| GH05 | MANUAL十节完整，真实仓库、发布状态、clone/安装/启动/更新/回滚/旧安装迁移、四Host及安全边界一致；无真实已验证tag时明确停止成员安装，不编造SHA或发布事实。 |
| GH06 | .gitignore保护秘密、本地outputs业务数据/缓存/构建结果，测试/fixtures/锁/CI/规范/指南可跟踪；源码包无私有配置。 |

## 初始事实与限制

远端main于开始迁移时为ce7ce74a357782fcda820174c60a9c41090d7fa9，仅README和LICENSE，无Release/CI记录、无ruleset。本地此前无Git。上述SHA不是可用MCP发行版。GitHub门禁、CI实际运行、首个Release及目标版本远端clone验收必须在获授权上传后另外验证；本地检查不能替代它们。

## 2026-10-20后续用户修订

CI验收只要求Windows，MCP公开6工具。远端先从main创建dev，再合入本地审查后的完整项目；README.md和LICENSE放弃本地版本，以main为准。Release CD先创建草稿，核对后另行授权人工正式公开。该修订取代首次审查中的Linux/11工具差额要求与直接公开流程；实际执行状态见tasks.md，六步标准见docs/DELIVERY-PLAN.md。

## 2026-10-21默认安装盘符修订

用户指定本项目默认安装目录改为D:\MCP\zhenzhen-nanobanana-mcp：仅变更盘符，仍是MCP父目录下的同名项目目录。安装脚本默认InstallRoot为D:\MCP，README/MANUAL及四Host共享模板同步；项目根目录仍按实际安装位置定位，不硬编码运行时根目录。历史验收路径保持原样，通用指南的C盘示例不作为本项目默认。已发布v0.2.0保持不变，旧脚本通过显式InstallRoot参数使用D盘；本轮仅提交合并开发分支，不新增收费调用、不发布版本。
