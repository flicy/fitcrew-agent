# Architecture Baseline

## 中文

### 以现有系统为基础

V3 必须扩展 V2 架构。

`apps/api` 用于 V3 API、领域模型、实验状态、个人模型、旅程状态以及经过授权的派生特征。不得绕过现有的认证和隐私中间件。

`apps/ios-bridge` 用于 Apple Health、Watch、HealthKit 和增量同步。V3 应通过现有的可信接口使用已同步的数据。

`integrations/hermes` 用于飞书通道、私聊身份、群聊隐私和模型路由。V3 的个人建议属于用户的私有上下文。

`infra/tencent` 继续沿用当前的生产部署模式。

### 建议的 V3 命名空间

建议使用 `/api/v3/today`、`/api/v3/journey`、`/api/v3/experiments`、`/api/v3/body-model` 和 `/api/v3/log`。这些名称仅为提议；实现前须对照当前 API 约定确认。

## English

## Existing system is the base

V3 must extend the V2 architecture.

### apps/api

Use for:

- V3 API
- domain model
- experiment state
- personal model
- journey state
- authorized derived features

Do not bypass existing auth and privacy middleware.

### apps/ios-bridge

Use for:

- Apple Health
- Watch
- HealthKit
- incremental sync

V3 should consume synced data through existing trusted interfaces.

### integrations/hermes

Use for:

- Feishu channel
- DM identity
- group privacy
- model routing

V3 personal recommendations belong to the private user context.

### infra/tencent

Continue current production pattern.

## Suggested V3 namespaces

```text
/api/v3/today
/api/v3/journey
/api/v3/experiments
/api/v3/body-model
/api/v3/log
```

These are proposed names. Confirm against current API conventions before implementing.
