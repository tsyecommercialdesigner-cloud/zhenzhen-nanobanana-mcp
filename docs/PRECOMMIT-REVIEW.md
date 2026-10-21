# 提交前审查与dev导入清单（2026-10-20修订）

本文件记录首次审查及后续用户修订后的实际提交边界。状态来源为 [002/tasks.md](../specs/002-github-distribution/tasks.md)，修订后的六步计划见 [DELIVERY-PLAN.md](DELIVERY-PLAN.md)。

## 已确认的基线和授权

- 仓库 `https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp.git`，默认main，基线 `ce7ce74a357782fcda820174c60a9c41090d7fa9`，原树只有README.md、LICENSE。
- 用户已授权先在GitHub从main创建dev，再把本地审查后的完整项目提交推送到dev。远端dev已首先创建在上述main基线上，本地切换dev跟踪origin/dev；没有重指main或强推。
- 用户明确放弃本地README.md及LICENSE；已从origin/main恢复并核对Git内容一致。两文件不列为本轮变更，详细安装/使用说明保留在MANUAL.md。
- 最终范围为 **69个新增文件、0修改、0删除**，包括本报告和修订计划。第一次审查曾有69项（含README修改），后续以本清单取代，不按旧清单覆盖远端README。
- “所有内容”是应入库的项目文件，不包含真实.env、凭据、私有Host、图片、SQLite、.venv、缓存、dist、ZIP或检查日志。dev上传本身未自动授权其他阶段；用户随后已单独授权PR/Windows CI/main门禁，Host配置/收费/合并及正式发布仍须后续授权。

## 首次发现的处置

| 标识 | 当前结论 |
|---|---|
| R01 CI平台 | 用户已明确只要求Windows，撤销旧Linux差额要求。CI保留windows-latest，运行dev push、PR及main push的quality；Windows Junction用例保留，不删除覆盖。 |
| R02 工具数量 | 用户确认实际6工具；契约/手册相符，另有1Prompt/1Resource。不增加占位工具；工程11阶段与工具数量分别记录。 |
| R03 草稿发布 | release.yml已改为gh release create --draft --verify-tag，不自动转公开。新增/加强隔离检查确保草稿flag存在、无自动edit公开，安装器在下载/安装前拒绝草稿。最终人工核对及公开流程见RELEASE.md。 |
| R04 门禁 | 初始main无保护/ruleset/release环境；随后按用户单独授权已启用main规则集25471021及PR #1，实际参数和验证见RELEASE.md与002/verification.md。release环境和标签保护仍为发布前阶段；本次未合并或发布。 |
| R05 上游证据 | API-ENDPOINT.md引用的validation/2026-10-20原始报告缺失，未补造或执行收费探针，003验收记录保留限制。 |
| R06 维护说明 | RELEASE.md、MANUAL及002规范/任务已同步dev、Windows、6工具、先草稿后核对公开。历史验收记录保留原日期事实，不把本地结果改写为远端成功。 |

## 检查与秘密边界

已有秘密/私有数据扫描、Git空白及忽略正反例通过，候选全为文本，无图片或数据库。唯一凭据模板为.env.example中的空ZHENZHEN_NANOBANANA_API_KEY；API图像URL/base64为脱敏占位。硬编码api_key均为not-real安全测试值。模式扫描不保证识别所有秘密，提交前还需核对staged清单和源码包。

本轮因workflow、测试与README来源变更，重新运行本地统一11阶段入口，并在推送前核对结果：format、lint、mypy、unittest/coverage、docs、contracts、security、build、protocol、member-install。本轮11阶段全部退出0，68项unittest通过，99个适用依赖审计0已知漏洞/0跳过。独立空缓存运行安装和测试.env内容/NTFS权限保留通过。源秘密扫描不读取或打印真实密钥，协议/安装使用隔离假配置，无收费业务调用；本地通过不代表真实Codex/DSH、收费上游、远端CI或正式Release已通过。

README/LICENSE直接保留远端版后，check-docs对正式Release链接的断言改查MANUAL，仍验证详细安装说明/模板；不要求改写用户指定保持原样的README。依赖声明、uv.lock及Python3.12.14保持锁定，启动不安装依赖。

## 最终提交清单

以下相对origin/main均为新增，LICENSE与README.md继承main保持不变。检查生成物不提交。

### 根目录与依赖（11）

