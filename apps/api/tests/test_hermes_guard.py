import asyncio
import importlib.util
import json
import logging
from enum import Enum
from pathlib import Path
from types import SimpleNamespace


def load_guard_module():
    path = Path("integrations/hermes/bodyos_guard/__init__.py")
    spec = importlib.util.spec_from_file_location("bodyos_guard", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_llm_middleware_removes_every_original_message() -> None:
    guard = load_guard_module()
    request = {
        "model": "bodyos-codex",
        "messages": [
            {"role": "system", "content": "identity ou_secret"},
            {"role": "user", "content": "我的血糖是 10.2"},
        ],
    }
    sanitized = {
        "schema_version": "bodyos-model.v1",
        "intent": "glucose_coaching",
        "channel": "dm",
        "features": {"glucose": {"mean_mg_dl": 101.2}},
        "knowledge": [],
        "constraints": ["not_medical_diagnosis"],
    }

    result = guard.rewrite_llm_request(request, sanitized)

    rendered = str(result["request"])
    assert "ou_secret" not in rendered
    assert "10.2" not in rendered
    assert "101.2" in rendered


def test_guard_failure_rewrites_to_a_closed_generic_request() -> None:
    guard = load_guard_module()
    request = {"messages": [{"role": "user", "content": "private raw text"}]}

    result = guard.rewrite_llm_request(request, None)

    rendered = str(result["request"])
    assert "private raw text" not in rendered
    assert "BODYOS_CONTEXT_UNAVAILABLE" in rendered


def test_middleware_reads_only_the_sanitized_session_sidecar(tmp_path, monkeypatch) -> None:
    guard = load_guard_module()
    monkeypatch.setenv("BODYOS_SANITIZED_CACHE_DIR", str(tmp_path))
    session_id = "session-containing-private-identity"
    envelope = {
        "schema_version": "bodyos-model.v1",
        "intent": "sleep_coaching",
        "channel": "dm",
        "features": {"status": "insufficient_data"},
        "knowledge": [],
        "constraints": ["not_medical_diagnosis"],
    }
    path = guard.cache_path(session_id)
    path.write_text(json.dumps({"mode": "model", "envelope": envelope}))

    result = guard._middleware(
        request={"messages": [{"role": "user", "content": "raw sleep message"}]},
        session_id=session_id,
    )

    assert session_id not in path.name
    rendered = str(result["request"])
    assert "raw sleep message" not in rendered
    assert "sleep_coaching" in rendered


def test_group_middleware_uses_only_the_prechecked_public_answer_sidecar(
    tmp_path, monkeypatch
) -> None:
    guard = load_guard_module()
    monkeypatch.setenv("BODYOS_SANITIZED_CACHE_DIR", str(tmp_path))
    session_id = "group-session"
    envelope = {
        "schema_version": "bodyos-group-answer.v1",
        "channel": "group",
        "reply": "餐后舒适散步有助于肌肉利用葡萄糖。",
    }
    guard.cache_path(session_id).write_text(
        json.dumps({"mode": "group_public", "envelope": envelope}),
        encoding="utf-8",
    )

    result = guard._middleware(
        request={"messages": [{"role": "user", "content": "我的血糖是 10.2"}]},
        session_id=session_id,
    )

    rendered = str(result["request"])
    assert "我的血糖是 10.2" not in rendered
    assert "bodyos-group-answer.v1" in rendered
    assert envelope["reply"] in rendered


class RecordingContext:
    def __init__(self) -> None:
        self.hooks: dict[str, object] = {}
        self.middleware: list[tuple[str, object]] = []

    def register_hook(self, name: str, callback) -> None:
        self.hooks[name] = callback

    def register_middleware(self, name: str, callback) -> None:
        self.middleware.append((name, callback))


class RecordingAdapter:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, chat_id: str, content: str, reply_to: str | None = None, metadata=None):
        self.sent.append(
            {"chat_id": chat_id, "content": content, "reply_to": reply_to, "metadata": metadata}
        )
        return SimpleNamespace(success=True)


class SequencedAdapter(RecordingAdapter):
    def __init__(self, outcomes: list[bool]) -> None:
        super().__init__()
        self._outcomes = iter(outcomes)

    async def send(self, chat_id: str, content: str, reply_to: str | None = None, metadata=None):
        await super().send(chat_id, content, reply_to=reply_to, metadata=metadata)
        return SimpleNamespace(success=next(self._outcomes))


class FakePlatform(Enum):
    FEISHU = "feishu"
    SLACK = "slack"


def feishu_event(*, text: str, chat_type: str = "group"):
    platform = FakePlatform.FEISHU
    sender_id = SimpleNamespace(
        open_id="ou_private_owner",
        user_id="tenant_user_id_that_must_not_be_used",
        union_id="on_union_identity",
    )
    source = SimpleNamespace(
        platform=platform,
        chat_id="oc_allowed_group" if chat_type == "group" else "ou_private_owner",
        chat_type=chat_type,
        user_id="tenant_user_id_that_must_not_be_used",
    )
    raw_message = SimpleNamespace(
        event=SimpleNamespace(sender=SimpleNamespace(sender_id=sender_id))
    )
    return SimpleNamespace(
        text=text,
        source=source,
        raw_message=raw_message,
        message_id="om_message_1",
    )


