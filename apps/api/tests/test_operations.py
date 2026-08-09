import importlib.util
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError

ROOT = Path(__file__).parents[3]


def test_tencent_compose_has_owner_alpha_hardening() -> None:
    compose = (ROOT / "infra/tencent/compose.yaml").read_text()

    for service in ("db:", "api:", "worker:", "gateway:", "caddy:"):
        assert service in compose
    assert "read_only: true" in compose
    assert "no-new-privileges:true" in compose
    assert "NET_BIND_SERVICE" in compose
    assert "mem_limit:" in compose
    assert "healthcheck:" in compose
    assert '"8000:8000"' not in compose
    assert "/tmp:size=64m,mode=1777" in compose

    workflow = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "--wait --wait-timeout 120 db api caddy" in workflow
    assert "curl --fail --silent --show-error http://127.0.0.1/healthz" in workflow
    assert "xcodebuild test" in workflow
    assert "platform=iOS Simulator,name=iPhone 16 Pro" in workflow


def test_deploy_rolls_back_the_full_service_set_when_a_post_deploy_gate_fails() -> None:
    deploy = (ROOT / "infra/tencent/deploy.sh").read_text()

    assert "PREVIOUS_IMAGE_TAG=" in deploy
    assert "rollback_on_failure" in deploy
    assert "trap 'rollback_on_failure $? '" not in deploy
    assert "trap 'rollback_on_failure $?" in deploy
    assert (
        "FITCREW_IMAGE_TAG=\"$PREVIOUS_IMAGE_TAG\" "
        "$COMPOSE up -d --no-build db api worker gateway caddy"
    ) in deploy
    assert "wait_for_service db health" in deploy
    assert "wait_for_service api health" in deploy
    assert "wait_for_service worker running" in deploy
    assert "wait_for_service gateway running" in deploy
    assert "wait_for_service caddy health" in deploy
    assert "https://${PUBLIC_HOST}/healthz" in deploy
    assert "--proto '=https'" in deploy
    assert "-k" not in deploy
    assert "--agree-tos" not in deploy
    assert "PREVIOUS_CADDYFILE=" in deploy
    assert 'install -m 0644 "$PREVIOUS_CADDYFILE" "$RUNTIME/Caddyfile"' in deploy


def test_operations_bundle_has_tls_backup_restore_and_sha_rollback() -> None:
    expected = [
        "Dockerfile.api",
        "Caddyfile.http",
        "Caddyfile.https",
        "deploy.sh",
        "backup.sh",
        "restore-test.sh",
        "rollback.sh",
        "renew-certificate.sh",
    ]
    for name in expected:
        assert (ROOT / "infra/tencent" / name).is_file(), name

    rollback = (ROOT / "infra/tencent/rollback.sh").read_text()
    assert "ROLLBACK_SHA" in rollback
    assert "git checkout" not in rollback
    assert "PREVIOUS_CADDYFILE" in rollback
    assert 'install -m 0644 "$PREVIOUS_CADDYFILE" "$RUNTIME/Caddyfile"' in rollback
    assert "$COMPOSE up -d --no-build db api worker gateway caddy" in rollback
    assert "wait_for_service db health" in rollback
    assert "wait_for_service api health" in rollback
    assert "wait_for_service worker running" in rollback
    assert "wait_for_service gateway running" in rollback
    assert "wait_for_service caddy health" in rollback
    assert "wait_for_api_loopback" in rollback
    assert "wait_for_public_https" in rollback
    assert "--proto '=https'" in rollback
    assert "-k" not in rollback
    assert '"$RUNTIME/tls/fullchain.pem"' in rollback
    assert '"$RUNTIME/tls/privkey.pem"' in rollback


def test_operations_document_rolls_back_failed_deployments_without_accepting_new_terms() -> None:
    document = (ROOT / "docs/operations/deployment-and-rollback.md").read_text()

    assert "自动回滚门禁" in document
    assert "automatic rollback gate" in document
    assert "不自动同意新的证书法律条款" in document
    assert "does not automatically accept a new certificate agreement" in document


