# FitCrew V2 Two-User Alpha Verification / 双用户 Alpha 验证

## 中文

验证日期：2026-08-09。证据仅记录布尔结果、测试计数和发布门槛，不包含飞书身份、设备令牌、配对链接或健康数值。

### 自动化证据

- Python API、策略与运维：`95 passed`，0 个失败；唯一警告为测试客户端上游弃用提示。
- Python lint：通过。
- Swift Health Core：10 项测试通过，0 个失败。
- iOS Simulator：新增的设备重配状态清理测试和既有配置测试执行成功；无签名 Simulator 构建成功。
- XcodeGen 发布配置：版本 `2.0.0`、正整数构建号、HealthKit、私密配对 URL、后台处理、无临床记录权限、出口合规声明和 1024×1024 无透明通道 App Icon 均通过检查。
- App 图标：使用 FitCrew 落地页现有绿色叶子标识，不使用生成式草案。
- 双语 Markdown：通过。
- Git 差异与秘密扫描：通过；未发现私钥或 `sk-` 形式凭据。

### 隔离结果

- 重复邀请同一飞书主体：幂等，通过。
- 未授权 Owner 请求：失败关闭，通过。
- 两位用户设备与逐类别同意：按独立 `fitcrew_user_id` 绑定，通过。
- 已属于其他用户的设备：HTTP 409 且原绑定未变化，通过。
- A 用户令牌上传 B 用户批次：HTTP 403，未写入健康样本，通过。
- 重新配对另一设备：清除上一设备本地同步游标和对账时间，通过。
- Chris 既有 Owner bootstrap、身份 rebind、同步状态与群聊固定低敏行为：回归通过。

### 尚存外部门槛

腾讯云双用户服务代码已经具备部署条件。薛程的远程 HealthKit 真机接入仍需 Account Holder 本人开通付费 Apple Developer Program、完成身份/协议步骤、创建 App Store Connect 记录、上传构建并通过首次 TestFlight 外部 Beta 审核。当前证据不宣称 TestFlight 已上传、审核通过或完成远程安装。

## English

Verification date: 2026-08-09. This evidence records only Boolean outcomes, test counts, and release gates. It contains no Feishu identity, device token, pairing URL, or health value.

### Automated evidence

- Python API, policy, and operations: `95 passed`, zero failures; the only warning is an upstream test-client deprecation notice.
- Python lint: passed.
- Swift Health Core: 10 tests passed, zero failures.
- iOS Simulator: the new device-repair state-reset test and existing configuration test executed successfully; the unsigned Simulator build succeeded.
- XcodeGen release configuration: version `2.0.0`, positive numeric build, HealthKit, private pairing URL, background processing, no clinical-record entitlement, export-compliance declaration, and a 1024×1024 alpha-free App Icon all passed validation.
- App icon: uses the existing green-leaf mark from the FitCrew landing page; the generated draft is not used.
- Bilingual Markdown: passed.
- Git diff and secret scan: passed; no private keys or `sk-`-style credentials were found.

### Isolation outcomes

- Reinviting the same Feishu subject: idempotent, passed.
- Unauthorized Owner request: failed closed, passed.
- Two users' devices and category consents: independently bound by `fitcrew_user_id`, passed.
- Device already owned by another user: HTTP 409 with the original binding unchanged, passed.
- User A token uploading a User B batch: HTTP 403 with no health sample written, passed.
- Pairing a different device: clears the prior device's local sync cursor and reconciliation time, passed.
- Chris's existing Owner bootstrap, identity rebind, sync status, and fixed low-sensitivity group behavior: regression passed.

### Remaining external gate

The Tencent two-user service code is deployable. Xue Cheng's remote HealthKit device onboarding still requires the Account Holder to activate the paid Apple Developer Program, complete identity and agreement steps, create the App Store Connect record, upload a build, and pass the first external TestFlight Beta review. This evidence does not claim that TestFlight has been uploaded, approved, or remotely installed.
