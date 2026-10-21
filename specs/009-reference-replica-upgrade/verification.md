# 共享规范复刻升级验证

2026-10-21，Linux x64、Python3.12.14、uv0.12.23、PowerShell7.4.13。延续feat/ecommerce-design-workflow及005–008未提交工作；未提交、推送、发布或改写私人Host/成员安装。

实际运行`.venv/bin/python scripts/check.py`退出0，11阶段format/lint/types/unit/coverage/docs/contracts/security/build/protocol/member-install全部通过。test-reports/checks.json记录各项exit_code=0，各阶段日志为本次实际输出。159项测试中158通过，1项Windows注册表测试按Linux平台跳过；新增17项共享复刻专项。此前原008的14项专项也单独通过。

| 验收 | 证据 |
|---|---|
| RU01/02 | 单图、同类系列、单屏详情、SKU及1主图+8详情+2SKU的整套构造成功；所有图共享相同style_digest和逐字相同规范区块，逐图构图可不同。原Visual/Scene/Layout/Text四节完整，可选Logical仅在填写时出现 |
| RU03 | 无效HEX/字体/层级、缺共享style、逐图style/scene/字体覆盖、跨类目全preserve、重复适配维度/图ID、错误类型/模板/顺序、SKU遗漏/重复/未知、跨SKU/未知事实、缺属性及证据类别不符均拒绝；术语/禁用词及副标题/正文含换行600字边界生效 |
| RU04 | 导出与受控Provider实际收到的prompt逐字相同，参考SHA顺序相同；三个模型家族、2k档位、真实接口/画幅和不支持组合均按原矩阵处理；model_copy构造的非法字段、摘要/面板篡改、超8000字及无授权在派发前拒绝 |
| RU05 | 参考和主商品/两SKU共3个冻结资产；删原文件后仍按冻结副本完成11图，红SKU不带蓝SKU观察。相同字节不同路径的风格/商品角色、私网URL、1+4张输入均拒绝。相同图重复提交仍11次派发。参考变动保存新冻结SHA，旧版本只读提示不变、旧确认不能提交；共享色值修改另产新摘要 |
| RU05/06 | 25项整套完整导出，一次提交拒绝后20+5成功，全部落盘且25次唯一派发。新版结果可复用原review_reference_replica，错误任务或文件SHA变化拒绝，Agent证据从进度读取 |
| RU06/07 | auto/legacy实际stdio各执行构造→未确认提交拒绝→确认→主图/详情/SKU各出1图→inspect真实结果→六维复核→只读导出/进度→重复提交，复核3条且派发标记仍3。21 Tools/9 Resources/6 Prompts发现正确 |
| RU07 | 构造输入/输出、Resource schema和完整JSON示例通过JSON Schema/Pydantic。构造不含新字段的008历史记录，原digest计算一致，重新读取后提示/任务相同且重复提交复用；旧replica仍走原编译器并通过原15项复刻回归 |

reference模块和复用suite辅助编译模块父进程语句覆盖率合计98%，suite.py为100%。安全审计无已知依赖漏洞，源码凭据扫描、wheel/sdist、空缓存无开发依赖重复安装、隔离.env内容/权限保留和双协议可用性检查通过。文档、契约、示例和user-files运行文件均同步。

所有供应商调用均为受控替身，真实收费0。没有证明实际模型字形、像素级相似度、跨图颜色/布局或字体授权；没有运行Windows CI或实际Host界面验收。Agent仍需查看真实结果、记录证据并交用户验收，不自动扣费迭代。

复现：使用005/007记录的可写缓存和PowerShell PATH运行完整检查；专项为`uv run --no-sync python -m unittest discover -s tests -p test_reference.py`。用户说明见docs/REFERENCE-REPLICA-UPGRADE.md，完整参数见examples/reference-replica.json。
