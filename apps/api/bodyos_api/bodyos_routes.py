import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from bodyos_api.auth import require_internal, require_model_proxy
from bodyos_api.bodyos import (
    BodyOSService,
    build_public_group_envelope,
    classify_explicit_group_token,
)
from bodyos_api.config import Settings, get_settings
from bodyos_api.crypto import FieldCipher
from bodyos_api.db import get_session
from bodyos_api.dlp import SensitiveOutput, assert_public_group_answer
from bodyos_api.model_gateway import HarnessFailure, validate_model_envelope
from bodyos_api.models import IdentityBinding
from bodyos_api.policy import BehaviorToken
from bodyos_api.runtime import get_field_cipher, get_model_gateway

router = APIRouter(tags=["bodyos"])


class EnvelopeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["feishu"]
    subject: str = Field(min_length=3, max_length=200)
    channel: Literal["dm", "group"]
    text: str = Field(min_length=1, max_length=4_000)


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model: str = "bodyos-codex"
    messages: list[ChatMessage] = Field(min_length=1, max_length=50)
    stream: bool = False


def _identity_user(session: Session, request: EnvelopeRequest, settings: Settings) -> str:
    pepper = settings.identity_pepper.get_secret_value()
    if not pepper:
        raise HTTPException(status_code=503, detail="identity mapping unavailable")
    subject_hash = hmac.new(pepper.encode(), request.subject.encode(), hashlib.sha256).hexdigest()
    identity = session.scalar(
        select(IdentityBinding).where(
            IdentityBinding.provider == request.provider,
            IdentityBinding.subject_hash == subject_hash,
            IdentityBinding.revoked_at.is_(None),
        )
    )
    if identity is None:
        raise HTTPException(status_code=403, detail="identity is not bound")
    return identity.fitcrew_user_id


@router.post("/v1/bodyos/envelope")
def create_bodyos_envelope(
    request: EnvelopeRequest,
    _: Annotated[None, Depends(require_internal)],
    session: Annotated[Session, Depends(get_session)],
    cipher: Annotated[FieldCipher, Depends(get_field_cipher)],
    settings: Annotated[Settings, Depends(get_settings)],
    gateway: Annotated[Any, Depends(get_model_gateway)],
) -> dict:
    if request.channel == "group":
        token = classify_explicit_group_token(request.text)
        public_envelope = build_public_group_envelope(request.text)
        if token is None and public_envelope is not None:
            try:
                result = gateway.respond(public_envelope)
                reply = assert_public_group_answer(result.text)
            except (HarnessFailure, SensitiveOutput):
                token = BehaviorToken.PRIVATE_COACHING
            else:
                return {
                    "mode": "group_public",
                    "reply": reply,
                    "envelope": {
                        "schema_version": "bodyos-group-answer.v1",
                        "channel": "group",
                        "reply": reply,
                    },
                }
        if token is None:
            token = BehaviorToken.PRIVATE_COACHING
        return {
            "mode": "deterministic",
            "reply": token.message,
            "envelope": {
                "schema_version": "bodyos-group.v1",
                "channel": "group",
                "behavior_token": token.value,
            },
        }
    user_id = _identity_user(session, request, settings)
    envelope = BodyOSService(session, cipher, gateway).build_envelope(user_id, request.text)
    return {"mode": "model", "envelope": envelope}


def _extract_envelope(request: ChatCompletionRequest) -> dict:
    prefix = "BODYOS_SANITIZED_ENVELOPE="
    content = request.messages[-1].content
    if not content.startswith(prefix):
        raise HTTPException(status_code=403, detail="sanitized envelope required")
    try:
        envelope = json.loads(content[len(prefix) :])
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=403, detail="invalid sanitized envelope") from error
    if not isinstance(envelope, dict):
        raise HTTPException(status_code=403, detail="invalid sanitized envelope")
    return envelope


