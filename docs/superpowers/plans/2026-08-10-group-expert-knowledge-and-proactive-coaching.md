# BodyOS Group Expert Knowledge and Proactive Coaching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让飞书群聊使用三本已审核的共享专家书籍回答通用健康问题，并在上海时区每天早晚和每周三主动发起安全、幂等、低打扰的群聊互动。 / Enable Feishu groups to answer general health questions with three reviewed shared expert books and proactively send safe, idempotent, low-interruption morning, evening, and weekly interactions in the Shanghai timezone.

**Architecture:** 现有加密知识表继续作为唯一知识存储，新增“私人来源发布为共享来源”和共享/私人组合检索。群聊公共信封升级到 `bodyos-public.v2` 并只携带脱敏问题与最多三个共享知识片段；个人数据仍只进入私聊。维护 Worker 增加基于数据库 Outbox 的调度和飞书发送器，固定早晚模板不调用模型，每周知识互动经过同一公共答案安全门禁。 / The existing encrypted knowledge tables remain the single knowledge store, with explicit private-to-shared publication and combined shared/private retrieval. Group envelopes move to `bodyos-public.v2` and carry only a sanitized question plus at most three shared passages; personal data remains DM-only. The maintenance worker gains a database Outbox scheduler and Feishu dispatcher; fixed morning/evening templates do not call a model, while weekly expert interactions use the same public-answer safety gate.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, httpx, pytest, Docker Compose, Feishu OpenAPI, Codex CLI primary harness, Hermes CLI fallback.

---

## 中文实施步骤

### Task 1：发布共享专家知识并提供组合检索

**Files:**
- Modify: `apps/api/bodyos_api/knowledge.py`
- Create: `scripts/publish_shared_books.py`
- Create: `infra/tencent/publish-shared-books.sh`
- Test: `apps/api/tests/test_knowledge.py`
- Test: `apps/api/tests/test_operations.py`

- [ ] **Step 1：先写共享发布与隔离的失败测试**

```python
def test_private_source_can_be_published_for_shared_retrieval(session, field_cipher):
    source = seed_private_book(session, field_cipher, title="控糖革命")
    published = KnowledgeService(session, field_cipher).publish_private_source(
        source.id,
        reviewer_role="owner_editor",
        rationale="approved for internal expert summaries",
        applicability="general lifestyle education",
    )
    assert published.visibility == "public"
    assert published.fitcrew_user_id is None
    assert published.review_status == "published"
    assert KnowledgeService(session, field_cipher).search_public("餐后葡萄糖")[0].source_id == source.id

def test_user_search_combines_published_and_owned_private_sources(session, field_cipher):
    hits = service.search_for_user(OWNER, "睡眠恢复", limit=3)
    assert {hit.title for hit in hits} == {"睡眠优化完全指南：科学与实践", "Owner 私人笔记"}
```

- [ ] **Step 2：运行测试并确认因方法不存在而失败**

Run: `uv run pytest apps/api/tests/test_knowledge.py -q`

Expected: FAIL，提示 `publish_private_source` 或 `search_for_user` 不存在。 / FAIL because the publication or combined-search method is missing.

- [ ] **Step 3：实现事务化发布与组合检索**

```python
def publish_private_source(
    self,
    source_id: str,
    *,
    reviewer_role: str,
    rationale: str,
    applicability: str,
) -> KnowledgeSource:
    source = self._session.get(KnowledgeSource, source_id)
    if source is None or source.visibility != "private" or source.review_status != "approved_private":
        raise ValueError("approved private knowledge source not found")
    source.fitcrew_user_id = None
    source.visibility = "public"
    source.review_status = "published"
    self._session.add(KnowledgeReview(
        source_id=source.id,
        reviewer_role=reviewer_role,
        decision="approved",
        rationale=rationale,
        applicability=applicability,
    ))
    self._session.commit()
    return source

def search_for_user(self, fitcrew_user_id: str, query: str, *, limit: int = 5) -> list[SearchHit]:
    private = self.search_private(fitcrew_user_id, query, limit=limit)
    shared = self.search_public(query, limit=limit)
    return sorted(private + shared, key=lambda hit: (-hit.score, hit.title, hit.page_number))[:limit]
```

