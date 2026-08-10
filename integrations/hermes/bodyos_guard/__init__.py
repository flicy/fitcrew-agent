"""Hermes BodyOS boundary using the supported pre-gateway dispatch hook."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

_PENDING_TASKS: set[asyncio.Task] = set()
_UNAVAILABLE_REPLY = "BodyOS 暂时不可用，请稍后再试。"
_DELIVERY_RETRY_DELAY_SECONDS = 0.25
_LOGGER = logging.getLogger("bodyos_guard")
_FEISHU_OPEN_ID_RE = re.compile(r"ou_[A-Za-z0-9_-]{6,128}\Z")
_PROVIDER_DETAIL_RE = re.compile(
    r"(?i)(?:"
    r"\b(?:api|provider|upstream|backend|status|error|failed|failure|authorization|"
    r"authentication|credentials?|quota|retry|retries|rate[- ]?limit(?:ed|ing)?|http|"
    r"request[_ -]?id|bearer|unauthorized|forbidden|unavailable|gateway|timeout|"
    r"connection)\b|"
    r"(?<!\d)[45]\d{2}(?!\d)|"
    r"api[_ -]?key|too\s+many\s+requests|non[- ]?retryable|sk-[a-z0-9_-]{6,}|"
    r"模型(?:服务|提供商|供应商|认证|鉴权|调用)|鉴权|密钥|配额|上游服务|后端服务|"
    r"错误代码|状态码|调用失败|认证失败|认证错误|配置错误|请重试|限流)"
)


def rewrite_llm_request(request: dict, sanitized_envelope: dict | None) -> dict:
    rewritten = {key: value for key, value in request.items() if key not in {"messages", "input"}}
    if sanitized_envelope is None:
        content = (
            "BODYOS_CONTEXT_UNAVAILABLE: reply that private coaching is temporarily "
            "unavailable."
        )
    else:
        content = "BODYOS_SANITIZED_ENVELOPE=" + json.dumps(
            sanitized_envelope,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    rewritten["messages"] = [
        {
            "role": "system",
            "content": (
                "You are BodyOS. Use only the sanitized envelope. Never request or infer raw "
                "health data, identity, or other conversation history."
            ),
        },
        {"role": "user", "content": content},
    ]
    return {
        "request": rewritten,
        "plugin": "bodyos_guard",
        "decision": "rewrite",
    }


def cache_path(session_id: str) -> Path:
    directory = Path(os.environ.get("BODYOS_SANITIZED_CACHE_DIR", "/tmp/bodyos-sanitized"))
    digest = hashlib.sha256(session_id.encode()).hexdigest()
    return directory / f"{digest}.json"


def _load_envelope(session_id: str) -> dict | None:
    if not session_id:
        return None
    try:
        record = json.loads(cache_path(session_id).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    envelope = record.get("envelope") if isinstance(record, dict) else None
    return envelope if isinstance(envelope, dict) else None


def _middleware(**kwargs):
    request = kwargs.get("request") or {}
    envelope = _load_envelope(str(kwargs.get("session_id") or ""))
    return rewrite_llm_request(request, envelope)


def _request_bodyos_reply_sync(payload: dict) -> dict:
    api_base = os.environ.get("BODYOS_API_BASE", "").rstrip("/")
    token = os.environ.get("BODYOS_INTERNAL_TOKEN", "")
    if not api_base or not token:
        raise RuntimeError("BodyOS routing is unavailable")
    request = urllib.request.Request(
        f"{api_base}/v1/bodyos/reply",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "X-BodyOS-Token": token},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=380) as response:
        body = response.read(16_385)
    if len(body) > 16_384:
        raise ValueError("BodyOS reply is too large")
    decoded = json.loads(body)
    if not isinstance(decoded, dict):
        raise ValueError("BodyOS reply is invalid")
    return decoded


async def _request_bodyos_reply(payload: dict) -> dict:
    return await asyncio.to_thread(_request_bodyos_reply_sync, payload)


async def _send_reactive_reply(adapter, chat_id: str, reply: str, reply_to: str | None) -> bool:
    for attempt_reply_to in (reply_to, None):
        try:
            result = await adapter.send(chat_id, reply, reply_to=attempt_reply_to)
        except Exception:
            result = None
        if getattr(result, "success", False) is True:
            return True
        if attempt_reply_to is not None and _DELIVERY_RETRY_DELAY_SECONDS > 0:
            await asyncio.sleep(_DELIVERY_RETRY_DELAY_SECONDS)
    _LOGGER.warning("BodyOS reactive delivery failed after bounded fallback")
    return False


def _checked_reply(payload: dict, channel: str) -> str:
    if not isinstance(payload, dict) or set(payload) != {"mode", "reply", "route"}:
        raise ValueError("BodyOS reply shape is invalid")
    mode = payload.get("mode")
    allowed_modes = {"group_public", "deterministic"} if channel == "group" else {"private"}
    if mode not in allowed_modes:
        raise ValueError("BodyOS reply mode is invalid")
    reply = payload.get("reply")
    route = payload.get("route")
    maximum = 800 if channel == "group" else 8_000
    if (
        not isinstance(reply, str)
        or reply != reply.strip()
        or not reply
        or len(reply) > maximum
        or any(ord(character) < 32 and character not in {"\n", "\t"} for character in reply)
        or not isinstance(route, str)
        or not route
        or len(route) > 64
        or _PROVIDER_DETAIL_RE.search(reply)
    ):
        raise ValueError("BodyOS reply content is invalid")
    return reply


def _field(value, name: str):
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def _enum_text(value) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").strip().casefold()


def _feishu_open_id(event) -> str | None:
    raw_message = getattr(event, "raw_message", None)
    event_body = _field(raw_message, "event") or raw_message
    sender = _field(event_body, "sender")
    sender_id = _field(sender, "sender_id")
    open_id = _field(sender_id, "open_id")
    if isinstance(open_id, str) and _FEISHU_OPEN_ID_RE.fullmatch(open_id):
        return open_id
    return None


async def _dispatch_feishu_event(event, gateway) -> None:
    source = getattr(event, "source", None)
    if source is None:
        return
    chat_type = _enum_text(getattr(source, "chat_type", ""))
    if chat_type == "dm":
        channel = "dm"
    elif chat_type in {"group", "forum"}:
        channel = "group"
    else:
        channel = None

    subject = _feishu_open_id(event)
    if channel is None or subject is None:
        reply = _UNAVAILABLE_REPLY
    else:
        payload = {
            "provider": "feishu",
            "subject": subject,
            "channel": channel,
            "text": str(getattr(event, "text", "") or ""),
        }
        try:
            reply = _checked_reply(await _request_bodyos_reply(payload), channel)
        except (OSError, RuntimeError, TypeError, ValueError, urllib.error.URLError):
            reply = _UNAVAILABLE_REPLY

    platform = getattr(source, "platform", None)
    adapters = getattr(gateway, "adapters", {})
    adapter = adapters.get(platform) if isinstance(adapters, dict) else None
    chat_id = str(getattr(source, "chat_id", "") or "")
    if adapter is None or not chat_id:
        return
    await _send_reactive_reply(
        adapter,
        chat_id,
        reply,
        str(getattr(event, "message_id", "") or "") or None,
    )


def _consume_task(task: asyncio.Task) -> None:
    _PENDING_TASKS.discard(task)
    with contextlib.suppress(asyncio.CancelledError, Exception):
        task.exception()


async def _drain_pending_tasks() -> None:
    pending = tuple(_PENDING_TASKS)
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)


def _pre_gateway_dispatch(*, event, gateway, session_store=None, **_kwargs):
    source = getattr(event, "source", None)
    platform = _enum_text(getattr(source, "platform", None))
    if platform != "feishu":
        return None
    try:
        task = asyncio.get_running_loop().create_task(_dispatch_feishu_event(event, gateway))
    except RuntimeError:
        return {"action": "skip", "reason": "bodyos_sanitized_dispatch"}
    _PENDING_TASKS.add(task)
    task.add_done_callback(_consume_task)
    return {"action": "skip", "reason": "bodyos_sanitized_dispatch"}


def register(ctx) -> None:
    logging.getLogger("hermes_plugins.platforms__feishu.adapter").setLevel(logging.WARNING)
    logging.getLogger("plugins.platforms.feishu.adapter").setLevel(logging.WARNING)
    logging.getLogger("gateway.run").setLevel(logging.WARNING)
    ctx.register_hook("pre_gateway_dispatch", _pre_gateway_dispatch)
