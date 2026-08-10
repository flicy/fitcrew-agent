import json
import re

from bodyos_api.policy import BehaviorToken


class SensitiveOutput(ValueError):
    pass


PUBLIC_FALLBACKS = {
    "glucose_coaching": (
        "一般而言，均衡餐食、合理进食顺序和饭后舒适活动有助于管理餐后波动。"
        "个体情况请在 BodyOS 私聊中讨论。"
    ),
    "sleep_coaching": (
        "规律作息、稳定起床时间和合适的白天活动通常有助于睡眠与恢复。"
        "个体情况请在 BodyOS 私聊中讨论。"
    ),
    "activity_coaching": (
        "训练量、恢复时间和睡眠需要共同安排；可以从能稳定坚持的小行动开始。"
        "个体情况请在 BodyOS 私聊中讨论。"
    ),
    "knowledge_coaching": (
        "健康知识需要结合适用范围理解；可以先选择一个今天能稳定完成的小行动。"
        "个体情况请在 BodyOS 私聊中讨论。"
    ),
    "general_health_coaching": (
        "可以先选择一个今天能够稳定完成的小行动，再观察长期变化。"
        "个体情况请在 BodyOS 私聊中讨论。"
    ),
}
PROACTIVE_FIXED_TEMPLATES = {
    "morning_action": (
        "早上好。今天你最想稳定完成的一个健康小行动是什么？可以从足够小的一步开始。"
    ),
    "evening_checkin": (
        "今晚的小行动完成了吗？可以回复：已完成、需要搭子，或行动小一点。"
    ),
}
WEEKLY_PUBLIC_FALLBACKS = {
    "meal_order": "本周一起讨论：一顿饭中的进食顺序，怎样帮助我们形成更稳定的饮食行动？",
    "small_actions": "本周一起讨论：怎样把健康目标变成今天可以完成的一小步？",
    "sleep_rhythm": "本周一起讨论：怎样用稳定作息支持睡眠与恢复？",
}
_KNOWLEDGE_STEMS = {
    intent: message.removesuffix("个体情况请在 BodyOS 私聊中讨论。").strip().rstrip("。！？；;")
    for intent, message in PUBLIC_FALLBACKS.items()
}
_REVIEWED_STATIC_MESSAGES = frozenset(
    [
        *PUBLIC_FALLBACKS.values(),
        *PROACTIVE_FIXED_TEMPLATES.values(),
        *WEEKLY_PUBLIC_FALLBACKS.values(),
    ]
)
_REVIEWED_TITLES = frozenset(
    {"控糖革命", "百岁人生行动手册", "睡眠优化完全指南：科学与实践"}
)
_REVIEWED_SUFFIX = "个体情况请在 BodyOS 私聊中讨论。"


def render_public_knowledge_answer(intent: str, title: str, page: int) -> str:
    if intent not in _KNOWLEDGE_STEMS or title not in _REVIEWED_TITLES:
        raise SensitiveOutput("public knowledge template is not reviewed")
    if isinstance(page, bool) or not isinstance(page, int) or not 1 <= page <= 99_999:
        raise SensitiveOutput("public knowledge page is invalid")
    return f"{_KNOWLEDGE_STEMS[intent]}（《{title}》第{page}页）。{_REVIEWED_SUFFIX}"


