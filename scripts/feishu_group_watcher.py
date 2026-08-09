#!/usr/bin/env python3
"""Reply to new Feishu group mentions through the deterministic BodyOS boundary.

The script never prints or persists message bodies, sender ids, or chat ids. It records only
hashed message ids for idempotency and emits aggregate operational counts.
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROFILE_DIR = Path(os.environ.get("FITCREW_PROFILE_DIR", SCRIPT_DIR.parent))
GROUPS_DIR = PROFILE_DIR / "memories" / "groups"
STATE_FILE = SCRIPT_DIR / ".feishu_watcher_state.json"
BOT_NAME = os.environ.get("FITCREW_BOT_NAME", "BodyOS")
LARK_CLI = os.environ.get("FITCREW_LARK_CLI", "lark-cli")
BODYOS_API_BASE = os.environ.get("BODYOS_API_BASE", "").rstrip("/")
BODYOS_INTERNAL_TOKEN = os.environ.get("BODYOS_INTERNAL_TOKEN", "")

SAFE_GROUP_REPLIES = {
    "今天完成了一个健康小行动。",
    "今天需要一个搭子陪我完成小行动。",
    "今天愿意分享一个健康小行动。",
    "今天选择把行动再变小一点。",
    "个性化健康建议请私聊 BodyOS。",
}
SAFE_GROUP_TOKENS = {
    "completed": "今天完成了一个健康小行动。",
    "need_buddy": "今天需要一个搭子陪我完成小行动。",
    "willing_to_share": "今天愿意分享一个健康小行动。",
    "smaller_action": "今天选择把行动再变小一点。",
    "private_coaching": "个性化健康建议请私聊 BodyOS。",
    "contact_bodyos": "请私聊 BodyOS 并发送“加入 BodyOS”，获取加入流程。",
}
_PUBLIC_IDENTIFIER_RE = re.compile(
    r"(?i)(?:\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b|"
    r"\b(?:https?://|www\.)\S+|"
    r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)|"
    r"\b(?:ou|oc|on|om|cli|msg)_[a-z0-9_-]{6,}\b|"
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b)"
)


def checked_group_reply(payload: dict) -> str | None:
    """Accept only fixed tokens or an API-checked public-answer envelope."""
    if not isinstance(payload, dict):
        return None
    reply = payload.get("reply")
    envelope = payload.get("envelope")
    if not isinstance(reply, str) or not isinstance(envelope, dict):
        return None
    if payload.get("mode") == "deterministic":
        token = envelope.get("behavior_token")
        expected_envelope = {
            "schema_version": "bodyos-group.v1",
            "channel": "group",
            "behavior_token": token,
        }
        if envelope != expected_envelope or SAFE_GROUP_TOKENS.get(token) != reply:
            return None
        return reply if reply in SAFE_GROUP_REPLIES or token == "contact_bodyos" else None
    if payload.get("mode") != "group_public":
        return None
    if set(payload) != {"mode", "reply", "envelope"}:
        return None
    if envelope != {
        "schema_version": "bodyos-group-answer.v1",
        "channel": "group",
        "reply": reply,
    }:
        return None
    normalized = reply.strip()
    if (
        normalized != reply
        or not normalized
        or len(normalized) > 800
        or _PUBLIC_IDENTIFIER_RE.search(normalized)
        or any(ord(character) < 32 for character in normalized)
    ):
        return None
    return normalized


def load_groups() -> list[tuple[str, str]]:
    groups = []
    for path in sorted(glob.glob(str(GROUPS_DIR / "oc_*.md"))):
        match = re.match(r"^(oc_[0-9a-fA-F]+)_(.+)\.md$", Path(path).name)
        if match:
            groups.append((match.group(1), match.group(2)))
    return groups


def run_lark(args: list[str]) -> dict | None:
    try:
        result = subprocess.run(
            [LARK_CLI, *args], capture_output=True, text=True, timeout=30, check=False
        )
        payload = json.loads(result.stdout)
        return payload if result.returncode == 0 and payload.get("ok") else None
    except (json.JSONDecodeError, ValueError, subprocess.TimeoutExpired, OSError):
        return None


def load_state() -> set[str]:
    try:
        payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return set(payload.get("processed_message_hashes", []))
    except (OSError, ValueError, TypeError):
        return set()


def save_state(processed: set[str]) -> None:
    SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    record = {"processed_message_hashes": sorted(processed)[-500:]}
    descriptor, temporary = tempfile.mkstemp(prefix="fitcrew-state-", dir=SCRIPT_DIR)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(record, handle, sort_keys=True)
        os.replace(temporary, STATE_FILE)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def message_hash(message_id: str) -> str:
    return hashlib.sha256(message_id.encode()).hexdigest()


def is_bot_mention(message: dict) -> bool:
    mentions = message.get("mentions", [])
    if any(mention.get("name") == BOT_NAME for mention in mentions):
        return True
    return f"@{BOT_NAME}" in str(message.get("content", ""))


def sender_subject(message: dict) -> str:
    sender = message.get("sender") or {}
    sender_id = sender.get("sender_id") or {}
    return str(sender.get("id") or sender_id.get("open_id") or "")


def bodyos_group_reply(subject: str, text: str) -> str | None:
    if not BODYOS_API_BASE or not BODYOS_INTERNAL_TOKEN or not subject:
        return None
    request = urllib.request.Request(
        f"{BODYOS_API_BASE}/v1/bodyos/envelope",
        data=json.dumps(
            {"provider": "feishu", "subject": subject, "channel": "group", "text": text},
            ensure_ascii=False,
        ).encode(),
        headers={
            "Content-Type": "application/json",
            "X-BodyOS-Token": BODYOS_INTERNAL_TOKEN,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read())
    except (OSError, ValueError, TypeError, urllib.error.URLError):
        return None
    return checked_group_reply(payload)


def reply_as_bot(message_id: str, reply: str) -> bool:
    key = f"bodyos-{message_hash(message_id)[:24]}"
    result = run_lark(
        [
            "im",
            "+messages-reply",
            "--message-id",
            message_id,
            "--text",
            reply,
            "--as",
            "bot",
            "--idempotency-key",
            key,
        ]
    )
    return result is not None


def main() -> None:
    if os.environ.get("BODYOS_SYNCHRONOUS_DISPATCH") == "1":
        print(json.dumps({"scanned": 0, "replied": 0, "failed": 0}))
        return
    processed = load_state()
    scanned = replied = failed = 0
    for chat_id, _chat_name in load_groups():
        result = run_lark(
            [
                "im",
                "+chat-messages-list",
                "--chat-id",
                chat_id,
                "--as",
                "bot",
                "--page-size",
                "20",
                "--order",
                "desc",
                "--no-reactions",
            ]
        )
        if not result:
            failed += 1
            continue
        messages = result.get("data", {}).get("messages", [])
        for message in reversed(messages):
            if message.get("msg_type") == "system":
                continue
            sender = message.get("sender") or {}
            if sender.get("sender_type") == "app" or not is_bot_mention(message):
                continue
            message_id = str(message.get("message_id") or "")
            digest = message_hash(message_id) if message_id else ""
            if not digest or digest in processed:
                continue
            scanned += 1
            reply = bodyos_group_reply(sender_subject(message), str(message.get("content", "")))
            if reply and reply_as_bot(message_id, reply):
                processed.add(digest)
                replied += 1
            else:
                failed += 1
    save_state(processed)
    print(json.dumps({"scanned": scanned, "replied": replied, "failed": failed}))


if __name__ == "__main__":
    main()
