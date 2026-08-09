# V2 Conversation Boundaries Implementation Plan / V2 对话边界实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement safe general group Q&A and useful sanitized DM request context without weakening FitCrew's user isolation or raw-data boundary. / 实现安全的群聊通用问答与有用的私聊安全上下文，同时不削弱用户隔离和原始数据边界。

**Architecture:** Add explicit public-question and private-context sanitizers at the API boundary. Public group questions use a dedicated model envelope with no identity, personal features, or private knowledge; generated answers are validated once and passed through Hermes/watcher as a checked answer envelope. DMs add only a bounded redacted text summary to the existing per-user aggregate envelope. / 在 API 边界增加明确的群聊公共问题与私聊上下文净化器。群聊使用不含身份、个人特征和私人知识的专用模型信封，生成答案经检查后由 Hermes/watcher 传递；私聊只在现有用户聚合信封中增加受限的脱敏文本摘要。

**Tech Stack:** Python 3.11, FastAPI, Pydantic, pytest, Hermes middleware, Feishu watcher. / Python 3.11、FastAPI、Pydantic、pytest、Hermes 中间件、飞书 watcher。

---

## 中文实施步骤

### Task 1：群聊通用问题红测

**Files:**
- Modify: `apps/api/tests/test_bodyos.py`
- Modify: `apps/api/tests/test_bodyos_routes.py`
- Modify: `apps/api/tests/test_model_gateway.py`

- [ ] 新增服务层测试：`晚饭后散步为什么有助于控糖？` 生成 `bodyos-public.v1` 模型信封并返回模型答案；信封不含用户 ID、features、knowledge 或原始健康数值。
- [ ] 新增 API 测试：通用群聊问题返回 `bodyos-group-answer.v1`；`我的餐后血糖是 10.2` 继续返回私聊 token 且不调用模型。
- [ ] 新增模型验证测试：公共信封可通过；包含 `fitcrew_user_id`、features、private knowledge、手机号或数值的公共信封被拒绝。
- [ ] 运行聚焦测试，确认新增测试在实现前失败：

```bash
uv run pytest apps/api/tests/test_bodyos.py apps/api/tests/test_bodyos_routes.py apps/api/tests/test_model_gateway.py -q
```

### Task 2：实现群聊公共问答

**Files:**
- Modify: `apps/api/bodyos_api/bodyos.py`
- Modify: `apps/api/bodyos_api/bodyos_routes.py`
- Modify: `apps/api/bodyos_api/model_gateway.py`
- Modify: `apps/api/bodyos_api/dlp.py`

- [ ] 在 `dlp.py` 实现 `sanitize_public_group_question(text) -> str | None` 和 `assert_public_group_answer(text) -> str`，保守拒绝第一人称、输入数值、标识符、联系方式、疾病治疗与用药请求。
- [ ] 在 `BodyOSService` 中让固定 token 保持确定性；只有通过门禁的消息构建 `bodyos-public.v1` 并调用模型。
- [ ] 扩展模型验证与 prompt：公共群聊只允许 `schema_version/channel/intent/public_context/constraints`，明确禁止个人化、诊断、请求数据和使用私人知识。
- [ ] API 对模型答案执行输出门禁并封装为 `bodyos-group-answer.v1`；代理只返回经验证的答案。
- [ ] 运行 Task 1 聚焦测试，确认转绿。

### Task 3：私聊安全上下文红测与实现

**Files:**
- Modify: `apps/api/tests/test_bodyos.py`
- Modify: `apps/api/tests/test_bodyos_routes.py`
- Modify: `apps/api/tests/test_model_gateway.py`
- Modify: `apps/api/bodyos_api/bodyos.py`
- Modify: `apps/api/bodyos_api/model_gateway.py`
- Modify: `apps/api/bodyos_api/dlp.py`

- [ ] 先写红测：输入“我叫 Chris，晚饭吃了米饭，餐后 10.2，有点困，电话 13800138000”，信封保留“晚饭吃了米饭”和“有点困”，但不含姓名、电话、`10.2` 或完整原文。
- [ ] 写红测：验证器拒绝手工注入邮箱、URL、open_id、UUID 或未脱敏数字的 `request_context`。
- [ ] 实现 `sanitize_private_request_context`：按设计移除敏感模式、所有数字与显式姓名自述，压缩空白并限制长度。
- [ ] 把安全摘要加入非同步状态 DM 的 `request_context`；同步状态信封保持原结构与确定性回复。
- [ ] 运行聚焦测试并确认转绿。

### Task 4：Hermes 与 watcher 兼容性

**Files:**
- Modify: `apps/api/tests/test_hermes_guard.py`
- Modify: `apps/api/tests/test_operations.py`
- Modify: `scripts/feishu_group_watcher.py`
- Modify: `integrations/hermes/bodyos_guard/__init__.py` only if the existing generic envelope rewrite cannot pass the new checked answer unchanged

- [ ] 先写红测：Guard 只能从 sidecar 读取 `bodyos-group-answer.v1`，原消息不能进入重写请求。
- [ ] 先写红测：watcher 接受 API 的 `group_public` 已检查回复，拒绝超长、空白或结构错误的回复。
- [ ] 最小修改 watcher，使固定 token 和已检查公共答案都能发送；不打印或持久化消息正文、用户 ID、群 ID 或答案内容。
- [ ] 运行 Hermes 与操作聚焦测试并确认转绿。

### Task 5：规则、全量验证与 PR

**Files:**
- Modify: `agent/HERMES.md`
- Modify: `agent/SOUL.md`
- Modify: `README.md` only to keep the developer boundary aligned after the code exists

- [ ] 更新双语运行规则：群聊允许安全通用问题信封，但禁止个人健康、私聊、私人知识和医疗判断；私聊只使用脱敏请求摘要。
- [ ] 运行完整门禁：

```bash
uv run pytest -q
uv run ruff check apps/api scripts integrations infra/tencent
uv run python scripts/check_bilingual_docs.py
(cd apps/ios-bridge/Core && swift test)
git diff --check
```

- [ ] 提交、推送并创建面向 `main` 的独立 PR；三项 CI 全绿后才合并。

### Task 6：生产发布与最小验收

- [ ] SSH 可达后，在 `/opt/fitcrew-bodyos` 精确检出新合并 SHA，运行 `./infra/tencent/deploy.sh`。
- [ ] 从 `infra/tencent` 运行 `./reconcile-feishu-allowlist.sh`，只重建 verified + non-revoked + active/invited 飞书身份并重启 gateway。
- [ ] 严格 HTTPS 验证 `/healthz`，不使用 `curl -k`。
- [ ] 群聊验收：通用控糖问题得到通用答案；带个人血糖数值的问题只引导私聊。
- [ ] 私聊验收：食物与身体感知被理解；同步状态只返回状态、时间和类别覆盖，不返回原始数值。

## English execution summary

1. Add red tests at the service, API, model-envelope, Hermes, and watcher seams.
2. Implement a conservative public group-question sanitizer and a dedicated model envelope with no identity, health features, or private knowledge.
3. Validate the generated group answer once and pass only that checked answer through Hermes and the watcher.
4. Add a bounded sanitized DM request context that preserves food and perception while removing identity, contact details, IDs, URLs, and numbers.
5. Update bilingual runtime rules, run all Python/Swift/policy/document gates, merge through an independent PR, then deploy and validate over strict HTTPS when SSH is available.
