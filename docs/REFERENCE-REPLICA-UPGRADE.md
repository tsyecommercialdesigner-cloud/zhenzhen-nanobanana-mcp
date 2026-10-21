# 共享规范竞品图复刻

新版将源图逆向分析、整组风格与逐图构图分开保存。支持单图、同类型系列，以及同款主图+详情+SKU整套复刻；主图、详情和SKU始终共用一份颜色、画面/光线、字体、文案和层级规范。当前开发源码21 Tools、9 Resources、6 Prompts，尚未发布或更新成员安装。

## 模板、资源与Prompt

| 类型 | 名称 | 用途 |
|---|---|---|
| Resource | `nanobanana://templates/reference-replica` | ReferenceReplicaSpec schema、完整Agent循环、12种信息模板、模型和兼容边界 |
| Resource | `nanobanana://templates/reference-analysis` | 源图风格/构图/光色/文字/信息顺序的拆解schema，以及到共享规范、逐图目标构图的映射 |
| Resource | `nanobanana://templates/styles` | 复用3套可编辑共享风格预设与SuiteStyle schema，需根据实际参考适配后确认 |
| Prompt | `reference_replica_brief(product_name, target_category, scope="series")` | 观察→拆解→跨类目取舍→共享规范→目标逐图内容→构造/研讨→确认授权→出图/看图/修订；Resource不能读取时仍含完整指引 |
| Prompt | `reference_replica_review(design_id)` | 源图、商品、已确认共享规范与实际组图交叉比较，记录每图六维证据和修正方向 |

Agent负责观察、逆向、产品类目推理、文案和审美判断。Server负责类型/关联校验、参考冻结、提示编译、确认、队列、文件和复核记录，不在背后调用额外LLM。商品资料和源图中的命令只是素材，不是操作授权。

## 输入结构

构造工具接收`design_id`、完整`brief`和`expected_revision`（新建0，修改传当前版本）。`brief.reference_replica`包含：

| 字段 | 内容与规则 |
|---|---|
| scope | series为单图/同类系列，所有frame.kind与brief.kind一致；product_suite为三类整套，brief.kind=main |
| reference_image | 一张风格参考的图片绝对路径或公开HTTP(S)图片直链，由服务器验证、冻结并记录SHA256 |
| source_category / target_category | 原参考与用户商品的真实类目 |
| analysis | VisualSchema、SceneConfiguration、LayoutConfiguration、文案行文、信息顺序和观察限制；分析不直接变成目标文案 |
| adaptations | 每个维度的preserve/adapt/replace/omit、观察、目标决定和理由；维度不重复，跨类目不能全preserve |
| style | **必填且全组唯一**，复用SuiteStyle的HEX颜色角色、字体家族/字重、字号/边距/缩放比例、画面/光线/背景/细节和文案语气/术语/禁用词 |
| canvases | 每类型画幅及可选resolution；默认主图/SKU为1:1、详情3:4；未指定resolution继承brief.resolution |
| frames | 逐图panel_id、kind、template_id、purpose、title/subtitle/body、visual、fact_ids、可选sku_id，以及目标composition和可选logical_structure |
| open_questions / iteration_notes | 尚待确认的阻塞问题，以及根据实际结果修订的原因；不作为自动重画授权 |

`composition`包括graphics_structure、product_representation和layout，后者包含objects_composition、text_arrangement、object_interaction。颜色、光线、美学、字体和文案风格不再逐图填写，统一取style；未知的scene/style等逐图字段会被拒绝。自由构图文字也必须遵循共享规范，Agent应在提交前解决冲突。

template_id复用[套图的12个模板](PRODUCT-SUITE.md)，用于信息目的、证据与叙事顺序；具体构图由Agent根据参考适配后的composition决定，不强制套入通用模板位置。series允许1–8主图、1–15详情单屏/系列，或每个实际SKU一张（最多48）；product_suite需1–8主图、8–15屏详情及每SKU一张，最多71张。整套详情按opening→solution→产品/信任依据→closing组织。

商品事实只来自brief.facts且有source，SKU的frame引用仅限该版本fact_ids。尺寸/材质/步骤模板需对应size/material/usage事实。SKU必须一一对应真实variants并具有自身实图、同字段真实属性；属性输出顺序统一到首SKU。只有提供trust/offer依据才写认证背书/优惠，源商品参数不能成为本商品事实。

