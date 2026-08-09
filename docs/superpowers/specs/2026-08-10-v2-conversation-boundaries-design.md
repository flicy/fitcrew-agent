# V2 Conversation Boundaries Design / V2 对话边界设计

## 中文

### 目标

补齐 FitCrew V2 已确认但当前代码尚未实现的两项用户能力：

1. BodyOS 在飞书群聊中回答通用饮食、训练、睡眠与控糖知识问题。
2. BodyOS 私聊在不传递原始聊天、身份或用户输入健康数值的前提下，保留食物与身体感知等完成回答所需的安全上下文。

### 根因

当前 `BodyOSService` 把所有非固定群聊意图映射为“个性化健康建议请私聊 BodyOS”，模型验证器也只接受 `channel=dm`。私聊虽能取得对应用户的聚合健康特征与私人知识，却完全丢弃用户当次问题，只保留意图。因此群聊不能通用问答，私聊也无法理解“今天吃了什么、当时有什么感受”。

### 群聊设计

- 固定打卡、搭子、分享、缩小行动和联系方式意图继续走确定性低敏回复。
- 其他消息只有在满足公开通用问题门禁时才进入模型：主题属于饮食、训练、睡眠或控糖；不含第一人称个人情境、原始健康数值、身份、联系方式、设备标识、疾病治疗或用药请求。
- 模型只收到 `bodyos-public.v1` 信封：通用意图、安全问题文本和固定约束；不含 `fitcrew_user_id`、个人特征、私人知识、群 ID、飞书 ID 或聊天历史。
- 模型回复由 API 做长度、标识符与敏感输出检查，再封装为 `bodyos-group-answer.v1`。Hermes Guard 和 cron watcher 都只消费这个已检查答案，不把原始消息传给第二个模型。
- 不满足公共问题门禁时继续返回“个性化健康建议请私聊 BodyOS”；涉及医疗急症、疾病、治疗或用药时不在群里个性化回答。

### 私聊设计

- 同步状态继续走原有确定性路径，不调用模型。
- 其他私聊在分类意图后生成 `request_context.sanitized_text`：移除 @ 提及、URL、邮箱、手机号、UUID、飞书 open_id、设备/配对令牌、显式姓名自述和所有用户输入数字；压缩空白并限制长度。
- 安全摘要保留非标识性的食物描述、餐次和身体感受，例如“晚饭吃了米饭，餐后有点困”。用户输入的健康数值不会进入模型；系统自己的授权日级聚合特征仍按原有加密和用户隔离路径提供。
- 模型信封继续不含姓名、身份 ID、聊天历史和原始健康序列。验证器对新字段做独立敏感模式扫描，任何不合格内容安全拒绝。

### 验收

- 群聊通用问题调用模型并返回通用答案；个人问题、数值、医疗/用药问题仍导向私聊或专业人员。
- 群聊模型信封不含任何用户 ID、个人健康特征、私人知识或原始数值。
- 私聊安全摘要保留食物与身体感受，但不含姓名、联系方式、ID 和用户输入数值。
- Hermes Guard、OpenAI 兼容代理和 cron watcher 都能消费新群聊答案；失败时安全关闭。
- 现有两用户隔离、同步状态、固定行为 token、HealthKit 和模型主备路由测试继续通过。

## English

### Goal

Complete two confirmed V2 behaviors that the current code does not implement: general food/training/sleep/glucose-management Q&A in Feishu groups, and useful food/body-perception context in BodyOS DMs without exposing raw chat, identity, or user-entered health values.

### Root cause

The current service maps every non-fixed group intent to the private-coaching token, while the model validator accepts only DM envelopes. DMs retrieve per-user aggregates and private knowledge but discard the current question after intent classification. Groups therefore cannot answer general questions, and DMs cannot understand what the person ate or felt.

### Group design

Fixed check-in/contact behaviors remain deterministic. Other messages reach a model only when they pass a public-question gate: an allowed topic, no first-person personal context, no raw values, no identifiers or contact details, and no request for disease treatment or medication. The model receives only a `bodyos-public.v1` envelope with safe question text and public constraints—never identity, personal features, private knowledge, chat IDs, or history. The API validates the generated answer and wraps it as `bodyos-group-answer.v1`; both Hermes Guard and the cron watcher consume only that checked answer. Unsafe or personal questions continue to route to DM.

### DM design

Sync status remains deterministic. Other DMs add a bounded `request_context.sanitized_text` that removes mentions, URLs, email, phone numbers, UUIDs, Feishu identifiers, device/pairing tokens, explicit name disclosures, and all user-entered numbers. Non-identifying food, meal, and body-perception language remains useful. Existing authorized daily aggregates and private knowledge remain isolated to the corresponding user.

### Acceptance

General group questions receive a general answer without private inputs; personal/numeric/medical questions fail closed to DM or professional care. DM context preserves food and perception while removing identity and entered values. Hermes Guard, the proxy, and the watcher consume the new group answer safely, and every existing isolation, sync-status, token, HealthKit, and routing test remains green.
