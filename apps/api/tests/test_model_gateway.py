import json
import subprocess
from io import BytesIO
from types import SimpleNamespace
from urllib.error import HTTPError

import bodyos_api.model_gateway as model_gateway_module
import bodyos_api.runtime as runtime_module
import pytest
from bodyos_api.model_gateway import (
    HarnessFailure,
    HarnessResult,
    ModelEnvelopeRejected,
    RoutedModelGateway,
)


class FakeHarness:
    def __init__(self, results: list[HarnessResult | Exception]):
        self.results = results
        self.prompts: list[str] = []

    def run(self, prompt: str) -> HarnessResult:
        self.prompts.append(prompt)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def envelope() -> dict:
    return {
        "schema_version": "bodyos-model.v1",
        "intent": "glucose_coaching",
        "channel": "dm",
        "features": {
            "date": "2026-08-01",
            "glucose": {"mean_mg_dl": 101.2, "coefficient_of_variation": 0.12},
            "data_quality": {"glucose_completeness": 0.92},
        },
        "knowledge": [
            {"title": "控糖革命", "page": 42, "excerpt": "先吃蔬菜和蛋白质。"}
        ],
        "constraints": ["not_medical_diagnosis", "cite_pages"],
    }


def public_group_envelope() -> dict:
    return {
        "schema_version": "bodyos-public.v2",
        "intent": "glucose_coaching",
        "channel": "group",
        "public_context": {"sanitized_text": "晚饭后散步为什么有助于控糖？"},
        "knowledge": [
            {"title": "控糖革命", "page": 12, "excerpt": "餐后舒适活动有助于控糖。"}
        ],
        "constraints": [
            "general_knowledge_only",
            "published_knowledge_only",
            "no_personal_health_data",
            "not_medical_diagnosis",
            "cite_pages",
        ],
    }


def test_primary_codex_harness_is_used_without_fallback() -> None:
    primary = FakeHarness([HarnessResult(text="建议从进食顺序开始。", route="codex")])
    fallback = FakeHarness([HarnessResult(text="unused", route="hermes")])

    result = RoutedModelGateway(primary, fallback, primary_attempts=2).respond(envelope())

    assert result.route == "codex"
    assert len(primary.prompts) == 1
    assert fallback.prompts == []


def test_hermes_cli_treats_http_error_text_as_failure_even_on_zero_exit(monkeypatch) -> None:
    monkeypatch.setattr(
        model_gateway_module.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout='HTTP 400: {"detail":"unsupported"}', stderr=""
        ),
    )

    with pytest.raises(HarnessFailure, match="hermes harness failed"):
        model_gateway_module.HermesCLIHarness().run("safe prompt")


def test_primary_retries_then_uses_hermes_harness() -> None:
    primary = FakeHarness([HarnessFailure("busy"), HarnessFailure("still busy")])
    fallback = FakeHarness([HarnessResult(text="备用回答", route="hermes")])

    result = RoutedModelGateway(primary, fallback, primary_attempts=2).respond(envelope())

    assert result.route == "hermes"
    assert len(primary.prompts) == 2
    assert len(fallback.prompts) == 1


def test_double_failure_closes_without_fabricated_answer() -> None:
    primary = FakeHarness([HarnessFailure("down")])
    fallback = FakeHarness([HarnessFailure("down")])

    with pytest.raises(HarnessFailure, match="all model harnesses failed"):
        RoutedModelGateway(primary, fallback, primary_attempts=1).respond(envelope())


def test_raw_or_identifying_fields_are_rejected_before_any_model_call() -> None:
    primary = FakeHarness([HarnessResult(text="must not run", route="codex")])
    fallback = FakeHarness([HarnessResult(text="must not run", route="hermes")])
    unsafe = envelope() | {"open_id": "ou_secret", "raw_samples": [100, 110]}

    with pytest.raises(ModelEnvelopeRejected):
        RoutedModelGateway(primary, fallback).respond(unsafe)

    assert primary.prompts == []
    assert fallback.prompts == []


def test_public_group_envelope_cannot_use_any_model_harness() -> None:
    primary = FakeHarness([HarnessResult(text="must not run", route="codex")])
    fallback = FakeHarness([HarnessResult(text="unused", route="hermes")])

    with pytest.raises(ModelEnvelopeRejected, match="unsupported model envelope"):
        RoutedModelGateway(primary, fallback).respond(public_group_envelope())

    assert primary.prompts == []
    assert fallback.prompts == []


def test_public_group_envelope_rejects_unbounded_or_identifying_knowledge() -> None:
    primary = FakeHarness([HarnessResult(text="must not run", route="codex")])
    fallback = FakeHarness([HarnessResult(text="must not run", route="hermes")])
    unsafe = public_group_envelope() | {
        "knowledge": [
            {
                "title": "控糖革命",
                "page": 12,
                "excerpt": "联系 ou_private123",
                "source_id": "private-source",
            }
        ]
    }

    with pytest.raises(ModelEnvelopeRejected):
        RoutedModelGateway(primary, fallback).respond(unsafe)

    assert primary.prompts == []
    assert fallback.prompts == []


