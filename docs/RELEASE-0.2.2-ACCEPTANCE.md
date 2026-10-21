# v0.2.2 正式发布、独立安装与同步协议验收

2026-10-21用户授权核对v0.2.2草稿，无误后正式公开，从GitHub正式版本在独立目录安装并验收8工具及同步功能；不更新D盘现用安装，不新增收费调用，不修改已有v0.2.0/v0.2.1。本文件记录发布后的新证据，不回写已有标签或发行包。

## 发布与附件

- [v0.2.2正式Release](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/releases/tag/v0.2.2)，id419358665，published_at为2026-10-21T09:33:21Z（北京时间17:33:21），draft=false、prerelease=false。
- 标签和独立安装HEAD均为`d831573e659bc2a8bf45689d6c1a0b9ce585e5cd`；[PR #15](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/pull/15)、[main CI39571818062](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39571818062)、[受控CD39574567861](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39574567861)均已完成。main/CD的11阶段和81项测试为上一轮的远端证据，本轮另做下述发布安装及同步专项验证。
- 公开前重新下载四个草稿附件，核对包版本、8工具契约、同步源码/测试、候选说明、空密钥模板、安全边界、资格JSON及SHA256SUMS。公开后通过未认证HTTP重新取得正式Release及四附件，全部资产id/digest/大小/更新时间不变，下载字节与草稿一致。

| 安装包 | SHA256 |
|---|---|
| zhenzhen_nanobanana_mcp-0.2.2-py3-none-any.whl | 828f03a21f8352dd7089b465ebbf24bd6f281ab12637f6918f5df7f99b8b3c8d |
| zhenzhen_nanobanana_mcp-0.2.2.tar.gz | 5a0a6dcb3b58a3f957e1d7de5b8c15eb3ec573358e0ecca1da06ee0fbb7391cf |

SHA256SUMS恰好覆盖两个包；另两附件为SHA256SUMS和release-eligibility.json。后者精确关联上述标签、版本、完整SHA及main CI。未替换附件、重新构建公开包或重指标签。

## GitHub独立成员安装

独立验收根为`D:\MCP-v022-acceptance-20261021-d831573e`，实际安装位于其`member-install\zhenzhen-nanobanana-mcp`。这是单独创建的验收目录，不是现用`D:\MCP\zhenzhen-nanobanana-mcp`。

从GitHub的v0.2.2标签下载`scripts/install-from-github.ps1`，执行：

```powershell
pwsh -NoProfile -File 'D:\MCP-v022-acceptance-20261021-d831573e\install-from-github.ps1' -Tag v0.2.2 -InstallRoot 'D:\MCP-v022-acceptance-20261021-d831573e\member-install'
```

安装器查询正式Release、资格附件及精确main提交的必需quality，通过后从远端clone标签，执行锁定无开发依赖安装及双协议smoke，退出0。没有从开发工作区复制服务源码。下载的安装器与clone内同一文件按文本比较一致（Git Windows checkout换行符与HTTP源文件可以不同）。

- 独立初始空uv缓存、专用.venv，Python3.12.14、FastMCP4.1.0、MCP SDK2.3.0；模块与发行元数据均0.2.2，导入路径来自独立安装。ruff/mypy/coverage未安装；jsonschema作为运行依赖的传递依赖存在，不以其存在误判为安装了开发组。
- 只在验收clone创建无真实权限的测试.env，未复制现用密钥。测试文件值覆盖空进程变量及无关Host工作目录中的空.env；再次`uv sync --locked --no-dev`后，测试.env字节/ACL及uv.lock不变。
- 安装器smoke的配置空值、错误输入、免费能力和两协议检查通过；追加协议进程从无关工作目录使用日常`uv --directory <独立项目目录> run --no-sync python -m zhenzhen_nanobanana_mcp`入口。

## 8工具及同步功能

实际SDK客户端与真实stdio服务进程分别以auto和legacy模式验证，对应协议2026-07-28、2025-11-25。每种模式均发现以下8工具、1 Prompt、1 Resource，无额外工具；每个工具的inputSchema/outputSchema与发布clone内003/contracts/mcp.json精确一致。

| 工具 | 本轮覆盖 |
|---|---|
| list_models | 免费查询及sync_generation=true、最长等待1200秒 |
| plan_ecommerce_images | 免费3项详情页规划 |
| submit_image_tasks | 仅替身服务做与同步入口同身份的重放，验证reused且不增加分派 |
| generate_images | 正常入口仅非法等待参数；替身服务覆盖真正等待、落盘、重放、编辑及失败 |
| wait_image_tasks | 正常入口查询不存在任务报错；替身服务验证超时后续等与取消等待后恢复 |
| get_image_tasks | 正常入口空任务查询；替身服务在同步等待期间并行查询running状态 |
| cancel_image_tasks | 正常入口访问不存在的测试身份，按预期isError |
| get_batch_result | 正常入口访问不存在的测试批次，按预期isError |

同时读取ecommerce_brief Prompt及nanobanana://capabilities Resource。正常服务没有有效绘图提交，非法generate_images未创建任务。

同步行为采用发布clone中的`tests/stdio_task_fixture.py`替换供应商render，仅本地生成16×16测试像素图，外部网络被socket/DNS拦截。两种协议均通过：

- gate未释放时generate_images保持等待，同时get_image_tasks可返回running；gate释放后才成功返回落盘路径，文件实际存在且SHA256匹配。
- 等待期间通过submit_image_tasks重放及完成后通过generate_images重放均reused，不增加替身分派。
- 以已落盘本机图作编辑参考，nano-banana-pro显式1536×2048路由到nano-banana-pro-2k，结果endpoint=edits，输出落盘且哈希匹配。这只证明本地路由与队列契约，不是供应商编辑效果实测。
- 等待1秒到期返回isError及wait_timed_out，后台任务保留；取消只读等待后任务仍处于活动态，再次wait_image_tasks可成功取得原任务结果，没有重提。
- 终态失败返回isError且wait_timed_out=false，不伪装成功。每种模式替身分派恰好4次（正常、编辑、超时、失败），真实供应商调用0。

另在同一无开发依赖环境执行发布源码中的`test_sync_tools.py`，10项测试全部通过，耗时15.802秒，包含原子冲突、跨实例防重、混合终态、客户端取消和双协议等专项。此为额外隔离测试，不是本轮重新运行全部81测试。

追加协议及同步专项测试启用外部联网拦截，观测到外部网络尝试0、真实收费调用0。GitHub/包源安装联网与业务联网分开记录。

## 保留范围与证据

v0.2.0/v0.2.1的Release说明、更新时间、全部附件id/digest/大小/更新时间和原标签SHA均与本轮前快照一致。现用D盘安装HEAD仍为09501092c369e2a314df757eece5fa8d7a38e64e、模块0.2.1；.env、uv.lock、pyproject.toml和模块版本文件哈希未变。没有写入现用任务账本/图片或修改Host配置，也没有为了验收停止现用服务。

原始证据在独立验收根，包括releases-before.json、prepublish-assets、prepublish-audit.json、public-assets、verified-public-release.json、member-install.log、locked-reinstall.log、config-preservation.json、public-protocol.py、guard/sitecustomize.py、extra-protocol-verification.log、sync-specialist-tests.log、release-install-verification.json和publication-final-check.json。测试图片、账本、缓存及环境只保留本机，不进入Git或发行物。

本轮未验证真实Codex/DSH GUI长时间调用、真实上游出图/编辑质量或全部模型/格式/变体，也未做现用数据迁移和收费故障恢复。8工具发现、同步协议替身结果和真实收费业务能力分别报告。本记录是发布后的维护文档，不因此更改已公开v0.2.2包内容。

## 后续归档与现用安装授权

用户随后授权将本验收文档和任务记录经dev→PR→Windows CI及审查→合并归档，并复验实际main合入提交CI；之后才更新D盘现用安装到已公开v0.2.2。上述“现用D盘未修改”是本次独立发布验收阶段的历史结论。后续更新应先确认无活动任务，停止相关服务并备份，保留.env内容/ACL、任务账本及历史图片；按正式标签切换并锁定安装，免费验证8工具和历史查询。实际PR、合入CI和安装更新结果在对应PR归档，不预填成功、不修改或重复发布任何已有版本，不新增收费调用。