def _is_reviewed_public_message(text: str) -> bool:
    if text in _REVIEWED_STATIC_MESSAGES:
        return True
    citations = _CITATION_RE.findall(text)
    if len(citations) != 1:
        return False
    title, page = citations[0]
    try:
        return any(
            text == render_public_knowledge_answer(intent, title, int(page))
            for intent in _KNOWLEDGE_STEMS
        )
    except (SensitiveOutput, ValueError):
        return False


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
    r"药|(?:安神|助眠|降糖)(?:片|剂)|褪黑素|镇静剂|注射|打针|口服|服药|吃药|"
    r"手术|旁路|切除|植入|[\u4e00-\u9fff]{2,12}(?:肽|激素)|"
    r"(?:吃|用|使用|服用).{0,8}(?:片|剂|药|素|辅助品)|病|症|患者|胸痛|呼吸困难|"
    r"doctor|diagnos|disease|treatment|medication|dosage|melatonin|metformin|emergency)"
)
_INTERVENTION_ACTION_RE = re.compile(
    r"(?i)(?:(?:吃|服用|使用|(?<!利)(?<!作)用|注射|打针)\s*"
    r"([^，,。；;!?！？\s]{1,16})|"
    r"\b(?:take|use|inject)\s+([a-z][a-z -]{1,30}))"
)
_LIFESTYLE_OBJECT_RE = re.compile(
    r"(?i)^(?:进食顺序|饮食|餐食|食物|蔬菜|蛋白质|碳水|散步|步行|运动|训练|健身|"
    r"作息|睡眠|呼吸|日光|阳光|习惯|小行动|meal order|diet|food|vegetable|protein|"
    r"carbohydrate|walk|exercise|training|sleep|breathing|daylight|habit)"
)
_DIAGNOSTIC_INFERENCE_RE = re.compile(
    r"(?i)(?:说明|表明|意味着|判断).{0,12}(?:是不是|是否|是|有|患)|"
    r"(?:说明|表明|意味着|判断).{0,20}(?:存在|出现).{0,12}(?:倾向|风险|病|症)|"
    r"(?:是不是|是否).{0,12}(?:病|症|患者)|"
    r"(?:indicate|mean|show|determine).{0,20}(?:diagnos|disease|condition)"
)
_UNSAFE_MEDICAL_ANSWER_RE = re.compile(
    r"(?i)(?:确诊|处方|剂量|二甲双胍|胰岛素|药|褪黑素|镇静剂|注射|打针|"
    r"口服|服药|吃药|急诊|昏迷|胸痛|呼吸困难|"
    r"你(?:很)?(?:可能|也许|或许)?(?:有|患有|患上(?:了)?|得了|是)"
    r"[^，。；;]{0,12}(?:糖尿病|疾病|病症|患者)|"
    r"(?:建议|应该|应当|可|可以|需要|最好)?[^，。；;]{0,8}"
    r"(?:服用|使用|停用|吃|加量|减量)[^，。；;]{0,12}"
    r"(?:药|药物|药品|药片|胰岛素|二甲双胍)|"
    r"diagnosed|prescription|dosage|metformin|"
    r"you (?:should|may|might|probably|likely) (?:take|stop|have|be|suffer)|emergency)"
)
_SAFE_MEDICAL_DISCLAIMER_RE = re.compile(
    r"(?i)(?:这|本回答)?不(?:是|构成)(?:个体|医疗|医学)?诊断|"
    r"不能替代(?:医生|医疗专业人员|专业诊疗)|not (?:a )?(?:personal |medical )?diagnosis"
)
_PROVIDER_DETAIL_RE = re.compile(
    r"(?i)(?:"
    r"\b(?:api|provider|upstream|backend|status|error|failed|failure|authorization|"
    r"authentication|credentials?|quota|retry|retries|rate[- ]?limit(?:ed|ing)?|http|"
    r"request[_ -]?id|bearer|unauthorized|forbidden|unavailable|gateway|timeout|"
    r"connection)\b|"
    r"(?<!\d)[45]\d{2}(?!\d)|api[_ -]?key|too\s+many\s+requests|"
    r"模型.{0,8}(?:问题|错误|异常|不可用)|(?:推理|模型|AI|大模型)?服务.{0,8}不可用|"
    r"模型(?:服务|提供商|供应商|认证|鉴权|调用)|鉴权|密钥|配额|上游服务|后端服务|"
    r"内部(?:服务器|错误|异常)|服务器异常|服务异常|系统(?:错误|异常|故障)|数据库|"
    r"连接失败|网络异常|请?稍候|稍后再试|"
    r"错误代码|状态码|调用失败|认证失败|认证错误|配置错误|请重试|限流)"
)
_CITATION_RE = re.compile(r"《([^》]{1,300})》[，,\s]*第\s*(\d{1,5})\s*页")
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
    r"晚饭后|饭后|餐后|早餐|午餐|晚餐|晚饭|先吃|力量训练|训练|运动|健身|散步|跑步|"
    r"睡眠|睡觉|恢复|血糖|葡萄糖|控糖|饮食|食物|进食|蔬菜|蛋白质|碳水)|"
    r"关于(?:饮食|食物|训练|运动|健身|睡眠|恢复|血糖|葡萄糖|控糖)|"
    r"(?:why|how|what|which|does|do|can|is|are|should|in\s+general|generally|usually|"
    r"after|before|food|diet|meal|training|workout|exercise|sleep|recovery|glucose)\b)"
)
_TITLECASE_IDENTITY_RE = re.compile(r"\b[A-Z][a-z]{1,30}\b")
_ENGLISH_NAMED_HEALTH_CONTEXT_RE = re.compile(
    r"(?i)(?:"
    r"(?:why|how|what)\s+(?:does|can|is|should)\s+([a-z][a-z'-]{1,30})\s+"
    r"(?=.{0,48}(?:feel|felt|has|had|gets?|sleeps?|ate|eats?|dinner|meal|"
    r"sleep|recovery|glucose|training|exercise)\b)|"
    r"\b([a-z][a-z'-]{1,30})\b(?=.{0,32}(?:晚饭|饭后|餐后|睡眠|睡觉|失眠|血糖|葡萄糖|"
    r"恢复|犯困|训练|运动|身体|不适|感觉|dinner|meal|sleep|recovery|glucose|"
    r"training|exercise)))"
)
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
    rf"(?:^|[，,。；;、\s]|帮助|关于|为什么|为何|怎么|如何)(?!(?:通常|一般|怎样|怎么|如何|为什么|"
    rf"有什么|是否|能否|可以|会不会|哪些))"
    rf"(?:(?:小|老)[\u4e00-\u9fff]{{1,2}}|[{_CHINESE_SURNAMES}][\u4e00-\u9fff]{{1,2}})"
    r"(?=.{0,16}(?:睡眠|睡觉|失眠|"
    r"血糖|葡萄糖|晚饭|餐后|恢复|犯困|训练|运动|身体|不适|感觉|吃|喝))"
)
_IDENTITY_TARGET_RE = re.compile(
    rf"(?i)(?:(?:对|帮助|给|关于)\s*(?:"
    rf"((?:小|老|阿)[\u4e00-\u9fff]{{1,2}}|[{_CHINESE_SURNAMES}][\u4e00-\u9fff]{{1,2}})|"
    rf"([a-z][a-z'-]{{1,30}}))|(?:for|help|about)\s+([a-z][a-z'-]{{1,30}}))"
)
_PERSONALIZED_ANSWER_RE = re.compile(
    r"(?i)(?:根据你(?:的|目前)|你的(?:血糖|睡眠|心率|身体|数据)|你已确诊|你应该服用|"
    r"your (?:glucose|sleep|heart rate|health data)|you (?:have|are diagnosed))"
)
_SPELLED_HEALTH_VALUE_RE = re.compile(
    r"(?i)(?:(?:血糖|葡萄糖|心率|HRV|体重|睡眠).{0,12}"
    r"[零〇一二两三四五六七八九十百]+(?:点[零〇一二两三四五六七八九]+)?|"
    r"[零〇一二两三四五六七八九十百]+(?:点[零〇一二两三四五六七八九]+)?"
    r"(?:左右|上下|约|是|为|的).{0,8}(?:血糖|葡萄糖|心率|HRV|体重|睡眠))"
    r"(?:毫摩尔每升|毫摩尔|mg/dl|mmol/l|次每分|小时|公斤)?"
)
_MIXED_LATIN_IDENTITY_RE = re.compile(
    r"(?i)(?:[\u4e00-\u9fff].*\b[a-z][a-z'-]{1,30}\b|"
    r"\b[a-z][a-z'-]{1,30}\b.*[\u4e00-\u9fff])"
)
_HEALTH_UNIT_RE = re.compile(
    r"(?i)(?:毫摩尔(?:每升)?|mmol\s*/\s*l|millimoles?\s+per\s+lit(?:re|er)|"
    r"mg\s*/\s*dl|bpm|"
    r"[零〇一二两三四五六七八九十百千万]+点[零〇一二两三四五六七八九]+|"
    r"[零〇一二两三四五六七八九十百千万]+(?:点[零〇一二两三四五六七八九]+)?"
    r"(?:小时|分钟|公斤|千克|次每分)|"
    r"\b[a-z]+\s+point\s+[a-z]+\b)"
)
_EXPLICIT_NAME_RE = re.compile(
    r"(?i)(?:我叫|我的名字是|姓名(?:是|为)?|name\s+is)\s*[^，,。；;!?！？\n]{1,80}[，,。；;]?"
)
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
_SPACE_RE = re.compile(r"\s+")
_GENERAL_ENGLISH_WORDS = frozenset(
    {
        "food",
        "diet",
        "meal",
        "training",
        "workout",
        "exercise",
        "sleep",
        "recovery",
        "glucose",
        "bodyos",
        "why",
        "how",
        "what",
        "which",
        "when",
        "where",
        "does",
        "can",
        "should",
    }
)
_CHINESE_ALIAS_RE = re.compile(
    r"(?:小|老|阿)[\u4e00-\u9fff]{1,2}"
    r"(?=.{0,20}(?:晚饭|饭后|餐后|睡眠|睡觉|失眠|血糖|葡萄糖|恢复|犯困|训练|"
    r"运动|身体|不适|感觉|可以|应该))"
)
_SAFE_CHINESE_ALIASES = frozenset(
    {"小行动", "小步骤", "小目标", "小习惯", "小幅度", "小一点"}
)


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