def test_register_uses_supported_pre_gateway_dispatch_hook_instead_of_dead_middleware() -> None:
    guard = load_guard_module()
    context = RecordingContext()

    guard.register(context)

    assert set(context.hooks) == {"pre_gateway_dispatch"}
    assert context.middleware == []


def test_register_suppresses_upstream_info_logs_that_include_message_text_or_chat_ids() -> None:
    guard = load_guard_module()
    context = RecordingContext()
    logger_names = ("hermes_plugins.platforms__feishu.adapter", "gateway.run")
    previous = {name: logging.getLogger(name).level for name in logger_names}
    try:
        for name in logger_names:
            logging.getLogger(name).setLevel(logging.NOTSET)

        guard.register(context)

        assert all(logging.getLogger(name).level >= logging.WARNING for name in logger_names)
    finally:
        for name, level in previous.items():
            logging.getLogger(name).setLevel(level)


def test_pre_dispatch_sends_only_the_checked_group_reply_and_skips_native_agent(
    monkeypatch,
) -> None:
    guard = load_guard_module()
    adapter = RecordingAdapter()
    event = feishu_event(text="晚饭后散步为什么有助于控糖？")
    raw_text = event.text

    async def scenario() -> None:
        async def fake_reply(payload: dict) -> dict:
            assert payload == {
                "provider": "feishu",
                "subject": "ou_private_owner",
                "channel": "group",
                "text": raw_text,
            }
            return {
                "mode": "group_public",
                "reply": "饭后轻松活动有助于肌肉利用葡萄糖。",
                "route": "codex",
            }

        monkeypatch.setattr(guard, "_request_bodyos_reply", fake_reply)
        gateway = SimpleNamespace(adapters={event.source.platform: adapter})

        decision = guard._pre_gateway_dispatch(event=event, gateway=gateway, session_store=None)

        assert decision == {"action": "skip", "reason": "bodyos_sanitized_dispatch"}
        await guard._drain_pending_tasks()

    asyncio.run(scenario())
    assert adapter.sent == [
        {
            "chat_id": "oc_allowed_group",
            "content": "饭后轻松活动有助于肌肉利用葡萄糖。",
            "reply_to": "om_message_1",
            "metadata": None,
        }
    ]
    assert raw_text not in str(adapter.sent)


def test_pre_dispatch_retries_a_rejected_reactive_reply_as_a_top_level_message(
    monkeypatch,
) -> None:
    guard = load_guard_module()
    adapter = SequencedAdapter([False, True])
    event = feishu_event(text="训练计划中为什么可持续的小行动比短期冲刺更重要？")

    async def scenario() -> None:
        async def fake_reply(_payload: dict) -> dict:
            return {
                "mode": "group_public",
                "reply": "可持续的小行动有助于形成稳定训练习惯。",
                "route": "deterministic_public_knowledge",
            }

        monkeypatch.setattr(guard, "_request_bodyos_reply", fake_reply)
        monkeypatch.setattr(guard, "_DELIVERY_RETRY_DELAY_SECONDS", 0, raising=False)
        gateway = SimpleNamespace(adapters={event.source.platform: adapter})

        assert guard._pre_gateway_dispatch(event=event, gateway=gateway)["action"] == "skip"
        await guard._drain_pending_tasks()

    asyncio.run(scenario())
    assert [attempt["reply_to"] for attempt in adapter.sent] == ["om_message_1", None]


def test_pre_dispatch_logs_only_a_content_free_status_after_delivery_exhaustion(
    monkeypatch, caplog
) -> None:
    guard = load_guard_module()
    adapter = SequencedAdapter([False, False])
    raw_text = "训练计划中为什么可持续的小行动比短期冲刺更重要？"
    event = feishu_event(text=raw_text)

    async def scenario() -> None:
        async def fake_reply(_payload: dict) -> dict:
            return {
                "mode": "group_public",
                "reply": "可持续的小行动有助于形成稳定训练习惯。",
                "route": "deterministic_public_knowledge",
            }

        monkeypatch.setattr(guard, "_request_bodyos_reply", fake_reply)
        monkeypatch.setattr(guard, "_DELIVERY_RETRY_DELAY_SECONDS", 0, raising=False)
        gateway = SimpleNamespace(adapters={event.source.platform: adapter})

        with caplog.at_level(logging.WARNING):
            assert guard._pre_gateway_dispatch(event=event, gateway=gateway)["action"] == "skip"
            await guard._drain_pending_tasks()

    asyncio.run(scenario())
    assert len(adapter.sent) == 2
    assert "reactive delivery failed" in caplog.text
    assert raw_text not in caplog.text
    assert event.source.chat_id not in caplog.text
    assert event.message_id not in caplog.text


