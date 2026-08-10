# FitCrew · AI 健身管理专家

> **BodyOS 是你在飞书中接触到的私人生活方式教练。**
> **BodyOS is the private lifestyle coach you meet in Feishu.**

[产品介绍](https://flicy.github.io/cola-pages/fitcrew/) · [V2 版本说明](https://github.com/flicy/fitcrew-agent/releases/tag/v2.0.0)

## 中文

FitCrew 把持续汇集的身体数据、你的主观感受和科学知识放进同一段长期对话里，帮助你看懂生活方式与身体状态之间可能存在的关系，并把建议落实成今天能做的小行动。

BodyOS 不是一个只会回答问题的 AI 客服。它是运行在飞书里的私人生活方式教练：群聊时陪大家一起行动和学习，私聊时在你主动授权的边界内理解你的身体数据与感受。

### V2 现在能做什么

1. **汇集 Apple Watch 与鱼跃血糖数据**
   经你授权，iPhone HealthKit Bridge 读取已经进入 Apple Health 的 Apple Watch 与鱼跃 Anytime 5 Pro 数据。Apple 设备和健康授权都不是使用 FitCrew 群聊能力的前提。

2. **理解食物 × 血糖 × 身体感知**
   在 BodyOS 私聊中，你可以讨论今天吃了什么、血糖如何变化、自己当时有什么感受。BodyOS 结合授权数据与知识库，帮助你寻找可能的生活方式关系，并给出可执行的小行动。

3. **在群聊里一起行动和学习**
   BodyOS 可以结合已发布的共享专家知识，回答通用的饮食、训练、睡眠与控糖问题，也可以参与打卡和日常健康互动。群聊不会读取或展示任何成员的个人健康数据、私聊内容或私人书摘。

4. **用科学书籍辅助判断**
   BodyOS 的共享专家知识层收录《控糖革命》《百岁人生行动手册》《睡眠优化完全指南：科学与实践》。群聊和私聊都可以在安全边界内引用已审核的书名与页码；原始 PDF 不会公开，也不会把书中观点包装成医疗结论。

5. **主动陪伴群里的健康行动**
   默认按北京时间每天 09:00 发起晨间小行动、20:30 发起晚间打卡，并在每周三 12:15 发起一次公共专家知识互动；22:00–08:00 保持静默。主动消息只包含公共行动与公共知识，不会播报任何成员的健康状态。

### 群聊与私聊怎么分工

| 场景 | 适合做什么 | 明确不做什么 |
| --- | --- | --- |
| 飞书群聊 | 共享专家知识；通用饮食、训练、睡眠、控糖问答；共同打卡；主动健康互动 | 不读取个人健康数据，不引用私聊或私人书摘，不公开原始数值 |
| BodyOS 私聊 | 基于本人授权数据，讨论食物、血糖、睡眠、训练与身体感知 | 不向其他用户泄露，不跨用户调用数据，不进行医疗诊断 |

简单说：**群里谈通用知识与行动，私聊才谈属于你的数据和感受。**

### 数据与隐私

- 飞书账号是主账号，系统用不可变的内部用户 ID 隔离每位用户。
- Apple Health 授权是可选项；没有 Apple 设备或不授权健康数据，也可以使用群聊与非健康数据能力。
- 健康类别按用户、设备和同意状态分别绑定；授权可撤回，跨用户上传会被拒绝。
- 原始健康字段加密保存；模型只接收完成回答所需的聚合特征、意图和知识摘录，不接收姓名、飞书 ID、聊天原文或完整原始健康序列。
- BodyOS 提供生活方式指导，不提供疾病诊断、治疗或用药建议，也不能替代医生。

### 开发者与验证

V2 的用户体验由以下组件组成：

- `apps/api/`：授权、加密摄取、日级特征、知识库、主动群聊调度和 BodyOS 数据边界。
- `apps/ios-bridge/`：HealthKit 最小读取授权、增量同步和实验期对账。
- `integrations/hermes/`：飞书通道、身份隔离、群聊隐私策略和模型路由。
- `infra/tencent/`：腾讯云部署、严格 HTTPS、加密备份与 SHA 回滚。
- `scripts/import_private_books.py`：在 Git 外加密导入本人拥有使用权的 PDF。
- `scripts/publish_shared_books.py`：经人工审核后，仅把指定三本书开放为 BodyOS 内部共享专家知识；不公开文件或正文。

已验证：Python / policy、Swift Core、iOS Simulator CI，以及生产 HTTPS 健康检查。公开端点 <https://124.156.218.104/healthz> 当前报告后端版本 `v2.0.0-alpha.1`。

尚未完成：TestFlight 外部分发、受邀测试者的完整真机验收，以及真实世界 16 天实验结论。项目不宣称已经获得任何健康效果。

```bash
uv sync --extra dev
uv run pytest -q
uv run ruff check apps/api scripts infra/tencent
(cd apps/ios-bridge/Core && swift test)
```

生产与真机操作见 `docs/operations/deployment-and-rollback.md` 和 `docs/experiments/owner-cgm-16-day-runbook.md`。私人 PDF、健康导出、身份信息、OAuth 凭据、飞书密钥、运行环境文件、配对信息和真实健康证据不得进入 Git。

## English

FitCrew brings continuously collected body data, subjective perception, and scientific knowledge into one long-running conversation. It helps people explore possible relationships between lifestyle and body state, then turn guidance into a small action they can take today.

BodyOS is not an AI support bot that forgets after each answer. It is a private lifestyle coach in Feishu: it helps a group learn and act together, while DMs use only the personal data and context that the corresponding person has explicitly authorized.

### What V2 can do now

1. **Bring Apple Watch and Yuwell glucose data together**
   With permission, the iPhone HealthKit Bridge reads Apple Watch and Yuwell Anytime 5 Pro data that has reached Apple Health. Apple hardware and health authorization are not prerequisites for FitCrew's group capabilities.

2. **Understand food × glucose × body perception**
   In a BodyOS DM, a person can discuss what they ate, how glucose changed, and how they felt at the time. BodyOS combines authorized data with the knowledge base to explore possible lifestyle relationships and suggest a practical small action.

3. **Learn and act together in group chat**
   BodyOS can use published shared expert knowledge to answer general questions about food, training, sleep, and glucose management, and it can participate in check-ins and everyday health interaction. A group never reads or exposes personal health data, DMs, or private excerpts.

4. **Use guidance from scientific books**
   The BodyOS shared expert-knowledge layer includes the confirmed Chinese titles *《控糖革命》*, *《百岁人生行动手册》*, and *《睡眠优化完全指南：科学与实践》*. Groups and DMs may cite reviewed title/page references within their safety boundaries. The source PDFs are not made public, and book claims are not presented as medical conclusions.

5. **Proactively support shared health actions**
   By default, BodyOS starts a morning small action at 09:00, an evening check-in at 20:30, and a public expert-knowledge interaction every Wednesday at 12:15, all in Asia/Shanghai time. It stays quiet from 22:00 to 08:00. Proactive messages contain only public actions and knowledge, never any member's health status.

### How groups and DMs divide the work

| Space | Appropriate use | Explicit boundary |
| --- | --- | --- |
| Feishu group | Shared expert knowledge; general food, training, sleep, and glucose-management Q&A; shared check-ins; proactive health interaction | No personal health-data access, no DM or private-excerpt context, and no raw values |
| BodyOS DM | Personal discussion of food, glucose, sleep, training, and body perception based on that person's authorization | No cross-user disclosure, no cross-user data access, and no medical diagnosis |

In short: **groups are for general knowledge and shared action; DMs are where your authorized data and perception belong.**

### Data and privacy

- Feishu is the primary account, and an immutable internal user ID isolates each person.
- Apple Health authorization is optional. People without Apple hardware or health permission can still use group and non-health-data capabilities.
- Health categories bind separately to the person, device, and current consent. Consent can be withdrawn, and cross-user uploads are rejected.
- Raw health fields are encrypted at rest. A model receives only the aggregates, intent, and knowledge excerpts required for the answer—never names, Feishu IDs, raw chats, or a complete raw health series.
- BodyOS provides lifestyle guidance, not disease diagnosis, treatment, or medication advice, and it does not replace a clinician.

### Developer and verification

The V2 experience is composed of:

- `apps/api/`: consent, encrypted ingestion, daily features, the knowledge base, proactive group scheduling, and BodyOS data boundaries.
- `apps/ios-bridge/`: minimum HealthKit read authorization, incremental sync, and study-period reconciliation.
- `integrations/hermes/`: Feishu channels, identity isolation, group privacy policy, and model routing.
- `infra/tencent/`: Tencent Cloud deployment, strict HTTPS, encrypted backups, and SHA rollback.
- `scripts/import_private_books.py`: encrypted import of privately supplied PDFs outside Git.
- `scripts/publish_shared_books.py`: after human review, exposes only the three specified books as internal BodyOS shared expert knowledge; it does not publish files or full text.

Verified evidence includes Python / policy, Swift Core, and iOS Simulator CI, plus the production HTTPS health check. The public endpoint at <https://124.156.218.104/healthz> currently reports backend version `v2.0.0-alpha.1`.

Not complete: external TestFlight distribution, full invited-tester physical-device acceptance, and results from the real-world 16-day study. The project makes no claim that a health outcome has already been achieved.

```bash
uv sync --extra dev
uv run pytest -q
uv run ruff check apps/api scripts infra/tencent
(cd apps/ios-bridge/Core && swift test)
```

See `docs/operations/deployment-and-rollback.md` and `docs/experiments/owner-cgm-16-day-runbook.md` for production and physical-device operations. Private PDFs, health exports, identities, OAuth credentials, Feishu secrets, runtime files, pairing artifacts, and real health evidence must never enter Git.
