# Windows 队列与 stdio CI 修复（2026-10-22）

## 失败证据

- main `74e3e104a5253e889cd1e3e9471272b77c86f3ae` 的 [Windows CI 39726182926](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39726182926) 首次运行失败：165 项测试中 3 个错误，包括共享实例 10 项队列在原 5 秒截止前未完成、双 stdio 提交超时、清理临时目录时 `tasks.sqlite3` 的 `PermissionError [WinError 32]`。
- 先前 dev [39724803722](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39724803722) attempt 1 出现 stdio 查询超时；同 SHA 的 PR 成功及 dev attempt 2 成功不能覆盖上述失败。原始失败日志、checks.json 和对应成功记录保留在本机忽略的证据目录，未删改；本轮不重跑旧运行。

## 定位与修改

1. 每次写连接都检查 WAL、建表、迁移和建索引，空闲 worker 也重复进入结构写事务。假上游、两个实例和 10 项任务的 SQL 追踪中，结构检查从 73 次降为 2 次（每实例一次）。仅在结构事务成功提交后按设备号和 inode 缓存；每次访问仍校验路径，数据库物理文件替换后重新初始化。
2. 短连接反复成为最后一个 WAL 连接，关闭时反复执行 WAL 收尾。worker 生命周期保留一个已完成查询、没有悬挂读事务的只读连接；停止时 finally 释放，即使 owner 清理失败也不占用 SQLite。独立写连接、`synchronous=FULL`、原子落盘、全局并发及收费防重边界保持。
3. Windows venv launcher 与实际 Python 子进程退出存在先后差异。测试 fixture 记录实际 PID，清理通过进程句柄等待实际退出；清理失败时仅终止捕获的测试进程并报告失败，不忽略删除错误或按名称结束进程。新增回归模拟 transport 返回后 SQLite 仍被子进程占用。

SQL 次数是热路径证据；本机单次耗时不是 GitHub runner 的性能保证。原失败日志没有内核句柄跟踪，不能把所有历史超时都归为单一已证实的操作系统原因。

## 验证与边界

- 新增不重复建表、数据库替换后初始化、owner 清理失败仍释放连接、Windows 子进程延迟退出时正确清理四项回归。旧代码的热路径回归失败，日志保留；原共享实例 10 项和 auto/legacy 双 stdio 用例继续执行。
- 原 3 秒/5 秒截止、并发、防重和落盘断言不变；依赖、CI 阈值及公开工具契约不变。不靠重跑旧 SHA 获取成功。
- 本地与远端执行结果、审查 SHA、PR 和合入提交 CI 分别记录，不预写未来通过。全部测试使用假上游和临时数据库，不构成收费或真实 Host 验收。
- 私有资料、原始图片和证据、D 盘安装、任务数据、Host 配置及既有 Release 保留；本轮不收费、不更新安装、不发布。

## 本地执行结果

2026-10-22：`uv run --no-sync python scripts/check.py` 的 11 阶段全部通过，169 项测试通过（新增 4 项）；审查补齐关闭 finally 与 keeper 初始化异常清理后，类型检查和 20 项队列/stdio 定向测试通过。保护核对确认 217 文件摘要、20 条现用任务、D 盘安装提交和 4 个 Release 不变。远端 PR/CI 和最终合入状态将在对应 PR 留存，本条不预先宣称其通过。
