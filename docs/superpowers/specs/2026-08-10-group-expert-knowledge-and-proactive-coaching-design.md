# BodyOS 群聊专家知识与主动教练设计 / BodyOS Group Expert Knowledge and Proactive Coaching Design

## 中文

### 目标

本次改动让 BodyOS 在飞书群聊中可靠完成两件事：

1. 使用经过审核的共享专家知识回答通用饮食、训练、睡眠与控糖问题。
2. 按低打扰节奏主动发起早间行动、晚间打卡和每周专家知识互动。

个人健康数据、个人身体感知、私聊历史和原始健康数值仍只属于对应用户的 BodyOS 私聊。群聊不会因为启用共享知识或主动触发而获得任何个人数据访问权。

### 当前问题与根因

- 三本已导入书籍当前以 `private` 可见性绑定在 Owner 名下；群聊信封明确禁止私人知识，因此群聊只能使用模型基础知识。
- 群聊输出安全门禁把部分出现在正常科普或免责声明中的医疗词也视为敏感内容，导致合法通用回答被整条丢弃并降级为“个性化健康建议请私聊 BodyOS”。
- `cron/jobs.seed.json` 中的五分钟任务只是轮询新的 `@BodyOS` 消息，不会主动发消息。
- 腾讯云运行时只启动 API、维护 Worker、Hermes Gateway、数据库和 Caddy；部署流程没有安装上述 Hermes cron。
- 维护 Worker 会生成少量研究周期 Outbox 事件，但当前没有飞书群聊发送消费者。因此生产环境不存在完整的主动触发闭环。

### 共享专家知识

“公共专家知识”在这里表示 **BodyOS 产品内所有已授权用户可使用的共享知识**，不表示公开网页下载、公开传播 PDF 或向模型提供整本书。

首批共享来源为：

- 《控糖革命》
- 《百岁人生行动手册》
- 《睡眠优化完全指南：科学与实践》

现有知识来源经一次明确的发布操作进入 `public + published` 状态，并移除用户所有权。发布操作必须保留来源版本、内容哈希、权利状态和审核记录。书籍原文不进入 Git、日志、群聊历史或公共网页。

私聊检索可以同时使用共享专家知识和该用户自己的私人知识；群聊只能使用 `public + published` 的共享知识。每次检索最多返回三个相关片段，模型负责概括，不输出长段原文，并保留书名和页码引用。

### 群聊被动问答

飞书群仍要求成员明确 `@黑客松助手`，避免机器人监听或打断所有对话。消息经过以下流程：

1. 使用已验证的飞书身份和群白名单完成授权。
2. 把问题分类为固定行为、通用知识或私人/高风险问题。
3. 通用问题完成标识符、联系方式、个人数值和提示注入清理。
4. 从共享专家知识检索最多三个带页码片段。
5. 构造不含用户身份、健康特征、私聊历史和原始数据的 `bodyos-public.v2` 信封。
6. 通过 Codex 主路由和 Hermes 备用路由生成简短中文回答。
7. 对答案执行身份、个人化、原始数值、诊断、用药、基础设施错误和控制字符检查。
8. 安全答案返回群聊；模型不可用或答案被拒绝时返回经过审核的通用知识兜底，不再把所有合法问题都导向私聊。

以下问题属于群聊允许范围：

- “饭后犯困可能和餐食结构有什么关系？”
- “为什么饭后散步有助于控糖？”
- “力量训练和睡眠恢复有什么关系？”
- “先吃蔬菜再吃主食有什么依据？”

以下内容仍转到私聊或建议咨询专业人员：

- 带有“我/某位成员”身份、个人经历或个人健康数值的分析。
- 询问第三人的健康状态。
- 疾病诊断、处方、药物剂量或紧急症状处置。
- 要求读取个人 Apple Health、血糖、睡眠或私聊历史。

输出安全策略从“命中任意医疗词即拒绝”改为“拒绝诊断、治疗、用药和个人化结论”。一般性的生理机制、生活方式教育和谨慎免责声明允许出现。

### 主动教练节奏

生产环境新增独立的群聊调度与 Outbox 消费能力，默认时区为 `Asia/Shanghai`：

- 每天 09:00：早间最小行动——邀请成员选择今天最想完成的一项小行动。
- 每天 20:30：晚间行动打卡——邀请成员回复“已完成”“需要搭子”或“行动小一点”。
- 每周三 12:15：专家知识互动——从三本共享书籍的轮换主题中提出一个通用问题，并提供一条带书名和页码的简短知识提示。

