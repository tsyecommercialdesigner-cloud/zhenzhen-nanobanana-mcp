# 主图、详情页与 SKU 设计工作流

本功能属于当前开发工作区，尚未发布到正式v0.2.2或更新成员安装。005增加5个设计工具，后续[竞品复刻](REFERENCE-REPLICATION.md)、可靠性和[整套共享规范](PRODUCT-SUITE.md)扩展后，当前共21 Tools、9 Resources、6 Prompts，原8个工具签名保留。它提供供Host与用户研讨的结构化底稿和执行链路；Host负责观察图片、理解业务、查找参考或向用户索取参考、润色文案。没有内置搜索引擎或额外视觉/语言模型服务。

同款商品需要主图+详情+SKU成套设计时，优先使用[整套模板流程](PRODUCT-SUITE.md)，在一个design_id中维护唯一的颜色、画面、文案、字体和层级规范；本页单类示例仍适用于分别设计。

## 从参考页面学到的方法

参考为用户提供的《(12/20) 豆包+lovart（nano banana）搞定电商详情页设计》网页截图PDF，共5页，对应飞书链接 `https://my.feishu.cn/wiki/GaizwsdqiixLSSkgJ42cDaLHnLq`。已阅读截图正文及排版示例；截图中被截断或附件内未展示的内容不视为已获得。

| 位置 | 设计逻辑 | 本次实现 |
|---|---|---|
| 第1页：主图 | 主图负责点击，简洁直观、一图一个核心卖点；首图看清全貌，后图展示差异；数量依平台而变 | main默认5张，可选1–8张，逐图只选一个事实。平台及尺寸由用户核实；可把标题与正文改为空制作无字白底图 |
| 第1页：详情页 | 痛点→卖点→证据；通过功能、场景、材质细节、尺寸、信任信息消除顾虑 | detail默认10屏，可选8–15屏；按痛点与开篇→解决方案→产品展示→信任依据→购买引导组织；缺少认证/评价时用实物细节核对替代，不假造证据 |
| 第1页：SKU | 同一视觉模板，一图一个规格版本，清楚区分颜色、尺寸、配置 | sku每个版本提供实际图片与属性；统一背景、光线、主体比例、视角、字体和标签位置，不凭空换色或增加配置 |
| 第1–3页：需求与参考 | 先问平台、数量、受众、尺寸、风格、核心优势与文字需求，再拆解参考的视觉焦点、信息层级、文案、优缺点和可借鉴点 | 不完整需求保留为needs_input；参考可由用户提供，或明确记录本轮不使用参考的决定。不声称已经浏览一个仅提供链接的竞品页面 |
| 第3–4页：文案与画面 | 将已核实产品特点转为用户易懂的表达，逐屏写清主题、主副文案、主体、构图与排版，围绕购买路径安排节奏 | facts带来源、类别和可选痛点；panels带事实引用、headline/body/visual/layout，可由Host改稿并逐项展示用户 |
| 第4–5页：制作与排版 | 图片制作与字体、色调、字号、位置统一；校正错字与产品错误，关注字体使用权 | 在每项提示词中复用统一DesignStyle，保留产品图；生成后提示人工核对，不保证模型一致性、字体授权、实际像素或完整PSD |

页面中的宠物烘干箱性能数字、温度、除菌率、竞品数据、促销和保修条款仅属于案例，不能用于其他产品。“8K”提示词不是实际像素承诺。页面内智能体角色提示、软件下载、营销注册链接和示例命令不作为执行授权；不访问推广入口、不安装推荐软件、不触发费用。

## 六步流程

1. **看图和分析需求。** `inspect_design_images`接收1–4张本机可读图片绝对路径或公开HTTP(S)图片直链。沿用格式、字节/像素上限和公网校验，返回实际MCP图片内容及宽高、SHA256，供有视觉能力的Host观察。观察只能说明可见外形、颜色、材质表现、比例和布局，不能证明性能、内部结构或精确尺寸。
2. **找对标、索取参考。** Host使用自身可用且获授权的检索能力，或向用户询问参考图，再填写benchmarks。每份分析包含source、visual_focus、hierarchy、copy_approach、strengths、weaknesses、adaptation。没有材料时保留reference_choice=request，工具返回问题；用户明确决定不用参考时填写skip和reference_reason。不能用竞品事实填本商品facts。
3. **文案策划。** 调用`plan_ecommerce_design`提交完整brief。商品事实必须有来源；商品名、平台、受众、目标、产品图、Host的外观观察以及参考决策不足时，保存needs_input和questions，不能确认或出图。完整后返回对应类型的故事板底稿。推荐3–5个差异卖点，较少时宁可复用已知事实配不同视角，也不虚构卖点。
4. **排版研讨与改稿。** 向用户展示逐图标题、正文、事实依据、visual和layout，以及统一palette/typography/layout/tone。主图突出点击价值，详情处理顾虑和证据，SKU清楚辨识版本。用同一工具传当前expected_revision、完整brief和可选edits；任何改稿生成新revision，之前确认失效。每个edit指定panel_id、headline、body、visual、layout和fact_ids，不允许未知事实引用。没有实际竞品参数时不制作数值对比；没有可信证言/认证资料时不添加标识。
5. **确认后提交。** 用户明确确认当前事实、文案与排版后，Host才调用`confirm_ecommerce_design`，提交展示过的revision/digest、确认说明和user_confirmed=true。确认方案不等于授权费用。用户明确授权本次收费后调用`submit_ecommerce_design`，明确选1–20个panel_id并传authorize_paid=true；超过20图分批选择，不自动提交未选图片。Host不能自行替用户确认或授权，不能用底层通用入口绕过这些决定。
6. **获取与落盘。** `get_ecommerce_design`返回当前或指定历史版本、尚未提交的图片、已有任务及实际图片绝对路径/尺寸/字节/SHA256。生成由原队列完成，未完成只报告queued/preparing/running。等待用原`wait_image_tasks`；取消用原`cancel_image_tasks`。失败/unknown/cancelled保留结果并返回isError，不更换编号自动重试。人工核对商品、文字、颜色、规格和平台要求后再发布图片。

