# Data Processing and Retention / 数据处理与保留

## 中文

范围说明：下文记录 V2 飞书主账号方案，不能直接作为 V3 iOS/小程序的终端用户隐私政策。V3 复用加密与身份基础，但采用平台登录和可选设备连接，提供用户侧导出/删除；AI 请求范围及新同意规则见 [确认反馈与 AI](../release/2026-09-09-ai-confirmed-feedback.md)。真实运营者、联系方式、服务提供方、部署及保留周期仍需核实后形成公开政策。

飞书账号是主账号，Apple 健康授权是可选项。系统把飞书 `open_id` 经 HMAC 映射并加密保存，再关联不可变的 `fitcrew_user_id`；模型 envelope 中两者都不出现。

处理范围包括：血糖、睡眠阶段、HRV、静息心率、训练、活动能量、步数、站立时间和活动摘要。设备上传必须带独立 token、设备绑定和当前 category consent；批次与样本 ID 幂等。原始值和日特征采用 AES-GCM 与字段级 AAD 加密。模型只收到日级统计、质量状态、意图、规则及最多三条带页码私人知识摘录，不收到问题原文或原始时间序列。

原始健康明细保留 30 天。经授权的日聚合、洞察和实验结果保留 13 个月。用户撤回某 category 后，新摄取被拒绝；导出和删除必须走 Owner 授权接口。私人 PDF 原文件保留在 Git 外私有目录，数据库只保存加密分段与最小来源元数据。公共候选知识必须经过来源、权利、适用范围和审核状态，不能由群消息或模型自动发布。

群聊策略优先于模型：仅输出五种固定行为 token，不显示健康/非健康行为明细、原始数据、跨群信息或私人书摘。教练、专家和普通成员都是用户；其建议与需求进入同一需求采集池，不因角色直接成为公共知识。

这是一套生活方式教练系统，不是医疗器械或诊断服务。异常症状、用药和疾病治疗由合格医疗专业人员处理。

## English

Scope: the following describes the V2 Feishu-primary design and is not a ready V3 iOS/Mini Program end-user privacy policy. V3 reuses encryption/identity foundations but adds platform login, optional device connection and user-facing export/erasure. See [AI feedback scope](../release/2026-09-09-ai-confirmed-feedback.md) for new request/consent rules. Verify the actual operator, contact, providers, deployment and retention before publishing a policy.

Feishu is the primary account and Apple Health authorization is optional. The service HMAC-maps and encrypts the Feishu `open_id`, then links it to an immutable `fitcrew_user_id`; neither identifier appears in a model envelope.

Processing can cover glucose, sleep stages, HRV, resting heart rate, workouts, active energy, steps, stand time, and activity summaries. Every upload requires a device token, active binding, and current category consent; batch and sample IDs are idempotent. Raw values and daily features use AES-GCM with field-specific AAD. A model receives only daily statistics, quality state, intent, constraints, and at most three page-cited private excerpts—never the raw question or time series.

Raw health detail is retained for 30 days. Authorized daily aggregates, insights, and experiment results are retained for 13 months. Withdrawing a category rejects new ingestion; export and deletion require the owner-authorized endpoint. Private source PDFs remain outside Git, while the database stores only encrypted chunks and minimum provenance metadata. Public knowledge candidates require source, rights, applicability, and review state; group messages and models cannot auto-publish them.

Group policy runs before any model: only five fixed behavior tokens are permitted, with no health or non-health behavior detail, raw data, cross-group information, or private excerpt. Coaches, experts, and regular members are all users; their suggestions and demands enter the same demand pool and do not become public knowledge because of role.

This is a lifestyle-coaching system, not a medical device or diagnostic service. Qualified clinicians handle abnormal symptoms, medication, and disease treatment.
