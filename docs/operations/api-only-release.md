# API 独立发布 / API-only release

## 中文

这是现有服务器的操作流程，尚未执行生产升级。它不代表小程序已上传或提审。发布前必须确认服务器实际使用本仓库的 Compose 项目、数据库及运行时路径；若实际结构不同，先修订流程。保留 Moticlaw 唯一飞书入口、现有身份、加密密钥、数据库与 HealthKit 同步。不得运行旧 `deploy.sh` / `rollback.sh`，也不得自动降级数据库。

连接功能新增 `0005_device_only_pairing`。回退旧 API 前必须停用未兑换的设备连接，避免旧逻辑修改健康授权；详见 [连接与回滚要求](../release/2026-09-09-wechat-ios-connection.md)。

### 进入发布前

1. 通过已有受信任 SSH 配置或账户持有人的控制台登录。SSH 验证失败时报告所用用户、主机和错误码；不改主机校验、不猜凭据。
2. 在固定私有 checkout 中选定 CI 通过的完整 commit SHA，确认工作区干净。记录 Compose 项目名和运行中的 API 镜像 ID，以及其他容器的 ID、镜像、启动时间。仅输出这些元数据；不要输出完整 `docker inspect` 或 `docker compose config`，二者可能含凭据。
3. 确认现有数据库健康、旧 API 镜像仍在本机、TLS 与反向代理正常、磁盘够用。备份当前私有 `.env.runtime`，保留所有身份 pepper、加密密钥与令牌。不要重新生成运行时环境。
4. 正式微信登录需要实际生产 AppID、AppSecret、`BODYOS_PUBLIC_AUTH_ENABLED=true`、`BODYOS_PUBLIC_BASE_URL=https://实际业务域名`。域名必须与平台配置一致；测试号和 IP 健康检查不是正式提审凭据。AI 另需已落实的服务商、告知及资格，不能仅打开开关就宣称可上线。秘密值只在服务器的私有配置中输入。
5. 审阅当前数据库 revision 到目标 revision 的迁移，并在隔离环境验证旧 API 能读取升级后的数据库。`0004_product_records` 的降级会删除产品记录，禁止作为回滚手段。旧程序启动脚本可能因不认识新 revision 而失败，必须验证后才把旧镜像作为可恢复目标。

### 备份与切换

下面命令在 Bash、仓库根目录执行。`candidate` 必须对应已核验 CI 的提交；命令不会替你验证平台配置。只在前述前置项满足后执行切换段，不要把整页无条件批量运行。

```bash
set -euo pipefail
umask 077
test -z "$(git status --porcelain)"
candidate=$(git rev-parse HEAD)
compose=(docker compose --env-file infra/tencent/runtime/.env.runtime -f infra/tencent/compose.yaml)
test -n "$("${compose[@]}" ps -q api)"
test -n "$("${compose[@]}" ps -q db)"
mkdir -p infra/tencent/runtime/release-evidence
evidence="infra/tencent/runtime/release-evidence/$candidate"
mkdir -p "$evidence"
cp -p infra/tencent/runtime/.env.runtime "$evidence/env.before"
docker ps -aq | xargs -r docker inspect --format '{{.Id}} {{.Name}} {{.Image}} {{.State.StartedAt}}' > "$evidence/containers.before"
"${compose[@]}" exec -T api alembic current > "$evidence/migration.before"
bash infra/tencent/backup.sh
backup=$(find "$PWD/infra/tencent/runtime/backups" -name 'bodyos-*.sql.enc' -print | sort | tail -n 1)
test -n "$backup"
bash infra/tencent/restore-test.sh "$backup"
FITCREW_API_IMAGE_TAG="$candidate" "${compose[@]}" build api
```

确认备份实际恢复通过，记录上述备份路径，再进入切换。API 入口启动时运行 `alembic upgrade head`；此步骤会迁移生产数据库。

```bash
python3 infra/tencent/set-runtime-image.py --service api --file infra/tencent/runtime/.env.runtime "$candidate"
"${compose[@]}" up -d --no-deps --no-build --wait --wait-timeout 120 api
"${compose[@]}" exec -T api alembic current > "$evidence/migration.after"
"${compose[@]}" exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=5)"
docker ps -aq | xargs -r docker inspect --format '{{.Id}} {{.Name}} {{.Image}} {{.State.StartedAt}}' > "$evidence/containers.after"
```

