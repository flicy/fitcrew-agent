# FitCrew V2 Two-User Alpha Design / FitCrew V2 双用户 Alpha 设计

## 中文

### 目标与范围

V2 今晚把腾讯云上的 BodyOS 从单 Owner Alpha 扩展为受控的双用户 Alpha。Chris 保留现有飞书身份、iOS HealthKit Bridge、Apple Health、Apple Fitness 与鱼跃血糖数据链路。薛程只获得 BodyOS 群聊和独立私聊能力；本版本不为薛程创建设备绑定、HealthKit 同意记录或健康样本空间。

小米手环、薛程的 Apple Watch 数据、TestFlight 与 App Store Connect 分发进入后续版本。当前没有付费 Apple Developer Program 会员，本版本不得付费、伪造 TestFlight 可用性或发送不可安装的 IPA。

### 方案选择

采用受控邀请制。Owner 通过受保护的管理接口为指定飞书主体创建独立 `User` 与 `IdentityBinding`，随后把同一主体加入 Hermes 私聊白名单。系统不开放自动注册，也不允许仅靠群成员身份访问私人接口。

与“只增加飞书白名单”相比，受控邀请会建立稳定、可审计的用户身份；与“开放所有飞书用户自动注册”相比，它缩小了 Alpha 的隐私与滥用风险。

### 架构与数据流

1. 新增幂等的 Feishu-only 用户邀请接口与运维脚本。输入仅包括飞书主体和基础区域设置；输出只保存在腾讯云受限运行目录，不打印主体、内部用户 ID 或密钥。
2. 每位用户映射到独立 `fitcrew_user_id`。私聊请求先经过 HMAC 身份查找，再以该用户 ID 查询设备、每日特征、知识和记忆；任何查询都必须带用户过滤条件。
3. Chris 的既有身份、设备令牌、同意记录与健康数据保持不变。邀请薛程不得重新绑定、撤销或覆盖 Chris 的记录。
4. 薛程没有设备绑定。同步状态固定呈现为“未连接、无最新同步时间、无数据类别覆盖”；模型不得收到 Chris 的特征、知识或记忆。
5. 群聊继续使用确定性低敏行为 token。群聊不读取任何用户的健康数据、私聊、私人知识或记忆。
6. Hermes 保持 `FEISHU_ALLOW_ALL_USERS=false`，只允许 Chris 与薛程私聊。腾讯云是唯一生产网关；本机旧 BodyOS 网关保持停止。

### 错误与安全处理

- 重复邀请同一飞书主体必须返回幂等成功，不创建第二个用户。
- 已绑定到其他用户的主体必须拒绝，且不改变任何现有记录。
- 未邀请的私聊用户必须失败关闭，不把原始消息回退给模型。
- 无设备用户不得获得配对令牌、同意记录或任何其他用户的同步状态。
- 部署失败时保留当前生产版本；数据库迁移、API 健康检查和网关健康检查全部通过后才切换。

### 测试边界与验收

公共测试边界为管理邀请 API、BodyOS envelope API、OpenAI 兼容模型代理和飞书真实群聊/私聊。

自动测试验证：幂等邀请、跨用户身份冲突拒绝、两个私聊用户的数据隔离、无设备用户同步状态、群聊固定回复、Owner 现有数据路径回归、秘密扫描、双语文档、Python/Swift/Simulator CI。

真实验收验证：Chris 的同步状态与类别覆盖保持不变；薛程能在 BodyOS 群获得固定行为回复，并能在私聊获得不含 Chris 数据的“未连接”状态；未邀请用户不能使用私人 BodyOS。验收证据只记录布尔结果和状态标签，不记录飞书 ID、健康数值、令牌或聊天正文。

### 发布边界

代码提交到现有 `codex/v2-owner-alpha` 分支并更新 PR #1，等待 CI 全绿后部署腾讯云。今晚不合并 PR、不创建 Release、不购买 Apple 会员。上线成功以双用户飞书验收、公开健康检查和重启恢复通过为准。

## English

### Goal and scope

V2 expands the Tencent-hosted BodyOS service from a single-owner alpha to a controlled two-user alpha tonight. Chris keeps the existing Feishu identity, iOS HealthKit Bridge, Apple Health, Apple Fitness, and Yuwell glucose pipeline. Xue Cheng receives group chat and an isolated DM only; this release creates no device binding, HealthKit consent, or health-sample space for the invited user.

Xiaomi band support, Xue Cheng's Apple Watch data, TestFlight, and App Store Connect distribution move to a later release. There is no paid Apple Developer Program membership, so this release must not purchase one, claim TestFlight availability, or distribute an unusable IPA.

### Chosen approach

Use controlled invitation. A protected owner operation creates an independent `User` and `IdentityBinding` for a specific Feishu subject, after which the same subject is added to the Hermes DM allowlist. Automatic registration remains closed, and group membership alone never grants private access.

Controlled invitation provides a stable and auditable identity, unlike an allowlist-only change, while avoiding the privacy and abuse surface of open self-registration.

### Architecture and data flow

1. Add an idempotent Feishu-only invitation endpoint and operations script. Inputs are limited to the Feishu subject and basic locale settings. Outputs stay in a restricted Tencent runtime directory; the subject, internal user ID, and secrets are never printed.
2. Each person maps to an independent `fitcrew_user_id`. DM requests resolve the HMAC identity first and then query devices, daily features, knowledge, and memory with that user ID on every query.
3. Chris's existing identity, device token, consents, and health data remain unchanged. Inviting Xue Cheng must not rebind, revoke, or overwrite Chris's records.
4. Xue Cheng has no device binding. Sync status deterministically reports disconnected, no latest sync time, and no category coverage; the model never receives Chris's features, knowledge, or memory.
5. Groups continue to use deterministic low-sensitivity behavior tokens and never read health data, DMs, private knowledge, or memory.
6. Hermes keeps `FEISHU_ALLOW_ALL_USERS=false` and permits DMs only from Chris and Xue Cheng. Tencent is the sole production gateway; the old local BodyOS gateway stays stopped.

### Error and security handling

- Reinviting the same Feishu subject is idempotent and never creates a second user.
- A subject already bound to another user is rejected without mutating existing records.
- DMs from uninvited users fail closed and never fall back to the raw message or model.
- A user without a device never receives pairing tokens, consent records, or another user's sync status.
- Deployment retains the current production version on failure and cuts over only after migration, API health, and gateway health pass.

### Test seams and acceptance

Public test seams are the management invitation API, BodyOS envelope API, OpenAI-compatible model proxy, and real Feishu group/DM behavior.

Automated tests cover idempotent invitation, cross-user identity conflict rejection, two-user DM isolation, disconnected status for a device-free user, deterministic group replies, owner data-path regression, secret scanning, bilingual docs, and Python/Swift/Simulator CI.

Live acceptance confirms that Chris's sync status and category coverage remain unchanged; Xue Cheng receives the canonical group behavior response and a disconnected DM status containing none of Chris's data; uninvited users cannot use private BodyOS. Evidence records only booleans and status labels, never Feishu IDs, health values, tokens, or chat bodies.

### Release boundary

Changes land on the existing `codex/v2-owner-alpha` branch and update PR #1. Deployment to Tencent follows green CI. Tonight does not merge the PR, create a Release, or purchase an Apple membership. Completion requires two-user Feishu acceptance, the public health check, and restart recovery.
