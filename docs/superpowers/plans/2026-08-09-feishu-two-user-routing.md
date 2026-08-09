# Feishu Two-User Routing Repair Implementation Plan

> **For implementation:** use this plan as a checklist. Every change must remain fail-closed, avoid logging message content or Feishu identifiers, and preserve the Owner's existing identity and health data.

## 中文

### 已验证问题与目标

生产运行时只把 Owner 写入 `FEISHU_ALLOWED_USERS`。Hermes 的飞书群规则会先允许白名单群中的 `@` 消息，但全局 Gateway 授权随后再次检查用户白名单，因此已受控邀请的第二位用户会在群聊和私聊被静默拒绝。修复目标是让一次受控邀请同时写入仅限运行时读取的飞书访问清单，重启 gateway 后允许该用户到达 BodyOS 的身份与隐私门禁；未邀请用户仍被拒绝。

群聊的“个性化健康建议请私聊 BodyOS。”是既定的隐私策略：群聊不读取健康、私有记忆、知识或模型。应增加公开且低敏的“联系 / 加入 BodyOS”固定回复，满足加入咨询，同时保持个性化建议在私聊中完成。

### 不可破坏的边界

- `FEISHU_ALLOW_ALL_USERS=false` 与 `GATEWAY_ALLOW_ALL_USERS=false` 始终为关闭式白名单。
- 不猜测或通过姓名查找飞书 `open_id`；仅使用 Owner 在受控邀请流程中输入的精确 subject。
- 运行时清单、二维码、配对码、身份和健康数据不得进入 Git、日志、终端成功输出或公开文档。
- 群聊不调用模型，不返回任何原始健康值、私有记忆或知识库内容。
- 不能重绑、覆盖或撤销 Owner 的现有身份、设备、consent 与数据。

### 实现步骤

1. 先为群聊“联系 / 加入 BodyOS”写失败测试：它返回唯一的低敏固定文本、路由为 deterministic、不会调用模型；普通健康提问仍走现有私聊提示。
2. 增加 `BehaviorToken.CONTACT_BODYOS` 与中英相关的低敏实现/操作说明。只识别加入、联系方式和联系 BodyOS 的明确措辞，不把健康问题错分为联系请求。
3. 在邀请脚本中，在 API 受控邀请成功后，把精确 subject 原子地加入私有的 `/owner-runtime/feishu-allowed-users`。文件权限 `0600`，目录 `0700`；清单合并当前关闭式环境白名单并去重，不能打印内容。
4. 让 gateway 以只读方式挂载私有 owner runtime。入口启动时仅在该私有文件存在且格式有效时覆盖 `FEISHU_ALLOWED_USERS`；文件缺失时回退到现有环境白名单，异常或空清单时安全失败而非开放访问。
5. 新增无回显 `infra/tencent/bootstrap-invited-user.sh`：读取精确 subject、设备公开标识和本地 slug，以一次容器执行创建邀请，再仅重启 gateway 使清单生效。它不得使用 `docker compose config`、不得输出输入值、二维码或 token，也不得把临时变量写进 `runtime/.env.runtime`。
6. 更新部署运维文档的“第二位用户邀请”章节，明确这个脚本是唯一支持路径；修复已存在邀请时，需要使用该受控脚本并输入开发者控制台/已核实来源得到的精确 `open_id`，不得按姓名猜测。
7. 增加回归测试：私有清单写入的原子性/权限/去重；gateway 只读挂载与缺失时 owner-only 回退；wrapper 不回显输入/不持久化临时环境；群联系 token 的固定、无模型、无健康输出。运行完整 Python、Ruff、双语文档、Swift Core 与无签名 Simulator build。

### 验收与上线

合并后用 Tencent 服务器中现有的严格 `deploy.sh` 发布；部署失败或 HTTPS 门禁失败必须停止。发布后不发送真实健康消息或二维码。由 Owner 在服务器上以精确 subject 执行受控邀请脚本后，重新启动 gateway；再由第二位用户验证：群聊 `@黑客松助手 提供我 BodyOS 的联系方式` 得到固定联系指引，私聊可获得其独立的同步状态且不含原始数值。Owner 的既有同步状态必须不变。

## English

### Verified problem and goal

The production runtime initially writes only the Owner to `FEISHU_ALLOWED_USERS`. Hermes may first admit an @-mention in an allowed group, but global Gateway authorization checks the user allowlist again. A controlled invited second user is therefore silently rejected in both group chat and DM. The repair makes a controlled invitation update a runtime-private Feishu access list; after a gateway restart, that user reaches BodyOS identity and privacy gates while uninvited users remain denied.

The group reply, “Please DM BodyOS for personalised health guidance,” is intentional privacy policy: groups do not read health, private memory, knowledge, or a model. Add a public, low-sensitivity fixed “contact / join BodyOS” response for onboarding questions while keeping personalised guidance in DM.

### Non-negotiable boundaries

- `FEISHU_ALLOW_ALL_USERS=false` and `GATEWAY_ALLOW_ALL_USERS=false` remain closed allowlists.
- Never guess or resolve a Feishu `open_id` from a name; use only the exact subject entered by the Owner in the controlled invitation flow.
- Runtime lists, QR codes, pairing codes, identities, and health data never enter Git, logs, terminal success output, or public documents.
- A group never calls a model or returns raw health data, private memory, or private knowledge.
- Do not rebind, overwrite, or revoke the Owner's existing identity, device, consent, or data.

### Implementation steps

1. Write failing tests for an explicit group “contact / join BodyOS” request: it returns one low-sensitivity fixed reply, is deterministic, and never invokes the model; ordinary health prompts retain the existing DM-only prompt.
2. Add `BehaviorToken.CONTACT_BODYOS` and matching bilingual low-sensitivity implementation and operations copy. Match only explicit join/contact wording, so health questions cannot be misclassified.
3. After a successful controlled API invitation, have the invitation script atomically add the exact subject to a private `/owner-runtime/feishu-allowed-users` file. Use `0600` file and `0700` directory modes; merge and deduplicate the current closed environment allowlist without printing contents.
4. Mount the private Owner runtime read-only in the gateway. At startup, override `FEISHU_ALLOWED_USERS` only when that private file exists and is valid; otherwise fall back to the current environment allowlist. An invalid or empty file must fail closed, never open access.
5. Add a no-echo `infra/tencent/bootstrap-invited-user.sh`: collect the exact subject, public device ID, and local slug; issue the invitation with one container execution; then restart only the gateway so the access list applies. It must not run `docker compose config`, print input/QR/token, or persist temporary variables to `runtime/.env.runtime`.
6. Update the controlled-invitation operations guide so this wrapper is the supported path. When an invitation already exists, the Owner must use the exact `open_id` from a verified source or developer console, never a guessed name.
7. Add regression coverage for atomic/permissioned/deduplicated private-list writes; gateway read-only mount and missing-file Owner-only fallback; a wrapper that does not echo input or persist temporary environment; and the group contact token's fixed/no-model/no-health behaviour. Run full Python, Ruff, bilingual-doc, Swift Core, and unsigned Simulator checks.

### Acceptance and release

After merge, deploy through the existing strict Tencent `deploy.sh`; stop on deployment or HTTPS-gate failure. Do not send real health messages or QR codes. The Owner runs the controlled invitation wrapper with the exact subject and restarts the gateway. The invited user then verifies that `@Hackathon Assistant provide my BodyOS contact` receives fixed contact guidance in group chat, and DM returns only that user's isolated sync state without raw values. The Owner's existing sync state must remain unchanged.