- [ ] **Step 4：实现无正文输出的生产发布命令**

`scripts/publish_shared_books.py` 必须只选择最新 `approved_private` 版本，标题限定为三本确认书籍，调用 `publish_private_source`，最后只输出计数：

```python
BOOK_TITLES = (
    "控糖革命",
    "百岁人生行动手册",
    "睡眠优化完全指南：科学与实践",
)

print(json.dumps({"published": published_count, "already_published": existing_count}))
```

`infra/tencent/publish-shared-books.sh` 只运行 API 容器中的命令，不打印数据库、身份或知识内容：

```sh
docker compose --env-file runtime/.env.runtime -f compose.yaml \
  exec -T api python scripts/publish_shared_books.py
```

- [ ] **Step 5：验证并提交**

Run: `uv run pytest apps/api/tests/test_knowledge.py apps/api/tests/test_operations.py -q && uv run ruff check apps/api/bodyos_api/knowledge.py scripts/publish_shared_books.py`

Expected: PASS，且发布脚本具备执行权限、无书籍正文输出。 / PASS with an executable no-content publication command.

```bash
git add apps/api/bodyos_api/knowledge.py scripts/publish_shared_books.py infra/tencent/publish-shared-books.sh apps/api/tests/test_knowledge.py apps/api/tests/test_operations.py
git commit -m "feat: publish shared expert knowledge"
```

### Task 2：让群聊公共信封检索共享书籍

**Files:**
- Modify: `apps/api/bodyos_api/bodyos.py`
- Modify: `apps/api/bodyos_api/model_gateway.py`
- Modify: `apps/api/bodyos_api/bodyos_routes.py`
- Test: `apps/api/tests/test_bodyos.py`
- Test: `apps/api/tests/test_bodyos_routes.py`
- Test: `apps/api/tests/test_model_gateway.py`

- [ ] **Step 1：先写 `bodyos-public.v2` 失败测试**

```python
def test_general_group_question_uses_only_published_knowledge(session, field_cipher):
    seed_published_book(session, field_cipher)
    service.handle(USER_ID, ConversationRequest(channel="group", text="饭后散步为什么有助于控糖？"))
    envelope = gateway.envelopes[0]
    assert envelope["schema_version"] == "bodyos-public.v2"
    assert envelope["knowledge"][0] == {
        "title": "控糖革命",
        "page": 12,
        "excerpt": "进餐顺序可能影响餐后葡萄糖曲线。",
    }
    assert "features" not in envelope
    assert USER_ID not in str(envelope)
```

- [ ] **Step 2：运行并确认旧信封没有 `knowledge` 而失败**

Run: `uv run pytest apps/api/tests/test_bodyos.py apps/api/tests/test_bodyos_routes.py apps/api/tests/test_model_gateway.py -q`

Expected: FAIL，当前 schema 为 `bodyos-public.v1` 且没有共享知识。 / FAIL because the current v1 envelope has no shared knowledge.

- [ ] **Step 3：让公共信封由服务实例构造并加入检索结果**

```python
def build_public_group_envelope(self, text: str) -> dict | None:
    safe_text = sanitize_public_group_question(text)
    if safe_text is None:
        return None
    hits = KnowledgeService(self._session, self._cipher).search_public(safe_text, limit=3)
    return {
        "schema_version": "bodyos-public.v2",
        "intent": classify_intent(safe_text),
        "channel": "group",
        "public_context": {"sanitized_text": safe_text},
        "knowledge": [{"title": h.title, "page": h.page_number, "excerpt": h.excerpt} for h in hits],
        "constraints": ["general_knowledge_only", "published_knowledge_only", "no_personal_health_data", "not_medical_diagnosis", "cite_pages"],
    }
```

私聊 `_knowledge` 改用 `search_for_user`，让共享知识和对应用户私人知识共同参与检索。

- [ ] **Step 4：严格校验新信封并要求带页码引用**

