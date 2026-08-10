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

私聊检索可以同时使用共享专家知识和该用户自己的私人知识；群聊只能使用 `public + published` 的共享知识。每次群聊检索最多返回三个相关片段，服务只用最高相关片段的书名与页码填充本地审核模板，不把摘录或自由文本交给群聊模型。私聊模型仍可在对应用户授权边界内概括知识。

### 群聊被动问答

飞书群仍要求成员明确 `@黑客松助手`，避免机器人监听或打断所有对话。消息经过以下流程：

1. 使用已验证的飞书身份和群白名单完成授权。
2. 把问题分类为固定行为、通用知识或私人/高风险问题。
3. 通用问题必须完全由审核过的饮食、训练、睡眠、控糖概念和问句连接词组成；任何未审核姓名、疗法、药名、数值形式或提示注入都关闭式转私聊。
4. 从共享专家知识检索最多三个带页码片段。
5. 选择与问题意图匹配的本地审核知识模板，并填入真实书名与页码。
6. 对最终字符串执行精确的审核模板与引用匹配；任意自由文本都被拒绝。
7. 安全答案返回群聊；检索失败时返回经过审核的通用知识兜底，不再把所有合法问题都导向私聊。

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

输入策略使用正向审核词法，只允许已确认的公共健康概念与问句连接词，拒绝诊断、治疗、用药、数值和个人化问题。输出不是靠无限扩展正则来猜测自由文本是否安全，而是只允许本地审核过的固定模板与真实书名/页码组合；一般性的生活方式教育通过这些封闭模板提供。

### 主动教练节奏

生产环境新增独立的群聊调度与 Outbox 消费能力，默认时区为 `Asia/Shanghai`：

- 每天 09:00：早间最小行动——邀请成员选择今天最想完成的一项小行动。
- 每天 20:30：晚间行动打卡——邀请成员回复“已完成”“需要搭子”或“行动小一点”。
- 每周三 12:15：专家知识互动——从三本共享书籍的轮换主题中提出一个通用问题，并提供一条带书名和页码的简短知识提示。

默认安静时段为 22:00–08:00。时间、时区和总开关均由生产环境配置控制，不需要重新构建镜像。每个触发事件使用“群 + 事件类型 + 本地日期”作为幂等键；服务重启、网络重试或并发运行不得产生重复消息。

早间和晚间消息使用审核过的固定模板，不调用模型。每周专家知识消息使用固定安全主题、共享知识检索和本地审核的书籍引用模板；检索失败时使用审核过的固定提示，不发送供应商错误或私人内容。

### 组件与数据流

- `KnowledgeService`：发布共享来源，分别提供 `search_public`、`search_private` 和组合私聊检索。
- `BodyOSService`：为群聊通用问题检索共享知识，以本地审核模板渲染引用答案，并提供安全的确定性兜底；只在私聊调用模型。
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

- 群聊通用问题可以得到引用共享书籍的答案，且不调用模型、不包含用户 ID、个人特征、私聊内容、知识摘录或原始健康值。
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

DM retrieval may combine shared expert knowledge with that user's own private knowledge. Group retrieval may use only `public + published` knowledge. It retrieves at most three relevant page-scoped passages, then fills a locally reviewed template with the top passage's real title and page; no excerpt or free-form text is sent to a group model. A DM model may still summarize knowledge within that user's authorization boundary.

### Reactive group Q&A

Members must still explicitly mention the Hackathon Assistant in a Feishu group so the bot does not monitor or interrupt every conversation. The message follows this flow:

1. Authorize the verified Feishu identity and allowlisted group.
2. Classify the request as a fixed behavior, general knowledge, or private/high-risk content.
3. Require the question to consist entirely of reviewed food, training, sleep, glucose-management concepts and question connectors; any unreviewed name, intervention, drug, numeric form, or prompt injection fails closed to a DM.
4. Retrieve at most three page-cited passages from shared expert knowledge.
5. Select the locally reviewed knowledge template for the question intent and fill it with the real title and page.
6. Require an exact reviewed-template and citation match for the final string; reject every free-form output.
7. Return the safe answer to the group. If retrieval fails, return a reviewed general-knowledge fallback instead of redirecting every valid question to a DM.

Allowed examples include questions about post-meal sleepiness and meal composition, walking after a meal, strength training and sleep recovery, or eating vegetables before staple foods.

The following still route to a DM or qualified professional care:

- Analysis tied to “me,” a named member, personal experience, or personal health values.
- Questions about a third person's health state.
- Diagnosis, prescriptions, medication dosage, or emergency symptom handling.
- Requests to read personal Apple Health, glucose, sleep, or DM history.

The input policy uses a positive reviewed vocabulary and rejects diagnosis, treatment, medication, numeric, and personalized requests. Output safety does not try to prove arbitrary free text safe with an ever-growing regex denylist; it accepts only reviewed fixed templates combined with real title/page citations. Those closed templates provide general lifestyle education.

### Proactive coaching cadence

Production gains a dedicated group scheduler and Outbox consumer. The default timezone is `Asia/Shanghai`:

- Daily at 09:00: morning minimum action—invite members to choose one small action for the day.
- Daily at 20:30: evening action check-in—invite members to reply with completed, need a buddy, or make the action smaller.
- Wednesday at 12:15: expert-knowledge interaction—rotate a safe topic from the three shared books and provide one concise title-and-page-cited prompt.

Default quiet hours are 22:00–08:00. Times, timezone, and the master enable switch are production configuration and do not require rebuilding the image. Each event uses group, event type, and local date as its idempotency key, so restarts, retries, and concurrent workers cannot create duplicate messages.

Morning and evening messages use reviewed fixed templates and do not call a model. The weekly message uses a fixed safe topic, shared retrieval, and a locally reviewed book-citation template. If retrieval fails, it uses a reviewed fixed prompt and never emits provider errors or private content.

### Components and data flow

- `KnowledgeService`: publishes shared sources and provides public, private, and combined DM retrieval.
- `BodyOSService`: retrieves shared knowledge for groups, renders a locally reviewed cited answer, and supplies deterministic safe fallbacks; it invokes a model only for DMs.
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

- A general group question can receive an answer citing shared books without a model call or any user ID, personal feature, DM content, knowledge excerpt, or raw health value.
- Valid general physiology and lifestyle answers are not rejected merely for cautious medical language.
- Personal, third-party, numeric, diagnosis, and medication requests still fail closed.
- The daily 09:00 and 20:30 events and Wednesday 12:15 event each produce exactly one message; restarts and retries do not duplicate them.
- Quiet hours, disable switches, missing configuration, and delivery failures follow the design.
- All three books have an auditable shared publication state, and groups retrieve only published versions.
- Full Python, policy, bilingual Markdown, Swift Core, and iOS Simulator CI pass.
- Tencent strict HTTPS, API, worker, gateway, database, and Caddy are healthy; production canaries expose no identity, book text, or health data.