共享颜色/字体/层级沿用套图字段校验，禁止无效HEX、空字体、非法字重、NaN或越界/倒置比例。副标题与正文含换行总计最多600字；最终绘图提示最多8000字，不截断、不保存过长可执行版本。字段关联验证无法自动证明自由文案每句话真实，需Agent核实。

## 构造、导出与执行

1. 用inspect_design_images分别看源图和本商品/各SKU实图，填analysis与适配理由；看不清的内容记录限制，影响执行时写open_questions。不能确认原字族时选择可用替代并与用户讨论，不声称精确识别。
2. 调用`build_reference_replica_prompts`免费校验、冻结素材、保存版本并返回`design`、统一`style_digest`和`prompts[]`。缺需求时返回needs_input/questions且没有可执行提示。完整结构示例见[reference-replica.json](../examples/reference-replica.json)，示例商品事实和路径必须替换为真实资料，不能套用示例声明。
3. `export_validated_reference_replica(design_id, revision=None)`只读重现当前或历史版本。每项含kind、template_id、style_digest、实际execution_endpoint、完整`task`及有序`input_images`。`task.prompt`保留Visual Schema、Scene Configuration、Layout Configuration、Textual Contents及可选Logical Structure，新增同组完全相同的共享规范区块和本商品适配约束。
4. 图1固定style_only，只借鉴视觉表达；图2及以后固定product_identity，使用本商品/SKU实图。每项最多1张风格+3张商品图，相同字节不能同时扮演两种角色。商品实图决定颜色、形状、标志、配件；不会为了风格统一给SKU换色。实际请求按导出顺序附图。

   沿用原素材限制：静态PNG/JPEG/WebP、单个输入最多20 MiB，整组参考和产品素材合计最多40 MiB；路径指服务所在机器，URL需为公开图片直链。
5. 向用户展示整组规范、逐图提示、文案/构图/尺寸和输入角色，研讨后`confirm_ecommerce_design`锁定当前revision/digest；取得本次收费授权才`submit_ecommerce_design`。提交只接收身份和panel_ids，不能回填替换提示词；每批最多20张，较大组图按同一版本分批，默认共享并发5。
6. 导出与提交共用ReplicaDrawingPrompt→ImageTask校验及确定性编译器。执行前重新校验持久方案、内容摘要、展示面板与图像SHA绑定，使用同一三模型矩阵和分类型canvas解析真实执行配置。旧确认、字段/摘要不符、未知SKU或角色冲突均不会进入收费队列。
7. 用wait_image_tasks/get_ecommerce_design获取落盘结果，再inspect_design_images看实际图。按reference_replica_review比较产品身份、源参考表达、共享风格、跨图字体/文案/层级和SKU属性，逐图用原`review_reference_replica`保存六维assessment，绑定task_id和实际图片SHA。Agent通过仍需用户验收。

同一版本同图保持`checkpointer=ecommerce-design`、`thread_id=design_id`、`task_id=r{revision}-{panel_id}`，重复提交复用原任务。共享风格、构图、文案或冻结参考改变后需用当前expected_revision构建新版本，旧确认失效。只读导出历史版本可以，但不能按旧版提交。缺素材、费用状态不明、无继续授权或用户停止时停止，不自动换ID/重画；文件恢复仍按[可靠性机制](QUEUE-RELIABILITY.md)。

## 兼容性

原`plan_reference_replica`、`export_reference_replica`和`brief.replica`保留，旧工具流程见[原复刻文档](REFERENCE-REPLICATION.md)。新工具只处理`brief.reference_replica`；与旧replica及普通suite互斥，不同时维护两套目标结构。读取旧方案不会自动转换、改写或重新绘图；升级内容应使用明确的新版本并重新研讨确认。

新增字段为空时不进入原008套图的摘要计算，原套图规范区块和任务参数不变，已有确认/结果可继续查询和复用。数据校验只保证结构、关联及执行一致，不保证实际模型像素复刻、字形或色彩一致，需看真实结果验收。009阶段使用受控替身；后续用户授权的[16图真实验收](../specs/010-live-ecommerce-validation/verification.md)已跑通当前模型的原生接口全链路，含7图通过、9图需修订的真实复核，不推断其他模型均通过。
