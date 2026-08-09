import json
import re

from bodyos_api.policy import BehaviorToken


class SensitiveOutput(ValueError):
    pass


_CANONICAL_GROUP_MESSAGES = frozenset(token.message for token in BehaviorToken)

_EMAIL_RE = re.compile(r"(?i)\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b")
_URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)\S+")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)")
_UUID_RE = re.compile(
    r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b"
)
_FEISHU_ID_RE = re.compile(r"(?i)\b(?:ou|oc|on|om|cli|msg)_[a-z0-9_-]{6,}\b")
_SECRET_RE = re.compile(
    r"(?i)\b(?:device|pairing|binding|consent|token|secret|open[_ -]?id)"
    r"\s*[:=：]?\s*[a-z0-9._-]{6,}\b"
)
_MENTION_RE = re.compile(r"(?is)<at\b[^>]*>.*?</at>|@(?:BodyOS|黑客松助手|_user_\d+)\s*")
_FIRST_PERSON_RE = re.compile(r"(?i)(?:我|本人|我的|我们|my\b|me\b|mine\b|i\s+(?:am|have|feel)\b)")
_MEDICAL_RE = re.compile(
    r"(?i)(?:诊断|确诊|疾病|病症|治疗|处方|药物|用药|剂量|二甲双胍|胰岛素|急诊|昏迷|"
    r"胸痛|呼吸困难|doctor|diagnos|disease|treatment|medication|dosage|emergency)"
)
_PROMPT_INJECTION_RE = re.compile(
    r"(?i)(?:忽略(?:之前|以上|所有)?(?:的)?(?:指令|规则)|绕过(?:规则|限制)|"
    r"system\s+prompt|developer\s+message|reveal\s+(?:the\s+)?prompt|jailbreak)"
)
_PUBLIC_TOPIC_RE = re.compile(
    r"(?i)(?:饮食|食物|吃|早餐|午餐|晚餐|晚饭|餐后|进食|蔬菜|蛋白质|碳水|"
    r"训练|运动|健身|散步|跑步|力量|睡眠|睡觉|入睡|恢复|血糖|葡萄糖|控糖|"
    r"food|diet|meal|training|workout|exercise|sleep|glucose)"
)
_PERSONALIZED_ANSWER_RE = re.compile(
    r"(?i)(?:根据你(?:的|目前)|你的(?:血糖|睡眠|心率|身体|数据)|你已确诊|你应该服用|"
    r"your (?:glucose|sleep|heart rate|health data)|you (?:have|are diagnosed))"
)
_EXPLICIT_NAME_RE = re.compile(
    r"(?i)(?:我叫|我的名字是|姓名(?:是|为)?|name\s+is)\s*[^，,。；;!?！？\n]{1,80}[，,。；;]?"
)
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
_SPACE_RE = re.compile(r"\s+")


def _plain_text(text: str) -> str:
    normalized = text.strip()
    if normalized.startswith("{"):
        try:
            payload = json.loads(normalized)
        except (json.JSONDecodeError, TypeError):
            pass
        else:
            if isinstance(payload, dict) and isinstance(payload.get("text"), str):
                normalized = payload["text"]
    normalized = _MENTION_RE.sub("", normalized)
    return _SPACE_RE.sub(" ", normalized).strip()


def _contains_identifier(text: str) -> bool:
    return any(
        pattern.search(text)
        for pattern in (_EMAIL_RE, _URL_RE, _PHONE_RE, _UUID_RE, _FEISHU_ID_RE, _SECRET_RE)
    )


def assert_group_safe(text: str) -> str:
    """Accept only canonical, pre-reviewed low-sensitivity group messages."""
    normalized = text.strip()
    if normalized not in _CANONICAL_GROUP_MESSAGES:
        raise SensitiveOutput("group output must be a canonical confirmed behavior token")
    return normalized


def sanitize_public_group_question(text: str) -> str | None:
    """Return a bounded general-health question or fail closed to private coaching."""
    normalized = _plain_text(text)
    if not normalized or len(normalized) > 500:
        return None
    if (
        _contains_identifier(normalized)
        or _FIRST_PERSON_RE.search(normalized)
        or _MEDICAL_RE.search(normalized)
        or _PROMPT_INJECTION_RE.search(normalized)
        or _NUMBER_RE.search(normalized)
        or not _PUBLIC_TOPIC_RE.search(normalized)
    ):
        return None
    return normalized


def assert_public_group_answer(text: str) -> str:
    """Validate a model answer before it can be relayed to a Feishu group."""
    if not isinstance(text, str):
        raise SensitiveOutput("public group answer must be text")
    normalized = _SPACE_RE.sub(" ", text).strip()
    if not normalized or len(normalized) > 800:
        raise SensitiveOutput("public group answer must be non-empty and bounded")
    if (
        _contains_identifier(normalized)
        or _PERSONALIZED_ANSWER_RE.search(normalized)
        or _MEDICAL_RE.search(normalized)
        or any(ord(character) < 32 for character in normalized)
    ):
        raise SensitiveOutput("public group answer contains private or medical content")
    return normalized


def sanitize_private_request_context(text: str) -> str | None:
    """Preserve food/perception language while removing entered values and identity."""
    normalized = _plain_text(text)
    normalized = _EXPLICIT_NAME_RE.sub("", normalized)
    for pattern in (_EMAIL_RE, _URL_RE, _PHONE_RE, _UUID_RE, _FEISHU_ID_RE, _SECRET_RE):
        normalized = pattern.sub("", normalized)
    normalized = _NUMBER_RE.sub("", normalized)
    normalized = re.sub(
        r"\b(?:open[_ -]?id|token|secret|device|pairing)\s*[:=：]?", "", normalized, flags=re.I
    )
    normalized = re.sub(r"[，,。；;]\s*[，,。；;]+", "，", normalized)
    normalized = _SPACE_RE.sub(" ", normalized).strip(" ，,。；;")
    if not normalized:
        return None
    return normalized[:800].rstrip()


def assert_private_request_context(text: str) -> str:
    if not isinstance(text, str):
        raise SensitiveOutput("private request context must be text")
    normalized = text.strip()
    if (
        not normalized
        or len(normalized) > 800
        or _contains_identifier(normalized)
        or _EXPLICIT_NAME_RE.search(normalized)
        or _NUMBER_RE.search(normalized)
    ):
        raise SensitiveOutput("private request context is not safely redacted")
    return normalized