@pytest.mark.parametrize(
    "unsafe_context",
    [
        "我的血糖是 10.2",
        "电话 13800138000",
        "联系 ou_private123",
        "用户 11111111-1111-4111-8111-111111111111",
    ],
)
def test_public_group_envelope_rejects_personal_or_identifying_context(
    unsafe_context: str,
) -> None:
    primary = FakeHarness([HarnessResult(text="must not run", route="codex")])
    fallback = FakeHarness([HarnessResult(text="must not run", route="hermes")])
    unsafe = public_group_envelope() | {
        "public_context": {"sanitized_text": unsafe_context}
    }

    with pytest.raises(ModelEnvelopeRejected):
        RoutedModelGateway(primary, fallback).respond(unsafe)

    assert primary.prompts == []
    assert fallback.prompts == []


def test_private_request_context_rejects_manually_injected_identifiers() -> None:
    primary = FakeHarness([HarnessResult(text="must not run", route="codex")])
    fallback = FakeHarness([HarnessResult(text="must not run", route="hermes")])
    unsafe = envelope() | {
        "request_context": {"sanitized_text": "晚饭后联系 me@example.com"}
    }

    with pytest.raises(ModelEnvelopeRejected):
        RoutedModelGateway(primary, fallback).respond(unsafe)

    assert primary.prompts == []
    assert fallback.prompts == []


def test_cloudbase_harness_posts_only_the_rendered_private_prompt(monkeypatch) -> None:
    requests = []

    class Response:
        def __enter__(self):
            return BytesIO(b'{"choices":[{"message":{"content":"{\\"choice\\":\\"gentle\\"}"}}]}')

        def __exit__(self, *_):
            return False

    def fake_urlopen(request, *, timeout):
        requests.append((request, timeout))
        return Response()

    monkeypatch.setattr(model_gateway_module, "urlopen", fake_urlopen)
    harness = model_gateway_module.CloudBaseAIHarness(
        env_id="fitcrew-1234", api_key="secret-key", model="hy3", timeout_seconds=8
    )

    result = RoutedModelGateway(harness, FakeHarness([])).respond(envelope())

    assert result == HarnessResult(text='{"choice":"gentle"}', route="cloudbase:hy3")
    request, timeout = requests[0]
    assert (
        request.full_url
        == "https://fitcrew-1234.api.tcloudbasegateway.com/v1/ai/cloudbase/chat/completions"
    )
    assert request.get_header("Authorization") == "Bearer secret-key"
    assert timeout == 8
    body = json.loads(request.data)
    assert body["model"] == "hy3"
    assert body["stream"] is False
    assert body["messages"][0]["role"] == "user"
    assert "BODYOS_ENVELOPE=" in body["messages"][0]["content"]
    assert "open_id" not in body["messages"][0]["content"]


@pytest.mark.parametrize("env_id", ["", "https://evil.example", "foo/bar", "foo.example"])
def test_cloudbase_harness_rejects_invalid_environment(env_id) -> None:
    with pytest.raises(ValueError):
        model_gateway_module.CloudBaseAIHarness(env_id=env_id, api_key="secret", model="hy3")


def test_cloudbase_harness_fails_closed_without_leaking_http_error(monkeypatch) -> None:
    def fail(*_args, **_kwargs):
        raise HTTPError("https://example", 401, "secret-key rejected", {}, None)

    monkeypatch.setattr(model_gateway_module, "urlopen", fail)
    harness = model_gateway_module.CloudBaseAIHarness(
        env_id="fitcrew-1234", api_key="secret-key", model="hy3"
    )
    with pytest.raises(HarnessFailure, match="cloudbase AI request failed") as failure:
        harness.run("safe prompt")
    assert "secret-key" not in str(failure.value)


def test_cloudbase_runtime_has_no_undisclosed_cli_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_module,
        "get_settings",
        lambda: SimpleNamespace(
            private_wechat_cloud_enabled=False,
            cloudbase_ai_env_id="fitcrew-1234",
            cloudbase_ai_api_key=SimpleNamespace(get_secret_value=lambda: "secret-key"),
            cloudbase_ai_model="hy3",
            model_timeout_seconds=8,
        ),
    )
    runtime_module.get_model_gateway.cache_clear()
    gateway = runtime_module.get_model_gateway()
    assert isinstance(gateway._primary, model_gateway_module.CloudBaseAIHarness)
    assert isinstance(gateway._fallback, model_gateway_module.UnavailableHarness)
    runtime_module.get_model_gateway.cache_clear()


def test_partial_cloudbase_runtime_does_not_use_cli_harnesses(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_module,
        "get_settings",
        lambda: SimpleNamespace(
            private_wechat_cloud_enabled=False,
            cloudbase_ai_env_id="fitcrew-1234",
            cloudbase_ai_api_key=SimpleNamespace(get_secret_value=lambda: ""),
            cloudbase_ai_model="hy3",
            model_timeout_seconds=8,
        ),
    )
    runtime_module.get_model_gateway.cache_clear()
    gateway = runtime_module.get_model_gateway()
    with pytest.raises(HarnessFailure):
        gateway.respond(envelope())
    runtime_module.get_model_gateway.cache_clear()


def test_private_cloud_runtime_without_ai_config_never_uses_cli_harnesses(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_module,
        "get_settings",
        lambda: SimpleNamespace(
            private_wechat_cloud_enabled=True,
            cloudbase_ai_env_id="",
            cloudbase_ai_api_key=SimpleNamespace(get_secret_value=lambda: ""),
            cloudbase_ai_model="",
            model_timeout_seconds=8,
        ),
    )
    runtime_module.get_model_gateway.cache_clear()
    gateway = runtime_module.get_model_gateway()
    with pytest.raises(HarnessFailure):
        gateway.respond(envelope())
    runtime_module.get_model_gateway.cache_clear()
