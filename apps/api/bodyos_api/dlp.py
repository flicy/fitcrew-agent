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
_THIRD_PERSON_RE = re.compile(
    r"(?i)(?:"
    r"(?:他|她|朋友|同事|家人|父亲|母亲|爸爸|妈妈|伴侣|孩子|老公|老婆)"
    r"(?:的|最近|今天|昨晚|这几天|吃|喝|睡|感觉|觉得|血糖|身体|餐后)|"
    r"\b(?:he|she|they|him|her|his|hers|their|friend|colleague|partner|spouse|"
    r"child|father|mother)\b)"
)
_NAMED_SCENARIO_RE = re.compile(
    r"(?i)^(?!(?:力量训练|睡眠|晚饭|餐后|血糖|控糖|运动|训练|食物|饮食|进食|"
    r"饭后|餐食|蔬菜|蛋白质|碳水|跑步|散步|恢复))"
    r"(?:(?:小|老)?[\u4e00-\u9fff]{1,4})"
    r"(?:最近|今天|昨晚|这几天|晚饭|餐后|睡眠|睡觉|失眠|感觉|觉得|血糖|身体|"
    r"吃了|喝了|训练后|运动后|恢复|犯困|不适)|"
    r"^[A-Z][A-Za-z'-]{1,30}\s+"
    r"(?:recently|today|yesterday|feels?|felt|has|had|sleeps?|ate|eats?|trains?|"
    r"exercises?|is|was)\b"
)
_MEDICAL_RE = re.compile(
    r"(?i)(?:诊断|确诊|疾病|病症|治疗|处方|药物|用药|剂量|二甲双胍|胰岛素|急诊|昏迷|"
    r"胸痛|呼吸困难|doctor|diagnos|disease|treatment|medication|dosage|emergency)"
)
_UNSAFE_MEDICAL_ANSWER_RE = re.compile(
    r"(?i)(?:确诊|处方|剂量|二甲双胍|胰岛素|急诊|昏迷|胸痛|呼吸困难|"
    r"你(?:患有|得了|应该(?:服用|使用|停用))|建议你(?:服用|使用|停用)|"
    r"diagnosed|prescription|dosage|you should (?:take|stop)|emergency)"
)
_PROMPT_INJECTION_RE = re.compile(
    r"(?i)(?:忽略(?:之前|以上|所有)?(?:的)?(?:指令|规则)|绕过(?:规则|限制)|"
    r"system\s+prompt|developer\s+message|reveal\s+(?:the\s+)?prompt|jailbreak)"
)
_PUBLIC_TOPIC_RE = re.compile(
    r"(?i)(?:饮食|餐食|食物|吃|早餐|午餐|晚餐|晚饭|饭后|餐后|犯困|进食|蔬菜|蛋白质|碳水|"
    r"训练|运动|健身|散步|跑步|力量|睡眠|睡觉|入睡|恢复|血糖|葡萄糖|控糖|"
    r"food|diet|meal|training|workout|exercise|sleep|glucose)"
)
_PUBLIC_GENERAL_START_RE = re.compile(
    r"(?i)^(?:"
    r"(?:为什么|为何|怎样|怎么|如何|什么|哪些|是否|能否|可以|一顿饭|一餐|通常|一般|"
    r"晚饭后|饭后|餐后|早餐|午餐|晚餐|晚饭|力量训练|训练|运动|健身|散步|跑步|"
    r"睡眠|睡觉|恢复|血糖|葡萄糖|控糖|饮食|食物|进食|蔬菜|蛋白质|碳水)|"
    r"关于(?:饮食|食物|训练|运动|健身|睡眠|恢复|血糖|葡萄糖|控糖)|"
    r"(?:why|how|what|which|does|do|can|is|are|should|in\s+general|generally|usually|"
    r"after|before|food|diet|meal|training|workout|exercise|sleep|recovery|glucose)\b)"
)
_TITLECASE_IDENTITY_RE = re.compile(r"\b[A-Z][a-z]{1,30}\b")
_CHINESE_SURNAMES = (
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢邹喻"
    "柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳鲍史唐费廉岑薛雷贺倪汤"
    "滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄穆萧尹姚邵湛汪祁毛禹"
    "狄米贝明臧计伏成戴谈宋茅庞熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江"
    "童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍虞万支柯管卢莫房裘缪解应宗丁宣"
    "邓郁单杭洪包诸左石崔吉钮龚程嵇邢滑裴陆荣翁荀羊甄家封芮储靳井段富巫乌"
    "焦巴弓牧山谷车侯全班仰秋仲伊宫宁仇栾暴甘厉戎祖武符刘景詹束龙叶幸司黎"
    "白怀蒲鄂索咸赖卓蔺屠蒙池乔闻党翟谭贡劳姬申扶冉宰雍桑桂牛寿通边扈燕冀"
    "尚农温别庄晏柴瞿阎慕连茹习宦艾鱼容向古易慎戈廖庾居衡步都耿满弘匡国文"
    "寇广东欧沃利越隆师巩聂晁勾敖融冷辛阚那简饶空曾沙养鞠须丰巢关相查后荆"
    "红游竺权盖益桓公"
)
_CHINESE_NAMED_HEALTH_CONTEXT_RE = re.compile(
    rf"(?:^|[，,。；;、\s]|帮助|关于)(?!(?:通常|一般|怎样|怎么|如何|为什么|"
    rf"有什么|是否|能否|可以|会不会|哪些))[{_CHINESE_SURNAMES}]"
    r"[\u4e00-\u9fff]{1,2}"
    r"(?=.{0,16}(?:睡眠|睡觉|失眠|"
    r"血糖|葡萄糖|晚饭|餐后|恢复|犯困|训练|运动|身体|不适|感觉|吃|喝))"
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
    general_start = _PUBLIC_GENERAL_START_RE.search(normalized)
    if (
        _contains_identifier(normalized)
        or _FIRST_PERSON_RE.search(normalized)
        or _THIRD_PERSON_RE.search(normalized)
        or _NAMED_SCENARIO_RE.search(normalized)
        or _MEDICAL_RE.search(normalized)
        or _PROMPT_INJECTION_RE.search(normalized)
        or _NUMBER_RE.search(normalized)
        or not _PUBLIC_TOPIC_RE.search(normalized)
        or general_start is None
    ):
        return None
    remainder = normalized[general_start.end() :]
    if _TITLECASE_IDENTITY_RE.search(remainder) or _CHINESE_NAMED_HEALTH_CONTEXT_RE.search(
        remainder
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
        or _UNSAFE_MEDICAL_ANSWER_RE.search(normalized)
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
