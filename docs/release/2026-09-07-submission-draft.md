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
