# Architecture Baseline

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
