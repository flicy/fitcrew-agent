# FitCrew 免费正式版实施计划 / Free Public Release Plan

> 执行 / Execution: subagent-driven-development; isolate ownership, test first, review specification before quality.

## 已确认目标 / Approved goal

微信个人主体小程序和个人主体 iOS 正式提审；免费，无微信提醒；iOS 真实 Apple Health。保留 V2 服务和现有 Demo。用户已于 2026-09-07 确认开始。

Submit personal-account WeChat and iOS apps for production review. Free, no WeChat reminders, real Apple Health on iOS. Preserve V2 services and existing demos. Execution approved on 2026-09-07.

## 基线与架构 / Baseline and architecture

远端 main 为 7cea489；独立分支 codex/free-public-release-20260907。旧本地目录部分 iCloud 占位，保持不动。后端沿用 FastAPI、SQLAlchemy、AES-GCM、User、DeviceBinding、Consent；原生界面扩展现有 HealthKit Bridge，不建第二套数据链。小程序调用同一私有 API。现有飞书入口不改。

Remote main is 7cea489; work occurs on codex/free-public-release-20260907. Preserve iCloud-backed old checkouts. Extend FastAPI, SQLAlchemy, AES-GCM, User, DeviceBinding and Consent. Extend the existing native HealthKit Bridge. WeChat consumes the same private API. Do not change the Feishu ingress.

## 顺序 / Sequence

- [x] 检出与基线 / Checkout and baseline: 340 Python tests and 11 Swift Core tests pass.
- [x] 共享基础闭环 / Shared foundation: encrypted journey, experiment, mission and log records, auth, ownership, revisions, idempotency and descriptive results. Full demo parity remains unverified / 完整 Demo 等价尚未验证。
- [ ] iOS: five tabs, goal onboarding, real API errors, reuse HealthKit, account and privacy controls, simulator build and device evidence.
- [ ] 微信 / WeChat: five pages, wx.login server exchange into existing identity tables, authenticated API, no client secret, real loading/error/retry, review configuration.
- [ ] 发布验收 / Release: integration tests, migration, unsigned build, platform configuration and verified backend, review materials, owner confirmation, actual submission evidence.

## API 合同 / API contract

All private routes use the existing `Authorization: Bearer <device token>` and existing user IDs. JSON field names are snake_case. Mutations return an updated resource; errors contain `detail`. Clients never claim success before a 2xx response.

所有私有接口复用设备 Bearer 和内部用户 ID；JSON 使用 snake_case。写入返回更新对象，失败 detail。客户端收到 2xx 前不得显示成功。

- `GET /v3/state` → `{journey: object|null, experiments: [], logs: [], mission: object|null, health: {sample_count, last_sync_at}, privacy_version: "2026-09-07"}`.
- `PUT /v3/journey` body `{goal: "sleep"|"energy"|"activity", request_id: UUID}` → `{id, goal, title, start_date, days:90, revision}`.
- `POST /v3/experiments/propose` body `{request_id: UUID}` → `{id,title,hypothesis,intervention,metrics:[],success_criteria:[],stop_conditions:[],data_categories:[],duration_days:7,status:"proposed",revision,source:"rule_based",result:null}`. Initial rule proposals must be labeled as rules, never falsely labeled AI. Model proposals are a separate explicit capability to complete before release.
- `POST /v3/experiments/{id}/transition` body `{action:"accept"|"pause"|"resume"|"stop"|"evaluate",revision:int,request_id:UUID}`. Acceptance discloses full experiment scope; evaluation cannot infer causal effects from insufficient evidence.
- `POST /v3/logs` body `{energy:1..5,stress:1..3,feeling:"充沛"|"正常"|"有点累"|"很累"|"不适",note:string<=500,request_id:UUID}` → `{id,energy,stress,feeling,note,created_at,revision}`.
- `DELETE /v3/logs/{id}` → `{deleted:true,receipt_id}`. Confirm in client before deletion.
- `POST /v3/mission` body `{action:"done"|"lighten"|"skip",request_id:UUID}` → `{id,title,status,date,why,revision}`.
- `GET /v3/export` → private JSON export; never write real export into Git.
- `DELETE /v3/data` body `{confirmation:"DELETE"}` → `{deleted:true,receipt_id}`. Removes personal V3 records and health-derived data; retains identity until account deletion.
- `DELETE /v3/account` body `{confirmation:"DELETE"}` → `{deleted:true,receipt_id}`; revoke credentials and erase private data.

## 首批测试 / First tests

`apps/api/tests/test_v3_routes.py` verifies unauthenticated rejection, per-user isolation, encrypted-at-rest fields, idempotent retries, stale revisions, no conclusions without observations, experiment acceptance/pause/stop, and export/deletion. Run `uv run pytest -q apps/api/tests/test_v3_routes.py`, then full pytest and ruff. iOS uses existing Swift test and unsigned xcodebuild. WeChat verifies API serialization/error paths in Node tests and later real Developer Tools.

首批测试覆盖未授权拒绝、跨用户隔离、加密、重复请求、版本冲突、无观察不下结论、实验状态、导出与删除。先针对性测试，再全量回归；小程序需开发者工具实测，iOS 需真机验证，均不能用测试替代。

## 外部门槛 / External gates

本轮双端基础代码及规格/质量复核已推进；客户端与发布复选项保留未完成，因为真机和平台验收尚未完成。最新测试与复核结果见发布验证记录。/ Client foundations and reviews have progressed; device and platform acceptance remain incomplete, so client/release checkboxes stay open. See the release verification record for current evidence.

Apple membership, identity/legal/payment steps require owner action. WeChat AppID, category, filing, HTTPS domain and credentials must be verified. Production state must be read live, not inferred from README. No submission or deployment claim without authoritative proof. Keep progressing on independent work while gates remain.

Apple 会员、身份、协议和付款由用户完成；核实微信 AppID、类目、备案、HTTPS 域名及凭据。生产状态需现场核验，不能引用 README 当作现状。存在门槛时继续其他可推进工作，真实提审前不得称完成。
