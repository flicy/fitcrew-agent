# 实验健康观察 / Experiment health observations

## 中文

实验现在可以在原有手动精力结果旁展示已授权的睡眠、步数、心率变异性样本观察。提案会列出具体健康类别、观察指标和方法；确认开始才应用。原有未披露健康范围的实验保持原范围。此实现不代表真实设备联调、生产部署或平台提审完成。

- 范围绑定提案时已有的具体授权记录，时区固定为开始时的用户时区。后来的新授权不扩大旧实验；撤回后重新授权也不会自动恢复旧实验的访问。
- 基线和观察窗只纳入完全位于窗内的日历日。与暂停区间有任何重叠的整日排除。两窗各至少四天有可用数值才比较按日均值；真实零值保留，缺失、来源冲突及异常不补零。结果附使用日期、来源、样本天数及排除天数。
- 展示的是部分样本的描述性变化，不表示全天覆盖或行动效果。健康值不发送给 AI；用户对行动的主观反馈及确认记忆仍与健康观察数值区分。
- 健康观察在读取时从当前样本和仍有效的授权重新计算，不落入实验结果、幂等响应缓存或确认记忆。撤回授权、删除样本或新增来源冲突都会改变下次读取，避免保留失效数值。
- 全部数据导出包含健康观察；仅手动记录与实验的导出不包含健康观察值。原始健康导出范围保持不变。
- 两端展示观察摘要和来源。iOS 的手动实验结果同时改成可读摘要，不再向用户直接展示内部结果字段。

验证：完整后端回归 406 项通过，另有六个健康观察测试覆盖加密样本摄取、零值、冲突、删除、撤权与重新授权、暂停、时区、部分边界日、跨用户隔离及导出范围。小程序 33 项测试和官方离线编译通过；Swift Core 的七个 XCTest 与 11 个 Swift Testing 测试通过。新增 iOS 页面仍需完整模拟器构建和真机验收；新页面视觉验收未完成。以上使用合成测试样本，不是用户真实健康数据验收。

## English

Experiments can now show consented sleep, step-count and HRV sample observations alongside manual energy results. Proposals disclose the precise health categories, metrics and method; acceptance is required. Existing experiments without disclosed health scope retain their original scope. This implementation does not establish real-device integration, production deployment or platform submission.

- Scope is bound to the specific consent records present at proposal time; timezone is fixed at acceptance. Later grants do not expand an old experiment, and a new grant after withdrawal does not automatically reactivate its access.
- Include only calendar days wholly inside each baseline/observation window. Exclude entire days overlapping any pause. Both windows need four usable days before comparing day-weighted means. Preserve measured zero; never replace missing, conflicting or invalid values with zero. Return contributing dates, sources, sample-day counts and quality-excluded counts.
- Changes describe partial samples, not full-day coverage or intervention effects. Health values are not sent to AI. Subjective feedback and explicitly confirmed memories remain separate from health-observation values.
- Recompute observations from current samples and still-valid consent on read. Do not persist them in experiment results, idempotency response caches or confirmed memories. Withdrawal, deletion and new source conflicts affect the next read instead of leaving stale values.
- All-data export includes observations; product-only export excludes their health values. The existing raw-health export scope is unchanged.
- Both clients show readable summaries and sources. iOS also renders manual experiment summaries instead of internal result fields.

Validation: 406 backend tests pass. Six health-observation tests cover encrypted ingestion, zero, conflicts, deletion, withdrawal/regrant, pauses, timezone, partial boundary days, user isolation and export scope. All 33 Mini Program tests and official offline compilation pass. Swift Core passes seven XCTest and 11 Swift Testing tests. The new iOS page still needs a complete simulator build and device acceptance; visual acceptance remains incomplete. Tests use synthetic samples and do not verify the user's real health data.
