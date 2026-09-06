# 当前状态 / Current State

更新时间 / Updated: 2026-09-07

## 中文

V1 群聊搭子及 V2 私有健康数据服务是既有基线。V2 包含 HealthKit、分类授权、加密与幂等摄取、健康聚合、飞书身份、私聊个性化、群聊隔离、去标识化模型输入、知识审核及腾讯云部署材料。历史部署文档不等于本次已核验生产状态；生产飞书入口继续由 Moticlaw 承担，不能启动旧 gateway 替代。

V3 免费双端正式提审工作在独立分支 `codex/free-public-release-20260907`，基于 `7cea489`。原 iCloud 工作区未改动，尚未部署或提交审核。

已新增共享 `/v3` 私有产品 API：加密旅程、实验、手动记录、每日行动；幂等、版本冲突、用户隔离、导出、删除和注销；Apple/微信服务端身份验证；可撤回的独立 AI 聚合同意。迁移为 `0004_product_records`。沿用 User、DeviceBinding、Consent 和既有 HealthKit 摄取，未建第二套健康数据栈。

iOS 扩展 Bridge 为五页，沿用真实 HealthKit；微信新增原生五页。客户端本轮独立身份/隐私边界复核通过。紫色新版首页已在模拟器观察，无签名构建成功；真机 HealthKit、微信官方编译及生产联调未完成。后端当前 364 测试通过；SQLite 迁移测试不能证明 PostgreSQL 多连接并发语义。

当前实验实现为手动记录的每周观察与描述性对比；AI 仅在配置和独立同意后从受限动作中选择。不能宣传已实现完整长期身体模型、自动健康因果推理、双端身份自动合并或完整 Demo 等价。用户要求的完整首发范围与个人主体 AI 资格仍需核实，不得以开关隐瞒功能。

继续执行前阅读 [发布门槛](../release/2026-09-07-public-review-gates.md) 和 [提审材料草稿](../release/2026-09-07-submission-draft.md)。优先完成客户端复核；取得 Apple 会员、微信真实 AppID/类目/备案、HTTPS 域名、真实服务商及隐私政策信息后再进行平台验证。旧服务健康检查 HTTP 200 不证明 V3 已发布。无正式回执不得标记目标完成。

## English

V1 group companionship and V2 private health services remain the baseline. V2 includes HealthKit, category consent, encrypted/idempotent ingestion, aggregation, Feishu identity, private personalization, group isolation, de-identified model inputs, knowledge review and Tencent deployment materials. Historical documentation is not current production evidence. Preserve Moticlaw as sole Feishu ingress; do not launch the legacy gateway.

V3 uses isolated branch `codex/free-public-release-20260907` from `7cea489`. The original iCloud checkout is unchanged. No new deployment or review submission occurred.

The shared private `/v3` API adds encrypted journeys, experiments, logs and actions; retry/revision/ownership protection, export and erasure; verified Apple/WeChat login; and separately revocable AI aggregate consent. Migration `0004_product_records` extends existing User, DeviceBinding, Consent and HealthKit infrastructure.

iOS and WeChat have five native tabs/pages. This round of account/privacy reviews passed. The purple iOS home was observed and unsigned builds passed; real-device HealthKit, official WeChat compilation and production integration remain unverified. The backend currently passes 364 tests; SQLite tests do not establish PostgreSQL multi-connection semantics.

Current experiments provide weekly manual-record observations and descriptive comparisons. Configured, separately authorized AI selects constrained actions. Do not claim a complete long-term body model, health causal inference, automatic cross-platform identity merging or full demo parity. Full first-release scope and personal-subject AI eligibility remain unresolved; switches must not conceal functionality.

Read the linked release gates and submission draft. Finish client reviews, obtain verified membership/account/domain/provider/privacy details, then perform platform and device acceptance. The old service's HTTP 200 does not prove V3 deployment. Formal submission receipts are required for completion.
