import importlib.util
from pathlib import Path

import pytest


def load_watcher():
    path = Path("scripts/feishu_group_watcher.py")
    spec = importlib.util.spec_from_file_location("feishu_group_watcher", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_watcher_accepts_a_structurally_checked_public_group_answer() -> None:
    watcher = load_watcher()
    reply = "餐后舒适散步有助于肌肉利用葡萄糖。"

    assert watcher.checked_group_reply(
        {
            "mode": "group_public",
            "reply": reply,
            "envelope": {
                "schema_version": "bodyos-group-answer.v1",
                "channel": "group",
                "reply": reply,
            },
        }
    ) == reply


@pytest.mark.parametrize(
    "payload",
    [
        {"mode": "group_public", "reply": "", "envelope": {}},
        {
            "mode": "group_public",
            "reply": "安全回答",
            "envelope": {
                "schema_version": "bodyos-group-answer.v1",
                "channel": "group",
                "reply": "不同回答",
            },
        },
        {
            "mode": "group_public",
            "reply": "x" * 801,
            "envelope": {
                "schema_version": "bodyos-group-answer.v1",
                "channel": "group",
                "reply": "x" * 801,
            },
        },
        {
            "mode": "group_public",
            "reply": "联系 ou_private123",
            "envelope": {
                "schema_version": "bodyos-group-answer.v1",
                "channel": "group",
                "reply": "联系 ou_private123",
            },
        },
    ],
)
def test_watcher_rejects_malformed_or_sensitive_public_answers(payload: dict) -> None:
    assert load_watcher().checked_group_reply(payload) is None


def test_watcher_keeps_accepting_only_canonical_deterministic_replies() -> None:
    watcher = load_watcher()

    assert watcher.checked_group_reply(
        {
            "mode": "deterministic",
            "reply": "今天完成了一个健康小行动。",
            "envelope": {
                "schema_version": "bodyos-group.v1",
                "channel": "group",
                "behavior_token": "completed",
            },
        }
    ) == "今天完成了一个健康小行动。"
    assert watcher.checked_group_reply(
        {"mode": "deterministic", "reply": "任意输出", "envelope": {}}
    ) is None
