# 整套模板验证记录

2026-10-21，Linux x64、Python3.12.14、uv0.12.23、PowerShell7.4.13。在原feat/ecommerce-design-workflow保留005–007工作并实现008，没有提交、推送、发布或改写私人Host/成员安装。

实际运行`.venv/bin/python scripts/check.py`退出0：format、lint、types、unit、coverage、docs、contracts、security、build、protocol、member-install共11项全部通过。结果为test-reports/checks.json与各阶段日志。142项测试中141通过，1项Windows注册表测试按Linux平台跳过；新增14项整套专项。

| 验收 | 实际证据 |
|---|---|
| PS01 | 19 Tools、7 Resources、4 Prompts在真实auto/legacy stdio发现；5套图Resources可读、12版式类型正确、3预设通过SuiteStyle校验；规划/复核Prompt可获取 |
| PS02 | 1主图+8详情+2SKU的11张提示，style_digest相同且共享风格区块逐字相同；主图/SKU为1:1、详情为3:4；字段不允许逐图style覆盖 |
| PS03 | 错HEX、空字体、非法字重、NaN、错误层级/越界比例、未知字段、错模板/顺序/ID、SKU遗漏/重复/未知、跨SKU事实与缺属性被拒绝；证据类别、禁用词和术语校验生效 |
| PS04 | 导出文本与真正送入受控Provider的prompt逐字相同，引用SHA也相同；持久摘要变化/面板与类型化方案不一致、model_copy绕过字段校验和超8000字拒绝；不保存过长可执行版本 |
| PS05 | 共享色值修改使新revision/digest和style_digest变化，旧批准/旧提交拒绝；缺需求、未确认或无收费授权不派发；SKU仅自身图与外观，属性统一顺序；重复同图保持11次原始派发 |
| PS06 | 三模型家族、2k分档、真实接口/端点与不支持组合拒绝；25张整套一次提交拒绝后按20+5成功，全部落盘、无遗漏、共25次派发，仍使用同一规范 |
| PS07 | auto/legacy真实stdio分别完整构造→拒绝未确认提交→确认→3类各出1张→等待/导出→重复提交，唯一派发标记仍3；实际schema导出一致，完整JSON示例同时通过JSON Schema和Pydantic；原设计/复刻/队列测试全部回归通过 |

新suite模块父进程语句覆盖率97%，suite编译器100%。安全审计未发现已知依赖漏洞，源码凭据扫描通过；wheel/sdist构建、空缓存无开发依赖重复安装与隔离.env内容/权限保留通过。文档与user-files交付输入同步。

所有绘图均为受控替身，真实收费调用0；没有证明实际模型能实现完全相同字形、颜色或构图，没有运行Windows CI或实际Host界面验收。跨图审美、文字/字形、商品忠实度需Agent看实际结果并由用户验收，工具不自动收费重画。

复现完整检查需将本环境PowerShell目录加入PATH，并使用/workspace可写缓存（见005/007验证记录）。专项：`uv run --no-sync python -m unittest discover -s tests -p test_suite.py`。用户说明和示例见docs/PRODUCT-SUITE.md与examples/product-suite.json。
