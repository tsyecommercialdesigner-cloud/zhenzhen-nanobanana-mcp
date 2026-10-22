# 同款商品的主图、详情页和SKU整套设计

本套图模块提供2个免费工具、5个JSON Resources、2个Prompts；含后续复刻升级的整个服务现有21 Tools、9 Resources、6 Prompts。尚未发布到正式v0.2.2或更新成员安装。

整套图保存为同一个design_id中的一个版本，使用唯一的`suite.style`。颜色角色、画面/光线/背景、文案语气与术语、字体家族/字重、标题/副标题/正文比例、商品缩放、边距和间距在所有图中继承。每图只能选择模板、填写内容与构图；不能新增style字段覆盖全组规范。SKU的实际颜色属于商品身份，不因风格统一而被换色。

## 模板和Prompt

| 类型 | 名称 | 用途 |
|---|---|---|
| Resource | `nanobanana://templates/product-suite` | 流程、资源导航、ProductSuiteSpec JSON Schema、模型及执行边界 |
| Resource | `nanobanana://templates/styles` | 3套可编辑预设：natural_clean自然简洁、technical_clear理性精确、warm_daily温暖生活；附SuiteStyle schema |
| Resource | `nanobanana://templates/main` | main.hero首图、main.benefit单卖点、main.scene真实场景，共3版式 |
| Resource | `nanobanana://templates/detail` | opening开篇、solution方案、feature功能、material材质、size尺寸、usage步骤、proof依据、closing收束，共8版式（ID以detail.开头） |
| Resource | `nanobanana://templates/sku` | sku.variant：一图一版本，统一视角/比例/标签与属性顺序 |
| Prompt | `product_suite_brief(product_name)` | 分析需求→参考→共享规范→逐图文案排版研讨→构造→确认→授权出图→落盘复核 |
| Prompt | `product_suite_review(design_id)` | 看真实结果，逐图和跨类型核对商品、SKU、色系、画面、字体、文案、层级与留白；给出证据再决定是否修订 |

预设不是商品资料，也不是平台合规保证。选定一套预设后应根据用户产品、平台和参考修改并共同确认。主图一图一个核心信息；详情按痛点/用途开篇→解决方案→产品展示/证据→选择引导；缺少信任证据时用中性实物细节，不生成认证、评价或承诺。尺寸、材质、步骤模板需要相应类别的事实引用。

## 构造与执行

`build_product_suite_prompts(design_id, brief, expected_revision=0)`免费校验并保存完整方案，返回：

- `design`：版本、digest、状态、问题、逐图文案/构图、冻结素材和完整输入。
- `style_digest`：共享风格的SHA256，所有类型相同。
- `prompts[]`：每项的panel_id、kind、template_id、style_digest、execution_endpoint及实际`task`，其中`task.prompt`是最终可执行绘图提示词。

`export_product_suite_prompts(design_id, revision=None)`只读重新导出同一提示词，不产生版本或费用。历史版可以审阅，提交必须匹配当前批准版。

整套需1–8张主图、8–15屏详情及每个实际SKU一张图（最多48 SKU，整套最多71图）。每个SKU需自己的实图、真实属性及可用事实ID，属性字段一致，输出顺序统一到首个SKU。主商品图与SKU图一并冻结并绑定SHA256。需要只设计一类图片时继续用`plan_ecommerce_design`；需要以竞品参考为基础进行整套迁移时用[共享规范复刻](REFERENCE-REPLICA-UPGRADE.md)。普通套图也可把对标观察转为benchmarks和共享style；suite、旧replica和新reference_replica三种目标结构互斥，选择适用流程。

完整可校验的参数示例见[product-suite.json](../examples/product-suite.json)，包括1主图、8详情、2SKU与明确的共享规范。示例收纳篮属性、文案和事实仅用于演示，必须全部替换为用户核实的资料及服务机器可读的真实图片绝对路径；不能把示例事实用于实际商品。Windows路径在JSON中用双反斜杠，如`D:\\素材\\蓝色篮.png`。

默认主图/SKU画幅1:1、详情3:4。按平台修改`suite.canvases.main/detail/sku.aspect_ratio`，各类型可分别指定resolution；未指定则继承brief.resolution。尺寸用于本服务已有模型分档，不保证供应商实际输出像素；字号比例始终以画布宽为基准。整套中`brief.style`、`brief.aspect_ratio`、main_count/detail_count是旧单类流程字段，不参与套图编译；数量取frames，风格取suite.style，画幅取suite.canvases。

向用户展示全套规范、逐图文案/构图/尺寸和提示词进行研讨后，使用现有`confirm_ecommerce_design`确认当前revision/digest。取得本次收费授权后调用`submit_ecommerce_design`，只传设计身份和明确选中的panel_ids。每批最多20图，较大组图按同一设计、同一revision/digest分批；默认共享并发5。固定task_id为`r{revision}-{panel_id}`，重复提交复用原任务。

改稿时使用当前expected_revision和完整brief再次构造；修改任一共享规范或逐图内容均使旧确认失效。不能用普通edits改套图，也不能在提交时回填替换prompt。任务查询、等待、异常恢复、图片校验与落盘继续使用[可靠性机制](QUEUE-RELIABILITY.md)。

## 校验边界

Pydantic class包括SuitePalette、SuiteTypography、SuiteHierarchy、SuiteCopyStyle、SuiteStyle、SuiteCanvas、SuiteFrame、ProductSuiteSpec，以及类型化绘图中间结构DrawingPrompt和执行结果CompiledSuitePrompt。所有继承Contract的class拒绝未知字段。

颜色必须为六位HEX；字体名不可空，字重取指定值且标题≥副标题≥正文；比例数值必须有限且处于范围内，字号标题>副标题>正文，商品缩放和两侧边距不能超出画布。模板必须匹配图片类型，图ID唯一，详情按阶段有序，SKU不遗漏/重复或串用事实，文案检查禁用词和统一术语。事实引用能核对关联，不能自动证明自由文案的每句话真实。

Server先验证Brief与帧，再构造DrawingPrompt，最终通过ImageTask验证提示词长度（最多8000字）及执行参数；模型/格式/端点按本服务三家族实际矩阵解析。预览与真实提交共用编译器；提交时再次校验持久方案和面板一致性，只将校验后的task送入队列。风格区块在所有图片提示中完全相同，模板v1稳定保存并有版本标记。

Agent负责观察、推理、参考适配、文案语义和实际结果复核。共享规范能约束输入，不能保证绘图模型生成的字形、颜色或布局每次完全一致。用`get_ecommerce_design`取得落盘路径，再用`inspect_design_images`查看真实结果，并按`product_suite_review`跨图比较。发现偏差先定位统一规范或单图问题，再向用户展示修订；不自动收费重画。
