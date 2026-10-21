# v0.2.2 候选版本与草稿范围

2026-10-21用户授权：纳入已合并的同步出图能力，更新版本号，经dev→PR→Windows CI与审查→合并，再复验实际main合入提交CI，通过受控Release工作流及正常release环境审批创建草稿。暂不正式公开，不更新D盘安装，不新增收费调用，不修改已有版本。

## 新增能力

- `generate_images`：接收与异步submit相同的三元组及1–12项任务，在一次MCP调用中等待本组终态，成功图片落盘后返回；支持原有模型/参考图编辑与路由。
- `wait_image_tasks`：只等待明确指定的1–100个已有任务，不新增绘图请求。原6个异步/查询工具保留，当前共8 Tools、1 Prompt、1 Resource。
- 两入口与原异步队列共用SQLite、防重、原子冲突和共享并发限制，不新增供应商端点、HTTP重试或数据库迁移。
- 等待默认600秒、严格整数1–1200，包含排队时间。到期返回isError及wait_timed_out和当前结果；仅结束本次等待，后台任务不被取消/重提。失败/unknown/cancelled不伪装成功，使用原身份继续查询或等待。Host结束整个服务仍受原有恢复边界约束。
- 版本元数据、模块与uv.lock根项目同步为0.2.2；Python3.12.14、依赖及SDK版本保持。包含最新指南/手册中DSH三profile和既有本机迁移验收记录。

实现依据：[004规范](../specs/004-sync-image-tools/spec.md)、[本地验收](../specs/004-sync-image-tools/verification.md)。功能由[PR #14](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/pull/14)合入a424a26768951ec6892b7db95e2faee5ae89403a，该SHA的main CI39568874388成功；它不是本次版本提交未来CI的替代。

## 验证与交付边界

本版既有81项测试包含10项同步专项验证：gate等待/文件哈希、跨入口/跨实例防重、编辑路由、等待超时/取消、非法输入、原子冲突、混合失败及双协议真实stdio替身。重新运行本地/远端11阶段与独立运行安装；未来PR/SHA/CI/CD/资产信息只按实际结果在PR与草稿记录，不预填成功。

草稿由既有Release工作流生成新v0.2.2标签、wheel、sdist、SHA256SUMS及release-eligibility.json；只复用该次verify产物。核对包版本、注册的8工具、两个同步接口、锁文件、文档、空密钥模板、包内安全边界和资产哈希。标签可见不等于Release正式公开，安装器仍拒绝草稿。

v0.2.0/v0.2.1标签、说明、附件保持不变；成员快速安装例仍固定最新已公开v0.2.1。D盘现用安装仍保持0950109及现有私有配置/数据，本轮不更新。没有新增真实供应商收费调用、真实Host长等待、GUI、故障恢复或全部模型实测，不能把CI替身成功当作以上业务验收。
