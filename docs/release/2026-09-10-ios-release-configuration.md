# iOS 发布配置 / iOS release configuration

## 中文

XcodeGen 现在保留 `FitCrewAPIBaseURL` 和 `PrivacyPolicyURL` 的构建变量。真实值分别从 `FITCREW_API_BASE_URL` 和 `FITCREW_PRIVACY_POLICY_URL` 传入，避免手改 Info.plist 后被重新生成覆盖。没有配置时仍不能进行正式 Apple 登录，不提供默认生产域名。

账号与域名核实后，在仓库根目录执行以下构建步骤。环境变量必须是实际已部署服务和已核实公开政策的 HTTPS 地址；下面没有提供或购买域名。Team 必须来自本人可用开发者账号。构建不接受协议、不代付会员，也不执行上传。

```bash
: "${FITCREW_API_BASE_URL:?Set verified production HTTPS API URL}"
: "${FITCREW_PRIVACY_POLICY_URL:?Set verified public privacy policy URL}"
: "${FITCREW_DEVELOPMENT_TEAM:?Set verified Apple team}"
xcodegen generate --spec apps/ios-bridge/project.yml
xcodebuild -project apps/ios-bridge/FitCrewHealthBridge.xcodeproj \
  -scheme FitCrewHealthBridge -configuration Release \
  -destination 'generic/platform=iOS' \
  -archivePath "$PWD/.sandbox/FitCrew.xcarchive" \
  "DEVELOPMENT_TEAM=$FITCREW_DEVELOPMENT_TEAM" \
  "FITCREW_API_BASE_URL=$FITCREW_API_BASE_URL" \
  "FITCREW_PRIVACY_POLICY_URL=$FITCREW_PRIVACY_POLICY_URL" archive
python3 scripts/validate_ios_release.py \
  .sandbox/FitCrew.xcarchive/Products/Applications/FitCrewHealthBridge.app/Info.plist
```

检查器读取构建产物，不接受源码中的未替换变量。它检查 URL 格式、版本、包标识、健康读取告知和全局传输安全开关；通过不证明域名归属、联网可达、签名、主体资格、隐私内容、真机验收或正式提审。仍须记录具体版本、提交时间与平台审核状态。失败时保留日志并修复实际配置，不关闭 TLS 或删除 HealthKit/Apple 登录能力来绕过。

2026-09-10 本轮签名构建仍报 `No Accounts` 和缺少 `com.fitcrew.healthbridge` 描述文件。需要本人打开 **Xcode → Settings → Accounts / Apple Accounts → + → Apple Account** 登录；已有本机开发证书不能替代此步骤。微信开发者工具实测未登录；服务器现有 root SSH 验证失败。未改变生产环境，未提交平台审核。

本轮验证：3 项针对性测试、Ruff、生成配置检查和双语文档检查通过；无签名 `iphoneos Release` 构建成功。读取最终 App 确认两个构建变量已替换为 `build-fixture.invalid` 测试地址，产物检查按预期拒绝这些测试域名。该包未安装、未上传，不是可分发产物。

## English

XcodeGen now preserves the `FitCrewAPIBaseURL` and `PrivacyPolicyURL` build substitutions. Supply their actual values through `FITCREW_API_BASE_URL` and `FITCREW_PRIVACY_POLICY_URL`; regenerating the project will no longer require manual plist edits. Missing configuration still disables public Apple login. No production domain is supplied by default.

After verifying the account and domains, run the commands above from the repository root. Environment values must identify the deployed HTTPS service, verified public privacy policy and legitimate Apple development team. The commands neither purchase a domain/membership nor accept agreements or upload a build.

The validator reads the built app, rejecting unresolved source substitutions. It checks URL shape, version, bundle identifier, HealthKit disclosure and the global transport-security switch. Passing does not establish domain ownership, reachability, signing, entity eligibility, privacy content, device acceptance or submission. A formal receipt still requires the exact version, submission time and platform review status. Preserve failure logs and fix the actual configuration; do not bypass TLS or remove HealthKit/Apple login capabilities.

The 2026-09-10 signing attempt still reports `No Accounts` and a missing provisioning profile for `com.fitcrew.healthbridge`. The owner must sign in through **Xcode → Settings → Accounts / Apple Accounts → + → Apple Account**; an existing local development certificate does not replace this step. WeChat Developer Tools remains signed out and the existing root SSH authentication failed. No production environment was changed and no review was submitted.

Validation this round: three targeted tests, Ruff, generated configuration and bilingual documentation checks passed. An unsigned iphoneos Release build succeeded; the built app contained both resolved build-fixture.invalid URLs and the validator correctly rejected those test domains. The app was neither installed nor uploaded and is not a distributable artifact.
