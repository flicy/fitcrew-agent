# FitCrew 正式提审状态 / Production Review Status

## 中文

用户确认：个人主体微信小程序与个人主体 iOS；首发免费、无微信提醒；真实 Apple Health。当前处于开发与本地验证，尚未部署新版本或提交正式审核。

### 已核实的工程事实

- 新工程基于远端主干 `7cea489c7d06cd30904b1853df3968ba6916260a`，独立分支 `codex/free-public-release-20260907`。旧工作区含 iCloud 占位文件，未覆盖。
- 复用 V2 身份、设备令牌、Consent、加密摄取与 HealthKit，新增 `/v3` 产品接口；不修改生产飞书入口。
- 原有 Python 基线 340 项、Swift Core 11 项通过。新增测试覆盖身份验证、无数据、记录、幂等、跨用户隔离、实验授权/暂停/结束、删除及结果失效。最终计数以最新验证记录为准。
- Python 最终一轮 364 项测试通过。iOS 无签名模拟器构建成功，并已直接观察紫色新版首页及未连接空状态；交互自动化仍遇到 AX 错误，完整导航验收待补。无签名构建和模拟器截图不是 HealthKit 真机同步、分发或提审证据。
- 小程序五个原生页面已实现，本地 14 项测试通过。缺少真实 AppID、HTTPS 业务域名和微信开发者工具；未完成官方编译及真机登录。
- 旧公网服务 `/healthz` 返回 HTTP 200；仅证明旧服务可用，不证明 V3 部署或飞书消息链可用。

### 需要用户或平台完成的事项

| 事项 | 当前证据 | 下一步 |
| --- | --- | --- |
| Apple 开发者会员 | 用户明确尚未开通 | 本人以个人身份完成身份核验、协议及付款；代码不代替这些步骤 |
| Apple 应用配置 | 未核验 Team、App ID、Apple 登录密钥及 App Store Connect 记录 | 会员生效后在本人账号创建并核实；敏感凭据仅放服务端 |
| 真机 | 尚未收到可连接 iPhone 的确认 | 验证真实登录、HealthKit 类别、首同步、拒绝/受限与撤回 |
| 隐私政策 | 运营者身份、联系方式、公开政策地址及备份留存周期未核实 | iOS 配置真实 HTTPS `PrivacyPolicyURL`；微信后台配置隐私保护指引。不能用版本号文字代替可阅读的政策 |
| 微信账号 | 用户确认已有个人主体账号，未提供 AppID | 读取真实 AppID、后台类目、备案及服务器域名状态 |
| 微信个人主体与 AI | 官方个人类目列有工具—健康管理；AI问答/AI创作列在非个人部分 | 完整 AI 功能不得默认用记录类目申报；以真实功能核实资格，不隐藏审核后开启的功能 |
| HTTPS 域名与备案 | 当前仅核实旧公网 IP 服务 | 小程序需符合官方域名要求；不得把 IP 地址当作已备案业务域名 |
| 模型服务 | 复用既有 gateway，公共 AI 配置默认关闭 | 确定真实服务商、用途披露、适用备案/登记及协议；显式单独授权后才发送最小聚合 |
| 提审 | 未提交 | 完成工程、真机/平台验证和材料核对后，用户确认具体版本再提交 |

### 配置与部署边界

`BODYOS_PUBLIC_AUTH_ENABLED`、`BODYOS_WECHAT_APP_ID`、`BODYOS_WECHAT_APP_SECRET`、`BODYOS_APPLE_CLIENT_ID`、`BODYOS_APPLE_CLIENT_SECRET`、`BODYOS_PUBLIC_BASE_URL` 由部署环境提供，不能写入 Git。Apple client secret 是服务端签名的有期限凭据，不是 Apple 账号密码。

AI 另需 `BODYOS_PRODUCT_AI_ENABLED`、`BODYOS_PRODUCT_AI_PROVIDER`、`BODYOS_PRODUCT_AI_NOTICE_VERSION`，名称须与真实接收数据的服务商一致，变更披露版本后旧 AI 同意失效。代码开关用于真实能力与配置状态，不用于绕过审核。

iOS 客户端另需真实服务地址 `FitCrewAPIBaseURL` 和公开政策 `PrivacyPolicyURL`；两者均不是秘密。未配置有效 HTTPS 政策时，Apple 正式登录入口禁用。构建已验证，但不代表这些发布配置已填好。

