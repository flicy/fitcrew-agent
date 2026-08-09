# FitCrew V2 User-Facing Release Story Design / FitCrew V2 用户视角发布叙事设计

## 中文

### 1. 目标

修正 FitCrew V2 当前公开材料中过度强调工程 Alpha、CI、部署与配对机制的问题，恢复一直不变的产品定义：

- **FitCrew · AI 健身管理专家**
- **BodyOS 是用户在飞书中接触到的私人生活方式教练**

V2 的公开叙事必须先回答“用户现在可以用它做什么”，工程验证只能作为末尾的可信依据。README、GitHub `v2.0.0` Release、小红书/公众号发布文案与产品落地页采用同一套定义、功能顺序和隐私边界。

### 2. V2 的四项用户能力

1. **自动汇集身体数据**：在用户主动授权后，通过 iPhone 上的 HealthKit Bridge 读取汇入 Apple Health 的 Apple Watch 与鱼跃 Anytime 5 Pro 血糖仪数据。对外不宣称存在独立 watchOS App，也不把 Apple 设备或健康授权写成使用 FitCrew 的前提。
2. **理解食物、血糖与身体感知**：用户可以在 BodyOS 私聊中询问今天吃的食物、血糖变化和主观身体感知之间可能存在的生活方式关系。BodyOS 结合用户授权的数据与知识库提供可执行建议，不进行疾病诊断、治疗或用药判断。
3. **在群聊里进行健康互动**：BodyOS 可以在群聊中回答通用的饮食、训练、睡眠与控糖知识问题，也可以参与打卡和日常健康互动。群聊不读取用户个人健康数据、私聊内容或私人知识库，不公开任何原始健康数值。
4. **获得科学书籍指导**：私人知识库明确收录并使用《控糖革命》《百岁人生行动手册》《睡眠优化完全指南：科学与实践》。回答应基于书中内容并在系统可取得页码时提供来源，不把书籍观点包装成医疗结论。

### 3. README 信息架构

README 中文与英文保持语义一致，按以下顺序重写：

1. 首屏标题与一句话定位：FitCrew 是 AI 健身管理专家；BodyOS 是飞书里的私人生活方式教练。
2. “V2 现在能做什么”：用用户语言展示上述四项能力。
3. “怎么使用”：群聊用于通用知识与共同坚持；私聊用于基于授权数据的个人生活方式分析。
4. “科学依据”：列出三本书及知识库的来源机制。
5. “数据与隐私”：Apple Health 授权可选；个人数据不进群；原始字段加密；不做医疗诊断。
6. “开发者与验证”：最后才列组件、测试、部署状态、TestFlight 边界与本地运行命令。

README 不再用“两用户 Alpha”“一次性配对”“CI 全绿”作为开场，也不把尚未完成的 TestFlight 或 16 天实验放在首屏阻断产品理解。这些信息保留在开发者章节，确保事实透明。

### 4. GitHub Release 与社交发布内容

现有 `v2.0.0` Release 原位更新，不新建或移动标签。Release 的中文与英文内容先写四项用户能力，再写隐私/医疗边界，最后用短段落记录工程验证与尚未完成事项。

小红书和公众号采用“我把 Apple Watch、血糖仪和三本书接进了飞书里的私人生活方式教练”这一用户实验叙事：

- 小红书突出真实使用场景、四项新增能力和可感知变化，避免发布成技术周报。
- 公众号解释为什么数据、身体感知与科学知识需要放在同一个持续对话里，再介绍 FitCrew 与 BodyOS 的分工。
- 两处都不得宣称已经完成 16 天实验、已经通过 TestFlight 外部分发、获得医疗效果或能替代医生。

### 5. 产品落地页更新

页面来源为 `flicy/cola-pages` 仓库 `gh-pages` 分支的 `fitcrew/index.html`。保持现有绿色叶子视觉、单页结构、响应式布局和已有链接，不重新设计品牌。

具体更新：

1. 导航增加“V2 更新”锚点。
2. 在核心能力与路线图之间增加清晰的“V2 已上线”模块，使用四张卡片呈现：Apple Watch + 鱼跃血糖数据、食物 × 血糖 × 身体感知、群聊通用健康问答、三本科学书籍。
3. 路线图把 `v2 · 开发中` 改为 `v2 · 已上线`，内容从“未来零输入”改为已经交付的四项能力；后续版本只保留为简短展望。
4. “专家系统”和“知识共建”区域把模糊的《抗糖革命》/精力管理表述替换为用户确认的三本完整书名。
5. 修正群聊演示和能力描述：允许通用饮食、训练、睡眠、控糖问答与打卡互动，但不声称在群里调用个人健康数据或“结合你的私密情况”。
6. 隐私区域明确区分：群聊回答通用知识；个人数据分析只在对应用户私聊并基于授权数据发生。
7. 增加指向 GitHub `v2.0.0` Release 的“查看版本说明”链接。

### 6. 事实与用词规则

- 产品名称统一为 `FitCrew`，不得写成 `FitClew`。
- 厂商统一为“鱼跃”，设备名使用“鱼跃 Anytime 5 Pro”。
- 中文书名严格使用：《控糖革命》《百岁人生行动手册》《睡眠优化完全指南：科学与实践》。
- 用户视角可以说“采集 Apple Watch 和鱼跃血糖仪的数据”，技术说明需写清数据经 Apple Health / HealthKit 授权通道读取，避免暗示未经授权的直连。
- `BodyOS` 是用户接触到的教练；Moticlaw/Hermes/Codex 是实现层，不进入首屏产品定位。
- BodyOS 提供生活方式指导，不提供医疗诊断、治疗或用药建议。

