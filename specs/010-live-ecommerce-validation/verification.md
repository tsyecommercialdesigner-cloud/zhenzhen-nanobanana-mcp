# 真实16图验收结果

2026-10-21，用户在会话中明确授权真实收费，随后确认保留8屏详情限制，最终调用上限调整为5主图+8详情+3SKU=16。执行前未修改8屏业务规则。使用Zippo官方公开HeatBank 9s黑/银/蓝独立SKU实图，参数来自[官方商品页](https://www.zippo.com/products/heatbank-9s-rechargeable-hand-warmer-box)。6 Pro手持实图只作干净背景/自然柔光/握持构图参考，不迁移其矩形机身、防水或手电功能。

脱敏机器证据见[live-acceptance.json](live-acceptance.json)，包括数量、模型/接口、设计/风格摘要、每图尺寸和SHA256。真实素材、完整提示/图片/原响应及费用/任务账本全部留在仓库外，不进入提交或PR。

| 项目 | 实际结果 |
|---|---|
| MCP完整链路 | 真实stdio读取Resources/启动Prompt→inspect输入图→build_reference_replica_prompts→导出/批准测试方案→submit→wait/query→inspect实际图→六维review_reference_replica→进度/只读导出/重复提交 |
| 本次实际模型/接口 | gemini-nano-banana-2.1，Gemini原生/v1beta/models/gemini-nano-banana-2.1:generateContent；真实供应商API，非MockTransport |
| 执行 | 先完成第1张正式主图，再提交其余15；观测5个running。16任务成功、每任务1图，共5主图+8详情+3SKU，无失败/unknown或遗漏 |
| 费用边界 | 发送前持久预留，实际POST=16且每任务post_attempts=1；关闭自动POST重试，分类5/8/3、总量16；重复提交全部16图后POST仍16，复核没有收费请求 |
| 文件与提示 | 16图SHA256验证全部通过；8张主图/SKU输出1024×1024，8屏详情896×1200。模型分辨率请求仅用于选档，实际详情像素与请求768×1024不同，未伪称精确像素；执行前真实HTTP提示与批准任务匹配，执行后导出逐字不变 |
| 复核 | Agent实际查看全部16图，MCP inspect确认SHA后保存16条六维证据；7条agent_passed、9条revise。3个SKU颜色/身份正确，存在文字、布局及结构细节待修订，不视为上架验收 |
| 初次启动问题 | MCP SDK过滤子进程环境，专用手动入口最初缺密钥启动失败，费用0；修复为只显式转交本服务密钥和网络配置，不传GitHub凭据，不落盘密钥，然后仍使用同一manifest/预算 |
| 云网络适配 | 直连只读检查拒绝连接，显式HTTPS出口代理+环境CA的只读模型目录查询成功；专用真实transport保留TLS校验、每请求独立连接，复用正式Provider，不改变生产默认HTTP/URL安全边界 |

流程验收通过，视觉问题如实进入复核：m03/d04正文被改写，m04新增9h文字；m02暖色辉光覆盖主体；d01/d04/d05正文锚点漂移；d04/d05新绘接口/指示灯具体位置未由输入图证明；3张SKU的副标题强调色、说明对齐、商品/标题位置不完全统一。后续应补结构细节图、将绘图约束放requirements而不是可绘制正文，并统一固定文字排版层。本轮没有修图、重画或超出16次的收费探测。

本地`.venv/bin/python scripts/check.py`退出0，11阶段format/lint/types/unit/coverage/docs/contracts/security/build/protocol/member-install全通过。164项自动化测试中163通过、1项Windows注册表测试在Linux按平台跳过，新增5项费用边界测试均为替身、不触发收费。自动化与真实16图结果分开记录；GitHub Windows CI以PR实际检查为准。

真实验收覆盖当前模型/原生接口/该组图流程，没有证明全部三个模型家族、全部格式/变体、实际供应商账单金额、精确字族/像素或所有Host均通过。ModelCatalog的全矩阵upstream_verified仍保留false，不用一个路径的成功推断全部模型已验证。

用户条件授权的后续动作是提交、常规推送dev并创建dev→main PR；不包含合并或发布。实际提交与CI链接将在PR中保留，本验收不单独授予后续真实收费。

已完成交付动作：功能提交`8d5cca1a893cf4a9dcb0f095ed2b4dc3856acc1b`常规推送dev，并创建[dev→main PR #19](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/pull/19)。GitHub Windows quality的实际状态与日志以该PR检查为准；本记录不提前宣称远端CI通过，也未合并或发布。

首轮Windows CI暴露验收脚本/新夹具的SQLite连接未显式关闭、中文子进程管道编码，以及耐久文件批量测试触发短等待上限。已改为事务退出后显式close（不依赖GC/忽略删除失败），新增连接关闭回归，并明确子进程UTF-8。批量测试只对Windows将完成等待从10/30秒调整为30/90秒，以适应覆盖率模式下的耐久文件操作；200任务、25图、3进程、并发5、SHA/幂等/完整性断言全部保留，非吞吐SLA不变。此修复不重新执行收费测试，原16次计数和结果仍保持。

修复后重新运行本地完整门禁，`.venv/bin/python scripts/check.py`退出0，11阶段全部通过。当前165项测试中164通过、1项Windows注册表测试在Linux按平台跳过；包含6项不收费的预算专项测试。该结果是本地验证，不能替代PR上最新提交的Windows CI结果。
