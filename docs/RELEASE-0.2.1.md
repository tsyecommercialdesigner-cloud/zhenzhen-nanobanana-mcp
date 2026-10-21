# 0.2.1 候选版本与草稿范围

2026-10-21用户授权：先将版本号更新为0.2.1，经dev→PR→Windows CI及审查后合入main，再复验同一合入SHA的main CI，经release环境正常审批创建Release草稿。暂不正式公开，不新增收费调用，不改动或重复发布v0.2.0。

## 本版内容

- 包元数据、模块版本及uv.lock项目版本同步为0.2.1；Python3.12.14与全部依赖版本保持不变。
- 纳入[PR #7](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/pull/7)的D盘默认安装目录：D:\MCP\zhenzhen-nanobanana-mcp。安装脚本父目录D:\MCP，四Host共享模板与手册对应同一路径，目录深度不变。
- 同步本机更新的AGENTS.md、CLAUDE.md、CONVENTIONS.md及手册指南，Windows默认盘符均为D；三份约定核心正文一致，既有安装路径不会被自动迁移。
- 纳入[0.2.0正式发布及独立安装验收](RELEASE-ACCEPTANCE.md)、最新任务状态和验证记录。既有[Host验收](HOST-VALIDATION.md)、[单张](SINGLE-IMAGE-ACCEPTANCE.md)、[小批量与编辑](BATCH-EDIT-ACCEPTANCE.md)、[十项](TEN-IMAGE-ACCEPTANCE.md)记录保留原版本、路径、调用次数和限制，不当作本轮新增实测。
- 包含既有发布资格根URL与精确安装包校验清单修复；本轮不改发布工作流、不新增业务功能或接口变更。

## 核验与限制

执行锁定安装及统一检查scripts/check.py，覆盖71项既有测试、文档/契约/秘密与依赖检查、构建、无收费stdio和独立无开发依赖安装。核对wheel/sdist的版本和内容、D盘默认路径、验收文档及SHA256SUMS；CI与草稿的最终SHA、run和资产以实际GitHub记录为准，不在提交前填入未来成功状态。

受控CD仅创建新的v0.2.1标签及draft Release；标签创建后可见，Release暂不正式公开，安装器仍拒绝草稿。只复用该verify产物，不替换v0.2.0的标签、资产或说明。

没有新增收费生成/编辑、真实Host GUI、D盘现用安装迁移或真实故障重启恢复测试。新版的静态检查/隔离协议及安装检查，与历史Host/收费业务证据分开报告；公开后正式Release安装验收须另行授权执行。