| 状态 | 路径 |
|---|---|
| A | `.env.example` |
| A | `.gitignore` |
| A | `.mcp.json.example` |
| A | `.python-version` |
| A | `AGENTS.md` |
| A | `CLAUDE.md` |
| A | `CONVENTIONS.md` |
| A | `MANUAL.md` |
| A | `pyproject.toml` |
| A | `user-files.json` |
| A | `uv.lock` |

### 流水线（3）

| 状态 | 路径 |
|---|---|
| A | `.github/pull_request_template.md` |
| A | `.github/workflows/ci.yml` |
| A | `.github/workflows/release.yml` |

### 运行源码（11）

| 状态 | 路径 |
|---|---|
| A | `src/zhenzhen_nanobanana_mcp/__init__.py` |
| A | `src/zhenzhen_nanobanana_mcp/__main__.py` |
| A | `src/zhenzhen_nanobanana_mcp/config.py` |
| A | `src/zhenzhen_nanobanana_mcp/media.py` |
| A | `src/zhenzhen_nanobanana_mcp/models.py` |
| A | `src/zhenzhen_nanobanana_mcp/planning.py` |
| A | `src/zhenzhen_nanobanana_mcp/provider.py` |
| A | `src/zhenzhen_nanobanana_mcp/server.py` |
| A | `src/zhenzhen_nanobanana_mcp/service.py` |
| A | `src/zhenzhen_nanobanana_mcp/smoke.py` |
| A | `src/zhenzhen_nanobanana_mcp/tasks.py` |

### 测试与替身（6）

| 状态 | 路径 |
|---|---|
| A | `tests/stdio_task_fixture.py` |
| A | `tests/test_config.py` |
| A | `tests/test_delivery.py` |
| A | `tests/test_distribution.py` |
| A | `tests/test_service.py` |
| A | `tests/test_tasks.py` |

### 工程与交付脚本（12）

| 状态 | 路径 |
|---|---|
| A | `scripts/check-docs.py` |
| A | `scripts/check.py` |
| A | `scripts/delivery-common.ps1` |
| A | `scripts/export-contracts.py` |
| A | `scripts/install-from-github.ps1` |
| A | `scripts/package-user.ps1` |
| A | `scripts/release.py` |
| A | `scripts/security-check.py` |
| A | `scripts/smoke-test.ps1` |
| A | `scripts/sync-manual-templates.py` |
| A | `scripts/verify-delivery.py` |
| A | `scripts/verify-install.py` |

### Host模板（3）

| 状态 | 路径 |
|---|---|
| A | `templates/claude-code.mcp.json.example` |
| A | `templates/codex.config.toml.example` |
| A | `templates/dsh.patch.yml.example` |

### 项目文档（7）

| 状态 | 路径 |
|---|---|
| A | `docs/API-ENDPOINT.md` |
| A | `docs/DELIVERY-PLAN.md` |
| A | `docs/ENGINEERING-GUIDE.md` |
| A | `docs/MANUAL-WRITING-GUIDE.md` |
| A | `docs/PRECOMMIT-REVIEW.md` |
| A | `docs/RELEASE.md` |
| A | `docs/host-evidence.md` |

### 规范与验收历史（16）

| 状态 | 路径 |
|---|---|
| A | `specs/001-ecommerce-images/contracts/mcp.json` |
| A | `specs/001-ecommerce-images/contracts/upstream.md` |
| A | `specs/001-ecommerce-images/plan.md` |
| A | `specs/001-ecommerce-images/spec.md` |
| A | `specs/001-ecommerce-images/tasks.md` |
| A | `specs/001-ecommerce-images/verification.md` |
| A | `specs/002-github-distribution/plan.md` |
| A | `specs/002-github-distribution/spec.md` |
| A | `specs/002-github-distribution/tasks.md` |
| A | `specs/002-github-distribution/verification.md` |
| A | `specs/003-async-image-tasks/contracts/mcp.json` |
| A | `specs/003-async-image-tasks/contracts/upstream.md` |
| A | `specs/003-async-image-tasks/plan.md` |
| A | `specs/003-async-image-tasks/spec.md` |
| A | `specs/003-async-image-tasks/tasks.md` |
| A | `specs/003-async-image-tasks/verification.md` |

任务进度在002/tasks.md更新，最终远端dev SHA与CI链接以实际GitHub结果报告，不在提交内容中预造自身commit SHA。main合并和发布仍经后续PR/CI/评审流程。
