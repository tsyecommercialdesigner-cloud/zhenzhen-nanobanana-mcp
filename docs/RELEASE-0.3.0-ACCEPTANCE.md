# v0.3.0 正式发布与独立安装验收（2026-10-22）

## 发布与分支

[v0.3.0](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/releases/tag/v0.3.0) 已于北京时间2026-10-22 10:46:29正式公开，非草稿、非预发布。Release ID为420254387，轻量标签固定指向 `c6121a7f142558aa53bc622505b4f1d1e17fcca2`。发布完成时本地dev、origin/dev与origin/main均为此提交；这是当时快照，不要求后续文档提交保持同一HEAD。没有修改或重复发布v0.2.0、v0.2.1、v0.2.2。

先将dev快进到原main 856e362，同步[Windows CI39710226705](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39710226705)通过。按用户确认准备v0.3.0，版本/锁/运行版本和21工具文档经[PR #23](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/pull/23)审查及两项Windows quality后正常合并。再次快进本地/远端dev到发布提交，最终[main CI39711818265](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39711818265)与[dev同步CI39711828294](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39711828294)均成功；main报告为165测试、11阶段全部通过。

[受控CD39712366288](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39712366288)再次完成165测试和11阶段检查，经维护者账户正常release环境审批创建新标签及草稿，没有绕过门禁。草稿资格、包版本、空密钥模板和哈希核对通过后，按本轮已授权范围正式公开。未发布PyPI或额外成员ZIP。

## 附件核对

草稿下载核对及公开后API摘要一致，附件未替换：

| 附件 | SHA256 |
|---|---|
| zhenzhen_nanobanana_mcp-0.3.0-py3-none-any.whl | e9559429a27d9f79ab3bf6fc40d787e65562af0636d786dddecd38d3c6cddabb |
| zhenzhen_nanobanana_mcp-0.3.0.tar.gz | 95da6ed93ded5163fc68061fe1c5a273a2ac1fa4390b5bd11f247b4b99ef3d4b |
| SHA256SUMS | 047518037448ee6b496619c1984d021d9025172659487a1ed96e33856612487a |
| release-eligibility.json | d8807e03dcf7772bd0f2febc7c33c7b6941b5580fdc21f914bb1cc9331b5f9ba |

资格记录的tag/version/完整SHA及main CI精确对应，SHA256SUMS只覆盖当前wheel和sdist。检查包内元数据及运行版本为0.3.0；包不含真实.env，.env.example的唯一有效配置项为空密钥字段。旧三个Release的正文、发布记录和资产ID/名称/大小/摘要/更新时间与发布前基线一致。

## 正式发布版本的独立安装

正式公开后，使用维护工作区已审查的 `scripts/install-from-github.ps1 -Tag v0.3.0 -InstallRoot <独立父目录>`，从GitHub正式Release读取资格/CI记录并clone实际标签。实际独立目录及其完整原始证据保存在本机私有验收位置，不将机器专属路径写入公共报告。

安装项目在其同名子目录，使用新专用uv-cache与独立.venv，执行 `sync --locked --no-dev`，不是复用开发安装。标签SHA与发布记录一致；运行Python3.12.14、发行包0.3.0，mypy等开发依赖未安装。默认模板仍指向 `D:\MCP\zhenzhen-nanobanana-mcp`，此次实际安装在E盘独立目录，没有更新现用D盘。

安装器实际执行假配置协议检查，两种模式均status=passed：协议2026-07-28与兼容2025-11-25，21 Tools、9 Resources、6 Prompts，受控业务网络计数0；包含免费规划/查询、输入错误及空文件密钥拒绝回退。此为正式标签安装与协议验收，不是GUI、绘图质量或新增真实Host模型推理。

没有复制真实凭据，独立项目未创建.env或outputs/tasks.sqlite3；未发起有效绘图任务。安装stdout/stderr与acceptance.json保留在本机独立验收目录。草稿下载包、哈希、CD/CI报告、公开后核对和保护指纹均保留在本机忽略目录，不随文档入库。

## 保护与未验证项

发布验收时，原始DSH随机测试图、旧色块、原会话/预检报告、隐藏答案、原有Host结果及协议报告的指纹一致。现用Desktop/Codex配置和D盘.env指纹一致；当时D盘安装HEAD仍为v0.2.2的 `d831573e659bc2a8bf45689d6c1a0b9ce585e5cd`。该阶段没有删除验收证据或改动现用Host。

保留[原最小DSH profile看图未通过](HOST-VALIDATION-PR19.md)的历史结果；[独立CLI补齐附件及视觉路由后Agent看图通过](DSH-VISION-HOST-VALIDATION.md)，Desktop GUI和现用完整profile仍未验证。历史16图为7图Agent通过、9图需修订，不等于全部可上架。全模型/变体及真实故障恢复等未覆盖项不因发布而补齐。

发布验收阶段新增收费调用0，没有修改现用Host配置、更新D盘安装或改动旧Release。后续另行授权的[D盘升级](LOCAL-V0.3.0-UPGRADE-ACCEPTANCE.md)及[当前会话真实绘图验收](LIVE-V0.3.0-ACCEPTANCE.md)按各自记录区分；后续文档归档不回写已发布标签或附件。
