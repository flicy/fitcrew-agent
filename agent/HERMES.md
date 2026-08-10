# Hermes Runtime Rules / Hermes 运行规则

## 中文

Hermes 在 V2 中是飞书通道壳与 Codex Harness 的备用能力，不是原始健康数据访问者。`bodyos_guard` 使用 Hermes 已支持的 `pre_gateway_dispatch` 钩子，把飞书事件交给 BodyOS 安全 API；API 只用去标识化 envelope 调用模型，并返回已检查的最终答复。插件发回答复后终止原生代理流程。任一步失败都保持安全关闭（fail closed），不把原消息回退给模型。

- 保持 `FEISHU_ALLOW_ALL_USERS=false`；只有同时位于 `FEISHU_ALLOWED_USERS` 且已明确绑定的受控 BodyOS 身份可以进入私聊与私人教练。未知或未受邀身份继续拒绝。
- 未列入 `group_rules` 的群默认拒绝；白名单群仍须 @。打卡与加入流程走固定低敏 token；饮食、训练、睡眠与控糖的通用问题只能使用 `bodyos-public.v2` 和已发布的共享专家知识，且不得带入身份、个人特征、私人书摘、健康数值或聊天历史。API 审核后的 `bodyos-group-answer.v1` 才能发回群聊。
- 主动群聊教练仅发送经审核的固定公共模板，或由 `bodyos-public.v2` 对每周公共主题生成的安全答案；不得把群聊变成任何用户的健康播报。
- 涉及第一人称个人情境、用户输入数值、疾病、治疗或用药的问题必须安全引导到私聊或专业人员，不得在群里个性化回答。
- 私聊模型只能使用对应用户的授权日级聚合特征、私人知识和 `request_context.sanitized_text`；不得使用原始消息、身份、联系方式、用户输入数值或原始健康序列。
- 模型端点只能是 BodyOS 的 OpenAI 兼容代理；不得配置付费 API Key 作为静默备用。
- Codex CLI 主路由失败两次后，才调用 Hermes `openai-codex` OAuth 备用；两者失败则安全报错。
- 日志只记录路由、策略结果、计数、错误码与散列引用，不记录消息正文、身份、样本值或书摘。
- Profile、OAuth、`.env`、sanitized cache 权限为 `0700/0600`，不得提交 Git。

## English

In V2, Hermes is the Feishu channel shell and the fallback capability for Codex Harness; it is not a raw-health-data reader. `bodyos_guard` uses Hermes's supported `pre_gateway_dispatch` hook to send Feishu events to the BodyOS safety API. The API invokes a model only with a de-identified envelope and returns a checked final answer. The plugin sends that answer and stops the native agent path. Any failure remains fail closed; the original message is never used as fallback model input.

- Keep `FEISHU_ALLOW_ALL_USERS=false`; only explicitly bound, controlled-allowlisted BodyOS identities may use DMs and private coaching. Unknown and uninvited users remain denied.
- Groups absent from `group_rules` are denied, and allowlisted groups still require a mention. Check-ins and joining use fixed low-sensitivity behavior tokens. Group paths contain only fixed/public material—never health data or private content. General food, training, sleep, and glucose-management questions may use only `bodyos-public.v2` and published shared expert knowledge, without identity, personal features, private excerpts, entered values, or chat history. Only an API-checked `bodyos-group-answer.v1` may return to the group.
- Proactive group coaching sends only reviewed fixed public templates or a safe `bodyos-public.v2` answer to a weekly public topic; it must never become a health broadcast about any user.
- First-person personal context, entered values, disease, treatment, or medication questions must fail closed to a DM or professional care; never personalize them in a group.
- A DM model may use only the corresponding user's authorized daily aggregates, private knowledge, and `request_context.sanitized_text`; never the raw message, identity, contact details, entered values, or raw health samples.
- The model endpoint must be the BodyOS OpenAI-compatible proxy. Never configure a paid API key as a silent fallback.
- Retry Codex CLI twice before invoking Hermes `openai-codex` OAuth fallback. Fail closed if both routes fail.
- Logs contain only route, policy result, counts, error codes, and hashed references—never message text, identity, sample values, or book excerpts.
- Profile, OAuth, `.env`, and sanitized cache permissions are `0700/0600`; none may enter Git.
