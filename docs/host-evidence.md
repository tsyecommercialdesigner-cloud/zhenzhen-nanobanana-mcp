# Host 配置依据（2026-10-14）

本地命令只读帮助/版本/schema，不注册服务、不修改现有 Host。

按更新规范，四个 Host 的后端密钥改为服务自身固定读取项目 `.env`；默认不使用 env/env_vars/!!js 转发密钥。下述旧版环境机制资料仅作为可选兼容背景，当前模板无需凭据变量展开。

- Codex CLI `0.153.0`：`codex mcp add --help` 验证 `NAME -- COMMAND...`；`codex mcp --help` 验证 get/list。TOML 的 env_vars、stdio args、超时字段另参考 [官方 MCP 文档](https://developers.openai.com/codex/mcp)。
- Claude Code `2.1.258`：`claude mcp add --help` 验证 project scope/stdio/-- 分隔。JSON 变量展开和 per-server timeout 参考 [官方 MCP 文档](https://code.claude.com/docs/en/mcp)。
- DSH `0.2.0-rc.2`：`dsh --help` 验证 `--profile`、`--patch`、`--dump-config-schema`；本机 web schema 中 plugin `@deepseek-ai/dsh-mcp-client` 的 config98 支持 stdio、command/args/env、serverName（1–32 字符）、toolCallTimeoutMs、failOnStartupError/reconnect。只截取该结构验证模板，`!!js` 只作为惰性标记，未读取真实密钥。完整 web profile 已有四个无关 Loader carrier 错误，故完整 profile 验证未通过/未修复。
- Cherry Studio：参考 [官方 MCP 文档](https://docs.cherryai.com.cn/advanced-basic/mcp)；交付本地 MCP JSON，实际 GUI 版本、变量继承和超时设置未验证。

PowerShell CLI 帮助和模板语法已核对，Bash/Zsh 命令来自同一 CLI 帮助并使用 POSIX 安装路径，未运行；真实 GUI 发现、Tool业务、Prompt/Resource桥接均未验证。无需认证的 stdio smoke 不代表 Host 联调成功。

FastMCP 功能核对 [工具文档](https://gofastmcp.com/servers/tools)，实际 ToolResult 从锁定包 `fastmcp.tools.base` 导入；底层 SDK 的 snake_case 字段不改变 wire 的 `isError`/`structuredContent`。Gemini 映射参考 [官方图片文档](https://ai.google.dev/gemini-api/docs/image-generation)，贞贞具体代理兼容性仍以真实上游验证为准。
