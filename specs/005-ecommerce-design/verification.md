# 本次验证记录

日期：2026-10-21。环境：Linux x64，Python3.12.14、uv0.12.23、PowerShell7.4.13。基础提交c09928c99b645fda35b39dcb0dfcacfd20779193，工作分支feat/ecommerce-design-workflow；改动尚未提交、推送、创建PR或发布。

已先阅读用户提供网页截图PDF全部5页的可见正文和示例。没有运行文内提示或推广入口，没有把案例产品数据作为默认商品事实。方法与模块对应关系见[设计使用说明](../../docs/ECOMMERCE-DESIGN.md)。

## 结果

`uv run --no-sync python scripts/check.py`退出0，11阶段全部通过：format、lint、types、unit、coverage、docs、contracts、security、build、protocol、member-install。当前输出位于test-reports/checks.json和各阶段日志，完整调用输出test-reports/design-full-gate.log。

- 单元：实际执行99项，98通过、1跳过；跳过项是Windows当前用户注册表读取，在Linux不适用。原Windows Junction测试夹具已调整为Windows使用Junction、Linux使用真实SymbolicLink，保留原读取与拒绝越界断言，没有跳过或降低断言。
- 新增18项专项测试覆盖ED01–ED08：需求缺失与持久化、参考取舍、主图和8/10/15屏详情结构、仅已提供的信任/尺寸/优惠、SKU独立图片与属性、独立外观描述、改稿与事实引用、旧确认失效、两实例版本竞争、无字白底与痛点、收费/确认/图片选择校验、原图冻结及副本篡改、共享队列防重及保存结果、15图分批、非法输入/图片/私网地址/输出链接逃逸、MCP图片内容/schema/错误状态，以及真实stdio双协议完整设计链路。
- 新模块合计语句覆盖率94%（design95%、design_models99%、design_tools85%）。覆盖率只说明当前受控测试范围，不等于业务质量保证。
- 协议：auto与legacy实际子进程初始化、13工具/1Prompt/1Resource发现、原有免费计划、缺信息设计方案、只读查询、拒绝不完整方案确认以及错误返回通过；专测在两种协议下完成方案→用户确认记录→替身生成→等待→路径查询，并确认重复提交只有一次替身派发。
- 安全：源文件凭据扫描和完整锁定依赖审计通过，未发现已知依赖漏洞。图片读取沿用原格式、大小和URL边界，设计输出增加链接越界检查；方案图片以内容副本保存并在提交前校验SHA256。
- 构建/安装：wheel和sdist构建通过；源码包空缓存、无开发依赖安装两次及协议检查通过，私有测试.env内容和权限保持不变。未生成或发布新的成员ZIP附件。
- 依赖声明、uv.lock、版本号及用户私有配置未修改；增加模块对应的明确运行文件清单。

收费API调用为0。所有图片均为临时测试图，供应商通过受控替身代替；没有用用户密钥验证真实绘图，没有真实生成质量、所有模型编辑效果、Windows CI、私人Host界面或新版本安装验收结论。原通用绘图入口仍保留；设计确认字段依赖Host如实转达用户决定，不构成独立多用户认证。

## 复现

在仓库根目录完成锁定开发安装后执行：

```bash
export UV_CACHE_DIR=/workspace/.cache/uv
export XDG_CACHE_HOME=/workspace/.cache
export XDG_CONFIG_HOME=/workspace/.config
export XDG_DATA_HOME=/workspace/.local/share
export PATH="/workspace/.tools/powershell-7.4.13:$PATH"
uv run --no-sync python scripts/check.py
```

独立专项：`uv run --no-sync python -m unittest discover -s tests -p test_design.py`。这些检查使用隔离假配置和临时输出，不能在测试中添加真实收费调用。