现有 `infra/tencent/deploy.sh` 会启动历史 gateway，不能直接用于此次生产升级。发布时须保留 Moticlaw 单一飞书入口，先确认服务器实际运行组件、备份、数据库迁移及回滚；只发布本次获准的数据 API/客户端。不得直接运行旧全服务部署脚本。

### 完成证据

两端各自需要：实际版本号/构建号、可安装产物、核心交互及失败状态记录、真实账号与设备验收、适用隐私/备案材料、平台正式审核提交时间及状态。截图、测试、上传、体验版或 TestFlight 均不能替代正式提审回执。

## English

Approved scope: personal-account WeChat and iOS production review, free release, no WeChat reminders, real Apple Health. Development and local verification are in progress; the new release has not been deployed or submitted.

The isolated branch extends main `7cea489` and preserves the iCloud-backed old workspace and production Feishu ingress. It reuses V2 identity, device credentials, consent, encrypted ingestion and HealthKit. Baseline checks passed (340 Python tests and 11 Swift Core tests); the latest backend run passed 364 tests. New tests cover provider authentication, isolation, retry protection, experiments and erasure. An unsigned iOS build passed and the purple home screen with its disconnected empty state was directly observed; AX interaction errors leave full navigation and device acceptance incomplete. The native WeChat five-page client passed 14 local tests, but official compilation and real login await Developer Tools, AppID and a verified HTTPS domain. The old public health check returned 200, which proves neither V3 deployment nor Feishu delivery.

External gates: owner Apple membership, identity/legal/payment steps; verified Team/App ID/Sign in with Apple server credentials; a real iPhone; actual WeChat AppID, category, filing and HTTPS domain; truthful model-provider disclosure and applicable AI registration. WeChat's personal health-record category does not establish eligibility for the full AI feature set. Confirm qualifications for actual functionality and never hide features for review.

Verify the operator, contact, retention/backup policy and public privacy URL. iOS needs real `FitCrewAPIBaseURL` and HTTPS `PrivacyPolicyURL`; Apple login is disabled without a valid policy URL. Configure the WeChat platform privacy contract too. A policy version string is not a readable policy, and successful builds do not establish complete release configuration.

Store `BODYOS_PUBLIC_AUTH_ENABLED`, `BODYOS_WECHAT_APP_ID`, `BODYOS_WECHAT_APP_SECRET`, `BODYOS_APPLE_CLIENT_ID`, `BODYOS_APPLE_CLIENT_SECRET` and `BODYOS_PUBLIC_BASE_URL` in the deployment environment. Apple client secret is an expiring server-signed credential, not an account password. AI additionally requires `BODYOS_PRODUCT_AI_ENABLED`, `BODYOS_PRODUCT_AI_PROVIDER` and `BODYOS_PRODUCT_AI_NOTICE_VERSION`; identify the actual recipient and invalidate prior consent when disclosure changes. Configuration switches are not review bypasses.

Do not run the legacy all-service deployment script: it starts the historical gateway. Inspect live services, backup, migrate and plan rollback while preserving Moticlaw as sole Feishu ingress. Deploy only the authorized data API/client changes. Completion requires each platform's actual build, device acceptance, privacy/filing materials and formal review submission receipt. Tests, screenshots, uploads, experience builds and TestFlight do not prove production submission.

## 官方依据 / Official references

- [Apple enrollment](https://developer.apple.com/help/account/membership/program-enrollment/)
- [Apple review: data collection and storage](https://developer.apple.com/app-store/review/guidelines/#data-collection-and-storage)
- [Apple health and fitness](https://developer.apple.com/health-fitness/)
- [Apple account deletion](https://developer.apple.com/support/offering-account-deletion-in-your-app/)
- [WeChat service categories](https://developers.weixin.qq.com/miniprogram/product/material/)
- [WeChat network requirements](https://developers.weixin.qq.com/miniprogram/dev/framework/ability/network.html)
- [WeChat privacy authorization](https://developers.weixin.qq.com/miniprogram/dev/framework/user-privacy/PrivacyAuthorize.html)
- [WeChat filing guidance](https://developers.weixin.qq.com/miniprogram/product/record_guidelines.html)
- [Apple mainland China app information](https://developer.apple.com/cn/help/app-store-connect/reference/app-information/app-information)