def test_tls_sync_uses_host_files_without_a_privileged_export_mount() -> None:
    sync = (ROOT / "infra/tencent/sync-certificate.sh").read_text()
    compose = (ROOT / "infra/tencent/compose.yaml").read_text()
    certbot_service = compose.split("  certbot:\n", maxsplit=1)[1].split(
        "\nvolumes:\n", maxsplit=1
    )[0]

    assert 'source_dir="$HERE/runtime/letsencrypt/live/$PUBLIC_HOST"' in sync
    assert "$COMPOSE" not in sync
    assert "/export" not in certbot_service
    assert "CHOWN" not in certbot_service
    assert "FOWNER" not in certbot_service


def test_certificate_renewal_restarts_caddy_when_admin_api_is_disabled() -> None:
    renewal = (ROOT / "infra/tencent/renew-certificate.sh").read_text()
    caddyfile = (ROOT / "infra/tencent/Caddyfile.https").read_text()

    assert "admin off" in caddyfile
    assert "$COMPOSE restart caddy" in renewal
    assert "caddy reload" not in renewal


def test_model_login_uses_the_installed_hermes_auth_cli() -> None:
    login = (ROOT / "infra/tencent/model-login.sh").read_text()

    assert "--cap-add CHOWN" in login
    assert "--cap-add FOWNER" in login
    assert "chown -R 10001:10001 /home/bodyos/.codex /home/bodyos/.hermes" in login
    assert "hermes auth add openai-codex" in login
    assert "hermes login openai-codex" not in login


def test_examples_do_not_contain_committable_secrets() -> None:
    example = (ROOT / "infra/tencent/env.example").read_text()
    assert "sk-" not in example
    assert "cli_" not in example
    assert "CHANGE_ME" not in example
    assert "BODYOS_ENCRYPTION_KEY=" not in example


def test_alembic_uses_the_production_database_environment() -> None:
    migration_environment = (ROOT / "apps/api/migrations/env.py").read_text()
    assert 'os.environ.get("BODYOS_DATABASE_URL")' in migration_environment
    assert 'config.set_main_option("sqlalchemy.url"' in migration_environment


def test_invited_user_bootstrap_never_prints_pairing_secrets() -> None:
    script_path = ROOT / "scripts/bootstrap_invited_user.py"

    assert script_path.is_file()
    source = script_path.read_text()
    assert "print(payload)" not in source
    assert "mode=0o700" in source
    assert "pairing-idempotency-key" in source
    assert "rotate_idempotency_key" in source
    assert "pairing_expired" in source
    assert "os.replace" in source
    assert "secrets.token_urlsafe(32)" in source
    assert "idempotency_key" in source
    assert "os.chmod(temporary, 0o600)" in source
    assert 'print("Invited user pairing stored outside Git.")' in source


def test_owner_bootstrap_uses_private_idempotency_key_and_no_direct_secrets() -> None:
    source = (ROOT / "scripts/bootstrap_owner.py").read_text()

    assert "owner-pairing-idempotency-key" in source
    assert "secrets.token_urlsafe(32)" in source
    assert '"idempotency_key": idempotency_key' in source
    assert "issue_owner_pairing_with_expiry_rotation" in source
    assert "rotate_idempotency_key" in source
    assert "pairing_expired" in source
    assert "os.replace" in source
    assert "print(payload)" not in source