`validate_model_envelope` 仅接受 `title/page/excerpt`，每次最多三项，拒绝 `source_id`、所有权、身份、原始值和任意额外字段。`render_model_prompt` 明确要求概括、短答并保留书名页码，不允许长段复述。

- [ ] **Step 5：运行测试并提交**

Run: `uv run pytest apps/api/tests/test_bodyos.py apps/api/tests/test_bodyos_routes.py apps/api/tests/test_model_gateway.py -q && uv run ruff check apps/api/bodyos_api`

Expected: PASS，群聊信封只含通用问题与发布知识。 / PASS with only a general question and published knowledge in group envelopes.

```bash
git add apps/api/bodyos_api/bodyos.py apps/api/bodyos_api/bodyos_routes.py apps/api/bodyos_api/model_gateway.py apps/api/tests/test_bodyos.py apps/api/tests/test_bodyos_routes.py apps/api/tests/test_model_gateway.py
git commit -m "feat: ground group answers in shared books"
```

### Task 3：放宽通用科普并增加安全兜底

**Files:**
- Modify: `apps/api/bodyos_api/dlp.py`
- Modify: `apps/api/bodyos_api/bodyos.py`
- Test: `apps/api/tests/test_dlp.py`
- Test: `apps/api/tests/test_bodyos.py`
- Test: `apps/api/tests/test_bodyos_routes.py`

- [ ] **Step 1：先写允许与拒绝边界的失败测试**

```python
@pytest.mark.parametrize("question", [
    "饭后犯困可能和餐食结构有什么关系？",
    "为什么饭后散步有助于控糖？",
    "一般来说，睡眠不足为什么会影响食欲？",
])
def test_public_gate_allows_general_lifestyle_mechanisms(question):
    assert sanitize_public_group_question(question) == question

@pytest.mark.parametrize("question", [
    "我今天饭后犯困，结合我的血糖分析一下",
    "张三饭后犯困是不是生病了？",
    "胰岛素应该打多少剂量？",
])
def test_public_gate_still_rejects_personal_diagnostic_or_medication_requests(question):
    assert sanitize_public_group_question(question) is None

def test_model_disclaimer_does_not_discard_an_otherwise_general_answer():
    answer = "一般而言，饭后轻松活动有助于肌肉利用葡萄糖；这不是个体诊断。"
    assert assert_public_group_answer(answer) == answer
```

- [ ] **Step 2：运行并确认现有 `_MEDICAL_RE` 导致预期失败**

Run: `uv run pytest apps/api/tests/test_dlp.py apps/api/tests/test_bodyos.py apps/api/tests/test_bodyos_routes.py -q`

Expected: FAIL，通用答案被宽泛医疗词拒绝，失败时仍返回私聊 token。 / FAIL because broad medical terms reject general education and failure still redirects to DM.

- [ ] **Step 3：分离高风险请求与安全免责声明**

用 `_DIAGNOSIS_OR_MEDICATION_RE` 只拦截要求诊断、治疗、处方、药物或剂量的请求；输出门禁拒绝确定性个体诊断和用药指令，但允许“不是诊断”“一般而言”等通用免责声明。身份、数值、个人化和基础设施错误规则保持不变。

- [ ] **Step 4：新增经过门禁的确定性公共兜底**

```python
PUBLIC_FALLBACKS = {
    "glucose_coaching": "一般而言，均衡餐食、合理进食顺序和饭后舒适活动有助于管理餐后波动。个体情况请在 BodyOS 私聊中讨论。",
    "sleep_coaching": "规律作息、稳定起床时间和合适的白天活动通常有助于睡眠与恢复。个体情况请在 BodyOS 私聊中讨论。",
    "activity_coaching": "训练量、恢复时间和睡眠需要共同安排；从能稳定坚持的小行动开始。个体情况请在 BodyOS 私聊中讨论。",
    "general_health_coaching": "先选择一个今天能够稳定完成的小行动，再观察长期变化。个体情况请在 BodyOS 私聊中讨论。",
}
```

模型失败或模型输出被拒绝时，对匹配 intent 的固定回复再次执行 `assert_public_group_answer`，并返回 `route="deterministic_public"`。只有输入本身不适合群聊时才返回私人教练 token。

