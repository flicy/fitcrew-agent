# Changelog / 更新记录

## 中文

### 未发布：V3 双端正式版开发（2026-09-07）

- 新增加密旅程、实验、每日行动与手动记录，复用 V2 身份与健康摄取。
- 新增 Apple/微信公开登录验证、独立 AI 聚合同意、导出、删除及注销；加强旧请求和撤回后的写入保护。
- iOS 新增五个原生页；微信新增五页小程序工程。免费，无微信提醒。
- 后端 364 项测试通过，iOS 无签名构建通过；本轮客户端复核通过；真机、平台配置及提审仍未完成。详见发布门槛文档，不代表完整 Demo 或正式上线。

### 未发布：v2.0.0-alpha.1（Owner-only）

- 新增可选 HealthKit Bridge，接入 Apple 健康、Apple 健身及鱼跃写入 Apple 健康的血糖数据。
- 新增加密、幂等、按 consent category 的摄取，以及血糖/睡眠/活动/恢复日聚合。
- 新增飞书主账号与内部稳定身份绑定；群聊固定 token，个性化信息仅在本人私聊。
- 新增 Codex CLI 主路由与 Hermes OpenAI Codex OAuth 备用，模型仅看去标识化 envelope。
- 新增私人 PDF 加密分段、页码引用、公共知识审核与需求状态机。
- 新增腾讯云单机部署、免费公网 IP HTTPS、加密备份、恢复演练与 SHA 回滚。

### v1.0「搭子」— 2026-07-22

首个多群健康搭子 Agent 包，提供群运营、行为打卡、私聊与基础隔离。V2 收紧了 V1 的自由群聊和文件记忆边界；旧行为不得绕过 V2 策略层。

## English

### Unreleased: V3 dual-platform production-release development (2026-09-07)

- Added encrypted journeys, experiments, daily actions and manual logs on V2 identity and health ingestion.
- Added verified Apple/WeChat login, separate AI aggregate consent, export and erasure; strengthened stale-request and revocation write protection.
- Added five native iOS tabs and a five-page WeChat project. Free, without WeChat reminders.
- 364 backend tests and unsigned iOS builds pass. This round of client review passed; device verification, platform configuration and submission remain incomplete; see release gates. This is not full demo parity or a production release.

### Unreleased: v2.0.0-alpha.1 (owner-only)

- Added an optional HealthKit Bridge for Apple Health, Apple Fitness, and Yuwell glucose data written into Apple Health.
- Added encrypted, idempotent, consent-category ingestion plus daily glucose, sleep, activity, and recovery aggregates.
- Added Feishu-primary identity binding; groups use fixed tokens and personalized information stays in the owner's DM.
- Added Codex CLI primary routing with Hermes OpenAI Codex OAuth fallback; models see only de-identified envelopes.
- Added encrypted private-PDF chunks, page citations, public-knowledge review, and a demand state machine.
- Added single-host Tencent deployment, free public-IP HTTPS, encrypted backups, restore tests, and SHA rollback.

### v1.0 “Buddy” — 2026-07-22

The first multi-group health-buddy Agent package provided group operations, behavior check-ins, DMs, and basic isolation. V2 tightens V1's free-form group and file-memory boundaries; legacy behavior may not bypass V2 policy.
