# Changelog / 更新记录

## 中文

### 未发布：微信云托管私有传输准备（2026-10-09）

- 小程序可配置 `wx.cloud.callContainer`，沿用现有 `/v3` API、设备令牌和隐私边界；无环境 ID、服务名或 HTTPS 配对地址时保持拒绝请求。新增本地传输与配置验证测试。尚未开通云环境、部署数据库或后端、真机验收、上传或提审；见[传输准备](docs/release/2026-10-09-cloudbase-transport.md)。
- 后端增加可选的腾讯云开发 AI 服务端路由。只有环境、模型和密钥完整时启用；配置不全时不向用户展示可用 AI，也不回退到未披露的其他服务商。尚未在真实云账号调用。
- 增加 CloudBase PG 专用 schema 的离线建表清单生成器，包含当前模型、索引和 Alembic 版本戳；只供审核，不连接或修改数据库。

### 未发布：微信正式 AppID 配置（2026-09-24）

- 按运营者确认，将 `wxae59705a7cce30f9` 写入小程序发布工程，并移除本地校验器中针对该 AppID 的历史测试号硬编码拒绝；校验仍要求合法 HTTPS 业务域名与启用域名校验。运营者声明尚未由后台凭据或正式上传回执独立证实，未因此部署或提审。

### 未发布：服务器只读诊断（2026-09-17）

- 新增可在腾讯云控制台独立运行的发布前检查：磁盘、固定容器元数据、备份/密钥存在性与只读 schema revision；不读取秘密或健康记录，不清理或部署。补齐失败和输出过滤测试，纠正状态文档中已过时的登录/服务器信息。尚未在生产执行或正式提审。

### 未发布：微信原生 Profile 修复（2026-09-10）

- 将设备连接模块改为顶层显式引用，修复官方模拟器“我的”页模块缺失白屏；原生复测正文显示且无调试器错误。基础库修复与验收边界见 `docs/release/2026-09-10-native-wechat-runtime.md`。

### 未发布：小程序时间显示（2026-09-10）

- 连接有效期、设备会话和其他时间保留 UTC/偏移标记，缺少时区时明确提示，避免误认为设备本地时间。iOS 实验时间保留完整来源字符串，无同类截断。

### 未发布：iOS 发布地址配置（2026-09-10）

- 增加服务与隐私政策 URL 的构建变量，防止 XcodeGen 覆盖手动配置；新增最终 App 配置检查。配对与反馈 AI 等当前能力见 `docs/agent-context/CURRENT_STATE.md`。尚未部署或提审。

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

### Unreleased: private WeChat Cloud Hosting transport preparation (2026-10-09)

- The Mini Program can use `wx.cloud.callContainer` against the existing `/v3` API, device tokens, and privacy boundary. Missing environment ID, service name, or HTTPS pairing URL fails closed. Local transport/configuration tests were added. No cloud environment, database, backend deployment, device acceptance, upload, or formal submission exists yet; see the [transport note](docs/release/2026-10-09-cloudbase-transport.md).
- An optional server-side CloudBase AI route now requires a complete environment, model, and secret key. Partial configuration does not advertise AI or fall back to an undisclosed provider. No real cloud-account invocation has been verified.
- Add an offline CloudBase PG private-schema manifest generator covering current models, indexes, and the Alembic revision. It is review-only and never connects to or mutates a database.

### Unreleased: formal WeChat AppID configuration (2026-09-24)

- Put owner-confirmed `wxae59705a7cce30f9` in the Mini Program release project and remove the historic sandbox-ID hard-coded rejection from the local validator. Validation still requires a legal HTTPS business domain with domain checking enabled. The owner declaration is not independently established by dashboard credentials or a formal upload receipt; this did not deploy or submit anything.

### Unreleased: read-only server diagnostics (2026-09-17)

- Add a standalone Tencent-console preflight for disk, fixed container metadata, backup/key presence and read-only schema revision. It does not read secrets or health records, clean up or deploy. Add failure/output-filtering tests and correct stale login/server status. No production execution or formal submission occurred.

### Unreleased: native WeChat Profile fix (2026-09-10)

- Explicitly import the device-pairing module at top level, fixing the missing-module blank Profile in official DevTools. Native retest rendered its contents with zero debugger errors; see the runtime diagnosis document for cache repair and acceptance limits.

### Unreleased: Mini Program timestamps (2026-09-10)

- Connection expiry, device sessions and other timestamps retain UTC/offset labels; unspecified zones are explicit. iOS experiment dates retain the complete source string without this truncation.

### Unreleased: iOS release URL configuration (2026-09-10)

- Added API/privacy URL build substitutions and built-app configuration validation. Current pairing and feedback AI capabilities are documented in `docs/agent-context/CURRENT_STATE.md`. No deployment or submission occurred.

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