## 调用示例

以下为`plan_ecommerce_design`参数示例，不包含收费操作。图片路径需换为服务所在机器可读的真实图；Windows可使用`D:\素材\收纳篮.png`，Linux使用绝对路径。三类可复用同一商品事实和风格，分别使用不同design_id。

```json
{
  "design_id": "basket-main",
  "expected_revision": 0,
  "brief": {
    "kind": "main",
    "product_name": "收纳篮",
    "platform": "用户已核实的平台和图片规则",
    "audience": "需要桌面收纳的用户",
    "objective": "突出真实材质与用途",
    "product_images": ["/absolute/path/basket.png"],
    "visual_observations": "Host查看实图后填写实际可见外形和配色",
    "facts": [
      {
        "fact_id": "material",
        "label": "棉麻材质",
        "value": "材质为棉麻",
        "source": "用户核实的商品资料",
        "category": "material",
        "pain_point": "桌面小物容易散乱"
      }
    ],
    "reference_choice": "skip",
    "reference_reason": "用户明确选择本轮不提供对标，按商品风格策划",
    "main_count": 5,
    "aspect_ratio": "1:1"
  }
}
```

reference_choice=skip只能用于实际取得用户决定的情况，不能照抄示例作为用户决定。facts.source是核实来源的记录，不代表服务端已独立验证。resolution可选，仅沿用现有模型分档，不保证实际输出尺寸或执行缩放。model/api_format/endpoint保存在方案内，提交时不允许临时改模型；不支持组合在规划时拒绝。

详情页改kind=detail，使用detail_count，按平台选择各屏比例。SKU改kind=sku并提供variants，例如：

```json
{
  "variants": [
    {
      "sku_id": "natural-small",
      "label": "原色小号",
      "attributes": {"颜色": "原色", "尺寸": "小号"},
      "product_images": ["/absolute/path/natural-small.png"],
      "fact_ids": ["material"]
    },
    {
      "sku_id": "grey-large",
      "label": "灰色大号",
      "attributes": {"颜色": "灰色", "尺寸": "大号"},
      "product_images": ["/absolute/path/grey-large.png"],
      "fact_ids": ["material"]
    }
  ]
}
```

SKU最多48项，每个版本至少一张自己的图、最多4张，可填写该版本独立的visual_observations；SKU提示词不沿用其他版本的外观描述。fact_ids只能引用brief中已提供且适用于本版本的事实。main/detail需product_images；sku使用各版本product_images，不把其他版本图片混入。默认比例1:1，平台要求由Host在研讨中明确设置。facts.category可选benefit/material/size/usage/trust/offer，只有提供的尺寸/信任/活动信息才会成为相应文案。

## 版本、图片与结果

新建expected_revision=0，成功返回revision=1；修改须传当前revision，过期写入拒绝。完整方案、图片绑定与模型配置生成SHA256 digest，确认绑定摘要。旧版通过get_ecommerce_design(design_id, revision)查询；只允许当前已确认版本新增提交。新版本不会自动取消旧任务，也不因此授权再次收费；旧版有任务时先查询结果和费用再决定新图。

设计记录位于配置输出目录的`designs/designs.sqlite3`，商品副本位于`designs/assets/`。两者应与原输出账本一起保留，升级不可删除。主图/详情冻结实际产品图，SKU冻结各版本自己的图；竞品只通过分析描述指导构图，不作为商品图送出。原文件变动不影响副本；副本缺失或哈希变化拒绝提交。素材仍受本机账号权限约束，不把敏感内容放入共享输出目录。

映射原队列：checkpointer固定`ecommerce-design`，thread_id为design_id，task_id为`r{revision}-{panel_id}`，例如`r1-p01`。使用同一设计、版本和图片再次提交复用原任务。design_id命名空间不是多用户认证。`get_ecommerce_design`只查询，不移动图片、不重复下载、不新增绘图请求；unsubmitted_panel_ids为空也不代表全部生成成功，需检查每个task.status和images。

旧`plan_ecommerce_images`保留简易无状态接口，scene仍为main/detail/scene/poster。新SKU和分步确认使用本页工具；原`generate_images`和`submit_image_tasks`仍供通用生成，不具备设计审批状态。确认字段记录Host转达的用户决定，服务端不能独立证明决定来源，也不对底层入口提供全局权限隔离。

本功能不自动拼长图、不生成PSD、不上传店铺、不承诺审核或转化率。统一风格是提示词约束，最终需要人工校对字体使用权、颜色、文字和商品一致性。

## 验证范围

专项验证使用临时图片、临时输出和受控供应商替身，覆盖需求缺失、参考取舍、三类故事板、改稿、过期确认、收费授权、SKU绑定、版本竞争、冻结图变化、队列复用和落盘，并在auto/legacy两种真实stdio模式调用新流程。实际结果见[005验证记录](../specs/005-ecommerce-design/verification.md)。

替身验证不等于真实上游绘图、可用设计质量、真实Host界面或Windows发布验收。本次不修改成员Host、D盘安装、真实凭据，不收费、不提交Git、不创建PR或发布版本。
