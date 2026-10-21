# 2026-10-21 同步工具本地验收

开发环境Windows、Python3.12.14、既有uv独立.venv和锁定依赖。未升级SDK/依赖、未修改SQLite表结构或业务指纹；元数据仍为0.2.1，未创建新版本或发布。新能力最初在开发工作区完成，正式v0.2.1及D盘现用副本仍为原6工具版；后续用户已授权按dev→PR→Windows CI及审查→合并并复验main CI归档，不自动更新运行副本。

## 检查结果

`uv run --no-sync python scripts/check.py`退出0，test-reports/checks.json的11阶段均exit_code=0：格式、lint、类型、81项单元测试/覆盖率、文档、注册契约、秘密/依赖审计、构建、双模式stdio及独立成员安装。pip-audit未报告已知漏洞。独立空缓存无开发依赖安装成功，测试.env内容/权限保留，business_calls=0。

| 验收 | 证据 |
|---|---|
| ST01 | tests/test_sync_tools.py的gate控制证明同步调用在渲染释放前不返回，查询可并行进行；成功后图片存在且SHA256匹配。参考图编辑继承pro-2k/edits路由，未另加HTTP调用路径。 |
| ST02 | 同步生成期间异步同身份提交返回reused；完成后改变等待时限的同步重放复用相同路径，替身render仅调用一次。跨实例复用不再渲染，冲突组不插入新项。原共享并发/10项测试继续通过。 |
| ST03 | 缺失任务、空数组、重复编号明确错误，不产生绘图任务；查询限定命名空间/会话。wait复用原get的完整存在性校验，不使用分页结果冒充整组完成。 |
| ST04 | MCP输入拒绝0、1201、bool、字符串和浮点等待值，提交前失败。1秒等待到期返回isError=true、wait_timed_out=true及活跃状态；之后只读wait取得成功且render仍一次。 |
| ST05 | 单独取消等待协程与实际MCP客户端取消generate_images调用均不取消worker；原任务继续成功，只读wait可取得文件。未强杀真实业务MCP进程，不能把此结果称为真实供应商断线恢复验收。 |
| ST06 | 混合succeeded/failed/unknown保留成功图片并返回isError；显式取消的终态任务返回cancelled、isError且wait_timed_out=false。 |
| ST07 | 新增10项同步专项测试通过；2026-07-28/兼容2025-11-25两模式的真实stdio子进程用文件gate及唯一fake-post marker验证生成超时、继续等待、同步重放只有一次替身派发。smoke发现8工具，免费/非法输入调用通过，注册JSON与当前实际导出逐字一致。 |

当前注册快照仍按既有检查入口生成到`../003-async-image-tasks/contracts/mcp.json`，新增等待输出为TaskWaitResult（TaskPage加wait_timed_out），旧submit/get/cancel工具签名保持；list_models增加同步能力和最大等待时限字段。

本地证据为test-reports/checks.json、unit.log、protocol.log、security.log、member-install.log及.cache/sync-tests.log，不作为Git业务资料提交。README/MANUAL相对链接和JSON/模板检查通过。

## 未验证与交付边界

没有真实上游收费生成/编辑或账单验证；所有新增出图测试均用替身。没有现用Codex/DSH/其他GUI联调、Host长时间等待稳定性或真实供应商故障恢复。没有修改用户.env、Host配置、现用D盘安装或已有任务数据。最初本地验收阶段未执行提交推送、远端CI、PR或Release；后续交付已获授权，实际远端CI及合入结果在对应PR记录，不预填为通过。本地通过不代表GitHub CI或已安装客户端已发现新增工具。

同步等待默认600、最大1200秒，包含排队时间。Host时限应更长；等待结束不等于任务取消，Host关闭整个服务则不能保持后台执行。可能已发出的任务依旧不自动重试，unknown须人工核对。
