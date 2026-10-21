# 竞品复刻验证记录

2026-10-21，Linux x64，Python3.12.14、uv0.12.23、PowerShell7.4.13。沿用feat/ecommerce-design-workflow工作分支，保留005未提交成果；没有提交、推送、PR、发布或私人Host变更。

完整执行 `uv run --no-sync python scripts/check.py`，退出0，11阶段全部通过：格式、lint、类型、单元、覆盖率导出、文档、注册契约、安全扫描与依赖审计、构建、双协议smoke、空缓存无开发依赖源码安装。日志位于test-reports/replica-full-gate.log、checks.json及各阶段文件。

实际运行113项单元测试，112通过、1项Windows当前用户注册表读取在Linux按平台跳过。新增14项复刻专项覆盖：

| 验收 | 证据 |
|---|---|
| RR01/RR02 | 源图分析与目标方案分别持久化，源图竞品销量不进入目标提示；必填控制字段/重复ID拒绝；跨类目全部preserve拒绝；未知本商品事实引用和未解决问题阻止后续操作 |
| RR03 | style_only第一张、product_identity后续且SHA对应原图；单张详情图；SKU独立照片/观察及一版本一图校验；图像角色混用、同图、超4输入、私网/相对路径拒绝；冻结风格图篡改阻止收费 |
| RR04 | 必需Markdown章节与控制维度完整，可选Logical Structure有/无两种情况；输出画幅、像素需求与实际模型分档；导出的文本及附图顺序与Provider替身收到的完全相同；原外部模型导向已由007更正为当前三个模型家族，未知执行模型仍拒绝 |
| RR05 | 复用确认与收费权限；旧版本拒绝新增提交；修改replica导致重新确认；普通edits不能制造展示/执行分歧；同版本重复提交只派发一次；原设计/通用绘图测试继续通过 |
| RR06 | 六维证据结构；未通过或不确定项强制修正动作；正确生成文件绑定并持久恢复复核；错误task/revision/hash和改动文件拒绝；agent_passed/revise/needs_user_review不触发额外绘图 |
| RR07/RR08 | auto与legacy实际stdio客户端读取Resource、调用Prompt、计划→导出→拒绝未确认提交→确认→替身出图→等待→实际图片读取→复核→持久查询；当前16 Tools、2 Resources、2 Prompts发现、schema导出与源码包安装检查通过 |

新增3模块在本次父进程覆盖率统计约90%；部分工具调用在实际stdio子进程中执行，该报告未合并子进程覆盖率，不能用父进程未覆盖行推断这些工具未执行。测试断言实际返回结果和落盘文件，未用零测试、跳过断言或模拟成功日志代替验证。

安全扫描和锁定依赖审计通过，未发现已知依赖漏洞；依赖声明、uv.lock、版本号和现有模型矩阵未更改。成员源文件清单包含全部新增运行模块，wheel/sdist构建及源码包空缓存重复安装、私有测试.env内容和权限保留通过；未生成/发布新成员ZIP。

所有Provider为受控替身，收费请求0；没有真实风格相似度、视觉质量、所有供应商多图效果、Windows CI或私人Host界面验收结论。复核内容来自Host Agent，服务器只验证关联/哈希/结构，不声称独立识图。导出并不改变实际接口，也不代表用户已确认或授权。

复现专项：`uv run --no-sync python -m unittest discover -s tests -p test_replica.py`。完整检查使用005验证记录中的缓存/PowerShell路径初始化，再运行scripts/check.py。
