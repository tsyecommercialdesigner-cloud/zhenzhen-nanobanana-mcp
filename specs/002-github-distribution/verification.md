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
