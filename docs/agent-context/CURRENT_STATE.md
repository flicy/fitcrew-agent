# 当前状态 / Current State

更新时间 / Updated: 2026-09-10

## 中文

正式发布分支为 `codex/free-public-release-20260907`，继承 V2 的 User、DeviceBinding、Consent、加密摄取与 HealthKit；生产飞书入口保留 Moticlaw。本次尚未部署或正式提审。不要把早期 9 月 7 日的缺失项或测试数量当作当前状态。

最新已核验 CI 的代码为 `1386968c85788db05e932358300fc1a9f8949077`，运行 `34358841593` 成功。五页原生小程序与 iOS、90 天旅程、手动记录、实验与健康观察、导出/删除和独立 AI 同意已经实现；这不等于完整 Demo 等价或平台验收。

后续于早期快照实现的关键能力：

- `0cc080a`：实验基于当前有效健康授权计算描述性观察，排除暂停日与不足证据；不宣称因果结论。
- `81924d8`：iOS 配对请求保护账号切换与旧请求回写。
- `a652acf`：微信登录账号生成限时单次 iOS 连接，列出和撤销自己的设备；不自动合并 Apple 身份。迁移已到 `0005_device_only_pairing`，回滚注意事项见连接文档。
- `7f63bbd`：重复确认未变化的健康授权保留原授权，不使既有实验无故失效。
- `1386968`：用户重新单独同意后，AI 仅接收同目标最多 10 条已确认结构化反馈；撤回记忆会使相关待执行建议失效。不是微信 AI 灰度资格或完整主动干预能力的证明。

本轮补齐 iOS 发布地址构建变量与产物配置检查，详见 [发布配置](../release/2026-09-10-ios-release-configuration.md)。此前通过的 CI 不证明这次新增改动已通过云端验证。

实际阻塞：微信开发者工具仍未登录，只有已授权用于开发的测试 AppID，正式 AppID/类目/备案/HTTPS 域名未核实；现有 root SSH 验证被拒绝，未升级服务器；iPhone 可被发现但不等于可安装验收，Xcode 签名构建仍报未添加账号和缺少描述文件。运营者、隐私政策、AI 服务商与资格、Apple 提交主体和会员状态仍须核实，不编造或通过隐藏功能绕过。

下一步优先完成微信正式配置与真实登录/保存/重登/删除联调；Apple 账号可用后签名构建并进行真实 HealthKit 验收。正式提审前核对具体版本、材料与用户确认，最终必须留存平台提交时间和审核状态。招募与小红书发布继续延后。不得运行旧全服务部署或破坏数据、密钥和身份；API 单独发布见 `docs/operations/api-only-release.md`。

## English

The release branch is `codex/free-public-release-20260907`. It extends V2 User, DeviceBinding, Consent, encrypted ingestion and HealthKit, preserving Moticlaw as the sole production Feishu ingress. No production deployment or formal submission has occurred. Do not use September 7 missing-feature snapshots or test counts as current evidence.

The latest verified CI revision is `1386968c85788db05e932358300fc1a9f8949077`, with successful run `34358841593`. Five native pages on each client, the 90-day journey, manual records, experiments and health observations, export/erasure and separate AI consent exist. This does not establish full demo parity or platform acceptance.

Key changes since the early snapshot:

- `0cc080a`: consent-filtered descriptive health observations, excluding paused days and insufficient evidence; no causal claim.
- `81924d8`: iOS pairing guards against account changes and stale responses.
- `a652acf`: authenticated WeChat users can issue expiring one-time iOS connections, list devices and revoke them. Apple identities are not automatically merged. Migration is now `0005_device_only_pairing`; consult the connection document before rollback.
- `7f63bbd`: reconfirming unchanged health grants preserves existing authorizations and experiments.
- `1386968`: renewed separate consent lets AI receive up to ten confirmed structured feedback items for the same goal. Withdrawing memory invalidates dependent pending proposals. This does not prove WeChat AI eligibility or complete proactive intervention.

This round adds iOS release URL build substitutions and built-artifact configuration checks; see the linked release configuration document. Earlier CI results do not verify these new changes.

Current blockers: WeChat Developer Tools is signed out; only the authorized test AppID is known, with production AppID/category/filing/HTTPS domain unverified. Existing root SSH authentication is refused; no server upgrade occurred. iPhone discovery does not establish installation readiness, and Xcode signing still reports missing accounts/profiles. Operator/privacy details, actual AI provider and eligibility, Apple submitting entity and membership remain unresolved. Do not invent them or conceal features.

Next: production WeChat configuration and real login/save/relogin/erasure acceptance, then signed iOS and real HealthKit acceptance once the Apple account is available. Confirm the concrete version/materials before formal submission and retain platform submission time/status. Recruitment and Xiaohongshu publishing remain deferred. Preserve production identities, keys and data; use the API-only procedure rather than legacy full-service deployment.
