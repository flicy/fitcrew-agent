from dataclasses import dataclass
from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from bodyos_api.crypto import EncryptedValue, FieldCipher
from bodyos_api.dlp import (
    SensitiveOutput,
    assert_public_group_answer,
    sanitize_private_request_context,
    sanitize_public_group_question,
)
from bodyos_api.knowledge import KnowledgeService
from bodyos_api.model_gateway import HarnessFailure
from bodyos_api.models import DailyFeature, DeviceBinding, HealthSample
from bodyos_api.policy import BehaviorToken


@dataclass(frozen=True, slots=True)
class ConversationRequest:
    channel: str
    text: str


@dataclass(frozen=True, slots=True)
class ConversationReply:
    text: str
    route: str


def classify_intent(text: str) -> str:
    lowered = text.casefold()
    if any(
        term in lowered for term in ("同步状态", "最新同步", "类别覆盖", "数据覆盖", "sync status")
    ):
        return "sync_status"
    if any(term in lowered for term in ("血糖", "葡萄糖", "餐后", "控糖", "glucose")):
        return "glucose_coaching"
    if any(term in lowered for term in ("睡眠", "睡觉", "失眠", "sleep")):
        return "sleep_coaching"
    if any(term in lowered for term in ("运动", "训练", "健身", "workout")):
        return "activity_coaching"
    if any(term in lowered for term in ("书", "知识库", "依据", "原理")):
        return "knowledge_coaching"
    return "general_health_coaching"


def classify_explicit_group_token(text: str) -> BehaviorToken | None:
    lowered = text.casefold()
    if any(
        term in lowered
        for term in (
            "联系方式",
            "怎么加入",
            "加入bodyos",
            "联系bodyos",
            "contact bodyos",
            "join bodyos",
        )
    ):
        return BehaviorToken.CONTACT_BODYOS
    if any(term in lowered for term in ("需要搭子", "找搭子", "need_buddy")):
        return BehaviorToken.NEED_BUDDY
    if any(term in lowered for term in ("行动小一点", "降低难度", "smaller_action")):
        return BehaviorToken.SMALLER_ACTION
    if any(term in lowered for term in ("愿意分享", "willing_to_share")):
        return BehaviorToken.WILLING_TO_SHARE
    if any(term in lowered for term in ("已完成", "完成打卡", "completed")):
        return BehaviorToken.COMPLETED
    return None


def classify_group_token(text: str) -> BehaviorToken:
    return classify_explicit_group_token(text) or BehaviorToken.PRIVATE_COACHING


def build_public_group_envelope(text: str, *, knowledge: list[dict] | None = None) -> dict | None:
    if classify_explicit_group_token(text) is not None:
        return None
    safe_text = sanitize_public_group_question(text)
    if safe_text is None:
        return None
    return {
        "schema_version": "bodyos-public.v2",
        "intent": classify_intent(safe_text),
        "channel": "group",
        "public_context": {"sanitized_text": safe_text},
        "knowledge": knowledge or [],
        "constraints": [
            "general_knowledge_only",
            "published_knowledge_only",
            "no_personal_health_data",
            "not_medical_diagnosis",
            "cite_pages",
        ],
    }


_KNOWLEDGE_QUERY = {
    "glucose_coaching": "进食顺序 餐后 血糖",
    "sleep_coaching": "睡眠 恢复",
    "activity_coaching": "运动 训练 恢复",
    "knowledge_coaching": "健康 行动",
    "general_health_coaching": "健康 最小行动",
}

_CATEGORY_GROUPS = (
    ("血糖", frozenset({"blood_glucose"})),
    ("睡眠", frozenset({"sleep_asleep", "sleep_core", "sleep_deep", "sleep_rem"})),
    (
        "心率与恢复",
        frozenset({"heart_rate_variability", "resting_heart_rate"}),
    ),
    (
        "健身与活动",
        frozenset(
            {
                "workout",
                "active_energy",
                "step_count",
                "stand_hours",
                "activity_summary",
            }
        ),
    ),
)