### 7. 验收标准

- README 和 Release 的首屏先出现稳定产品定位与四项 V2 能力，工程术语只在后部出现。
- README、Release、社交文案、落地页对四项能力的名称、顺序、书名和群聊边界一致。
- 落地页在桌面和移动端均能直接看到“V2 已上线”，原有绿色叶子品牌与链接不受损。
- 页面不再出现 `v2 · 开发中`，不再把群聊描述为可以读取个人健康数据。
- 所有仓库 Markdown 保持中英文双语；HTML 中的公开中文内容不新增未经确认的医疗或效果主张。
- FitCrew Agent 仓库和 Cola Pages 仓库分别通过独立 PR 合并；更新现有 GitHub Release 前核对它指向的 `v2.0.0` 标签不变。

## English

### 1. Goal

Correct the current FitCrew V2 public material, which leads with engineering Alpha status, CI, deployment, and pairing mechanics. Restore the stable product definition:

- **FitCrew · AI Fitness Management Expert**
- **BodyOS is the private lifestyle coach people meet in Feishu**

The V2 story must first explain what a person can do today. Engineering evidence belongs at the end. The README, GitHub `v2.0.0` Release, Xiaohongshu/WeChat copy, and product landing page must use the same definitions, capability order, and privacy boundary.

### 2. Four user-facing V2 capabilities

1. **Bring body data together automatically:** with explicit permission, the iPhone HealthKit Bridge reads Apple Watch and Yuwell Anytime 5 Pro glucose data that reaches Apple Health. Public copy must not claim a separate watchOS app or make Apple hardware and health authorization prerequisites for all FitCrew use.
2. **Understand food, glucose, and body perception:** in a BodyOS DM, a person can ask about possible lifestyle relationships between today's food, glucose changes, and subjective body perception. BodyOS combines authorized data with the knowledge base to suggest practical actions; it does not diagnose, treat, or advise on medication.
3. **Interact in group chat:** BodyOS can answer general questions about food, training, sleep, and glucose management in groups and participate in check-ins and routine health interaction. It never reads personal health data, DMs, or private knowledge in a group, and it never exposes raw health values there.
4. **Use scientific book guidance:** the private knowledge base explicitly includes *Glucose Revolution*, *The 100-Year Life Action Handbook*, and *The Complete Guide to Sleep Optimization: Science and Practice* under their confirmed Chinese titles. Answers use these sources and cite pages when available without presenting a book claim as a medical conclusion.

### 3. README information architecture

The Chinese and English README sections remain semantically aligned and follow this order:

1. Product title and one-line definition.
2. “What V2 can do now,” expressed through the four user capabilities.
3. “How to use it”: groups for general knowledge and shared consistency; DMs for personal lifestyle analysis based on authorized data.
4. “Scientific basis”: the three books and source mechanism.
5. “Data and privacy”: optional Apple Health permission, no personal data in groups, encrypted raw fields, and no diagnosis.
6. “Developer and verification”: components, tests, deployment status, TestFlight boundaries, and local commands at the end.

The README no longer opens with “two-user Alpha,” one-time pairing, or green CI. TestFlight and the 16-day study remain transparently documented in the developer section without blocking comprehension of the product.

### 4. GitHub Release and social copy

Edit the existing `v2.0.0` Release in place without creating or moving a tag. Chinese and English release text lead with the four capabilities, then privacy/medical boundaries, followed by a short engineering-evidence and incomplete-items section.

Xiaohongshu and WeChat use the personal experiment story, “I connected Apple Watch, a glucose monitor, and three books to a private lifestyle coach in Feishu.” Xiaohongshu emphasizes real usage and perceptible value; WeChat explains why data, body perception, and scientific knowledge belong in one continuous conversation. Neither channel claims a completed 16-day study, external TestFlight availability, a health outcome, or replacement of medical care.

### 5. Product landing-page update

The page source is `fitcrew/index.html` on the `gh-pages` branch of `flicy/cola-pages`. Preserve the green-leaf identity, single-page structure, responsive behavior, and existing links.

Add a “V2 update” navigation anchor and a visible “V2 is live” four-card section. Change the roadmap from `v2 · in development` to `v2 · live`. Replace vague book references with the three confirmed titles. Correct group-chat demonstrations so they cover general knowledge and check-ins without implying access to personal health data. Clarify that personal analysis happens only in the corresponding DM with authorization. Add a link to the existing GitHub `v2.0.0` Release.

### 6. Fact and terminology rules

Use `FitCrew`, “Yuwell,” and the three exact confirmed Chinese book titles. User-facing copy may say Apple Watch and glucose-monitor data collection; technical copy must explain the authorized Apple Health / HealthKit route. BodyOS is the coach-facing product; Moticlaw, Hermes, and Codex stay in the implementation layer. BodyOS offers lifestyle guidance, not diagnosis, treatment, or medication advice.

### 7. Acceptance criteria

- README and Release lead with the stable product definition and four V2 capabilities.
- README, Release, social copy, and landing page agree on capability order, book titles, and group privacy.
- The landing page visibly says V2 is live on desktop and mobile without damaging the green-leaf brand or links.
- No `v2 · in development` remains, and no group copy implies personal-health access.
- Repository Markdown remains bilingual; public HTML adds no unconfirmed medical or outcome claim.
- FitCrew Agent and Cola Pages changes use separate PRs; editing the existing Release must not move the `v2.0.0` tag.
