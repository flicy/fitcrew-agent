# Hermes Runtime Rules / Hermes 运行规则

## 中文

Hermes 在 V2 中是飞书通道壳与 Codex Harness 的备用能力，不是原始健康数据访问者。`gateway_hook` 先把事件交给 BodyOS API；`bodyos_guard` 再用经校验的去标识化 envelope 完整替换模型消息。任一步失败都拒绝请求，保持安全关闭（fail closed），不把原消息回退给模型。

- 保持 `FEISHU_ALLOW_ALL_USERS=false`；只有同时位于 `FEISHU_ALLOWED_USERS` 且已明确绑定的受控 BodyOS 身份可以进入私聊与私人教练。未知或未受邀身份继续拒绝。
- 未列入 `group_rules` 的群默认拒绝；白名单群仍须 @，只走固定的低敏行为 token，绝不返回健康数据或私有内容。
- 模型端点只能是 BodyOS 的 OpenAI 兼容代理；不得配置付费 API Key 作为静默备用。
- Codex CLI 主路由失败两次后，才调用 Hermes `openai-codex` OAuth 备用；两者失败则安全报错。
- 日志只记录路由、策略结果、计数、错误码与散列引用，不记录消息正文、身份、样本值或书摘。
- Profile、OAuth、`.env`、sanitized cache 权限为 `0700/0600`，不得提交 Git。

## English

In V2, Hermes is the Feishu channel shell and the fallback capability for Codex Harness; it is not a raw-health-data reader. `gateway_hook` sends the event to the BodyOS API first, then `bodyos_guard` replaces the entire model request with a validated de-identified envelope. Any failure denies the request and fails closed; the original message is never used as fallback model input.

- Keep `FEISHU_ALLOW_ALL_USERS=false`; only explicitly bound, controlled-allowlisted BodyOS identities may use DMs and private coaching. Unknown and uninvited users remain denied.
- Groups absent from `group_rules` are denied. An allowlisted group still requires a mention and only follows fixed low-sensitivity behavior tokens, never health data or private content.
- The model endpoint must be the BodyOS OpenAI-compatible proxy. Never configure a paid API key as a silent fallback.
- Retry Codex CLI twice before invoking Hermes `openai-codex` OAuth fallback. Fail closed if both routes fail.
- Logs contain only route, policy result, counts, error codes, and hashed references—never message text, identity, sample values, or book excerpts.
- Profile, OAuth, `.env`, and sanitized cache permissions are `0700/0600`; none may enter Git.