class BodyOSService:
    def __init__(self, session: Session, cipher: FieldCipher, model_gateway):
        self._session = session
        self._cipher = cipher
        self._model_gateway = model_gateway

    def handle(self, fitcrew_user_id: str, request: ConversationRequest) -> ConversationReply:
        if request.channel == "group":
            explicit_token = classify_explicit_group_token(request.text)
            if explicit_token is not None:
                return ConversationReply(text=explicit_token.message, route="deterministic")
            envelope = self.build_public_group_envelope(request.text)
            if envelope is None:
                return ConversationReply(
                    text=BehaviorToken.PRIVATE_COACHING.message,
                    route="deterministic",
                )
            try:
                reply = self._model_gateway.respond(envelope)
                safe_reply = assert_public_group_answer(reply.text)
            except (HarnessFailure, SensitiveOutput):
                return ConversationReply(
                    text=BehaviorToken.PRIVATE_COACHING.message,
                    route="deterministic",
                )
            return ConversationReply(text=safe_reply, route=reply.route)
        if request.channel != "dm":
            raise PermissionError("unsupported conversation channel")

        envelope = self.build_envelope(fitcrew_user_id, request.text)
        reply = self._model_gateway.respond(envelope)
        return ConversationReply(text=reply.text, route=reply.route)

    def build_public_group_envelope(self, text: str) -> dict | None:
        envelope = build_public_group_envelope(text)
        if envelope is None:
            return None
        query = _KNOWLEDGE_QUERY[envelope["intent"]]
        hits = KnowledgeService(self._session, self._cipher).search_public(query, limit=3)
        envelope["knowledge"] = [
            {
                "title": hit.title,
                "page": hit.page_number,
                "excerpt": hit.excerpt,
            }
            for hit in hits
        ]
        return envelope

    def build_envelope(self, fitcrew_user_id: str, text: str) -> dict:
        intent = classify_intent(text)
        if intent == "sync_status":
            return {
                "schema_version": "bodyos-model.v1",
                "intent": intent,
                "channel": "dm",
                "features": self._sync_status(fitcrew_user_id),
                "knowledge": [],
                "constraints": ["no_raw_health_values"],
            }
        envelope = {
            "schema_version": "bodyos-model.v1",
            "intent": intent,
            "channel": "dm",
            "features": self._latest_features(fitcrew_user_id),
            "knowledge": self._knowledge(fitcrew_user_id, intent),
            "constraints": [
                "not_medical_diagnosis",
                "cite_pages",
                "no_raw_health_data",
            ],
        }
        request_context = sanitize_private_request_context(text)
        if request_context is not None:
            envelope["request_context"] = {"sanitized_text": request_context}
        return envelope

    def _sync_status(self, fitcrew_user_id: str) -> dict:
        device = self._session.scalar(
            select(DeviceBinding)
            .where(
                DeviceBinding.fitcrew_user_id == fitcrew_user_id,
                DeviceBinding.revoked_at.is_(None),
            )
            .order_by(DeviceBinding.last_sync_at.desc())
            .limit(1)
        )
        kinds = set(
            self._session.scalars(
                select(HealthSample.kind)
                .where(HealthSample.fitcrew_user_id == fitcrew_user_id)
                .distinct()
            ).all()
        )
        categories = [label for label, members in _CATEGORY_GROUPS if members & kinds]
        last_sync_at = device.last_sync_at if device is not None else None
        if last_sync_at is not None and last_sync_at.tzinfo is None:
            last_sync_at = last_sync_at.replace(tzinfo=UTC)
        return {
            "connection_status": "connected" if device is not None else "disconnected",
            "latest_sync_at": last_sync_at.isoformat() if last_sync_at is not None else None,
            "category_coverage": categories,
        }

    def _latest_features(self, fitcrew_user_id: str) -> dict:
        feature = self._session.scalar(
            select(DailyFeature)
            .where(DailyFeature.fitcrew_user_id == fitcrew_user_id)
            .order_by(DailyFeature.feature_date.desc())
            .limit(1)
        )
        if feature is None:
            return {"status": "insufficient_data"}
        aad = f"feature:{fitcrew_user_id}:{feature.feature_date}:{feature.feature_set}"
        payload = self._cipher.decrypt_json(
            EncryptedValue(feature.payload_nonce, feature.payload_ciphertext), aad=aad
        )
        return {
            "date": feature.feature_date,
            "quality_status": feature.quality_status,
            **payload,
        }

    def _knowledge(self, fitcrew_user_id: str, intent: str) -> list[dict]:
        hits = KnowledgeService(self._session, self._cipher).search_for_user(
            fitcrew_user_id, _KNOWLEDGE_QUERY[intent], limit=3
        )
        return [
            {
                "title": hit.title,
                "page": hit.page_number,
                "excerpt": hit.excerpt,
            }
            for hit in hits
        ]
