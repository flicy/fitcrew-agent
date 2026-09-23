# 微信账号连接 iOS / Connect iOS to a WeChat account

## 中文

采用复用现有身份的设备连接方案：小程序生成 15 分钟有效、限一次使用的连接；在 FitCrew iOS 粘贴或打开后，用户确认替换本机账号连接。配对不自动合并独立的 Apple 登录账号，不移动或删除原账号记录。连接后 iOS 与小程序访问同一用户的记录，健康上传仍需在 iOS 单独选择类别并申请系统读取权限。

- 小程序先解释链接持有者可访问私人账号，由用户主动复制；不自动复制，不把链接存入本地持久化存储。离开页面隐藏链接，账号变化丢弃迟到结果。网络结果不确定时保留请求编号；已用或过期的确定冲突允许重新生成。
- 服务端仅允许已登录的微信设备生成连接。密钥由服务器密钥与账号及请求编号派生；新连接撤销同账号旧的未使用连接，不能撤销其他账号的连接。兑换与删除按用户锁串行化，删除数据或注销后旧连接失效。
- 复用 `PairingExchangeSession`、`DeviceBinding` 与用户表，迁移 `0005_device_only_pairing` 增加明确的“保留现有授权”字段。新设备连接不新增、不撤回原健康授权，返回空上传授权范围；新设备会话 30 天到期。旧邀请流程仍保留原行为。
- 小程序显示由该流程连接的有效设备，并允许断开。断开撤销该设备的服务端令牌，保留云端记录，不影响微信登录；不声称能远程清除已经导出或查看的本机副本。撤销未使用链接与断开已连接设备是不同操作。
- iOS 不再仅凭外部链接自动兑换；先显示服务域名和替换账号说明，取消不发送兑换请求。确认期间账号变化会使提示失效；兑换时仍执行账号代次、请求顺序和服务地址检查。

本地后端回归 411 项通过，其中包含真实加密产品记录在两种设备之间读取、授权不变、一次使用、撤销与过期、删除失效、跨用户隔离及设备断开。小程序边界测试与官方离线编译已覆盖初步入口；最终测试计数与 iOS 完整构建以对应提交 CI 为准。尚未完成微信真机登录、iPhone 实际安装、HealthKit 联调或任何正式提审。此前截图或浏览器预览不能证明这些入口已在真机验收。

回滚要求：回退到不认识“仅设备连接”的旧 API 之前，必须停用所有该模式的未使用连接；否则旧兑换逻辑可能误改健康授权。新增迁移的降级会删除该模式的兑换行，但不会删除用户记录或设备。禁止将 `0004_product_records` 降级用作应用回滚。生产迁移仍需备份、隔离恢复和兼容性验证。

## English

Reuse the existing user identity through device connection: the Mini Program creates a single-use link valid for 15 minutes. Opening or pasting it in FitCrew iOS requires confirmation before replacing the local account connection. This does not merge an independent Apple-login account or move/delete its records. Both devices then read the same user's records; health uploads still require separate category selection and system authorization in iOS.

- Explain account access before creation and require an explicit copy action. Never copy automatically or persist the link in Mini Program storage. Hide it on page exit and discard stale responses after account changes. Reuse request IDs for uncertain network outcomes; renew after a definitive expired/used conflict.
- Only an authenticated WeChat device may issue a link. The server derives its secret from its private key, user and request ID. A new link invalidates that user's previous unused links without affecting others. User locks serialize exchange and deletion; data/account deletion invalidates old invitations.
- Reuse the existing pairing, device and user tables. Migration `0005_device_only_pairing` adds an explicit consent-preservation flag. Device-only exchange neither grants nor withdraws health consent, returns an empty upload scope, and issues a 30-day device session. Legacy invitations retain their previous behavior.
- Show active devices created through this flow and allow disconnection. Revoke only that device token, preserving cloud records and WeChat access. Do not promise remote deletion of previously viewed/exported local copies. Cancelling unused links and disconnecting devices are separate actions.
- iOS no longer automatically exchanges an external link. Show the server and account-replacement notice first; cancellation sends no exchange request. An identity change invalidates the pending confirmation; exchange still enforces identity revision, request ordering and matching server URL.

The local backend regression passes 411 tests, including reading an encrypted product record through both device identities, unchanged consent, one-time use, cancellation/expiry, deletion invalidation, user isolation and disconnection. Mini Program boundary tests and official offline compilation cover the initial entry; consult matching commit CI for final counts and the complete iOS build. Real WeChat login, iPhone installation, HealthKit integration and formal submissions remain unverified. Earlier screenshots or browser previews do not prove device acceptance.

Before rolling back to an API that does not understand device-only pairing, invalidate every unused device-only link; old exchange code could otherwise replace health consent. Downgrading the new migration deletes those exchange rows, not user records or devices. Never downgrade `0004_product_records` as an application rollback. Production migration still requires backup, isolated restore and compatibility validation.