核对所有非 API 容器的 ID、镜像、启动时间未变，并确认未新增旧飞书 gateway。严格 TLS 检查实际业务域名 `/healthz`，通过实际微信登录检查 `/v3/state`、记录保存/重登读取、隐私同意、导出、删除及用户隔离。不要把真实健康内容、令牌或环境文件放入证据报告。仅有健康检查不足以判定发布完成。

### 失败后

切换前失败：保持现有服务运行，修复后从失败步骤继续。切换后失败：先记录失败阶段、目标 SHA、API 健康和迁移 revision；不要调用整套回滚、删除 volume 或降级 `0004`。仅在旧 API 与当前 schema 的兼容性已经验证时，恢复旧 API 镜像的独立 pin 并只重启 API。若不能确认兼容性，保持数据库不变，修复当前 API 或制定经核验的恢复方案；不能将历史备份直接覆盖新写入数据。

真正卡住时报告：已经完成的具体产物与验证、失败命令的非敏感摘要、是否改变了生产状态、缺少的唯一必要访问/配置、恢复点与下一步。不以本地测试、CI、测试号二维码或 `/healthz` 冒充平台提审成功；最后仍需正式版本号、提交时间及平台审核状态证据。

## English

Device connection adds `0005_device_only_pairing`. Invalidate unused device-only invitations before reverting to an older API to prevent legacy consent replacement; see [connection and rollback requirements](../release/2026-09-09-wechat-ios-connection.md).

This is an operational procedure for the existing server; no production upgrade has been performed. It does not mean the Mini Program has been uploaded or submitted. First verify that the actual server uses this repository's Compose project, database, and runtime paths; revise the procedure if it differs. Preserve Moticlaw as the sole Feishu ingress, existing identities, encryption keys, database, and HealthKit ingestion. Do not run legacy `deploy.sh` / `rollback.sh` or automatically downgrade the database.

### Before release

1. Use trusted SSH configuration or the account holder's console. If authentication fails, report the user, host, and error code without weakening host verification or guessing credentials.
2. Select the full SHA with passing CI in a clean private checkout. Record the Compose project, running API image ID, and other containers' IDs, images, and start times. Do not print unrestricted `docker inspect` or `docker compose config`, which can expose credentials.
3. Verify database health, the previous local API image, TLS, proxy, and disk space. Privately back up `.env.runtime`, preserving identity pepper, encryption keys, and tokens. Do not regenerate it.
4. Production WeChat authentication requires the real production AppID, AppSecret, `BODYOS_PUBLIC_AUTH_ENABLED=true`, and an HTTPS `BODYOS_PUBLIC_BASE_URL` matching the platform domain configuration. A sandbox AppID or IP health endpoint is not submission evidence. AI also requires an established provider, disclosure, and eligibility; a feature toggle is insufficient. Enter secrets only in private server configuration.
5. Review migrations from the actual revision and test old API compatibility against the upgraded schema in isolation. Downgrading `0004_product_records` deletes product records and must not serve as rollback. An old startup script may reject an unknown revision; verify it before treating that image as recoverable.

### Backup and switch

Run the shared Bash commands above from the repository root only after their prerequisites pass. `candidate` must identify the verified CI commit. The first block records private metadata, saves the existing environment, encrypts a database backup, restores it into the disposable test database, and builds only the API image. Record the restored backup path. The second block pins the API independently and recreates only API with `--no-deps --no-build`; its startup entry point runs production migrations with `alembic upgrade head`.

Compare every non-API container's ID, image, and start time, and confirm that no legacy Feishu gateway was introduced. Verify the actual business domain with strict TLS, then real WeChat login, `/v3/state`, record persistence after login, consent, export, deletion, and user isolation. Do not put real health content, tokens, or environment files in reports. Health checks alone do not establish release completion.

### Failure handling

Before switching, leave existing services running and resume from the failed step after fixing it. After switching, record the failed stage, target SHA, API health, and migration revision. Never invoke full-stack rollback, delete volumes, or downgrade `0004`. Only if the old API has verified compatibility with the current schema may its independent image pin be restored and only API restarted. Otherwise preserve the database and fix the current API or prepare a verified recovery procedure; never blindly overwrite newer data with an old backup.

When genuinely blocked, report concrete completed artifacts and checks, a non-sensitive failure summary, whether production changed, the necessary missing access/configuration, the recovery point, and next action. Local tests, CI, sandbox QR codes, and `/healthz` are not formal submission evidence. Completion still requires the formal version, submission time, and platform review status.
