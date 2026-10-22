# v0.3.0 发布说明

本版包含21 Tools、9 Resources、6 Prompts，采用Windows本地stdio、Python3.12.14和锁定依赖。默认安装路径为D:\MCP\zhenzhen-nanobanana-mcp，密钥仍为项目根.env中的ZHENZHEN_NANOBANANA_API_KEY。

## 新增能力

- 保留同步generate_images、异步submit_image_tasks和已有任务等待/查询；批次上限20项，默认共享输出目录并发5，待处理上限200。
- 设计工作流覆盖主图、详情页与SKU：实际看图、补充已核实商品事实、参考适配、版本化研讨/确认，再单独授权收费提交。
- 同款整套模板统一配色、画面、文案、字体与层级；共享规范竞品复刻区分产品身份与风格参考，导出和执行采用同一已校验提示词。
- 增加安全显式重试、原响应检查点恢复、参考图及结果哈希和原子文件发布；不确定收费状态不盲目重提。

## 验证与未覆盖范围

发布准备基线为856e362285c0a1255828c7a26d6bca59930d037a；最终发布提交、版本和成功main CI由受控CD生成的release-eligibility.json固定，不能将基线当作最终标签SHA。版本更新经dev→PR→Windows quality与评审→合并，再核对精确main提交CI。发布流程重复完整检查，创建tag和草稿，核对附件后公开；不覆盖v0.2.0、v0.2.1或v0.2.2。

- [21工具Host验收](HOST-VALIDATION-PR19.md)：Codex app-server与DSH CLI发现及免费调用通过；双协议发现21/9/6是独立协议验证，不等同Host全部Resources/Prompts桥接。
- [DSH实际看图](DSH-VISION-HOST-VALIDATION.md)：补齐独立附件存储与codeproxy-anthropic / claude-sonnet-5-5后，实际CLI Agent识别随机图形和数字通过；原最小profile未通过的结果保持，Desktop GUI仍未验证。
- [16图历史验收](../specs/010-live-ecommerce-validation/verification.md)：16图落盘及SHA通过，7图Agent通过、9图需修订；不等于整套可上架，不自动重画。
- Windows首次文档合入CI暴露的套图等待预算遗漏已在PR #22修复；保留失败记录、慢盘复现及原断言，没有以重跑掩盖问题。
- 全模型/变体、真实故障恢复、各GUI和现用完整DSH profile仍有未验证范围，不因Release补齐。

## 安装、升级与回滚

按[手册](../MANUAL.md)从正式GitHub Release核对资格记录，clone固定标签并uv sync --locked --no-dev，再以假配置做协议检查。草稿不满足成员安装资格。新版本不得启动时自动安装依赖。

升级先停止共享输出目录的服务，备份并保留原.env、ACL、SQLite任务/设计账本与图片；未知收费状态使用原三元组查询，不能清空账本或换身份重提。回滚使用已记录提交和对应锁，保留新账本与证据，旧版不保证识别新版设计/恢复字段。没有远程部署或数据库重建操作。

本轮仅发布与隔离安装/协议验证：不新增收费模型/绘图调用，不改现用Host配置，不更新D盘现用安装，不删除任何验收证据。可选ZIP未请求，不额外发布成员ZIP。
