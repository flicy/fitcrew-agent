# FitCrew V2 Two-User Health Alpha Design / FitCrew V2 双用户健康 Alpha 设计

## 中文

### 目标与范围

V2 把腾讯云上的 BodyOS 扩展为受控的双用户健康 Alpha。Chris 保留现有飞书身份、iOS HealthKit Bridge、Apple Health、Apple Fitness 与鱼跃血糖链路。薛程获得独立飞书群聊、私聊、iOS Bridge 配对与 Apple Watch/Apple Health 数据空间。

小米手环进入后续版本。V2 通过 TestFlight 向异地测试者分发同一个 iPhone App；无需开发 watchOS App，因为 Apple Watch 数据先进入配对 iPhone 的 HealthKit，再由 iOS Bridge 按用户授权读取。

### 账号与发布前提

TestFlight 需要有效的 Apple Developer Program 付费会员、App Store Connect App 记录、分发签名和外部测试审核。会员购买、身份验证、协议接受、税务或付款步骤只能由 Account Holder 本人完成。Codex 不代购、不接受法律协议、不读取 Apple 账号密码。

在会员生效前，可以完成代码、测试、App 图标与 TestFlight 元数据、隐私说明、Archive 配置和腾讯云多用户部署；无法完成真实 TestFlight 上传与外部安装。首次外部测试需要 Apple 审核，完成时间由 Apple 决定。

### 方案选择

采用受控邀请和每用户独立配对。Owner 通过受保护的管理接口为指定飞书主体创建独立用户；随后为该用户生成独立的一次性 iOS 配对载荷、设备令牌和逐类别同意记录。Hermes 仍使用私聊白名单，不开放自动注册。

与“共用 Owner 配对”相比，独立配对避免跨用户数据混合；与“开放所有飞书用户自动注册”相比，受控邀请缩小 Alpha 的隐私和滥用风险。

### 架构与数据流

1. 新增幂等的用户邀请、设备配对与撤销接口及运维脚本。身份主体、设备令牌和配对载荷只保存在腾讯云受限运行目录，不打印到终端、日志、Git 或 PR。
2. 每位用户映射到独立 `fitcrew_user_id`。飞书私聊先完成 HMAC 身份查找；健康上传先验证该用户的设备令牌和逐类别同意；所有健康、特征、知识和记忆查询都必须带用户过滤条件。
3. Chris 的既有身份、设备令牌、同意记录与健康数据保持不变。邀请及配对薛程不得重新绑定、撤销或覆盖 Chris 的任何记录。
4. 同一个 TestFlight App 在不同 iPhone 上安装。每台 iPhone 只保存自己的 Keychain 设备令牌和同意映射；扫描新的配对码会替换该设备的本地配置，不影响其他用户。
5. Apple Watch 数据由 iPhone HealthKit 汇总。Bridge 仅读取用户在系统健康权限页明确授权的类别，包括睡眠、HRV、静息心率、训练、活动能量、步数、站立和活动摘要；血糖仍是可选类别。
6. 群聊继续使用确定性低敏行为 token，不读取任何用户的健康数据、私聊、私人知识或记忆。
7. 腾讯云是唯一生产网关，本机旧 BodyOS 网关保持停止。

### TestFlight 分发

1. 使用唯一 Bundle ID、正式 App 图标、版本号与递增构建号生成 Release Archive。
2. App Store Connect 提供中英文 Beta 描述、测试重点、反馈邮箱、隐私政策 URL、支持 URL、审核联系人和 HealthKit 使用说明。
3. 处理出口合规问卷，声明应用自己的加密用途；不得猜测或自动提交法律答案。
4. 通过 Xcode 上传构建。薛程使用邮件邀请加入受限的外部测试组；不创建公开 TestFlight 链接。
5. 首个外部构建提交 TestFlight Beta App Review。Apple 批准后，薛程安装 TestFlight 和 BodyOS Bridge，再完成 HealthKit 授权与一次性配对。

### 错误与安全处理

- 重复邀请同一飞书主体必须幂等，不创建第二个用户。
- 已绑定到其他用户的主体或设备必须拒绝，且不改变现有记录。
- 设备令牌只能访问绑定用户；使用 A 用户令牌上传 B 用户批次必须失败关闭。
- 未邀请的私聊用户、未配对设备、未授权类别和撤销后的设备必须失败关闭，不把原始数据回退给模型。
- TestFlight、Apple 会员或审核未就绪时，腾讯云服务仍可上线，但不得宣称薛程已完成健康数据接入。
- 部署失败时保留上一生产版本；数据库迁移、API、网关和公开健康检查全部通过后才切换。

### 测试边界与验收

公共测试边界为管理邀请/配对 API、健康摄取 API、BodyOS envelope API、模型代理、iOS Core 与真机/TestFlight App。

自动测试验证：幂等邀请、两用户独立配对、跨用户主体/设备冲突拒绝、跨令牌上传拒绝、逐类别同意、两个私聊用户的数据隔离、群聊固定回复、Owner 现有链路回归、秘密扫描、双语文档、Python/Swift/Simulator CI。

真实验收分两阶段：

1. 腾讯云阶段：Chris 现有同步不变；两位用户群聊和私聊隔离；服务重启后身份、设备与网关恢复。
2. TestFlight 阶段：Apple 批准后，薛程远程安装 App、授权 Apple Health、扫描专属配对码并同步至少一个真实批次；验收只记录连接状态、最新时间、类别覆盖和去标识化计数，不记录健康数值。

