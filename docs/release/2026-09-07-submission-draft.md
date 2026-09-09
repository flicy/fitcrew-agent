# 提审材料草稿 / Review Submission Draft

## 中文

状态：供用户核对，尚不能提交。运营者姓名、联系方式、隐私政策公开地址、备案、实际平台配置与功能资格必须核实后填写。不得将本草稿原样上传为已完成的申报。

### 产品信息

- 名称：FitCrew（以平台名称可用性及用户确认为准）。
- iOS 工程版本：3.0.0 (1)，最终 Bundle ID 及签名以本人开发者账号配置为准。
- 定位：记录日常感受，设定 90 天方向，通过每周小实验观察自己的变化。
- 简介草稿：选择睡眠、精力或活动方向，记录每日精力、压力和感受；接受、暂停或停止一项每周小实验，在记录足够时查看描述性变化。iOS 可在单独授权后读取并同步 Apple 健康数据。没有数据时展示空状态，不生成健康分数或诊断。
- 首发免费，不提供购买、订阅及微信提醒。
- 当前两种登录各自建立身份；跨端同一人的自动合并尚未实现，不能宣传双端账号互通。微信端不能自行读取 Apple Health。

### 审核说明草稿

应用不是医疗诊断、治疗或急救工具。实验结果是用户记录的描述性对比，不证明因果。审核人员可先查看五个页面与未连接状态；完整验证需可用的正式服务及实际平台登录。iOS 使用 Apple 登录，微信使用微信登录；HealthKit 授权可选，不授权仍可记录日常感受。请在“我的”查看授权、导出、删除数据与注销入口。AI 仅在已配置真实服务商且用户另行同意后处理最小聚合，当前实现不上传自由文本笔记或原始 HealthKit 样本至模型。申报功能、服务商与后台实际能力必须一致，不得通过关闭审核入口隐瞒计划功能。

### 隐私信息待核对表

| 项目 | 代码当前处理 | 发布前需确认 |
| --- | --- | --- |
| 平台身份 | 服务端验证 Apple/微信身份后签发设备令牌，身份字段加密保存 | 运营者、服务域名、凭据及实际留存政策 |
| 手动记录 | 精力、压力、感受、可选笔记、旅程和实验，服务端加密保存 | 对应平台隐私标签/声明、留存与备份删除周期 |
| Apple 健康 | 系统权限与服务端分类授权，复用既有加密摄取 | 真机实际读取类别、用途、权限拒绝/撤回表现 |
| AI | 单独授权，目标枚举及近期手动记录聚合；不发送笔记、账号标识或原始健康样本 | 服务商、协议、适用资质及处理地；个人主体资格未解决 |
| 删除 | 提供数据删除与注销；撤销授权及设备凭据，Apple 注销涉及撤销平台令牌 | 线上数据库验证、备份保留说明、外部服务留存，不能承诺未经验证的立即永久删除 |
| 导出 | 本人记录及健康导出 | 真机文件分享、导出文件清理，提醒用户已另存副本由本人管理 |

### 双端验收路径

1. 用真实账号登录，确认凭据未在日志、客户端响应或仓库泄露；测试取消、过期及重登。
2. 设置方向，保存感受，刷新/重启仍存在；第二个账号不能读取这些数据。
3. 接受、暂停、恢复、停止实验；重复提交不重复创建；不足数据不能显示已证实有效。
4. iOS 真机授权选定健康类别并同步真实样本；拒绝/撤回后不得继续上传；无样本不能显示虚构数据。
5. 明确查看模型接收者并同意后验证 AI；拒绝、撤回及服务失败都有真实状态，不能将规则结果写成模型成功。
6. 导出、删除单条、删除全部与注销；删除记录后相关实验结论失效，旧请求不能恢复已删除内容。
7. 完成平台编译/签名、隐私表单、资质与备案核对；记录实际版本及正式审核提交回执。

## English

Status: owner review draft, not ready for submission. Verify the operator's legal name, contact details, public privacy policy, filings, account configuration and feature eligibility before using it.

FitCrew helps users choose a 90-day sleep, energy or activity direction, log daily feelings and observe weekly experiments. Current iOS project version is 3.0.0 (1); the owner's developer account determines the final bundle identifier and signing. The release is free, without purchases, subscriptions or WeChat reminders. Results are descriptive observations, not medical diagnoses or causal proof. Empty data must remain empty. Apple and WeChat login currently create separate identities: cross-platform account merging is not implemented. WeChat cannot directly read Apple Health.

Reviewers can inspect the five tabs before connecting; full review requires working production authentication and service configuration. Optional HealthKit access requires both system permission and category consent. Profile provides consent, export, data deletion and account deletion. Configured AI requires separate consent and receives only the goal enum and recent manual-record aggregates, not notes, account identifiers or raw HealthKit samples. Declare actual providers and features truthfully; personal-account AI eligibility remains unresolved.

Privacy verification must cover encrypted platform identity, manual records and health ingestion; actual retention, backup expiry and hosting; AI provider, agreements, processing location and eligibility; server-side deletion and Apple token revocation; and on-device export cleanup. Do not promise unverified immediate permanent deletion of backups or copies already saved by the user.

Acceptance requires real platform login and cancellation/expiry tests; persistent records and two-account isolation; idempotent experiment transitions and insufficient-data states; real-device HealthKit reads plus denial/revocation; explicit AI recipient consent and honest failure states; export and deletion that invalidate dependent results and prevent stale-request resurrection; then platform builds, signing, truthful privacy/filing forms and formal review submission receipts.

