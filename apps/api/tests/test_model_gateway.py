import subprocess

import bodyos_api.model_gateway as model_gateway_module
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
