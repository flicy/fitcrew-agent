import importlib.util
import json
from pathlib import Path


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
