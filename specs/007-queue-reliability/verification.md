# 可靠性与容量验证

2026-10-21，Linux x64、Python3.12.14、uv0.12.23、PowerShell7.4.13。继续使用feat/ecommerce-design-workflow，保留005/006未提交工作。未提交、推送、发布或修改私人Host/成员安装。

最终 `uv run --no-sync python scripts/check.py`退出0，11阶段全部通过：format/lint/types/unit/coverage/docs/contracts/security/build/protocol/member-install。输出test-reports/reliability-full-gate.log、checks.json和各阶段日志均属于本次实际运行。

实际执行128项测试，127通过、1项Windows注册表测试在Linux按平台跳过。新增14项可靠性专项和1项三模型适配测试。最初协议检查发现批量上限替换误改等待时限断言，已恢复1200秒；最终完整检查重新执行并通过，未改变等待上限或降低断言。

| 要求 | 实际验证 |
|---|---|
| QR01 | 复刻覆盖三个真实模型家族的执行名称、接口及端点；已有2k/4k路由继续通过；Prompt/Resource/当前文档去掉旧模型导向。prompt_target与实际分档模型一致 |
| QR02 | 5个同时进行的同步MCP调用都进入受控Provider后才放行；同时登记20项异步任务立即返回，最后25项均完成且并发峰值恰好5。21项输入拒绝；15屏详情可单次提交，分批重放不重复出图 |
| QR03 | 旧字段指纹/旧SQLite schema构造后原任务复用成功；新增字段原地迁移；连接失败后重试保留Idempotency-Key；参考摘要不符时post_attempts=0，修正后原键继续；连接失败后原图变化仍用冻结副本 |
| QR04 | 2次连接失败后第3次成功、键不变；ReadTimeout和HTTP503均不盲目重发。GET失败9次后可显式按原响应恢复且POST仍1次；响应后关闭进程再启动仅下载；暂时输出写失败从检查点恢复且render仍1次 |
| QR05 | 文件篡改/缺失通过查询发现；修复需要repair_files；损坏字节保留在.corrupt备份，恢复后SHA与原输出一致。图片URL变为其他内容时连续重试均拒绝替换原摘要，恢复原内容后才完成；响应检查点篡改拒绝且不重新出图 |
| QR06 | 仅安全阶段重排，混入未知POST的批次整体拒绝；尝试数、恢复能力和文件状态公开；等待与取消回归及recovering重启通过 |
| QR07 | 3个独立进程、200任务按20项批量登记，共用一个WAL账本；渲染峰值5，200个唯一派发标记、200个校验成功输出、无丢失/重复，SQLite integrity_check=ok |
| QR08 | 两协议实际stdio执行20项同步生成与原任务文件修复，派发数仍20；17 Tools/2 Resources/2 Prompts发现、schema生成检查、空缓存源码包无开发依赖重复安装、假.env内容/权限保留及安全审计通过 |

SQLite本次负载报告test-reports/sqlite-load.json：jobs=200、processes=3、peak_concurrency=5、elapsed_seconds=1.381、duplicate_dispatches=0、verified_outputs=200、sqlite_integrity=ok。耗时包含本次本机进程启动和小图替身执行，不是供应商吞吐或大图片性能基准。元数据采用短事务，图像/大响应保存为本地文件，故当前本机目标继续使用SQLite；没有依据引入额外数据库。跨机器/网络盘、持续高写入和真实大图负载未验证，未来如需要再评估开源免费的PostgreSQL。

队列/Provider/文件完整性模块父进程语句覆盖率约94%，跨进程/stdio断言另以实际文件、任务状态和唯一派发标记确认，未合并子进程覆盖率。记录中不包含未执行的真实业务成功：供应商全部使用受控替身，真实收费请求0，未证明上游支持Idempotency-Key去重，亦未运行Windows CI或实际Host界面验收。

当前运行环境未显式设置NANOBANANA_CONCURRENCY/MAX_PENDING_TASKS/SAFE_ATTEMPTS，使用代码默认5/200/3。已有成员安装仍须在后续发布升级后使用新功能；本次未替用户改写旧环境配置或重启私人服务。

复现：按005验证记录初始化本环境缓存/PowerShell路径，运行 `uv run --no-sync python scripts/check.py`。独立专项：`uv run --no-sync python -m unittest discover -s tests -p test_reliability.py`；基准会生成本次新的sqlite-load.json，数值随机器而变。测试不需要真实密钥且禁止添加收费探针。
