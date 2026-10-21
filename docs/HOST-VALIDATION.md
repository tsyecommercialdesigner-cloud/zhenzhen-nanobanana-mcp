# 2026-10-21 Host免费验收

目标提交：main的`91af94c38c64d46bdcc072259112a26037faeb30`，由[PR #2](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/pull/2)合入。对应[main Windows CI39524783398](https://github.com/tsyecommercialdesigner-cloud/zhenzhen-nanobanana-mcp/actions/runs/39524783398)成功，69测试及11阶段检查通过。没有生成标签、草稿或正式Release。

## 独立安装

从实际GitHub仓库`git clone --branch main --single-branch`到维护机独立测试父目录`E:\temporarily-workspace\nanobanana-host-validation-20261021`下的同名项目目录，核对完整SHA；使用空专用uv缓存执行`uv --directory <独立项目目录> sync --locked --no-dev`，Python3.12.14、uv0.12.9。确认运行包来自独立`.venv`，mypy等开发依赖未安装。

仅在独立项目写入`ZHENZHEN_NANOBANANA_API_KEY=host-validation-not-real`假凭据，不复制现用私有配置。启动使用`uv --directory <独立项目目录> run --no-sync python -m zhenzhen_nanobanana_mcp`；不触发依赖同步、构建或升级。现用C:\MCP安装与Host配置未修改。

另以独立空目录为项目根、从子进程删除新密钥进程字段后，验证实际Windows当前用户环境的新字段回退成功；只比较读取结果，未输出、落盘或修改真实凭据。旧名不回退由配置回归验证。

## 实际Host后端

按Codex→DSH顺序执行，无模型推理或绘图请求：

| Host | 实际入口与隔离 | 结果 |
|---|---|---|
| Codex CLI0.153.0 app-server | 独立CODEX_HOME与config.toml，`codex app-server --stdio`；实际app-server JSON-RPC初始化、临时thread/start、mcpServerStatus/list与mcpServer/tool/call | 6工具发现及下述免费调用通过 |
| DSH0.2.0-rc.2 CLI | 使用已安装CLI的`node <安装目录>/@deepseek-ai/dsh/lib/bin.js --profile host-check`，独立DSH_HOME/profile；挂载实际system-prompt、tools、mcp-client插件及Host内的只读验收探针 | ctx.tools实际发现6工具、经ToolRuntime.execute调用并通过，退出0 |

DSH采用独立最小profile，未加载用户web/desktop补丁、模型凭据或第三方插件。实际MCP SDK及桥接逻辑没有替换为fake，服务是远端克隆代码启动的stdio子进程；验收探针只驱动Host已有工具调用入口。Codex同样通过真实app-server调用MCP，未用Python MCP客户端代替Host。

两Host均发现：`list_models`、`plan_ecommerce_images`、`submit_image_tasks`、`get_image_tasks`、`cancel_image_tasks`、`get_batch_result`。仅调用以下免费功能：

| 调用 | 两Host的实际结果 |
|---|---|
| list_models | isError=false，7个模型，默认gemini-nano-banana-2.1，api_key_configured=true（假配置） |
| plan_ecommerce_images | ceramic mug / ceramic / detail / count=6，成功返回6项计划 |
| get_image_tasks | checkpointer=host-validation、thread_id=free-check，tasks=[]、next_cursor=null、isError=false |
| get_batch_result | 查询不存在的host-probe-no-such-batch，正确返回isError=true；DSH保留失败语义 |

未调用submit_image_tasks或cancel_image_tasks；独立项目没有生成outputs目录、SQLite账本或图片。未提交合法绘图请求，不存在收费任务重试。

## 证据与边界

原始Codex配置/库存/结果/RPC记录与DSH测试profile/结果/日志保留在上述独立测试父目录；均为专用假配置与本次测试数据，不把用户Host配置或秘密复制入库。工具结果的结构化内容与错误标记已逐项检查；Host子进程已退出。

本次证明实际Codex app-server与DSH CLI工具桥接和免费能力可用，不宣称点击GUI、Agent自主选工具、现用DSH完整profile、Prompts/Resources桥接或真实上游生成/编辑通过。收费验收及发布仍未授权，继续保持待办。
