# Tencent Deployment and Rollback / 腾讯云部署与回滚

## 中文

### 边界与架构

目标是现有东京 Lighthouse（2 vCPU、4 GB、60 GB），不创建新的收费云资源。Compose 常驻 PostgreSQL、BodyOS API、维护 Worker、Hermes 飞书通道和 Caddy；Codex CLI 使用 ChatGPT OAuth 为主路由，Hermes `openai-codex` OAuth 只在主路由失败后备用。Moticlaw macOS 应用仍是配置入口，不作为 Linux 常驻依赖。

公网只开放 80/443；数据库、API 和模型代理不映射主机端口。腾讯云防火墙保留 80/443，并把 22 限制到管理来源。公网 IP HTTPS 使用 Let’s Encrypt 160 小时 `shortlived` 证书和 Certbot 5.4+；定时器每 12 小时续签。[Let’s Encrypt 官方说明](https://letsencrypt.org/2026/03/11/shorter-certs-certbot)要求 IP 证书使用该配置。

### 首次部署

1. 在服务器安装 Git、Docker Engine、Docker Compose plugin、OpenSSL 和 Python 3。
2. 把仓库放在固定私有工作目录，切到 PR 中经过测试的完整 SHA；不要从未经测试的 `main` 临时构建。
3. 首次部署前，由账户持有人通过已审阅的证书流程取得并放置有效的受信任证书。`deploy.sh` 不自动同意新的证书法律条款，也不会在证书缺失时继续构建或切换服务。
4. 在 `infra/tencent/` 执行 `./deploy.sh`。脚本首次运行会无回显收集公网 IPv4、飞书应用凭据、Owner `open_id`、测试群与私聊 `chat_id`，生成 `runtime/.env.runtime` 和备份密钥，权限为 `0600`。
5. 确认 `https://<公网IP>/healthz` 返回版本。随后执行 `./model-login.sh`，分别完成 Codex 与 Hermes 的一次设备 OAuth；凭据只保存在 Docker volume。
6. 执行 `sudo ./install-timers.sh`，再用 `systemctl list-timers 'fitcrew-*'` 确认证书和每日备份任务已启用。
7. 执行 `./bootstrap-owner.sh`。私有目录会生成短期的一次性 `owner-pairing.png`、身份记录和仅用于安全重试的高熵幂等键；二维码只含 HTTPS 地址、配对码与过期时间，App 扫描后再交换凭据。若记录的 Owner 邀请已过期，安全重跑会轮换该私有幂等键并原子替换 Owner 配对工件；不会打印 bearer 凭据或修改运行时密钥。不会打印 token，也不进入 Git。

### 自动回滚门禁

`deploy.sh` 在写入新镜像标签前记录原有的完整不可变 SHA。仅当该旧镜像仍在本机时，脚本才启用自动回滚；首发没有可恢复版本时会明确停止，不会伪称已具备回滚能力。

新服务启动后必须依次通过：PostgreSQL、API 与 Caddy 的 Docker 健康检查；Worker 与 Feishu gateway 的运行状态；API 容器内部 `/healthz`；以及 `https://<公网IP>/healthz` 的严格 TLS 校验。公网检查不会使用 `-k` 或忽略证书错误。

任何镜像切换后的门禁失败都会把运行时镜像标签和部署前 Caddy 配置恢复为原状态，并对数据库、API、Worker、gateway 和 Caddy 执行一次无构建重启，然后以非零状态退出。手动 `rollback.sh` 也会在快照存在时恢复部署前 Caddy 配置；它要求现有受信任证书，并重复数据库/API/Caddy 健康、Worker/gateway 运行、API 回环和严格 HTTPS 门禁，绝不使用 `-k`。自动恢复命令也失败时，只记录通用失败结果；操作员应使用已记录 SHA 运行 `rollback.sh`，并按相同门禁复核。日志不得包含密钥、身份或健康内容。

### 受控邀请第二位用户

1. 飞书 subject 必须来自已核验的飞书开发者控制台或受信任事件来源；不得根据姓名猜测，也不要把 subject 记录到聊天、日志或 Git。准备同样从受信任来源获得的设备公开标识，以及仅含小写字母、数字、`_` 或 `-` 的本地代号。
2. 在 `infra/tencent/` 运行 `./bootstrap-invited-user.sh`。脚本在交互终端中无回显读取 subject 和设备公开标识，只把三项一次性变量传给 API 容器的本次 `docker compose exec -e`，不会写入 `runtime/.env.runtime`，也不会运行 `docker compose config`。
3. API 在邀请成功后、签发配对前，把 Owner 和受邀用户 subject 原子写入 `runtime/owner/feishu-allowed-users`。目录为 `0700`、文件为 `0600`；gateway 仅以只读方式加载该私有列表，并只重启 gateway 使关闭式白名单生效。`FEISHU_ALLOW_ALL_USERS=false` 与 `GATEWAY_ALLOW_ALL_USERS=false` 必须保持不变。
4. 配对 JSON、二维码和仅用于安全重试的高熵幂等键只保存在 `runtime/owner/invitees/<slug>/`，目录 `0700`、文件 `0600`。二维码只含 HTTPS 地址、一次性配对码和 15 分钟过期时间；扫描后由 App 交换短期凭据，不能重复兑换。若记录的邀请已过期，安全重跑会只在该私有目录中原子替换配对工件并轮换高熵幂等键；不会重绑设备、改变 consent 或打印 bearer 凭据。
5. 分别验证两位用户私聊隔离、群聊固定低敏回复及 Owner 原有同步状态不变。二维码只通过已核实收件人的私密渠道交付；未得到明确发送授权时不得发送，也不得粘贴到终端、飞书群、日志或 PR。

### 已有受邀用户的白名单迁移

如果第二位用户是在私有 gateway allowlist 引入之前创建的，在完成本版本部署后、要求该用户测试前，在 `infra/tencent/` 运行 `./reconcile-feishu-allowlist.sh`。该迁移只在 API 容器内使用现有加密、已验证、未撤销且用户状态为 `invited` 或 `active` 的飞书身份重建 `runtime/owner/feishu-allowed-users`，并在成功后只重启 gateway。`FEISHU_ALLOWED_USERS` 只用于检查运行环境格式，绝不是授权来源，因此旧的或被撤销 subject 不会因残留在环境变量中重新获得访问。它不会创建用户、重新配对设备、修改授权，也不会人工猜测姓名或 `open_id`。任何本应有效的身份无法解密或校验时，脚本会关闭式失败且不会写入新的 allowlist；请先排障，不要改为允许所有用户。

### 私人导入与共享专家知识发布

把三份本人有权用于私人分析的 PDF 以以下名称放入 `runtime/private-books/`：`glucose-revolution.pdf`、`sleep-guide.pdf`、`longevity-handbook.pdf`。目录权限保持 `0700`，文件不提交、不公开、不进入 CI。执行 `./import-private-books.sh` 后，正文按页分段并以 AES-GCM 加密；相同哈希重复导入幂等，内容变化产生新版本，检索保留书名与页码。权利状态默认是 `user_provided_private_use_unverified`，不能自动发布到公共知识库。

只有 Owner/编辑者确认这三本书可用于封闭的 BodyOS 共享专家知识后，才在 `infra/tencent/` 执行 `./publish-shared-books.sh`。脚本只认《控糖革命》《百岁人生行动手册》《睡眠优化完全指南：科学与实践》三个已审核标题；缺少任一本就关闭式失败，重复运行幂等，输出只有发布数量。这里的 `public` 表示 BodyOS 用户可检索的共享知识范围，不代表公开 PDF、下载链接、全文网页或 Git 内容。原始文件仍留在私有运行目录，群聊只取得最多三段保留书名与页码的摘录，并继续经过公共回答 DLP。

### 群聊共享知识与主动教练

部署会向已有 `runtime/.env.runtime` 原子补齐缺失的非密钥默认值，但不会覆盖已经设置的值：北京时间每天 09:00 晨间行动、20:30 晚间打卡、周三 12:15 每周专家互动，22:00–08:00 静默。`BODYOS_PROACTIVE_GROUP_ENABLED=false` 可暂停所有主动消息；恢复为 `true` 后，从下一个计划时点继续，不补发静默期或错过的消息。

Worker 每 60 秒检查计划，并保留五分钟的有限时钟漂移窗口；超过窗口不会追补。它用唯一事件键和[飞书消息创建接口](https://open.feishu.cn/document/server-docs/im-v1/message/create?lang=zh-CN)的 `uuid` 做幂等投递；失败最多重试三次，日志只含计数与错误码。晨间和晚间使用固定公共模板；每周互动只使用 `bodyos-public.v2` 与已发布的共享专家知识，模型不可用时退回固定公共问题。群聊的响应式问答仍需 @ 黑客松助手；个人情境、健康数值、诊断、治疗和用药继续引导到 BodyOS 私聊或专业人员。

安全验收只发送不含个人信息的通用问题，例如“先吃蔬菜再吃主食有什么依据？”，并确认回答不含姓名、身份、私聊内容、健康数值或私人书摘。不要为验收生成或上传健康数据，也不要在生产环境手动伪造 Outbox 事件。

### 备份、恢复与回滚

- `./backup.sh` 使用 `pg_dump` 后经 AES-256/PBKDF2 加密，保留 7 天；应用健康字段本身仍是 AES-GCM 密文。
- `./restore-test.sh <绝对备份路径>` 只还原到固定临时库 `bodyos_restore_test`，验证表数量后删除临时库。
- 发布前记录完整 commit SHA。部署脚本会执行自动回滚门禁；手动回滚执行 `ROLLBACK_SHA=<40位SHA> ./rollback.sh`。该脚本先备份，再切回本机已有的不可变镜像，并通过 `/healthz` 才算成功。数据库迁移不自动降级；若变更不向后兼容，先停写并按已验证备份恢复。
- 日志不得出现请求 URI、Header、消息正文、身份、健康值、书摘或 token。排障只记录版本、计数、策略结果与错误码。

## English

### Boundary and architecture

The target is the existing Tokyo Lighthouse (2 vCPU, 4 GB, 60 GB), with no new paid cloud resources. Compose keeps PostgreSQL, the BodyOS API, maintenance worker, Hermes Feishu channel, and Caddy resident. Codex CLI uses ChatGPT OAuth as primary; Hermes `openai-codex` OAuth is fallback only after primary failure. The Moticlaw macOS app remains a configuration surface, not a Linux runtime dependency.

Only ports 80/443 are public; the database, API, and model proxy have no host mapping. Keep 80/443 in the Tencent firewall and restrict port 22 to the management source. Public-IP HTTPS uses a 160-hour Let’s Encrypt `shortlived` certificate with Certbot 5.4+, renewed every 12 hours. The [official Let’s Encrypt instructions](https://letsencrypt.org/2026/03/11/shorter-certs-certbot) require this profile for IP certificates.

### First deployment

1. Install Git, Docker Engine, the Docker Compose plugin, OpenSSL, and Python 3 on the server.
2. Keep the repository in a fixed private directory at the exact tested PR SHA; do not build an untested moving `main`.
3. Before the first deployment, have the account holder obtain and place a valid trusted certificate through a reviewed certificate process. `deploy.sh` does not automatically accept a new certificate agreement and does not build or switch services when the certificate is absent.
4. Run `./deploy.sh` in `infra/tencent/`. On first run it collects the public IPv4, Feishu app credentials, owner `open_id`, test group, and DM `chat_id` without echo, then creates `runtime/.env.runtime` and a backup key with mode `0600`.
5. Confirm `https://<public-IP>/healthz`, then run `./model-login.sh` and complete one device OAuth flow for Codex and Hermes. Credentials remain in Docker volumes.
6. Run `sudo ./install-timers.sh`, then confirm certificate and daily-backup timers with `systemctl list-timers 'fitcrew-*'`.
7. Run `./bootstrap-owner.sh`. The private runtime directory receives a short-lived one-time `owner-pairing.png`, identity record, and high-entropy idempotency key used only for a safe retry. The QR contains only an HTTPS address, pairing code, and expiry; the app exchanges it for credentials after scanning. If the recorded Owner invitation has expired, a safe rerun rotates that private idempotency key and atomically replaces the Owner pairing artifact; it never prints bearer credentials or changes runtime secrets. No token is printed or committed.

### Automatic rollback gate

Before writing a new image tag, `deploy.sh` records the previous full immutable SHA. Automatic rollback is armed only when that previous image is still present locally; a first deployment with no recoverable version stops explicitly instead of claiming rollback coverage.

After startup, the new service set must pass, in order: Docker health checks for PostgreSQL, API, and Caddy; running-state checks for the worker and Feishu gateway; the API container's loopback `/healthz`; and strict TLS verification of `https://<public-IP>/healthz`. The public check never uses `-k` or ignores certificate errors.

If any post-switch gate fails, the script restores the runtime image tag and pre-deployment Caddy configuration, requests a no-build restart of database, API, worker, gateway, and Caddy, then exits non-zero. When the snapshot exists, manual `rollback.sh` also restores that pre-deployment Caddy configuration; it requires an existing trusted certificate and repeats the DB/API/Caddy health, worker/gateway running, API loopback, and strict HTTPS gates without `-k`. If that restore command also fails, it records only a generic failure result; the operator must use the recorded SHA with `rollback.sh` and verify the same gates. Logs must not contain credentials, identities, or health content.

### Controlled invitation of a second user

1. The Feishu subject must come from a verified Feishu developer-console or trusted event source; it must never be guessed from a person’s name or copied to chat, logs, or Git. Prepare a public device identifier from the same trusted source and a local slug containing only lowercase letters, digits, `_`, or `-`.
2. Run `./bootstrap-invited-user.sh` from `infra/tencent/`. In an interactive terminal it reads the subject and public device identifier without echo, passes all three one-time values only to that API container’s `docker compose exec -e`, never writes them to `runtime/.env.runtime`, and never runs `docker compose config`.
3. After the API invitation succeeds and before pairing issuance, it atomically stores the Owner and invitee subjects in `runtime/owner/feishu-allowed-users`. The directory is `0700` and file `0600`; the gateway loads that private list read-only and only gateway restarts so its closed allowlist takes effect. `FEISHU_ALLOW_ALL_USERS=false` and `GATEWAY_ALLOW_ALL_USERS=false` must remain unchanged.
4. The pairing JSON, QR, and high-entropy idempotency key used only for a safe retry remain under `runtime/owner/invitees/<slug>/`, with directory mode `0700` and file mode `0600`. The QR contains only an HTTPS address, one-time pairing code, and 15-minute expiry; the app exchanges it for short-lived provisioning data exactly once. If the recorded invitation has expired, a safe rerun rotates the high-entropy key and atomically replaces only this private pairing artifact; it does not rebind a device, change consent, or print bearer credentials.
5. Verify isolated DMs for both users, the fixed low-sensitivity group reply, and the Owner's unchanged sync status. Deliver the QR only through a verified private channel. Without explicit transmission authorization, do not send it or paste it into a terminal, Feishu group, logs, or a PR.

### Existing invitee allowlist migration

If the second user was created before the private gateway allowlist was introduced, run `./reconcile-feishu-allowlist.sh` from `infra/tencent/` after deploying this version and before asking that existing invitee to test. The migration reconstructs `runtime/owner/feishu-allowed-users` only inside the API container from existing encrypted, verified, non-revoked Feishu identities whose users are `invited` or `active`, then restarts only the gateway after success. `FEISHU_ALLOWED_USERS` is checked only for runtime-environment format; it is never an authorization source, so an old or revoked subject cannot regain access merely by remaining in that environment variable. It does not create a user, re-pair a device, change consent, or manually guess a name or `open_id`. If any expected active identity cannot be decrypted or validated, it fails closed and writes no new allowlist; investigate first and do not switch to allow-all access.

### Private import and shared expert-knowledge publication

Place the three owner-authorized private-analysis PDFs in `runtime/private-books/` as `glucose-revolution.pdf`, `sleep-guide.pdf`, and `longevity-handbook.pdf`. Keep the directory at `0700`; never commit, publish, or send the files to CI. `./import-private-books.sh` chunks by page and AES-GCM encrypts the text. The same hash is idempotent; changed content creates a new version; retrieval retains title/page citations. The default rights state is `user_provided_private_use_unverified`, so a source cannot be auto-published to public knowledge.

Only after the Owner/editor confirms that the three books may be used within the closed BodyOS shared expert-knowledge scope should an operator run `./publish-shared-books.sh` from `infra/tencent/`. The script recognizes only the three reviewed titles *《控糖革命》*, *《百岁人生行动手册》*, and *《睡眠优化完全指南：科学与实践》*. It fails closed if any title is missing, is idempotent on rerun, and prints counts only. Here, `public` means the shared retrieval scope available to BodyOS users; it does not mean a public PDF, download link, full-text webpage, or Git content. Source files remain in the private runtime directory. A group receives at most three title/page-cited excerpts, and the result still passes public-answer DLP.

### Group shared knowledge and proactive coaching

Deployment atomically appends missing non-secret defaults to an existing `runtime/.env.runtime` without overwriting configured values: morning action at 09:00, evening check-in at 20:30, weekly expert interaction on Wednesday at 12:15, and quiet hours from 22:00 to 08:00, all in Asia/Shanghai time. Set `BODYOS_PROACTIVE_GROUP_ENABLED=false` to pause every proactive message. After it returns to `true`, the worker resumes at the next scheduled slot and does not backfill a quiet-hour or missed message.

The worker checks the schedule every 60 seconds with a bounded five-minute clock-drift window; it never backfills after that window. It combines a unique event key with the [Feishu create-message API](https://open.feishu.cn/document/server-docs/im-v1/message/create?lang=zh-CN) `uuid` for idempotent delivery. A failure is retried at most three times; logs contain only counts and error codes. Morning/evening messages use fixed public templates. The weekly interaction uses only `bodyos-public.v2` and published shared expert knowledge, then falls back to a fixed public question if the model is unavailable. Reactive group Q&A still requires mentioning the bot. Personal context, health values, diagnosis, treatment, and medication remain routed to a BodyOS DM or qualified care.

A safe canary asks only a non-personal general question, for example, “Why might eating vegetables before staple carbohydrates help?” Confirm that the response contains no name, identity, DM content, health value, or private excerpt. Do not generate or upload health data for acceptance, and do not manually forge Outbox events in production.

### Backup, restore, and rollback

- `./backup.sh` pipes `pg_dump` through AES-256/PBKDF2 encryption and retains seven days. Application health fields remain AES-GCM ciphertext inside the dump.
- `./restore-test.sh <absolute-backup-path>` restores only into fixed temporary database `bodyos_restore_test`, checks schema cardinality, and removes it.
- Record the full commit SHA before release. The deployment script runs its automatic rollback gate; for a manual rollback, run `ROLLBACK_SHA=<40-char-SHA> ./rollback.sh`. It backs up first, switches to an existing immutable local image, and succeeds only after `/healthz`. Database migrations are not automatically downgraded; for an incompatible change, stop writes and restore a verified backup.
- Logs must not contain request URI, headers, message text, identities, health values, excerpts, or tokens. Troubleshooting records only version, counts, policy results, and error codes.
