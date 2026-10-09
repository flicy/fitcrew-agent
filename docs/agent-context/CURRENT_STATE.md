# 当前状态 / Current State

更新时间 / Updated: 2026-10-09

## 中文

**小程序和 iOS 均未正式提审，本发布分支尚未部署到生产。** 分支为 `codex/free-public-release-20260907`；最新已推送提交 `0d9aec2` 的 CI `37878946050` 三项全部成功。小程序私有云托管传输和可选的云开发 AI 服务端路由已在本地测试，真实云调用未验证。这些均不是云环境、真机或生产验收。

### 已有实现与验证边界

10 月 9 日新增微信优先的私有云托管模式：小程序公开配置可留空 `baseURL`，后端显式开启 `BODYOS_PRIVATE_WECHAT_CLOUD_ENABLED` 后只对微信登录放行，iOS 配对和 Apple 登录继续要求生产 HTTPS 地址。此模式只有本地测试，环境 ID、服务名、部署和真机均未验证。

五页原生小程序与 iOS、90 天旅程、手动记录、实验与健康观察、导出/删除、独立 AI 同意已有代码；不等于完整 Demo 等价或平台验收。继承 V2 User、DeviceBinding、Consent、加密摄取与 HealthKit，禁止新建平行身份或健康链路。

- `0cc080a`：实验以有效授权计算描述性观察，排除暂停日与不足证据，不宣称因果。
- `81924d8` / `a652acf`：iOS 配对保护账号切换与旧请求回写；微信账号可生成限时单次连接、列出和撤销设备，不自动合并 Apple 身份。目标迁移为 `0005_device_only_pairing`，见[连接与回滚要求](../release/2026-09-09-wechat-ios-connection.md)。
- `7f63bbd` / `1386968`：重复确认未变化的授权保留原授权；单独同意后 AI 接收同目标最多 10 条已确认结构化反馈；撤回记忆使相关待执行建议失效。这不证明微信 AI 灰度资格或完整主动干预能力。
- iOS 有发布地址构建变量和产物检查，见[发布配置](../release/2026-09-10-ios-release-configuration.md)。正式签名与真实 HealthKit 验收未完成。
- 官方微信工具的基础库及 Profile 模块已修复，见[原生排错](../release/2026-09-10-native-wechat-runtime.md)。9 月 16 日测试预览生成成功（126,337 字节），只证明测试包生成，二维码可能过期。用户已于 9 月 24 日确认正式 AppID 为 `wxae59705a7cce30f9`，并已写入发布工程；该声明尚未通过后台凭据或上传回执独立验证。现支持云托管私有链路配置，见[传输准备](../release/2026-10-09-cloudbase-transport.md)，但环境 ID、服务名、API `baseURL` 仍为空。浏览器预览使用合成数据，没有真实持久化服务。
- CloudBase PG 有离线私有 schema 清单生成器与受控运行时路由；专用模式只读核对表、列名、索引、唯一约束、外键目标和版本，不自动迁移。它尚未连接真实云数据库，也未验证列类型、权限、TLS、备份恢复或业务闭环。

### 服务器与阻塞

9 月 16 日通过用户登录的腾讯云控制台/TAT 成功执行只读诊断；此前“服务器完全无法访问”的说法已过时。东京轻量服务器 `lhins-kbymsgml` 的 `/opt/fitcrew-bodyos` 当时为干净提交 `fc4d441`，API、worker、旧 gateway、数据库与 Caddy 运行中。不得盲目重启全套服务或移除旧 gateway；先核实实际入口和依赖，保持既有飞书功能。

该次快照中根分区 59 GB 已用 56 GB，仅余 1.2 GB（99%）。尚未清理、验证备份恢复或升级。这是 9 月 16 日快照，不是实时读数。既往 `root@124.156.218.104` SSH 返回 `Permission denied (publickey,password)`，不能据此判断当前控制台状态。备用只读检查见 [API 独立发布流程](../operations/api-only-release.md) 和 `infra/tencent/release-preflight.py`；不读取秘密内容、不清理、不迁移、不部署。

其他未完成项：CloudBase 环境/服务/持久数据库及部署；iOS 配对另需公网 HTTPS 地址。微信类目与平台隐私配置、真实 AI 服务商及资格、Apple 会员/账号/签名、微信真实登录—保存—重登—删除验收、iPhone 安装与真实授权/同步/拒绝/撤回验收也未完成。10 月 9 日微信工具 CLI 的 `islogin` 为 `false`，`cloud env list` 要求重新登录；此前生成的扫码登录二维码已超时，仍不能确认云环境。云托管私有传输和 AI 服务端路由只有本地代码，环境未开通或部署，不宣称免费长期运行，不自动购买资源。

### 后续目标与证明

优先微信，再完成 iOS；首发免费，提醒可后置，保留 AI 方向。用户要求国庆假期前提审；原定 9 月 23 日首轮和 9 月 30 日前处理退回均已错过，不能表述为完成。当前须尽快确定可持续生产后端、完成备份恢复与数据库部署、正式配置和真机验收、上传提审。最后必须有平台版本号、提交时间和审核状态证据，测试号、预览、CI 或健康检查不能替代。

