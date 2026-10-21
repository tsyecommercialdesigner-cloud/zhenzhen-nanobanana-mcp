# v0.2.1 正式发布、D盘安装与协议验收

2026-10-21用户另行授权核对v0.2.1草稿，无误后正式公开，再从GitHub发布版本在独立目录安装及验收协议，重点核对D盘默认安装路径和最新验收文档；不得新增收费调用或修改v0.2.0。

## 发布及附件

- [v0.2.1正式Release](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/releases/tag/v0.2.1)，id419087832，published_at=2026-10-21T02:52:58Z，draft=false、prerelease=false。
- 标签/安装HEAD为09501092c369e2a314df757eece5fa8d7a38e64e；[main CI39534145510](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39534145510)和[受控CD39534393895](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39534393895)均成功。
- 公开前重新下载四个草稿附件，核对上轮已审资产id/digest、包版本、默认路径、验收文档、空密钥模板及包内安全边界；公开后再次下载，四附件id及digest不变，没有替换发行物或重指标签。

| 安装包 | SHA256 |
|---|---|
| zhenzhen_nanobanana_mcp-0.2.1-py3-none-any.whl | cfa79d4f0b1a45c8783e2d64f4bf60734ab3b7c7ecb9b7ab73e7a1c0b076a570 |
| zhenzhen_nanobanana_mcp-0.2.1.tar.gz | e33f5cd089016b790798ea9b5ac6e8720d46b9b59b34da8e7337c37663fdcba4 |

SHA256SUMS精确覆盖这两个包；release-eligibility.json的标签、版本、完整SHA及main CI匹配。四资产均与GitHub digest一致。v0.2.0的Release419061687元数据（含说明、更新时间）、全部附件id/digest/大小/更新时间和标签66555d72742cf54b98bd3dc4c57a94d3a98d7818均与本轮开始时相同。

## D盘独立成员安装

从正式GitHub Release验证后clone标签v0.2.1，实际目录为D:\MCP-v021-acceptance-20261021-c7b50eec\member-install\zhenzhen-nanobanana-mcp。这是显式指定专用父目录的隔离安装，不是覆盖现用D:\MCP目录。

- 对新clone中的安装器做PowerShell AST检查：默认InstallRoot精确为D:\MCP，拼接结果D:\MCP\zhenzhen-nanobanana-mcp，目录深度不变；四份Host模板的启动目录均一致。
- 独立空uv缓存、专用.venv，uv0.12.9、Python3.12.14，uv sync --locked --no-dev通过；模块及包元数据均0.2.1，依赖来自新.venv，ruff/mypy/coverage未安装。
- 新安装的[0.2.0正式发布验收](RELEASE-ACCEPTANCE.md)、[0.2.1候选说明](RELEASE-0.2.1.md)、Host/单张/小批量编辑/十项历史验收、任务及验证文档、三份Agent约定和手册指南，逐项与已核对sdist的文本一致；历史限制没有改写成新增实测。

## 无收费协议与配置

安装器smoke通过2026-07-28及兼容2025-11-25；均发现6工具、1Prompt、1Resource，配置空值和非法输入按预期失败。追加从无关Host cwd使用日常uv --directory <project> run --no-sync python -m zhenzhen_nanobanana_mcp入口连接，六工具inputSchema/outputSchema与发布契约精确一致。

免费模型查询、10项详情页规划、空任务查询及Prompt/Resource读取通过。submit_image_tasks只发送缺少tasks的非法输入；取消和旧批次查询只访问不存在的测试编号，均返回预期isError，没有有效绘图提交，任务仍为空。追加协议进程启用外部网络拦截，外部业务联网尝试0、新增收费调用0。

仅在专用安装创建测试.env，实际安装根文件优先于空进程变量及无关cwd文件；再次锁定安装保留.env字节/ACL和uv.lock。GitHub/包源的安装联网与业务联网分别记录。

原始证据留在D:\MCP-v021-acceptance-20261021-c7b50eec，包括prepublish-audit、public-assets、member-install.log、default-path-ast-check.json、extra-protocol-verification.log、release-install-verification.json、verified-public-release.json、v020-before/after.json及publication-final-check.json；不提交原始日志、环境或测试账本。正式Release说明同步结论。

本轮没有迁移现用D:\MCP安装或修改用户Host，也没有新增GUI、收费业务、真实故障重启恢复、全部模型/接口格式/变体测试。静态默认值验证、D盘隔离安装、免费协议及历史业务验收分别报告。