def _bodyos_reply(request: ChatCompletionRequest, gateway: Any) -> tuple[str, str]:
    envelope = _extract_envelope(request)
    if envelope.get("schema_version") == "bodyos-group-answer.v1":
        if (
            set(envelope) != {"schema_version", "channel", "reply"}
            or envelope.get("channel") != "group"
        ):
            raise HTTPException(status_code=403, detail="invalid public group answer")
        try:
            text = assert_public_group_answer(envelope.get("reply", ""))
        except SensitiveOutput as error:
            raise HTTPException(status_code=403, detail="invalid public group answer") from error
        route = "deterministic"
    elif envelope.get("schema_version") == "bodyos-group.v1":
        try:
            token = BehaviorToken(envelope.get("behavior_token"))
        except (TypeError, ValueError) as error:
            raise HTTPException(status_code=403, detail="invalid group token") from error
        if envelope != {
            "schema_version": "bodyos-group.v1",
            "channel": "group",
            "behavior_token": token.value,
        }:
            raise HTTPException(status_code=403, detail="invalid group token")
        text = token.message
        route = "deterministic"
    else:
        try:
            validate_model_envelope(envelope)
            if envelope.get("intent") == "sync_status":
                return _sync_status_reply(envelope), "deterministic"
            result = gateway.respond(envelope)
        except (HarnessFailure, ValueError) as error:
            raise HTTPException(status_code=503, detail="private coaching unavailable") from error
        text = result.text
        route = result.route
    return text, route


def _sync_status_reply(envelope: dict) -> str:
    features = envelope.get("features")
    if (
        envelope.get("knowledge") != []
        or envelope.get("constraints") != ["no_raw_health_values"]
        or not isinstance(features, dict)
        or set(features) != {"connection_status", "latest_sync_at", "category_coverage"}
    ):
        raise HTTPException(status_code=403, detail="invalid sync status envelope")

    connection_status = features.get("connection_status")
    latest_sync_at = features.get("latest_sync_at")
    category_coverage = features.get("category_coverage")
    allowed_categories = {"血糖", "睡眠", "心率与恢复", "健身与活动"}
    if connection_status not in {"connected", "disconnected"}:
        raise HTTPException(status_code=403, detail="invalid sync status envelope")
    if latest_sync_at is not None:
        if not isinstance(latest_sync_at, str):
            raise HTTPException(status_code=403, detail="invalid sync status envelope")
        try:
            datetime.fromisoformat(latest_sync_at)
        except ValueError as error:
            raise HTTPException(status_code=403, detail="invalid sync status envelope") from error
    if (
        not isinstance(category_coverage, list)
        or not all(isinstance(item, str) for item in category_coverage)
        or len(category_coverage) != len(set(category_coverage))
        or not set(category_coverage).issubset(allowed_categories)
    ):
        raise HTTPException(status_code=403, detail="invalid sync status envelope")

    status_text = "已连接" if connection_status == "connected" else "未连接"
    sync_time_text = latest_sync_at or "无"
    coverage_text = "、".join(category_coverage) or "无"
    return f"同步状态：{status_text}\n最新同步时间：{sync_time_text}\n数据类别覆盖：{coverage_text}"


def _stream_chat_completion(
    *, completion_id: str, created: int, model: str, text: str, route: str
) -> StreamingResponse:
    chunks = [
        {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": text},
                    "finish_reason": None,
                }
            ],
            "bodyos_route": route,
        },
        {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            "bodyos_route": route,
        },
    ]

    def events():
        for chunk in chunks:
            yield f"data: {json.dumps(chunk, ensure_ascii=False, separators=(',', ':'))}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/v1/chat/completions", response_model=None)
def chat_completions(
    request: ChatCompletionRequest,
    _: Annotated[None, Depends(require_model_proxy)],
    gateway: Annotated[Any, Depends(get_model_gateway)],
) -> dict | StreamingResponse:
    text, route = _bodyos_reply(request, gateway)
    completion_id = f"bodyos-{uuid.uuid4()}"
    created = int(time.time())
    if request.stream:
        return _stream_chat_completion(
            completion_id=completion_id,
            created=created,
            model=request.model,
            text=text,
            route=route,
        )
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "bodyos_route": route,
    }