## 2026-09-08 更新：当前候选范围 / Current candidate scope update

本节补充前述草稿，以当前发布分支源码为准。尚无生产部署、真机验收或平台正式提交回执。最终截图和构建号需在设计合入与完整验证后取得，不能使用合成数据预览冒充真实健康记录。

This section updates the draft from the current release branch. Production deployment, device acceptance and formal submission receipts remain absent. Capture final screenshots and build identifiers after design integration and complete verification; synthetic previews are not real health records.

### 可供审核的功能描述候选 / Candidate feature description

在六步引导中了解用途并选择记录方式，设定 90 天生活方式方向；记录精力、压力、整体感受及可选睡醒感受、运动感受、压力来源和笔记。查看 30/60/90 天手动记录趋势、缺口和按日期详情，理解旅程日历阶段。每周实验由本人确认开始，可暂停或停止；记录足够时展示描述性比较。观察里程碑可撤回，实验主观反馈可单独确认为私人记忆，来源删除会使依赖证据失效。以上描述是代码候选范围，仍需真实端到端验收。

A six-step onboarding explains purposes and record modes. Users choose a 90-day lifestyle direction; record energy, stress, general feelings and optional sleep/training feelings, stress sources and notes; and view manual 30/60/90-day trends, gaps, date details and calendar phases. Weekly experiments require explicit acceptance and can be paused or stopped. Sufficient records support descriptive comparisons. Observation milestones are withdrawable; subjective feedback can separately become a private confirmed memory. Source erasure invalidates dependent evidence. This is the implemented candidate scope, pending real end-to-end acceptance.

### 导出和删除核验路径 / Export and deletion acceptance

1. 分别导出全部、手动记录与实验、Apple 健康数据，检查文件 `export_metadata.scope` 与选择一致；回执只证明服务器生成，不证明本机保存或已发送。
2. 切换范围再次生成，确认旧文件清理；模拟清理失败，iOS 应阻止新生成并显示重试，不能仍分享旧文件。已另存或发出的副本不在应用控制范围内。
3. 仅删除全部手动记录，核对健康授权与同步位置、账号及实验历史保留；依赖记录的结果、确认记忆及里程碑失效，旧请求不可恢复记录。
4. 删除全部私有数据与注销分别测试，核对授权撤回、账号保留或会话撤销的差异及服务回执。查看本机清理错误是否与服务器成功分别呈现。

1. Export all, product/manual and Apple Health scopes separately and verify `export_metadata.scope`. A receipt establishes server generation, not local saving or delivery.
2. Regenerate with a different scope and check old-file removal. Simulated iOS cleanup failure must block regeneration and offer retry without exposing an old share link. Previously saved/shared external copies are outside app control.
3. Delete all manual records only: health consent/cursors, account and experiment history must remain; dependent results, confirmed memories and milestones must invalidate, and stale requests must not restore records.
4. Test full private-data deletion and account deletion separately, including their different consent/session effects, server receipts and independent local-cleanup errors.

### 不可据此宣称的能力 / Claims not established

实验保留手动记录比较；新提案现可披露并纳入已授权的健康样本观察，撤回授权、删除或来源冲突会重新影响结果，详见 [实验健康观察](2026-09-09-health-experiment-observations.md)。两端现已实现独立的 Apple 健康趋势卡，展示当前授权样本的睡眠小时、步数、HRV 和 30/60/90 天窗口；缺口不补零，来源冲突不显示数值，详情说明样本数和来源，有值也不代表全天完整覆盖。该卡通过代码测试，真实 HealthKit 长期数据链路仍未验收，不能描述为已验证的健康改善或个性化医学建议。确认记忆未自动送给 AI；不能宣传已读到微信聊天上下文、已获得左侧微信 AI 入口或已具备主动通知。iOS 与微信账号仍未自动关联，微信新账号不因此自动取得 iOS 的健康记录。首次权限分支、生产 AI 提供方及资格均需继续验证。

Experiments retain manual-record comparisons; new proposals can disclose and include consented health-sample observations, recomputed after withdrawal, deletion or source conflict. See [experiment health observations](2026-09-09-health-experiment-observations.md). Both clients now implement a separate Apple Health card showing authorized sleep hours, steps and HRV over 30/60/90-day windows. Missing observations are not zero-filled, conflicted values are hidden, and details identify sources/counts; measured values do not establish full-day coverage. Code tests pass, but longitudinal real-device HealthKit ingestion remains unverified, so the card cannot establish health improvement or personalized medical advice. Confirmed memories are not automatically sent to AI. Access to WeChat chat context, the developer AI entry or proactive notifications is not established. iOS and WeChat accounts are not automatically linked, so a new WeChat identity does not automatically obtain iOS health records. Initial permission branches and production AI provider/eligibility still require validation.


## 设备连接范围更新 / Device connection scope update

新增显式微信账号连接 iOS 的候选实现，复用同一账号记录，单独进行健康授权，并支持断开设备；不自动合并已有的 Apple 登录身份。详见 [连接说明](2026-09-09-wechat-ios-connection.md)。本段更新上述账号连接限制的代码状态，仍未完成真机和生产验收，不能作为提审回执。

An explicit WeChat-to-iOS device connection candidate now reuses the same account records, with separate health authorization and device disconnection. It does not automatically merge an existing Apple login identity. See [connection details](2026-09-09-wechat-ios-connection.md). This updates the implementation status of the account-connection limitation above, but does not establish device/production acceptance or submission.
