# v0.3.1 发布说明

本补丁保留 v0.3.0 的 21 Tools、9 Resources、6 Prompts、模型路由、Python 3.12.14、锁定依赖及本地 stdio。默认安装仍为 `D:\MCP\zhenzhen-nanobanana-mcp`；密钥字段和已有任务账本兼容，公开工具契约不变。

## 修复内容

- SQLite 结构初始化成功提交后按物理文件身份缓存，避免每次任务写入和空闲轮询都重复建表/迁移；替换数据库文件后重新初始化。
- worker 生命周期保留无悬挂读事务的 WAL 连接，停止及元数据清理异常时释放；独立写事务及 synchronous=FULL 保持。
- 参考图冻结、响应检查点、图片原子发布的阻塞磁盘操作移出事件循环；收集图片前等待检查点，取消和重复取消均排空已开始的写入，保留 fsync、SHA256 和收费防重。
- Windows stdio 测试等待实际 Python 子进程退出再清理数据库。200 项负载通过首波屏障验证五槽占满，保留原峰值 5、上限 5、总截止及防重/完整性断言；检查子进程统一 UTF-8 保留可读失败日志。

## 证据与范围

[PR #26](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/pull/26) 已合入修复基线 `e0a80b53accce98ab8819e2812d871ceb23a1d7a`；[同 SHA main CI39733006271](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39733006271) 首次通过 170 项测试、11 阶段。三进程/200 项替身负载峰值 5、重复派发 0、200 输出摘要通过，SQLite 完整性 ok。保留旧 main/dev、首轮候选和本地负载失败，未放宽阈值或重跑失败 SHA；见[诊断记录](QUEUE-CI-REPAIR.md)。

上述基线不是最终 v0.3.1 标签。版本准备须经 dev → PR → Windows CI → 审查合并，再核对最终 main CI，受控 CD 重复检查并创建不可覆盖的新标签及草稿。核对同一产物、资格 JSON 和 SHA256SUMS 后按本轮发布授权正式公开；精确版本/提交/CI 由附件 release-eligibility.json 固定。

既有 [Host](HOST-VALIDATION-PR19.md)、[DSH 看图](DSH-VISION-HOST-VALIDATION.md)和[15 图真实验收](LIVE-V0.3.0-ACCEPTANCE.md)保持各自版本及范围。本轮仅免费隔离安装与协议验收，不新增收费调用，不据此补齐全模型/变体、真实故障恢复、原最小 DSH profile 未通过或 Desktop GUI 未验证等项目。

## 安装、升级与回滚

从正式 GitHub Release 安装固定标签，按[手册](../MANUAL.md)核对资格记录和 main CI，执行 uv sync --locked --no-dev 及双协议检查；草稿不满足成员安装资格。升级保留 .env、ACL、任务/设计/批次 SQLite 与图片；未知收费结果继续用原身份查询，不能换编号重提或清空账本。回滚到已记录版本并安装对应锁，不删除新数据。

本轮不修改现用 Host 配置、不更新 D 盘现用安装、不删除备份或原始证据，不修改 v0.2.0/v0.2.1/v0.2.2/v0.3.0。没有 PyPI、远程部署或额外成员 ZIP 发布。
