# FitCrew Health Bridge TestFlight Metadata / TestFlight 元数据

## 中文

### 构建信息

- App 名称：FitCrew Health Bridge
- Bundle ID：`com.fitcrew.healthbridge`
- 版本：`2.0.0`；首个 TestFlight 构建号：`1`
- 分发：仅限邮件邀请的外部测试组，不创建公开链接
- 隐私政策：<https://github.com/flicy/fitcrew-agent/blob/main/docs/privacy/data-processing-and-retention.md>
- 支持与反馈：<https://github.com/flicy/fitcrew-agent/issues>

### Beta 描述

FitCrew Health Bridge 是 BodyOS 的只读 Apple 健康连接器。它在用户明确授权后读取血糖、睡眠、心率变异性、静息心率、训练与活动类别，并把数据加密同步到用户绑定的私人 BodyOS 空间。群聊不读取原始健康数据；测试版本不提供医疗诊断。

### 测试重点

1. 通过私密配对码绑定正确的 BodyOS 用户。
2. 逐项授权 Apple 健康读取权限，并确认拒绝任一类别不会阻止其他已授权类别。
3. 执行增量同步和全量对账；仅核对连接状态、最新同步时间和类别覆盖，不在反馈中提交健康数值。
4. 验证 Apple Watch 写入 iPhone HealthKit 的睡眠、恢复、训练和活动数据可以在授权后同步。
5. 确认重新配对另一台设备时会清除上一设备的本地同步游标。

### Beta App Review 说明

应用只向 HealthKit 请求读取权限，不写入健康数据，也不请求临床/可验证健康记录。配对码由 Owner 私下提供；审核账号无法自行注册。审核人员可在无真实健康样本时启动应用、打开隐私政策并检查授权界面。若需要完整配对演示，由 Account Holder 在 App Store Connect 的 Review Notes 中提供一次性审核配对方式，不得把真实用户二维码写入仓库。

### Account Holder 必须手工填写

- 真实姓名、电话、地址和可联系的反馈邮箱
- App Store Connect 审核联系人
- 出口合规问卷的法律确认
- 测试者邀请邮箱与隐私授权确认
- 首次外部构建的 Beta App Review 提交

当前门槛：付费 Apple Developer Program 尚未生效，因此此文件只代表上传准备完成，不代表已经上传、通过审核或可远程安装。

## English

### Build information

- App name: FitCrew Health Bridge
- Bundle ID: `com.fitcrew.healthbridge`
- Version: `2.0.0`; initial TestFlight build: `1`
- Distribution: email-only external testing group; no public link
- Privacy policy: <https://github.com/flicy/fitcrew-agent/blob/main/docs/privacy/data-processing-and-retention.md>
- Support and feedback: <https://github.com/flicy/fitcrew-agent/issues>

### Beta description

FitCrew Health Bridge is the read-only Apple Health connector for BodyOS. After explicit authorization, it reads glucose, sleep, heart-rate variability, resting heart rate, workouts, and activity categories, then sends them over an encrypted connection to the user's paired private BodyOS space. Group chats never read raw health data, and the beta does not provide medical diagnosis.

### Testing focus

1. Bind the correct BodyOS user with a private pairing code.
2. Grant Apple Health read permissions individually and confirm that denying one category does not block other authorized categories.
3. Run incremental sync and full reconciliation. Verify only connection status, latest sync time, and category coverage; never include health values in feedback.
4. Confirm that authorized sleep, recovery, workout, and activity records written by Apple Watch to iPhone HealthKit can sync.
5. Confirm that pairing a different device clears the prior device's local sync cursor.

### Beta App Review notes

The app requests read-only HealthKit access, writes no health data, and does not request clinical or verifiable health records. Pairing codes are privately issued by the Owner; reviewers cannot self-register. Reviewers can launch the app without real health samples, open the privacy policy, and inspect the authorization UI. If a full pairing demo is required, the Account Holder must provide a one-time review method in App Store Connect Review Notes; never commit a real user's QR code.

### Account Holder manual fields

- Legal name, phone, address, and a monitored feedback email
- App Store Connect review contact
- Legal confirmation for the export-compliance questionnaire
- Tester invitation email and privacy authorization confirmation
- Submission of the first external build for Beta App Review

Current gate: the paid Apple Developer Program membership is not active. This file proves upload readiness only; it does not claim that a build has been uploaded, approved, or made remotely installable.