- [ ] **Step 5：验证并提交**

Run: `uv run pytest apps/api/tests/test_dlp.py apps/api/tests/test_bodyos.py apps/api/tests/test_bodyos_routes.py -q && uv run ruff check apps/api/bodyos_api`

Expected: PASS，合法通用问题总能得到公共回答，私人/诊断/用药边界不变。 / PASS with reliable public answers and unchanged private/high-risk boundaries.

```bash
git add apps/api/bodyos_api/dlp.py apps/api/bodyos_api/bodyos.py apps/api/tests/test_dlp.py apps/api/tests/test_bodyos.py apps/api/tests/test_bodyos_routes.py
git commit -m "fix: keep safe general answers in groups"
```

### Task 4：建立幂等群聊调度与 Outbox 状态

**Files:**
- Modify: `apps/api/bodyos_api/models.py`
- Modify: `apps/api/bodyos_api/config.py`
- Create: `apps/api/bodyos_api/group_coach.py`
- Create: `apps/api/migrations/versions/0003_group_coach_outbox.py`
- Modify: `apps/api/tests/test_database_schema.py`
- Create: `apps/api/tests/test_group_coach.py`

- [ ] **Step 1：先写时区、安静时段和幂等失败测试**

```python
def test_scheduler_creates_each_due_shanghai_event_once(session):
    now = datetime(2026, 8, 12, 1, 0, tzinfo=UTC)  # 09:00 Asia/Shanghai
    first = GroupCoachScheduler(session, settings).enqueue_due(now)
    second = GroupCoachScheduler(session, settings).enqueue_due(now)
    assert first == 1
    assert second == 0
    assert session.scalar(select(OutboxEvent)).idempotency_key == "feishu-group:morning_action:2026-08-12"

def test_scheduler_does_not_send_inside_quiet_hours(session):
    assert GroupCoachScheduler(session, settings).enqueue_due(datetime(2026, 8, 11, 23, 0, tzinfo=SHANGHAI)) == 0
```

- [ ] **Step 2：运行并确认缺少模型字段和调度器而失败**

Run: `uv run pytest apps/api/tests/test_database_schema.py apps/api/tests/test_group_coach.py -q`

Expected: FAIL，因为 Outbox 没有幂等/计划/错误字段且调度器不存在。 / FAIL because the Outbox schema and scheduler are missing.

- [ ] **Step 3：扩展 Outbox，保持旧研究事件兼容**

```python
fitcrew_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.fitcrew_user_id"), index=True)
idempotency_key: Mapped[str | None] = mapped_column(String(160), unique=True)
scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
last_error_code: Mapped[str | None] = mapped_column(String(64))
```

Alembic 0003 对 `fitcrew_user_id` 改为 nullable，新增字段和唯一索引；fresh install 与从 0002 升级都必须通过。

- [ ] **Step 4：实现配置与到期事件生成**

配置默认值：

```python
proactive_group_enabled: bool = False
group_timezone: str = "Asia/Shanghai"
group_morning_time: str = "09:00"
group_evening_time: str = "20:30"
group_weekly_weekday: int = 2
group_weekly_time: str = "12:15"
group_quiet_start: str = "22:00"
group_quiet_end: str = "08:00"
```

`GroupCoachScheduler.enqueue_due(now)` 仅在启用、白名单群存在且到达分钟窗口时创建 `morning_action`、`evening_checkin` 或 `weekly_expert` 事件。Payload 只含 `template_id` 或 `topic_id`。

- [ ] **Step 5：验证并提交**

Run: `uv run pytest apps/api/tests/test_database_schema.py apps/api/tests/test_group_coach.py -q && uv run ruff check apps/api/bodyos_api/group_coach.py apps/api/bodyos_api/models.py apps/api/bodyos_api/config.py`

Expected: PASS，重复调度只保留一条 Outbox。 / PASS with exactly one Outbox event per schedule key.

```bash
git add apps/api/bodyos_api/models.py apps/api/bodyos_api/config.py apps/api/bodyos_api/group_coach.py apps/api/migrations/versions/0003_group_coach_outbox.py apps/api/tests/test_database_schema.py apps/api/tests/test_group_coach.py
git commit -m "feat: schedule proactive group coaching"
```

