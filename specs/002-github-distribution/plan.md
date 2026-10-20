# 方案

保留Python3.12.14、FastMCP及stdio，不自动迁移SDK。关联既有origin/main，本地migration/github-distribution分支以远端初始提交为父，保留工作树。CI主要平台Windows；其他平台尚未声明支持，现有Windows目录联接测试不冒充跨平台验收。

新增统一scripts/check.py：本地和CI相同命令，结果写入test-reports/；ruff、mypy、coverage/unittest、文档/模板及契约一致性、构建、stdio、源码运行安装。依赖检查用pip-audit扫描锁定导出的运行依赖，非零阻断，不忽略已知漏洞。源码秘密检查只扫描Git候选文件，禁止真实.env/私有配置及常见密钥形态，控制台只打印文件/原因；不把本地数据或缓存当代码扫描。工具仅加入dev组，运行依赖不无故升级。

锁定安装验收以构建sdist在临时父目录解包，空专用cache执行uv sync --locked --no-dev、smoke，验证运行依赖未借用开发环境及测试.env/ACL保留。CI的源码来自clean checkout；未上传前本地构建验收不能称为GitHub目标发布clone验收。

PR/push工作流用只读token，Actions固定核对过的SHA，uv固定0.12.9，Python3.12.14。稳定quality检查包含真实检查，不使用跳过/continue-on-error。workflow_dispatch发布接收完整SHA，仅默认分支工作流可运行，API验证同SHA默认分支push CI全成功，再重新检查/安装；publish作业使用release环境并独占contents:write。该环境需维护者设置required reviewers/tag规则，否则不得声称审批门禁启用。

手册以Release页面和受控安装脚本获取真实tag/SHA，核对CI/发布记录后clone；没有Release即停止。升级使用精确SHA/tag、检测dirty/untracked冲突、--no-overwrite-ignore，保留.env/outputs。旧非Git安装保留原目录，clone到新的同名项目目录父路径，转移私有数据前核对目标不存在，不清空旧环境。可选ZIP只说明既有显式命令，不重新生成/发布ZIP。
