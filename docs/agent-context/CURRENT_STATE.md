# Current State

更新时间：2026-08-15

## 当前稳定版本认知

### V1

已存在群聊健康搭子能力。

### V2

当前工程基线。

已知能力：

- HealthKit Bridge
- Apple Health
- Apple Fitness / Watch
- Yuwell CGM through Apple Health
- encrypted ingestion
- idempotency
- consent-category binding
- daily glucose aggregation
- sleep aggregation
- activity aggregation
- recovery aggregation
- Feishu-primary identity
- private DM personalization
- group privacy isolation
- de-identified model envelope
- shared knowledge review
- Tencent deployment
- HTTPS / backup / rollback

## V3

当前为产品与开发规划阶段。

目标：

把 V2 数据能力升级为长期 Decision & Learning Layer。

当前 V3 主结构：

```text
Today
Journey
Experiments
Log
Profile
```

核心循环：

```text
90 Day Journey
→ Weekly Experiment
→ Today Mission
→ Right Now Action
→ Evaluate
→ Learn
```

## 当前最重要的工程判断

V3 不应从 UI Demo 开始成为独立代码路径。

应先：

1. 增加 V3 domain model
2. 增加 API
3. 复用 V2 identity / consent / health aggregation
4. 增加 experiment state
5. 增加 Personal Body Model
6. 再做 App UI