### Task 5：实现受控飞书发送与有界重试

**Files:**
- Modify: `apps/api/bodyos_api/group_coach.py`
- Test: `apps/api/tests/test_group_coach.py`

- [ ] **Step 1：先写发送成功、失败和隐私失败测试**

```python
def test_dispatcher_sends_only_to_configured_group_and_marks_delivered(session, fake_transport):
    event = seed_pending_event(session, template_id="morning_action")
    result = FeishuGroupDispatcher(session, settings, transport=fake_transport).dispatch_due(now)
    assert result == {"delivered": 1, "retried": 0, "failed": 0}
    assert event.status == "delivered"
    assert fake_transport.receive_id == settings.feishu_allowed_group_id

def test_dispatcher_retries_three_times_without_storing_message_or_provider_detail(session):
    event = seed_pending_event(session)
    fake_transport.raise_code = "network_unavailable"
    dispatcher.dispatch_due(now)
    assert event.status == "pending"
    assert event.attempt_count == 1
    assert event.last_error_code == "network_unavailable"
    assert "message" not in event.payload_json
```

- [ ] **Step 2：运行并确认发送器不存在而失败**

Run: `uv run pytest apps/api/tests/test_group_coach.py -q`

Expected: FAIL because `FeishuGroupDispatcher` is missing.

- [ ] **Step 3：实现 Feishu OpenAPI 最小客户端**

发送器使用现有 `FEISHU_APP_ID`、`FEISHU_APP_SECRET` 和唯一 `FEISHU_ALLOWED_GROUP_ID`，先取得 tenant access token，再向 `im/v1/messages?receive_id_type=chat_id` 发送文本。构造函数接受注入 transport 以进行无网络测试。不得接受事件内传入任意群 ID。

- [ ] **Step 4：实现模板与每周知识消息**

```python
FIXED_TEMPLATES = {
    "morning_action": "早上好。今天你最想稳定完成的一个健康小行动是什么？可以从足够小的一步开始。",
    "evening_checkin": "今晚的小行动完成了吗？可以回复：已完成、需要搭子，或行动小一点。",
}
WEEKLY_TOPICS = (
    ("meal_order", "先吃蔬菜再吃主食有什么依据？"),
    ("small_actions", "为什么可持续的小行动比短期冲刺更重要？"),
    ("sleep_rhythm", "稳定起床时间为什么有助于睡眠恢复？"),
)
```

每周消息调用公共知识回答路径；成功答案必须经过 `assert_public_group_answer`。失败时保留事件重试；三次失败后发送不含引用的固定通用讨论问题并标记 delivered，避免泄露供应商错误。

- [ ] **Step 5：验证并提交**

Run: `uv run pytest apps/api/tests/test_group_coach.py -q && uv run ruff check apps/api/bodyos_api/group_coach.py`

Expected: PASS，测试传输中不出现身份、健康数据、书籍长文或任意群目标。 / PASS without identity, health data, long passages, or arbitrary destinations.

```bash
git add apps/api/bodyos_api/group_coach.py apps/api/tests/test_group_coach.py
git commit -m "feat: deliver proactive Feishu coaching safely"
```

### Task 6：把主动教练接入 Worker 和腾讯云运行时

**Files:**
- Modify: `apps/api/bodyos_api/jobs.py`
- Modify: `infra/tencent/compose.yaml`
- Modify: `infra/tencent/generate-runtime-env.py`
- Modify: `infra/tencent/env.example`
- Modify: `infra/tencent/deploy.sh`
- Modify: `infra/tencent/rollback.sh`
- Modify: `apps/api/tests/test_jobs.py`
- Modify: `apps/api/tests/test_operations.py`

- [ ] **Step 1：先写 Worker 和部署契约失败测试**