def test_forum_chat_is_always_routed_as_public_group(monkeypatch) -> None:
    guard = load_guard_module()
    adapter = RecordingAdapter()
    event = feishu_event(text="睡眠通常怎样影响恢复？", chat_type="forum")
    event.source.chat_id = "oc_forum_group"

    async def scenario() -> None:
        async def fake_reply(payload: dict) -> dict:
            assert payload["channel"] == "group"
            return {
                "mode": "group_public",
                "reply": "睡眠有助于恢复。",
                "route": "codex",
            }

        monkeypatch.setattr(guard, "_request_bodyos_reply", fake_reply)
        gateway = SimpleNamespace(adapters={event.source.platform: adapter})
        assert guard._pre_gateway_dispatch(event=event, gateway=gateway)["action"] == "skip"
        await guard._drain_pending_tasks()

    asyncio.run(scenario())
    assert adapter.sent[0]["chat_id"] == "oc_forum_group"


def test_unknown_feishu_chat_type_fails_closed_without_calling_api(monkeypatch) -> None:
    guard = load_guard_module()
    adapter = RecordingAdapter()
    event = feishu_event(text="private context", chat_type="mystery")

    async def scenario() -> None:
        async def forbidden_call(_payload: dict) -> dict:
            raise AssertionError("unknown chat type must not reach BodyOS API")

        monkeypatch.setattr(guard, "_request_bodyos_reply", forbidden_call)
        gateway = SimpleNamespace(adapters={event.source.platform: adapter})
        assert guard._pre_gateway_dispatch(event=event, gateway=gateway)["action"] == "skip"
        await guard._drain_pending_tasks()

    asyncio.run(scenario())
    assert "暂时不可用" in adapter.sent[0]["content"]


def test_pre_dispatch_routes_private_messages_to_the_same_sanitized_reply_boundary(
    monkeypatch,
) -> None:
    guard = load_guard_module()
    adapter = RecordingAdapter()
    event = feishu_event(text="晚饭吃米饭后犯困，和血糖有关吗？", chat_type="dm")

    async def scenario() -> None:
        async def fake_reply(payload: dict) -> dict:
            assert payload["channel"] == "dm"
            assert payload["subject"] == "ou_private_owner"
            assert "tenant_user_id" not in payload["subject"]
            return {
                "mode": "private",
                "reply": "可以先记录餐食构成和身体感受。",
                "route": "codex",
            }

        monkeypatch.setattr(guard, "_request_bodyos_reply", fake_reply)
        gateway = SimpleNamespace(adapters={event.source.platform: adapter})
        decision = guard._pre_gateway_dispatch(event=event, gateway=gateway, session_store=None)
        assert decision["action"] == "skip"
        await guard._drain_pending_tasks()

    asyncio.run(scenario())
    assert adapter.sent[0]["content"] == "可以先记录餐食构成和身体感受。"


def test_pre_dispatch_fails_closed_without_exposing_provider_details(monkeypatch) -> None:
    guard = load_guard_module()
    adapter = RecordingAdapter()
    event = feishu_event(text="为什么睡眠会影响恢复？")

    async def scenario() -> None:
        async def unavailable(_payload: dict) -> dict:
            raise OSError("provider secret detail")

        monkeypatch.setattr(guard, "_request_bodyos_reply", unavailable)
        gateway = SimpleNamespace(adapters={event.source.platform: adapter})
        decision = guard._pre_gateway_dispatch(event=event, gateway=gateway, session_store=None)
        assert decision["action"] == "skip"
        await guard._drain_pending_tasks()

    asyncio.run(scenario())
    rendered = str(adapter.sent)
    assert "provider secret detail" not in rendered
    assert "暂时不可用" in rendered


def test_checked_reply_rejects_provider_and_credential_details() -> None:
    guard = load_guard_module()

    for reply in (
        "HTTP 403 provider request_id=req-secret",
        "The model provider failed after retries.",
        "Authorization: Bearer sk-private-token",
        "Provider authentication failed. Check configured credentials.",
        "Rate limited after 3 retries.",
        "Non-retryable error: upstream rejected request.",
        "The upstream service returned 429.",
        "模型认证失败，请检查配置。",
        "API call failed with status 401.",
        "Error code: 403 from backend.",
        "Quota exceeded; please try later.",
        "Authentication failed for the model service.",
        "Invalid credentials for upstream.",
        "模型服务鉴权失败，请检查密钥。",
        "401 Unauthorized",
        "403 Forbidden",
        "503 Service Unavailable",
        "Bad Gateway",
        "Gateway timeout",
        "Connection reset by peer",
    ):
        try:
            guard._checked_reply({"mode": "private", "reply": reply, "route": "codex"}, "dm")
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe provider detail was accepted: {reply}")


def test_pre_dispatch_does_not_intercept_non_feishu_events() -> None:
    guard = load_guard_module()
    event = feishu_event(text="hello")
    event.source.platform = FakePlatform.SLACK

    assert (
        guard._pre_gateway_dispatch(
            event=event,
            gateway=SimpleNamespace(adapters={}),
            session_store=None,
        )
        is None
    )
