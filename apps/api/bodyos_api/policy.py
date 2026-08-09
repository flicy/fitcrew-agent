from dataclasses import dataclass
from enum import StrEnum


class Scope(StrEnum):
    PRIVATE = "private"
    GROUP = "group"
    SYSTEM = "system"


class ToolCapability(StrEnum):
    HEALTH = "health"
    PRIVATE_MEMORY = "private_memory"
    PRIVATE_KNOWLEDGE = "private_knowledge"
    PUBLIC_KNOWLEDGE = "public_knowledge"
    BEHAVIOR_TOKEN = "behavior_token"


class BehaviorToken(StrEnum):
    COMPLETED = "completed"
    NEED_BUDDY = "need_buddy"
    WILLING_TO_SHARE = "willing_to_share"
    SMALLER_ACTION = "smaller_action"
    CONTACT_BODYOS = "contact_bodyos"
    PRIVATE_COACHING = "private_coaching"

    @property
    def message(self) -> str:
        return {
            BehaviorToken.COMPLETED: "今天完成了一个健康小行动。",
            BehaviorToken.NEED_BUDDY: "今天需要一个搭子陪我完成小行动。",
            BehaviorToken.WILLING_TO_SHARE: "今天愿意分享一个健康小行动。",
            BehaviorToken.SMALLER_ACTION: "今天选择把行动再变小一点。",
            BehaviorToken.CONTACT_BODYOS: "请私聊 BodyOS 并发送“加入 BodyOS”，获取加入流程。",
            BehaviorToken.PRIVATE_COACHING: "个性化健康建议请私聊 BodyOS。",
        }[self]


@dataclass(frozen=True, slots=True)
class RequestContext:
    fitcrew_user_id: str
    scope: Scope
    purpose: str
    consent_id: str | None
    consent_categories: frozenset[str] = frozenset()


class PolicyDenied(PermissionError):
    status_code = 403


class PolicyEngine:
    _private_capabilities = frozenset(
        {
            ToolCapability.HEALTH,
            ToolCapability.PRIVATE_MEMORY,
            ToolCapability.PRIVATE_KNOWLEDGE,
        }
    )

    def require(
        self,
        context: RequestContext,
        capability: ToolCapability,
        *,
        category: str | None = None,
    ) -> None:
        if context.scope == Scope.GROUP and capability in self._private_capabilities:
            raise PolicyDenied(f"{capability.value} is unavailable in group scope")
        if capability == ToolCapability.HEALTH:
            if context.scope != Scope.PRIVATE or not context.consent_id:
                raise PolicyDenied("health access requires private scope and active consent")
            if category is None or category not in context.consent_categories:
                raise PolicyDenied("health category is not consented")

    def render_group_token(self, token: BehaviorToken, *, confirmed: bool) -> str:
        if not confirmed:
            raise PolicyDenied("group sharing requires an explicit preview confirmation")
        return token.message