```python
def test_job_cycle_enqueues_and_dispatches_group_events(session, settings, fake_dispatcher):
    counts = run_worker_cycle(session, now=MORNING_UTC, settings=settings, dispatcher=fake_dispatcher)
    assert counts["group_events_enqueued"] == 1
    assert counts["group_events_delivered"] == 1

def test_tencent_worker_checks_group_outbox_every_minute():
    compose = (ROOT / "infra/tencent/compose.yaml").read_text()
    assert '"--interval-seconds", "60"' in compose
    assert "BODYOS_PROACTIVE_GROUP_ENABLED" in compose
```

- [ ] **Step 2：运行并确认当前 Worker 只做六小时维护而失败**

Run: `uv run pytest apps/api/tests/test_jobs.py apps/api/tests/test_operations.py -q`

Expected: FAIL because the worker has no scheduler/dispatcher integration.

- [ ] **Step 3：把短周期群聊工作和六小时维护解耦**

`run_worker_cycle` 每分钟运行调度和发送；只有距上次维护至少六小时才执行原有 retention/study `run_once`。控制台只输出计数和内容无关错误码，不输出消息正文、群 ID 或知识内容。

- [ ] **Step 4：配置腾讯云默认节奏与安全关闭**

生产 runtime 增加：

```text
BODYOS_PROACTIVE_GROUP_ENABLED=true
BODYOS_GROUP_TIMEZONE=Asia/Shanghai
BODYOS_GROUP_MORNING_TIME=09:00
BODYOS_GROUP_EVENING_TIME=20:30
BODYOS_GROUP_WEEKLY_WEEKDAY=2
BODYOS_GROUP_WEEKLY_TIME=12:15
BODYOS_GROUP_QUIET_START=22:00
BODYOS_GROUP_QUIET_END=08:00
```

若旧 runtime 缺少这些键，部署脚本以原子方式追加非秘密默认值；不得重新生成或覆盖现有凭据。部署和回滚继续验证 Worker running、严格 HTTPS 与五项服务门禁。

- [ ] **Step 5：验证并提交**

Run: `uv run pytest apps/api/tests/test_jobs.py apps/api/tests/test_operations.py -q && sh -n infra/tencent/*.sh && uv run ruff check apps/api/bodyos_api/jobs.py`

Expected: PASS，主动功能可配置关闭，旧凭据不被改写。 / PASS with a configurable fail-closed feature and untouched existing credentials.

```bash
git add apps/api/bodyos_api/jobs.py infra/tencent/compose.yaml infra/tencent/generate-runtime-env.py infra/tencent/env.example infra/tencent/deploy.sh infra/tencent/rollback.sh apps/api/tests/test_jobs.py apps/api/tests/test_operations.py
git commit -m "feat: run proactive coaching in production"
```

### Task 7：更新运行手册、发布共享书籍并做全量门禁

**Files:**
- Modify: `README.md`
- Modify: `docs/operations/deployment-and-rollback.md`
- Create: `docs/evidence/2026-08-10-group-expert-coaching-verification.md`

- [ ] **Step 1：更新中英双语产品边界与运维步骤**

文档必须说明：群聊共享专家知识不是公开 PDF；一般问题可引用三本书；个人数据仍只在私聊；主动节奏为 09:00、20:30、周三 12:15；提供暂停开关、发布脚本、Outbox 无内容检查、回滚和 canary 步骤。

- [ ] **Step 2：运行完整自动化验证**

```bash
uv run pytest -q
uv run ruff check .
uv run python scripts/check_bilingual_docs.py
swift test --package-path apps/ios-bridge/Core
python scripts/check_ios_generated_config.py
xcodegen generate --spec apps/ios-bridge/project.yml --project /tmp/FitCrewHealthBridge
xcodebuild -project /tmp/FitCrewHealthBridge/FitCrewHealthBridge.xcodeproj \
  -scheme FitCrewHealthBridge -sdk iphonesimulator \
  -destination 'platform=iOS Simulator,name=iPhone 16 Pro' \
  CODE_SIGNING_ALLOWED=NO build
git diff --check
```

Expected: 全部通过；生成的 `.xcodeproj` 不提交。 / All checks pass and the generated Xcode project remains untracked.

- [ ] **Step 3：记录内容无关证据并提交**

证据只记录测试数量、Boolean 门禁、版本和服务健康，不记录群 ID、成员、消息正文、知识摘录、健康数据或凭据。