### 发布边界

变更更新现有 PR #1。CI 全绿且代码审查通过后，按用户本次授权合并 PR，并从合并后的 `main` SHA 部署腾讯云。TestFlight 构建只在付费会员生效并由用户完成必要协议后上传。不得购买会员、接受协议、邀请测试者或公开链接，除非用户在对应步骤明确授权。

## English

### Goal and scope

V2 expands Tencent-hosted BodyOS into a controlled two-user health alpha. Chris keeps the existing Feishu identity, iOS HealthKit Bridge, Apple Health, Apple Fitness, and Yuwell glucose pipeline. Xue Cheng receives isolated group chat, DM, iOS Bridge pairing, and an Apple Watch/Apple Health data space.

Xiaomi band support moves to a later release. V2 distributes the same iPhone app to the remote tester through TestFlight. A watchOS app is unnecessary because Apple Watch data reaches HealthKit on the paired iPhone before the iOS Bridge reads user-authorized categories.

### Account and release prerequisites

TestFlight requires an active paid Apple Developer Program membership, an App Store Connect app record, distribution signing, and external beta review. Only the Account Holder may complete membership purchase, identity verification, legal agreements, tax, or payment steps. Codex does not purchase membership, accept agreements, or access Apple account credentials.

Before membership activation, development can complete code, tests, icons, TestFlight metadata, privacy text, archive configuration, and Tencent multi-user deployment. A real TestFlight upload and remote install remain unavailable. Apple controls the timing of the first external beta review.

### Chosen approach

Use controlled invitation with per-user pairing. A protected owner operation creates an independent user for a specific Feishu subject, then issues a unique one-time iOS pairing payload, device token, and per-category consents. Hermes retains a DM allowlist and does not permit open registration.

Independent pairing prevents cross-user data mixing, while controlled invitation avoids the privacy and abuse surface of public self-registration.

### Architecture and data flow

1. Add idempotent user invitation, device pairing, and revocation endpoints plus operations scripts. Identity subjects, device tokens, and pairing payloads remain only in a restricted Tencent runtime directory and never appear in terminal output, logs, Git, or PRs.
2. Each person maps to an independent `fitcrew_user_id`. Feishu DMs resolve the HMAC identity first; health uploads verify that user's device token and category consent. Every health, feature, knowledge, and memory query includes the user filter.
3. Chris's existing identity, token, consents, and health data remain unchanged. Inviting and pairing Xue Cheng must not rebind, revoke, or overwrite any Chris record.
4. The same TestFlight app installs on separate iPhones. Each iPhone stores only its own Keychain token and consent mapping. Scanning a new pairing code replaces that device's local configuration without affecting another user.
5. The iPhone HealthKit store aggregates Apple Watch data. The Bridge reads only system-authorized categories: sleep, HRV, resting heart rate, workouts, active energy, steps, stand hours, and activity summaries; glucose stays optional.
6. Groups continue to use deterministic low-sensitivity behavior tokens and never read health data, DMs, private knowledge, or memory.
7. Tencent is the sole production gateway; the old local BodyOS gateway stays stopped.

### TestFlight distribution

1. Produce a Release Archive with a unique Bundle ID, production icon, version, and incrementing build number.
2. App Store Connect receives bilingual beta description, test focus, feedback email, privacy policy URL, support URL, review contact, and HealthKit usage explanation.
3. Complete the export-compliance questionnaire for the app's encryption use; legal answers are never guessed or submitted automatically.
4. Upload through Xcode. Invite Xue Cheng by email to a restricted external group; do not create a public TestFlight link.
5. Submit the first external build for TestFlight Beta App Review. After approval, Xue Cheng installs TestFlight and BodyOS Bridge, grants HealthKit access, and scans the one-time pairing code.

### Error and security handling

- Reinviting the same subject is idempotent and never creates a second user.
- A subject or device already bound to another user is rejected without mutation.
- A device token accesses only its bound user; an A-user token uploading a B-user batch fails closed.
- Uninvited DMs, unpaired devices, unconsented categories, and revoked devices fail closed without raw-data or model fallback.
- If membership or beta review is not ready, Tencent may still go live, but the release must not claim Xue Cheng health ingestion is complete.
- Deployment retains the prior production version on failure and cuts over only after migration, API, gateway, and public health checks pass.

### Test seams and acceptance

Public seams are the management invite/pair APIs, health ingestion API, BodyOS envelope API, model proxy, iOS Core, and the physical/TestFlight app.

Automated tests cover idempotent invitation, independent two-user pairing, identity/device conflict rejection, cross-token upload denial, category consent, DM data isolation, deterministic group replies, owner regression, secret scanning, bilingual docs, and Python/Swift/Simulator CI.

Live acceptance has two phases:

1. Tencent: Chris's current sync remains intact; both users have isolated group/DM behavior; identity, devices, and gateway recover after restart.
2. TestFlight: after Apple approval, Xue Cheng remotely installs, grants Apple Health access, scans the dedicated pairing code, and syncs at least one real batch. Evidence stores only connection state, latest time, category coverage, and de-identified counts, never health values.

### Release boundary

Changes update PR #1. After green CI and code review, merge the PR under the user's explicit authorization and deploy Tencent from the merged `main` SHA. Upload a TestFlight build only after paid membership activates and the user completes required agreements. Do not purchase membership, accept agreements, invite testers, or create a public link without explicit authorization at the corresponding step.