用户提供的比赛要求包含 2026 年 7 月 17 日至 10 月 17 日正式上线，仍须核验官方规则，不能把提审当作上线。发布与招募已有[飞书审阅稿](https://my.feishu.cn/docx/VPUSdNJocoFpqixiS8Jc0ReYn3b)，未发帖、建群或报名。先提供真实可用的体验入口，再招募。继续每两小时真实进度同步，不把本地工作报告成生产进展。

## English

**Neither the Mini Program nor iOS has been formally submitted, and this release branch is not deployed to production.** Branch: `codex/free-public-release-20260907`. All three CI jobs passed for the latest pushed commit `0d9aec2` in run `37878946050`. The private WeChat Cloud Hosting transport and optional CloudBase AI server route have local test coverage but have not been called through a real cloud account. None of this is cloud, device, or production acceptance.

### Implementation and evidence limits

On October 9, a WeChat-first private Cloud Hosting mode was added: Mini Program `baseURL` may be empty, and an explicit server-side `BODYOS_PRIVATE_WECHAT_CLOUD_ENABLED` flag permits WeChat sign-in only. iOS pairing and Apple sign-in still require a production HTTPS address. This mode has only local test coverage; environment ID, service name, deployment, and device acceptance are unverified.

Both clients have five native pages, a 90-day journey, manual records, experiments, health observations, export/erasure and separate AI consent. This is not proof of full demo parity or platform acceptance. Preserve V2 User, DeviceBinding, Consent, encrypted ingestion and HealthKit rather than introducing parallel systems.

- `0cc080a`: consent-filtered descriptive experiment observations exclude paused days and insufficient evidence; no causal claims.
- `81924d8` / `a652acf`: iOS pairing guards account changes and stale responses. Authenticated WeChat users can issue expiring single-use connections and list/revoke devices; Apple identities are not automatically merged. Target migration: `0005_device_only_pairing`; consult the linked connection document before rollback.
- `7f63bbd` / `1386968`: unchanged consent preserves grants. Separate AI consent permits up to ten confirmed structured feedback items for the same goal; withdrawing memory invalidates dependent pending proposals. This establishes neither WeChat AI eligibility nor complete proactive intervention.
- iOS has release URL build variables and artifact checks; formal signing and real HealthKit acceptance remain incomplete. See the linked release configuration document.
- Official WeChat base-library and Profile dependency problems were repaired. The September 16 sandbox preview succeeded (126,337 bytes), proving packaging only; its QR may expire. The owner confirmed `wxae59705a7cce30f9` as the formal AppID on September 24 and it is now in the release project; that declaration is not independently verified by dashboard credentials or an upload receipt. The private Cloud Hosting client transport is locally prepared, but environment ID, service name and API `baseURL` remain empty. Browser previews use synthetic fixtures without real persistence.
- An offline CloudBase PG private-schema generator lists tables, indexes and the revision stamp; controlled runtime routing and read-only startup checks now cover table and column names, indexes, unique constraints, foreign-key targets, and revision. No real cloud database, column types, role/TLS configuration, backup recovery, or user flow has been verified.

### Server and blockers

On September 16, read-only diagnostics succeeded through the user's logged-in Tencent console/TAT. Claims that the server was entirely inaccessible are obsolete. On Tokyo Lighthouse `lhins-kbymsgml`, `/opt/fitcrew-bodyos` was clean at `fc4d441`; API, worker, legacy gateway, database and Caddy were running. Do not blindly restart the stack or remove the gateway; establish actual ingress/dependencies and preserve existing Feishu functionality.

That remote snapshot showed 56 GB used on a 59 GB root partition, with 1.2 GB free (99%). No cleanup, backup restore verification or upgrade occurred. These are September 16 observations, not live readings. Earlier `root@124.156.218.104` SSH attempts returned `Permission denied (publickey,password)`; this does not establish current console state. The standalone `infra/tencent/release-preflight.py`, documented in the API-only procedure, is a read-only fallback; it does not read secrets, clean up, migrate or deploy.

Remaining: CloudBase environment/service, persistent database and deployment; iOS pairing additionally needs a public HTTPS address. WeChat category and platform privacy details, real AI provider and eligibility, Apple membership/account/signing, real WeChat login/save/relogin/erasure, and iPhone installation with real HealthKit authorization/sync/denial/revocation are also unfinished. On October 9, DevTools CLI `islogin` was `false` and `cloud env list` required a fresh login. Earlier login QR codes expired without confirmation, so the environment remains unverified. The private Cloud Hosting transport and AI route are only local code, with no environment or deployed backend. Do not claim indefinite free production or buy resources automatically.

### Next goals and evidence

Prioritize WeChat, then finish iOS. Launch is free; reminders may follow later, while retaining AI. The original September 23 first-submission and September 30 correction targets were missed; do not present them as completed. The immediate sequence is a sustainable production backend, backup/restore and database deployment, final configuration and device acceptance, then upload and submission. Completion requires platform version, submission time and review status; sandbox previews, CI and health checks are insufficient.

The user-provided contest rules require going live between July 17 and October 17, 2026; official verification remains necessary, and submission is not publication. The linked Feishu launch/early-user review draft exists, but no posts, group or contest entry have been published. Establish a working trial entry before recruitment. Continue truthful two-hour updates, separating local work from production progress.