def _contains_named_health_context(text: str) -> bool:
    if _CHINESE_NAMED_HEALTH_CONTEXT_RE.search(text):
        return True
    for match in _ENGLISH_NAMED_HEALTH_CONTEXT_RE.finditer(text):
        candidate = next((value for value in match.groups() if value), "")
        if candidate.casefold() not in _GENERAL_ENGLISH_WORDS:
            return True
    return False


def _contains_identity_target(text: str) -> bool:
    if any(
        match.group(0) not in _SAFE_CHINESE_ALIASES for match in _CHINESE_ALIAS_RE.finditer(text)
    ):
        return True
    for match in _TITLECASE_IDENTITY_RE.finditer(text):
        if match.group(0).casefold() not in _GENERAL_ENGLISH_WORDS:
            return True
    for match in _IDENTITY_TARGET_RE.finditer(text):
        chinese, latin, english = match.groups()
        if chinese:
            return True
        candidate = latin or english or ""
        if candidate.casefold() not in _GENERAL_ENGLISH_WORDS:
            return True
    return False


def _contains_unsafe_intervention(text: str) -> bool:
    for match in _INTERVENTION_ACTION_RE.finditer(text):
        target = next((value for value in match.groups() if value), "")
        if not _LIFESTYLE_OBJECT_RE.search(target.strip()):
            return True
    return False


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
        or _contains_named_health_context(normalized)
        or _contains_identity_target(normalized)
        or _MIXED_LATIN_IDENTITY_RE.search(normalized)
        or _MEDICAL_RE.search(normalized)
        or _contains_unsafe_intervention(normalized)
        or _DIAGNOSTIC_INFERENCE_RE.search(normalized)
        or _PROMPT_INJECTION_RE.search(normalized)
        or _NUMBER_RE.search(normalized)
        or _SPELLED_HEALTH_VALUE_RE.search(normalized)
        or _HEALTH_UNIT_RE.search(normalized)
        or not _PUBLIC_TOPIC_RE.search(normalized)
        or general_start is None
    ):
        return None
    remainder = normalized[general_start.end() :]
    if _TITLECASE_IDENTITY_RE.search(remainder) or _contains_named_health_context(remainder):
        return None
    return normalized


def assert_public_group_answer(text: str) -> str:
    """Accept only locally rendered and reviewed public messages."""
    if not isinstance(text, str):
        raise SensitiveOutput("public group answer must be text")
    normalized = _SPACE_RE.sub(" ", text).strip()
    if not normalized or len(normalized) > 800:
        raise SensitiveOutput("public group answer must be non-empty and bounded")
    if not _is_reviewed_public_message(normalized):
        raise SensitiveOutput("public group answer is not a reviewed local template")
    return normalized


def assert_public_knowledge_citations(text: str, knowledge: list[dict]) -> str:
    """Require every public citation to match one of the retrieved title/page pairs."""
    normalized = assert_public_group_answer(text)
    allowed = {
        (hit.get("title"), hit.get("page"))
        for hit in knowledge
        if isinstance(hit, dict)
        and isinstance(hit.get("title"), str)
        and isinstance(hit.get("page"), int)
        and not isinstance(hit.get("page"), bool)
    }
    citations = {(title, int(page)) for title, page in _CITATION_RE.findall(normalized)}
    if not allowed or citations - allowed or not citations:
        raise SensitiveOutput("public knowledge citation is missing or unverified")
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
