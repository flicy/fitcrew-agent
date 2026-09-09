# 重复确认健康授权 / Reconfirming health consent

## 中文

此前 `/v3/consents` 每次都会撤销全部旧授权并重建记录，即使范围与告知版本完全相同。实验健康观察绑定具体授权记录，因此网络重试或第二台 iPhone 确认相同类别会使旧实验错误失去依据。

现在保留仍有效、仍勾选且告知版本相同的授权及其原始时间。添加类别只为新类别创建授权；取消类别会撤回对应授权。已经撤回的记录永不恢复，之后重新同意会创建新记录，旧实验不会因此自动恢复访问。告知版本变化同样需新授权。iOS 明确说明选择会更新整个账号的上传范围，以及撤回对旧实验的影响。

新增测试通过真实接口验证第二台设备和重复确认保留旧实验范围，添加/取消/重新同意的记录身份与撤回时间正确，告知版本变更生成新记录。此修复不构成真实 HealthKit 或平台审核验收。

## English

Previously, every `/v3/consents` call revoked and recreated all health grants, even with identical categories and disclosure. Experiment observations bind specific grants, so a network retry or a second iPhone confirming the same scope could incorrectly invalidate existing evidence access.

Keep active, selected grants with the same disclosure version and original timestamps. Create grants only for added categories; revoke omitted categories. Never revive withdrawn records: a later regrant creates a new record and does not reactivate an old experiment. Changed disclosure also requires a new grant. iOS explains that scope applies across the account and that withdrawal affects existing observations.

New endpoint tests verify preserved experiment scope after second-device/repeated confirmation, correct grant identity and withdrawal timestamps across addition/removal/regrant, and new receipts for changed disclosure. This does not establish real HealthKit integration or platform acceptance.
