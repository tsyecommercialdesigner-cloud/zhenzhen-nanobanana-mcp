# v0.2.0 正式发布与成员安装验收

2026-10-21用户明确授权核对草稿、无误后正式公开，并从GitHub发布版本在独立目录安装和验证协议；不得新增收费调用。本记录不扩展收费验收范围，也不修改现用Host配置。

## 发布核对

- [正式Release v0.2.0](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/releases/tag/v0.2.0)，id419061687，published_at=2026-10-21T02:12:59Z；复核draft=false、prerelease=false。
- 标签和独立安装HEAD均为66555d72742cf54b98bd3dc4c57a94d3a98d7818；[该提交的main Windows CI39529835229](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39529835229)及[受控CD39530083752](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39530083752)均成功。
- 公开前重新下载四个草稿附件，对照上轮已审资产的id/digest、标签、资格JSON与包内文件；公开后再次下载，四个资产id/digest均未变化。没有替换公开后的包、校验清单或资格记录，没有移动标签。
- 源码包包含README、MANUAL、锁文件及收费验收报告，不含真实.env、图片、数据库、依赖环境或缓存；.env.example密钥为空。

| 安装包 | SHA256 |
|---|---|
| zhenzhen_nanobanana_mcp-0.2.0-py3-none-any.whl | 03e9219f03002d80d56285a94ae3cd4071ebc8e3052eaa4ced0f97e4572b0b40 |
| zhenzhen_nanobanana_mcp-0.2.0.tar.gz | d8e08c42388f7dcf324af5fe1837f66c9f637a54a8de1dc0bf48a54f55f1027f |

两个包哈希与SHA256SUMS及GitHub资产digest一致；release-eligibility.json的版本、标签、完整SHA及CI地址匹配。main后续9224cb4中的清单工作流修复没有回写本发行标签，历史修复见[RELEASE.md](RELEASE.md)。

## 真实远端安装与无收费协议

在独立父目录运行正式Release安装器，指定-Tag v0.2.0，安装器通过公开GitHub API核验正式版及CI后，从远端标签clone，完成uv sync --locked --no-dev。使用专用空uv缓存、项目独立.venv，uv0.12.9、Python3.12.14、FastMCP4.1.0、MCP SDK2.3.0；源码模块来自新clone，依赖来自该.venv，ruff/mypy/coverage均未安装。没有复制开发工作区或借用开发依赖。

安装器smoke通过MCP2026-07-28和兼容2025-11-25两种模式，均发现6工具、1Prompt、1Resource，输入错误及配置空值按预期失败；stdout由协议客户端正常解析。

追加验证从无关Host工作目录，经日常入口uv --directory <project> run --no-sync python -m zhenzhen_nanobanana_mcp启动实际clone：

- 6工具的inputSchema/outputSchema与发布版契约精确一致；模型查询返回7模型和正确默认模型。
- 免费规划10项详情页、空任务查询、Prompt/Resource发现及读取成功。
- submit_image_tasks仅调用缺少tasks的非法输入，确认isError且没有有效提交；取消和旧批次查询只访问不存在的测试编号，确认isError，复查任务仍为空。
- 仅在新安装创建无真实权限的测试.env，证明实际根目录文件优先于空进程变量及无关cwd内的空文件；重新锁定安装保留.env字节/ACL，uv.lock不变。
- 追加协议进程加载外部网络拦截器，未发生外部联网尝试；有效绘图提交0，新增收费调用0。GitHub/包源的安装联网与业务联网分开核验。

原始证据位于本机专用目录E:\temporarily-workspace\nanobanana-release-v020-20261021-e8836748：prepublish-audit、public-assets、member-install.log、extra-protocol-verification.log、release-install-verification.json及verified-public-release.json。原始日志和环境不入库；公开Release说明同步验收结论。

此轮仅验Windows成员安装和stdio协议，没有追加真实Host GUI、真实故障重启恢复、其它全部模型/接口格式/变体或供应商账单后台测试。安装协议通过不等于补齐这些业务验收。
