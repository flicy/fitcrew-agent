# FitCrew / BodyOS V2.0

## 中文

FitCrew 是产品与社区品牌，BodyOS 是用户在飞书中接触的私人生活方式教练，Moticlaw 是 Agent 的配置与管理入口。V2.0 提供一条双用户 Alpha 路径：在用户选择授权时，可通过可选的 iOS HealthKit Bridge 接入 Apple Health、Apple Watch、Apple 健身，以及写入 Apple Health 的鱼跃 Anytime 5 Pro 数据；不使用 Apple 设备或不授权健康数据的用户仍可使用服务的非健康数据能力。

飞书账号是主账号，内部用不可变的 `fitcrew_user_id` 绑定身份。一次性配对把每位用户、设备和每个健康类别的同意分别绑定；跨用户上传会被拒绝，设备更换会轮换关联，授权可撤回。Apple 设备和健康授权均为可选项。原始健康数据以 AES-GCM 加密保存，模型只接收确定性聚合特征、意图和带页码的私人知识摘录，不接收姓名、飞书 ID、聊天原文或原始健康序列。

群聊只允许五种固定低敏行为结果：完成今日行动、需要搭子、愿意分享、把行动变小、转到私聊获取个性化建议。群聊不会展示原始健康数据；个性化健康信息只在对应用户的私聊出现，BodyOS 不做医疗诊断。

### V2.0 现状与验证

- 代码基线为 PR #2 合并提交 [`3438e02770a04478913dfeeead029d23a55167f5`](https://github.com/flicy/fitcrew-agent/commit/3438e02770a04478913dfeeead029d23a55167f5)。
- Python / policy、Swift Core 和 iOS Simulator CI 已通过。
- 生产 TLS 已验证；公开健康检查端点 <https://124.156.218.104/healthz> 当前观测返回 `v2.0.0-alpha.1`。
- TestFlight 提交流程已准备，但外部分发尚未完成；受邀测试者的真机验收也尚未完成。
- 现实世界的 16 天研究尚未完成；本项目未对任何健康结果作出主张。

这些证据说明工程路径、隔离边界和部署连接性已被验证，不构成任何个人健康结果、医疗诊断或远程 TestFlight 安装可用性的承诺。

### 组件

- `apps/api/`：FastAPI、授权、加密摄取、日特征、知识/需求池与 BodyOS 模型边界。
- `apps/ios-bridge/`：HealthKit 最小读取授权、增量同步及第 16 天全量对账。
- `integrations/hermes/`：Moticlaw/Hermes 通道的预模型 Guard；Codex CLI 为主路由，Hermes OpenAI Codex OAuth 为备用。
- `infra/tencent/`：现有腾讯云东京 Lighthouse 的零新增现金部署、IP HTTPS、加密备份与 SHA 回滚。
- `scripts/import_private_books.py`：在 Git 外把本人提供的 PDF 加密导入私人知识库。

### 本地验证

```bash
uv sync --extra dev
uv run pytest -q
uv run ruff check apps/api scripts infra/tencent
(cd apps/ios-bridge/Core && swift test)
```

生产部署和物理设备步骤见 `docs/operations/deployment-and-rollback.md` 与 `docs/experiments/owner-cgm-16-day-runbook.md`。三本私人 PDF、健康导出、OAuth 凭据、飞书密钥、运行环境文件与真实证据均不得进入 Git。

产品介绍页保持在 <https://flicy.github.io/cola-pages/fitcrew/>。本仓库所有变更通过 PR 进入 `main`；未经 Owner 明确批准不合并或发布版本。

## English

FitCrew is the product and community brand, BodyOS is the private lifestyle coach users meet in Feishu, and Moticlaw is the Agent configuration and management surface. V2.0 provides a two-user Alpha path: with a person's permission, an optional iOS HealthKit Bridge can connect Apple Health, Apple Watch, Apple Fitness, and Yuwell Anytime 5 Pro data written into Apple Health. People without an Apple device or health authorization can still use the service's non-health-data capabilities.

Feishu is the primary account while an immutable internal `fitcrew_user_id` binds identities. One-time pairing separately binds each person, device, and health-category consent; cross-user uploads are rejected, device replacement rotates the association, and consent can be withdrawn. Apple devices and health authorization are optional. Raw health fields are encrypted with AES-GCM. A model receives only deterministic aggregates, intent, and page-cited private knowledge excerpts—never names, Feishu IDs, raw chat, or raw health series.

Group chat permits only five fixed low-sensitivity outcomes: today's action completed, need a buddy, willing to share, make the action smaller, or move to DM for personalized guidance. Groups never expose raw health data; personalized health information stays in the corresponding user's DM, and BodyOS does not diagnose.

### V2.0 status and verification

- The code baseline is PR #2 merge commit [`3438e02770a04478913dfeeead029d23a55167f5`](https://github.com/flicy/fitcrew-agent/commit/3438e02770a04478913dfeeead029d23a55167f5).
- Python / policy, Swift Core, and iOS Simulator CI are green.
- Production TLS is verified. The public health endpoint, <https://124.156.218.104/healthz>, currently reports `v2.0.0-alpha.1`.
- The TestFlight submission flow is prepared, but external distribution is not complete, nor is an invited tester's physical-device acceptance.
- The real-world 16-day study is not complete, and this project makes no claim about any health outcome.

This evidence verifies the engineering path, isolation boundaries, and deployment connectivity. It is not a promise of an individual health outcome, medical diagnosis, or available remote TestFlight installation.

### Components

- `apps/api/`: FastAPI, consent, encrypted ingestion, daily features, knowledge/demand pools, and the BodyOS model boundary.
- `apps/ios-bridge/`: minimum HealthKit read authorization, incremental sync, and day-16 reconciliation.
- `integrations/hermes/`: the pre-model guard for Moticlaw/Hermes channels; Codex CLI is primary and Hermes OpenAI Codex OAuth is fallback.
- `infra/tencent/`: zero-new-cash deployment, IP HTTPS, encrypted backups, and SHA rollback on the existing Tokyo Lighthouse.
- `scripts/import_private_books.py`: encrypted private-book import outside Git.

### Local verification

```bash
uv sync --extra dev
uv run pytest -q
uv run ruff check apps/api scripts infra/tencent
(cd apps/ios-bridge/Core && swift test)
```

See `docs/operations/deployment-and-rollback.md` and `docs/experiments/owner-cgm-16-day-runbook.md` for production and physical-device steps. Private PDFs, health exports, OAuth credentials, Feishu secrets, runtime environments, and real private evidence must never enter Git.

The product page remains at <https://flicy.github.io/cola-pages/fitcrew/>. All repository changes reach `main` through a PR; no merge or release occurs without explicit owner approval.