默认安静时段为 22:00–08:00。时间、时区和总开关均由生产环境配置控制，不需要重新构建镜像。每个触发事件使用“群 + 事件类型 + 本地日期”作为幂等键；服务重启、网络重试或并发运行不得产生重复消息。

早间和晚间消息使用审核过的固定模板，不调用模型。每周专家知识消息使用固定安全主题、共享知识检索和群聊公共答案门禁；模型或检索失败时使用审核过的固定提示，不发送供应商错误或私人内容。

### 组件与数据流

- `KnowledgeService`：发布共享来源，分别提供 `search_public`、`search_private` 和组合私聊检索。
- `BodyOSService`：为群聊通用问题构造带共享知识的公共信封，并提供安全的确定性兜底。
- `GroupCoachScheduler`：根据上海时间生成到期事件，只写入无个人信息的 Outbox。
- `FeishuGroupDispatcher`：使用现有飞书应用凭据和已配置群白名单发送经过检查的群消息，不接受任意群 ID。
- 维护 Worker：以短周期检查到期触发与待发送 Outbox，同时保留原有六小时维护和研究检查点。

主动消息的 Outbox 只保存事件类型、模板/知识主题、目标群配置引用、计划时间、尝试次数和状态，不保存成员身份、健康数据或群聊内容。

### 失败与隐私处理

- 飞书发送失败最多进行三次有界重试；超过上限后保留无内容错误码供运维查看。
- 日志不得输出飞书凭据、群 ID、成员 ID、消息正文、知识原文或健康数据。
- 共享知识检索失败不会回退到私人知识。
- 未配置群白名单、凭据或启用开关时，主动发送安全关闭。
- 主动消息不 `@` 个人、不引用个人行为、不根据个人健康数据选择内容。
- 成员通过固定打卡词回复时，继续走现有确定性行为 token；个人解释和建议进入私聊。

### 验收标准

- 群聊通用问题可以得到引用共享书籍的答案，且信封不包含用户 ID、个人特征、私聊内容或原始健康值。
- 合法的通用生理机制和生活方式回答不会仅因出现谨慎医疗措辞而被拒绝。
- 个人、第三人、数值、诊断和用药问题仍安全关闭。
- 每日 09:00、20:30 和每周三 12:15 各只产生一条消息；重启与重试不会重复。
- 安静时段、禁用开关、缺少配置和发送失败均按设计处理。
- 三本书全部处于可审计的共享发布状态，群聊只能检索已发布版本。
- 全量 Python、策略、双语 Markdown、Swift Core 和 iOS Simulator CI 通过。
- 腾讯云严格 HTTPS、API、Worker、Gateway、数据库和 Caddy 健康；生产 canary 不输出身份、书籍原文或健康数据。

## English

### Goal

This change makes BodyOS reliably do two things in Feishu groups:

1. Answer general food, training, sleep, and glucose-management questions with reviewed shared expert knowledge.
2. Proactively initiate a morning action, an evening check-in, and a weekly expert-knowledge interaction at a low-interruption cadence.

Personal health data, personal body perceptions, DM history, and raw health values remain exclusive to the corresponding user's BodyOS DM. Enabling shared knowledge or proactive messages does not grant a group any access to personal data.

### Current problems and root causes

- The three imported books currently have `private` visibility and belong to the Owner. Public group envelopes prohibit private knowledge, so groups can use only the model's base knowledge.
- The group output gate treats some medical words found in ordinary education or cautious disclaimers as sensitive. Valid general answers are therefore discarded and replaced by the generic DM redirect.
- The five-minute job in `cron/jobs.seed.json` only polls for new `@BodyOS` messages; it does not initiate messages.
- The Tencent runtime starts the API, maintenance worker, Hermes gateway, database, and Caddy. Its deployment path does not install that Hermes cron job.
- The maintenance worker creates a small number of study Outbox events, but no Feishu group consumer exists. Production therefore has no complete proactive-delivery loop.

### Shared expert knowledge

“Public expert knowledge” means **shared knowledge available to all authorized BodyOS users inside the product**. It does not mean publicly downloadable PDFs, public redistribution, or sending a whole book to a model.

The initial shared sources are:

- *Glucose Revolution*
- *The 100-Year Life Action Handbook*
- *The Complete Guide to Sleep Optimization: Science and Practice*

An explicit publication operation moves each existing source into the `public + published` state and removes user ownership. Publication retains the source version, content hash, rights status, and review record. Book text never enters Git, logs, public web pages, or unbounded group history.

DM retrieval may combine shared expert knowledge with that user's own private knowledge. Group retrieval may use only `public + published` knowledge. A retrieval returns at most three relevant page-scoped passages. The model summarizes rather than reproducing long passages and preserves title and page citations.

