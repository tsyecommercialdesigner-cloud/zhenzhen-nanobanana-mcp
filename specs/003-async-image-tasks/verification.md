# 2026-10-20 本地验收：新 API 与异步任务

环境：Windows x64、PowerShell 7、uv0.12.9、Python3.12.14、FastMCP4.1.0、MCP2.3.0。版本0.2.0，分支 feature/async-image-tasks，继承尚未提交的 GitHub 分发迁移。无提交、推送、合并、发布、真实绘图或运行副本更新。

## 验收证据

| ID | 已验证行为与证据 |
|---|---|
| AT01 | tests/test_service.py：七模型所有适用格式与有/无参考图的28种组合；非法模型/格式与Edits组合在请求前拒绝。tests/test_tasks.py：不支持组合整组无新增。四变体继承用户确认的基础限制，分辨率1024/2048边界与Flash-lite保持验证。 |
| AT02 | MockTransport检查URL、Bearer头、Generations image字符串数组、Edits重复image字段（无image[]）、无参考图仍multipart、response_format=url、Chat最小字符串与Gemini省略generationConfig；图片字段解析、纯文本/业务/内容/下载错误及无下载凭据泄露验证。 |
| AT03 | 10任务gate验证工具先返回再放行渲染；多实例/线程验证唯一抢占与共享并发。两个独立stdio子进程共享同一SQLite目录，两个协议模式各验证10任务、跨进程复用、并发2时gate前恰好2个请求标记、gate后恰好10个排他标记和成功结果，无重复派发。 |
| AT04 | 同三元组同内容复用、不同命名空间/线程隔离、内容冲突整组回滚、跨线程同时提交只新增一条；重启复用结果不重新加载参考图。未以供应商端exactly-once作承诺。 |
| AT05 | 模拟queued/preparing恢复、running转unknown且不重发；正常关闭inflight、过期owner发送前失权、缺少参考图无POST、网络超时unknown、结果落账失败由heartbeat修复unknown而不重发。原上游地址与新配置不同时queued不向新地址派发。 |
| AT06 | 任务schema、scope、筛选、分页/next_cursor、成功图片文件与元数据；混合失败/unknown/cancelled为MCP isError，queued/running查询成功，历史批次只读保留。 |
| AT07 | 每轮1–12、容量12–1000、并发1–10及默认4/200；容量满/冲突原子拒绝；preparing取消阻止POST，running取消unknown，其他Host取消后原等待退出前保留并发槽。 |
| AT08 | 真实SDK stdio：2026-07-28元数据模式与2025-11-25握手模式，6工具/1Prompt/1Resource、免费计划、输入/输出/错误；fake provider跨进程生命周期不联网。smoke验证空.env拒绝启动/不回退/不泄露。 |
| AT09 | MANUAL十节与四模板、README、当前契约、0.2.0元数据/锁、运行清单tasks.py、tasks.sqlite3忽略规则同步；docs/API-ENDPOINT.md的Git路径大小写已与实际文件一致，用户文档内容未改写。001契约保留历史并标明取代关系。 |

本地统一入口：`uv --cache-dir .cache/uv run --no-sync python scripts/check.py`。11阶段为格式、lint、mypy、unittest、覆盖率、文档、导出契约、秘密/依赖审计、sdist/wheel构建、真实stdio协议、独立成员安装。67项unittest通过；覆盖率仅记录，不新增降低门槛或用覆盖率代替行为验收。队列16项专项包含上述双进程测试。原始证据为本机忽略的 test-reports/checks.json、unit.log、coverage.xml、dependency-audit.json、protocol.log、member-install.log。

独立安装从0.2.0 sdist解包到临时目录，空专用缓存执行 `uv sync --locked --no-dev`，确认依赖来自新.venv且无mypy；异cwd读取项目私有测试.env覆盖进程假值。重复锁定安装保留测试.env字节及NTFS SDDL，然后运行两个协议版本smoke，业务请求0。开发环境和真实配置保留。契约导出也使用空临时输出目录，避免lifespan触碰业务队列。

## 未验证与交付边界

- 所有绘图与编辑使用替身，本次收费调用0。新API文档引用的 docs/validation/2026-10-20 原始报告未在仓库提供；不把文档历史描述当作本次现场验证或账单核验。四变体、Chat/Gemini多模态与Generations参考图编码保留为待收费验证的兼容映射。
- 本次未做四Host GUI、真实上游、Linux/macOS、网络文件系统或不同机器共享SQLite验证。不保证精确输出尺寸、费用、退款或供应商网络侧exactly-once。
- SQLite只在同一实际输出目录共享本地队列；多个Host需配置相同并发。MCP关闭期间不执行，心跳租约30秒，重启仅恢复明确未发出任务。命名空间不是多用户认证。
- C:\MCP运行副本、用户.env/ACL、Host配置、现有业务账本未修改；无新成员ZIP。GitHub迁移G06仍待授权和实际远端CI/评审/发布，本地通过不等于GitHub Release已发布。
