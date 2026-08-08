# Tencent Deployment and Rollback / 腾讯云部署与回滚

## 中文

### 边界与架构

目标是现有东京 Lighthouse（2 vCPU、4 GB、60 GB），不创建新的收费云资源。Compose 常驻 PostgreSQL、BodyOS API、维护 Worker、Hermes 飞书通道和 Caddy；Codex CLI 使用 ChatGPT OAuth 为主路由，Hermes `openai-codex` OAuth 只在主路由失败后备用。Moticlaw macOS 应用仍是配置入口，不作为 Linux 常驻依赖。

公网只开放 80/443；数据库、API 和模型代理不映射主机端口。腾讯云防火墙保留 80/443，并把 22 限制到管理来源。公网 IP HTTPS 使用 Let’s Encrypt 160 小时 `shortlived` 证书和 Certbot 5.4+；定时器每 12 小时续签。[Let’s Encrypt 官方说明](https://letsencrypt.org/2026/03/11/shorter-certs-certbot)要求 IP 证书使用该配置。

### 首次部署

1. 在服务器安装 Git、Docker Engine、Docker Compose plugin、OpenSSL 和 Python 3。
2. 把仓库放在固定私有工作目录，切到 PR 中经过测试的完整 SHA；不要从未经测试的 `main` 临时构建。
3. 在 `infra/tencent/` 执行 `./deploy.sh`。脚本首次运行会无回显收集公网 IPv4、飞书应用凭据、Owner `open_id`、测试群与私聊 `chat_id`，生成 `runtime/.env.runtime` 和备份密钥，权限为 `0600`。
4. 确认 `https://<公网IP>/healthz` 返回版本。随后执行 `./model-login.sh`，分别完成 Codex 与 Hermes 的一次设备 OAuth；凭据只保存在 Docker volume。
5. 执行 `sudo ./install-timers.sh`，再用 `systemctl list-timers 'fitcrew-*'` 确认证书和每日备份任务已启用。
6. 执行 `./bootstrap-owner.sh`。私有目录会生成一次性 `owner-pairing.png` 与身份记录，不打印 token，也不进入 Git。

### 受控邀请第二位用户

1. 先备份 `runtime/.env.runtime`，再用无回显输入读取受邀用户的飞书 `open_id`、设备公开标识和本地代号。把 `open_id` 幂等追加到 `FEISHU_ALLOWED_USERS`，并临时写入 `BODYOS_INVITEE_FEISHU_SUBJECT`、`BODYOS_INVITEE_DEVICE_PUBLIC_ID`、`BODYOS_INVITEE_SLUG`。运行文件必须继续保持 `0600`，`FEISHU_ALLOW_ALL_USERS=false` 与 `GATEWAY_ALLOW_ALL_USERS=false` 不得改变。
2. 用 `docker compose --env-file runtime/.env.runtime -f compose.yaml up -d --force-recreate api gateway` 让 API 获取一次性邀请变量，并让 gateway 重新渲染关闭式白名单。不要使用 `docker compose config`，避免把环境值打印到终端。
3. 执行 `docker compose --env-file runtime/.env.runtime -f compose.yaml exec -T api python /app/scripts/bootstrap_invited_user.py`。唯一成功输出应为 `Invited user pairing stored outside Git.`；配对 JSON 和二维码只保存在 `runtime/owner/invitees/<slug>/`，目录 `0700`、文件 `0600`。
4. 从运行文件删除三个 `BODYOS_INVITEE_*` 临时变量，保留双用户 `FEISHU_ALLOWED_USERS`，再次只重建 `api gateway`。分别验证两位用户私聊隔离、群聊固定低敏回复及 Chris 原有同步状态不变。
5. 二维码只通过已核实收件人的私密渠道交付；未得到明确发送授权时不得发送，也不得粘贴到终端、飞书群、日志或 PR。

### 私人书籍

把三份本人有权用于私人分析的 PDF 以以下名称放入 `runtime/private-books/`：`glucose-revolution.pdf`、`sleep-guide.pdf`、`longevity-handbook.pdf`。目录权限保持 `0700`，文件不提交、不公开、不进入 CI。执行 `./import-private-books.sh` 后，正文按页分段并以 AES-GCM 加密；相同哈希重复导入幂等，内容变化产生新版本，检索保留书名与页码。权利状态默认是 `user_provided_private_use_unverified`，不能自动发布到公共知识库。

### 备份、恢复与回滚

- `./backup.sh` 使用 `pg_dump` 后经 AES-256/PBKDF2 加密，保留 7 天；应用健康字段本身仍是 AES-GCM 密文。
- `./restore-test.sh <绝对备份路径>` 只还原到固定临时库 `bodyos_restore_test`，验证表数量后删除临时库。
- 发布前记录完整 commit SHA。回滚执行 `ROLLBACK_SHA=<40位SHA> ./rollback.sh`；脚本先备份，再切回本机已有的不可变镜像，并通过 `/healthz` 才算成功。数据库迁移不自动降级；若变更不向后兼容，先停写并按已验证备份恢复。
- 日志不得出现请求 URI、Header、消息正文、身份、健康值、书摘或 token。排障只记录版本、计数、策略结果与错误码。

## English

### Boundary and architecture

The target is the existing Tokyo Lighthouse (2 vCPU, 4 GB, 60 GB), with no new paid cloud resources. Compose keeps PostgreSQL, the BodyOS API, maintenance worker, Hermes Feishu channel, and Caddy resident. Codex CLI uses ChatGPT OAuth as primary; Hermes `openai-codex` OAuth is fallback only after primary failure. The Moticlaw macOS app remains a configuration surface, not a Linux runtime dependency.

Only ports 80/443 are public; the database, API, and model proxy have no host mapping. Keep 80/443 in the Tencent firewall and restrict port 22 to the management source. Public-IP HTTPS uses a 160-hour Let’s Encrypt `shortlived` certificate with Certbot 5.4+, renewed every 12 hours. The [official Let’s Encrypt instructions](https://letsencrypt.org/2026/03/11/shorter-certs-certbot) require this profile for IP certificates.

### First deployment

1. Install Git, Docker Engine, the Docker Compose plugin, OpenSSL, and Python 3 on the server.
2. Keep the repository in a fixed private directory at the exact tested PR SHA; do not build an untested moving `main`.
3. Run `./deploy.sh` in `infra/tencent/`. On first run it collects the public IPv4, Feishu app credentials, owner `open_id`, test group, and DM `chat_id` without echo, then creates `runtime/.env.runtime` and a backup key with mode `0600`.
4. Confirm `https://<public-IP>/healthz`, then run `./model-login.sh` and complete one device OAuth flow for Codex and Hermes. Credentials remain in Docker volumes.
5. Run `sudo ./install-timers.sh`, then confirm certificate and daily-backup timers with `systemctl list-timers 'fitcrew-*'`.
6. Run `./bootstrap-owner.sh`. The private runtime directory receives a one-time `owner-pairing.png` and identity record; no token is printed or committed.

### Controlled invitation of a second user

1. Back up `runtime/.env.runtime`, then collect the invitee's Feishu `open_id`, public device identifier, and local slug with no-echo input. Idempotently append the `open_id` to `FEISHU_ALLOWED_USERS` and temporarily add `BODYOS_INVITEE_FEISHU_SUBJECT`, `BODYOS_INVITEE_DEVICE_PUBLIC_ID`, and `BODYOS_INVITEE_SLUG`. Keep the runtime file at `0600`; never change `FEISHU_ALLOW_ALL_USERS=false` or `GATEWAY_ALLOW_ALL_USERS=false`.
2. Run `docker compose --env-file runtime/.env.runtime -f compose.yaml up -d --force-recreate api gateway` so the API receives the one-time invitation variables and the gateway rerenders its closed allowlist. Do not run `docker compose config`, which can print environment values.
3. Run `docker compose --env-file runtime/.env.runtime -f compose.yaml exec -T api python /app/scripts/bootstrap_invited_user.py`. Its only success output is `Invited user pairing stored outside Git.` The pairing JSON and QR remain only under `runtime/owner/invitees/<slug>/`, with directory mode `0700` and file mode `0600`.
4. Remove the three temporary `BODYOS_INVITEE_*` entries, keep both users in `FEISHU_ALLOWED_USERS`, and recreate only `api gateway` again. Verify isolated DMs for both users, the fixed low-sensitivity group reply, and Chris's unchanged sync status.
5. Deliver the QR only through a verified private channel. Without explicit transmission authorization, do not send it or paste it into a terminal, Feishu group, logs, or a PR.

### Private books

Place the three owner-authorized private-analysis PDFs in `runtime/private-books/` as `glucose-revolution.pdf`, `sleep-guide.pdf`, and `longevity-handbook.pdf`. Keep the directory at `0700`; never commit, publish, or send the files to CI. `./import-private-books.sh` chunks by page and AES-GCM encrypts the text. The same hash is idempotent; changed content creates a new version; retrieval retains title/page citations. The default rights state is `user_provided_private_use_unverified`, so a source cannot be auto-published to public knowledge.

### Backup, restore, and rollback

- `./backup.sh` pipes `pg_dump` through AES-256/PBKDF2 encryption and retains seven days. Application health fields remain AES-GCM ciphertext inside the dump.
- `./restore-test.sh <absolute-backup-path>` restores only into fixed temporary database `bodyos_restore_test`, checks schema cardinality, and removes it.
- Record the full commit SHA before release. Run `ROLLBACK_SHA=<40-char-SHA> ./rollback.sh`; it backs up first, switches to an existing immutable local image, and succeeds only after `/healthz`. Database migrations are not automatically downgraded; for an incompatible change, stop writes and restore a verified backup.
- Logs must not contain request URI, headers, message text, identities, health values, excerpts, or tokens. Troubleshooting records only version, counts, policy results, and error codes.
