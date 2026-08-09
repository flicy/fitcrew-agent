# Apple Developer and TestFlight Readiness / Apple 开发者与 TestFlight 准备清单

## 中文

### 直接结论

FitCrew Health Bridge 要通过 TestFlight 远程安装，Chris 需要加入 Apple Developer Program。个人会员年费为 99 美元或当地等值货币；Apple 完成身份核验后才能购买。会员生效、必要协议完成、App Store Connect App 记录建立并上传签名构建后，才可以邀请薛程进行外部测试。首次外部 TestFlight 构建需要 Beta App Review，时间由 Apple 决定。

### 加入个人会员前准备

- 一个启用双重认证的 Apple Account。
- Apple Account 中使用与证件一致的真实姓名；个人会员的 App Store 销售者名称会显示该真实姓名。
- 可验证的邮箱、手机号和实体地址，不能使用邮政信箱。
- 达到所在地法定成年年龄。
- 本人可用的付款方式；年费为 99 美元或当地等值货币。
- 准备由 Account Holder 本人完成身份验证、Apple Developer Program License Agreement 和购买步骤。Codex 不代填证件、不接受协议、不付款。

官方入口：[加入 Apple Developer Program](https://developer.apple.com/programs/enroll/)、[会员注册说明](https://developer.apple.com/help/account/membership/program-enrollment)

### FitCrew App 提交前准备

- 唯一 Bundle ID、App 名称、正式图标、版本号和递增构建号。
- App Store Connect App 记录；必须先建立记录，才能上传构建。
- 中英文 Beta 描述、测试重点和反馈邮箱。
- 可公开访问的隐私政策 URL 与支持 URL。隐私政策必须说明收集哪些健康数据、用途、共享对象、保留/删除和撤回方式，并在 App 内可访问。
- 审核联系人与可让审核人员完成 HealthKit 授权和配对的说明；不得提供真实用户健康数据。
- 出口合规问卷。构建缺少合规信息会停留在 `Missing Compliance`；法律答案必须由 Account Holder 确认。

官方资料：[App Store Connect 工作流](https://developer.apple.com/help/app-store-connect/get-started/app-store-connect-workflow)、[上传构建](https://developer.apple.com/help/app-store-connect/manage-builds/upload-builds/)、[TestFlight 概览](https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview/)

### HealthKit 特别要求

- HealthKit 只能用于健康和健身目的，并在 App 描述中说明集成用途。
- App 必须明确披露从设备采集的具体健康类别。
- HealthKit 数据不得用于广告、营销或使用型数据挖掘，也不得向 HealthKit 写入虚假数据。
- App Store Connect 和 App 内都需要容易访问的隐私政策。

官方资料：[App Review Guidelines 2.5.1、5.1.1、5.1.3](https://developer.apple.com/app-store/review/guidelines/)、[HealthKit 隐私设计](https://developer.apple.com/documentation/healthkit/protecting-user-privacy)

### 外部 TestFlight 流程

1. 会员生效并完成必要协议。
2. 创建 App Store Connect App 记录。
3. 用 Xcode Release Archive 上传带 App Identifier 的签名构建。
4. 补齐出口合规和 Beta 测试信息。
5. 创建受限外部测试组，通过薛程的 Apple Account 邮箱邀请；FitCrew 不使用公开链接。
6. 首个构建提交 TestFlight Beta App Review。
7. Apple 批准后，薛程安装 TestFlight 和 FitCrew Health Bridge，授权 HealthKit 并扫描独立配对码。

官方资料：[邀请外部测试者](https://developer.apple.com/help/app-store-connect/test-a-beta-version/invite-external-testers)、[构建状态](https://developer.apple.com/help/app-store-connect/reference/app-build-statuses/)

### Account Holder 必须亲自完成

- 身份验证、会员购买和法律协议接受。
- 确认出口合规答案。
- 提供准确的真实姓名、地址、电话、反馈邮箱、审核联系人和薛程的邀请邮箱。
- 对任何 Apple 提出的健康、隐私或合规问题给出真实确认。

Codex 可以完成代码、测试、图标与元数据草稿、Archive 配置、上传前验证和操作引导；没有明确授权时，不执行购买、接受协议、上传构建或发送邀请。

## English

### Direct result

Remote TestFlight installation of FitCrew Health Bridge requires Chris to join the Apple Developer Program. Individual membership costs USD 99 per year or the local equivalent and can be purchased after Apple verifies the enrollment. The membership, required agreements, App Store Connect app record, and signed build must be ready before Xue Cheng can be invited. The first external TestFlight build requires Beta App Review, whose timing is controlled by Apple.

### Individual enrollment preparation

- An Apple Account with two-factor authentication enabled.
- A legal first and last name matching identity records; an individual developer's legal name becomes the App Store seller name.
- A verifiable email address, phone number, and physical address; P.O. boxes are not accepted.
- Legal age of majority in the enrollment region.
- A valid personal payment method; the annual fee is USD 99 or the local equivalent.
- The Account Holder must personally complete identity verification, the Apple Developer Program License Agreement, and purchase. Codex does not enter identity documents, accept agreements, or pay.

Official entry points: [Enroll](https://developer.apple.com/programs/enroll/) and [Program enrollment help](https://developer.apple.com/help/account/membership/program-enrollment)

### FitCrew submission preparation

- A unique Bundle ID, app name, production icon, marketing version, and incrementing build number.
- An App Store Connect app record, which must exist before build upload.
- Bilingual beta description, test focus, and feedback email.
- Public privacy-policy and support URLs. The policy must describe collected health categories, purposes, sharing, retention/deletion, and consent withdrawal, and must also be accessible inside the app.
- Review contact details and instructions that let reviewers exercise HealthKit authorization and pairing without real user health data.
- Export-compliance answers. A build missing this information remains in `Missing Compliance`; the Account Holder must confirm legal answers.

Official sources: [App Store Connect workflow](https://developer.apple.com/help/app-store-connect/get-started/app-store-connect-workflow), [Upload builds](https://developer.apple.com/help/app-store-connect/manage-builds/upload-builds/), and [TestFlight overview](https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview/)

### HealthKit-specific requirements

- HealthKit must serve health and fitness purposes, and the app description must explain the integration.
- The app must disclose the specific health categories it collects.
- HealthKit data cannot be used for advertising, marketing, or use-based data mining, and the app must not write false data.
- An easily accessible privacy policy is required in App Store Connect and inside the app.

Official sources: [App Review Guidelines 2.5.1, 5.1.1, and 5.1.3](https://developer.apple.com/app-store/review/guidelines/) and [Protecting HealthKit user privacy](https://developer.apple.com/documentation/healthkit/protecting-user-privacy)

### External TestFlight flow

1. Activate membership and complete required agreements.
2. Create the App Store Connect app record.
3. Upload a signed Xcode Release Archive with an App Identifier.
4. Complete export compliance and beta test information.
5. Create a restricted external group and invite Xue Cheng by Apple Account email; FitCrew does not use a public link.
6. Submit the first build to TestFlight Beta App Review.
7. After approval, Xue Cheng installs TestFlight and FitCrew Health Bridge, grants HealthKit access, and scans the dedicated pairing code.

Official sources: [Invite external testers](https://developer.apple.com/help/app-store-connect/test-a-beta-version/invite-external-testers) and [Build statuses](https://developer.apple.com/help/app-store-connect/reference/app-build-statuses/)

### Account Holder-only actions

- Identity verification, membership purchase, and legal agreement acceptance.
- Confirmation of export-compliance answers.
- Accurate legal name, address, phone, feedback email, review contact, and Xue Cheng's invitation email.
- Truthful confirmation of any health, privacy, or compliance question raised by Apple.

Codex can prepare code, tests, icon and metadata drafts, Archive configuration, pre-upload validation, and operating guidance. Without explicit authorization at the relevant step, it will not purchase membership, accept agreements, upload builds, or send invitations.