```bash
git add README.md docs/operations/deployment-and-rollback.md docs/evidence/2026-08-10-group-expert-coaching-verification.md
git commit -m "docs: operate shared group coaching"
```

### Task 8：代码审查、PR、合并、部署与生产验收

**Files:**
- Review: all changes since `433c153c63551806cd2938be4bf08de439a38e66`
- No new source files unless review finds a concrete defect

- [ ] **Step 1：独立审查安全、规格与质量**

审查重点：群聊知识只能 `public + published`；无身份/健康数据进入群信封；Outbox 幂等；发送目标固定；无消息正文日志；迁移兼容；模型失败安全兜底；私人/诊断/用药问题不放宽。

- [ ] **Step 2：推送分支、创建 PR 并等待全部 CI**

```bash
git push -u origin codex/fix-group-public-fallback
gh pr create --base main --head codex/fix-group-public-fallback \
  --title "feat: add shared expert group coaching" \
  --body-file /tmp/fitcrew-group-coaching-pr.md
gh pr checks --watch
```

PR 正文必须中英双语，只包含安全摘要和验证结果，不包含身份、书籍内容或健康数据。

- [ ] **Step 3：合并绿灯 PR 并取得唯一 main SHA**

```bash
gh pr merge --merge --delete-branch
git fetch origin main
git rev-parse origin/main
```

- [ ] **Step 4：在腾讯云部署并发布三本共享书籍**

```bash
cd /opt/fitcrew-bodyos
git fetch origin main
EXPECTED_SHA=$(git rev-parse FETCH_HEAD)
git checkout --detach FETCH_HEAD
test "$(git rev-parse HEAD)" = "$EXPECTED_SHA"
./infra/tencent/deploy.sh
cd infra/tencent
./publish-shared-books.sh
```

不得使用 `curl -k`、绕过证书、重新生成凭据、输出书籍正文或健康数据。

- [ ] **Step 5：严格生产验收**

```bash
curl --fail --proto '=https' --tlsv1.2 https://124.156.218.104/healthz
docker compose --env-file runtime/.env.runtime -f compose.yaml ps
```

再执行内容安全 canary：一个群聊通用问题应返回 `group_public` 或 `deterministic_public`，私聊同步状态保持不变，调度 dry-run 只报告到期事件数量。真实主动消息从下一个计划时间开始；不得为测试提前向飞书发送额外消息。

## English execution mirror

1. Write red tests for publishing an approved private source into the shared `public + published` state and combining shared with user-owned private retrieval. Implement the transaction, no-content CLI, and Tencent wrapper; verify and commit.
2. Write red tests for `bodyos-public.v2` with at most three published page-cited passages and no user or health fields. Implement strict envelope validation, shared group retrieval, combined DM retrieval, prompt citations, and commit.
3. Write red tests proving general lifestyle mechanisms and cautious disclaimers are allowed while personal, third-party, numeric, diagnosis, and medication requests remain denied. Replace the broad medical-word rejection, add a checked deterministic public fallback, verify, and commit.
4. Write red tests for Shanghai-time scheduling, quiet hours, and idempotency. Add nullable group Outbox ownership, unique idempotency, schedule/retry/error fields, Alembic 0003, configuration defaults, scheduler, verify, and commit.
5. Write red tests for fixed-destination Feishu delivery, bounded retries, and content-free persistence. Add a minimal injected Feishu transport, reviewed morning/evening templates, rotating weekly public-knowledge topics, verify, and commit.
6. Write red tests for one-minute proactive cycles and six-hour maintenance separation. Wire the scheduler/dispatcher into the worker, append only non-secret runtime defaults, retain strict deployment/rollback gates, verify, and commit.
7. Update bilingual README and operations documentation, run all Python/Ruff/bilingual/Swift/iOS/diff gates, record content-free evidence, and commit.
8. Review the complete diff, push a bilingual PR, wait for all CI, merge only when green, deploy the exact main SHA, publish the three shared sources, verify strict HTTPS and services, and allow real proactive messages to begin only at the next scheduled time.