def test_expired_owner_pairing_retries_once_with_a_rotated_private_key(
    tmp_path: Path, monkeypatch
) -> None:
    script_path = ROOT / "scripts/bootstrap_owner.py"
    spec = importlib.util.spec_from_file_location("bootstrap_owner_retry", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    record = tmp_path / "owner-bootstrap.json"
    record.write_text(
        json.dumps({"expires_at": (datetime.now(UTC) - timedelta(seconds=1)).isoformat()}),
        encoding="utf-8",
    )
    key_path = tmp_path / "owner-pairing-idempotency-key"
    key_path.write_text("old-key", encoding="utf-8")
    calls: list[dict] = []

    def fake_post(payload: dict, owner_token: str) -> dict:
        del owner_token
        calls.append(payload.copy())
        if len(calls) == 1:
            raise HTTPError("http://127.0.0.1:8000", 409, "expired", {}, None)
        return {"pairing_url": "fitcrew-health://configure?payload=opaque", "expires_at": "future"}

    monkeypatch.setattr(module, "post", fake_post)

    result = module.issue_owner_pairing_with_expiry_rotation(
        output_dir=tmp_path,
        owner_token="owner-token",
        subject="ou_owner",
        idempotency_key="old-key",
    )

    assert result["pairing_url"].startswith("fitcrew-health://")
    assert len(calls) == 2
    assert calls[0]["idempotency_key"] == "old-key"
    assert calls[1]["idempotency_key"] != "old-key"
    assert key_path.read_text(encoding="utf-8") == calls[1]["idempotency_key"]
    assert key_path.stat().st_mode & 0o777 == 0o600


def test_expired_invited_pairing_rotates_its_private_idempotency_key_atomically(
    tmp_path: Path,
) -> None:
    script_path = ROOT / "scripts/bootstrap_invited_user.py"
    spec = importlib.util.spec_from_file_location("bootstrap_invited_user", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    record = tmp_path / "pairing.json"
    record.write_text(
        json.dumps({"expires_at": (datetime.now(UTC) - timedelta(seconds=1)).isoformat()}),
        encoding="utf-8",
    )
    key_path = tmp_path / "pairing-idempotency-key"
    key_path.write_text("old-key", encoding="utf-8")

    rotated = module.rotate_idempotency_key(key_path)

    assert module.pairing_expired(record) is True
    assert rotated != "old-key"
    assert key_path.read_text(encoding="utf-8") == rotated
    assert key_path.stat().st_mode & 0o777 == 0o600


def test_expired_invited_pairing_retries_once_with_a_rotated_key(
    tmp_path: Path, monkeypatch
) -> None:
    script_path = ROOT / "scripts/bootstrap_invited_user.py"
    spec = importlib.util.spec_from_file_location("bootstrap_invited_user_retry", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    record = tmp_path / "pairing.json"
    record.write_text(
        json.dumps({"expires_at": (datetime.now(UTC) - timedelta(seconds=1)).isoformat()}),
        encoding="utf-8",
    )
    key_path = tmp_path / "pairing-idempotency-key"
    key_path.write_text("old-key", encoding="utf-8")
    calls: list[dict] = []

    def fake_post(path: str, payload: dict, owner_token: str) -> dict:
        del path, owner_token
        calls.append(payload.copy())
        if len(calls) == 1:
            raise HTTPError("http://127.0.0.1:8000", 409, "expired", {}, None)
        return {"pairing_url": "fitcrew-health://configure?payload=opaque", "expires_at": "future"}

    monkeypatch.setattr(module, "post", fake_post)

    result = module.issue_pairing_with_expiry_rotation(
        output_dir=tmp_path,
        owner_token="owner-token",
        subject="ou_invited",
        device_public_id="invited-iphone",
        idempotency_key="old-key",
    )

    assert result["pairing_url"].startswith("fitcrew-health://")
    assert len(calls) == 2
    assert calls[0]["idempotency_key"] == "old-key"
    assert calls[1]["idempotency_key"] != "old-key"
    assert key_path.read_text(encoding="utf-8") == calls[1]["idempotency_key"]


def test_invited_user_runtime_mount_is_explicitly_private_and_writable() -> None:
    compose = (ROOT / "infra/tencent/compose.yaml").read_text()

    assert "./runtime/owner:/owner-runtime:rw" in compose