### Reactive group Q&A

Members must still explicitly mention the Hackathon Assistant in a Feishu group so the bot does not monitor or interrupt every conversation. The message follows this flow:

1. Authorize the verified Feishu identity and allowlisted group.
2. Classify the request as a fixed behavior, general knowledge, or private/high-risk content.
3. Remove identifiers, contact details, personal values, and prompt-injection material from a general question.
4. Retrieve at most three page-cited passages from shared expert knowledge.
5. Build a `bodyos-public.v2` envelope without user identity, personal features, DM history, or raw data.
6. Generate a concise Chinese answer through the Codex primary route and Hermes fallback.
7. Check the answer for identity, personalization, raw values, diagnosis, medication, infrastructure errors, and control characters.
8. Return a safe answer to the group. If the model is unavailable or the answer is rejected, return a reviewed general-knowledge fallback instead of redirecting every valid question to a DM.

Allowed examples include questions about post-meal sleepiness and meal composition, walking after a meal, strength training and sleep recovery, or eating vegetables before staple foods.

The following still route to a DM or qualified professional care:

- Analysis tied to “me,” a named member, personal experience, or personal health values.
- Questions about a third person's health state.
- Diagnosis, prescriptions, medication dosage, or emergency symptom handling.
- Requests to read personal Apple Health, glucose, sleep, or DM history.

The output policy changes from “reject any medical word” to “reject diagnosis, treatment, medication, and personalized conclusions.” General physiological mechanisms, lifestyle education, and cautious disclaimers are allowed.

### Proactive coaching cadence

Production gains a dedicated group scheduler and Outbox consumer. The default timezone is `Asia/Shanghai`:

- Daily at 09:00: morning minimum action—invite members to choose one small action for the day.
- Daily at 20:30: evening action check-in—invite members to reply with completed, need a buddy, or make the action smaller.
- Wednesday at 12:15: expert-knowledge interaction—rotate a safe topic from the three shared books and provide one concise title-and-page-cited prompt.

Default quiet hours are 22:00–08:00. Times, timezone, and the master enable switch are production configuration and do not require rebuilding the image. Each event uses group, event type, and local date as its idempotency key, so restarts, retries, and concurrent workers cannot create duplicate messages.

Morning and evening messages use reviewed fixed templates and do not call a model. The weekly message uses a fixed safe topic, shared retrieval, and the public group answer gate. If retrieval or the model fails, it uses a reviewed fixed prompt and never emits provider errors or private content.

### Components and data flow

- `KnowledgeService`: publishes shared sources and provides public, private, and combined DM retrieval.
- `BodyOSService`: builds public envelopes with shared knowledge and supplies deterministic safe fallbacks.
- `GroupCoachScheduler`: creates due events in Shanghai time and writes only content-free or general-knowledge Outbox records.
- `FeishuGroupDispatcher`: sends checked group messages with the existing Feishu app credentials and configured group allowlist; it never accepts an arbitrary group ID.
- Maintenance worker: checks due triggers and pending Outbox events at a short interval while preserving the existing six-hour maintenance and study checkpoints.

The proactive Outbox stores only event type, template or knowledge topic, configured group reference, scheduled time, attempt count, and status. It stores no member identity, health data, or group conversation content.

### Failure and privacy handling

- Feishu delivery receives at most three bounded retries. Exhausted events keep only a content-free operations error code.
- Logs never print Feishu credentials, group IDs, member IDs, message bodies, book passages, or health data.
- Failed shared retrieval never falls back to private knowledge.
- Missing allowlist, credentials, or enable configuration fails closed.
- Proactive messages never mention individuals, cite personal behavior, or select content from personal health data.
- Fixed check-in replies continue through deterministic behavior tokens; personal interpretation and recommendations belong in DMs.

### Acceptance criteria

- A general group question can receive an answer citing shared books, while its envelope contains no user ID, personal feature, DM content, or raw health value.
- Valid general physiology and lifestyle answers are not rejected merely for cautious medical language.
- Personal, third-party, numeric, diagnosis, and medication requests still fail closed.
- The daily 09:00 and 20:30 events and Wednesday 12:15 event each produce exactly one message; restarts and retries do not duplicate them.
- Quiet hours, disable switches, missing configuration, and delivery failures follow the design.
- All three books have an auditable shared publication state, and groups retrieve only published versions.
- Full Python, policy, bilingual Markdown, Swift Core, and iOS Simulator CI pass.
- Tencent strict HTTPS, API, worker, gateway, database, and Caddy are healthy; production canaries expose no identity, book text, or health data.
