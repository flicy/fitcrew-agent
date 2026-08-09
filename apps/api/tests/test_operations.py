from pathlib import Path

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
    assert "secrets.token_urlsafe(32)" in source
    assert "idempotency_key" in source
    assert "os.chmod(record, 0o600)" in source
    assert "os.chmod(qr_path, 0o600)" in source
    assert 'print("Invited user pairing stored outside Git.")' in source


def test_invited_user_runtime_mount_is_explicitly_private_and_writable() -> None:
    compose = (ROOT / "infra/tencent/compose.yaml").read_text()

    assert "./runtime/owner:/owner-runtime:rw" in compose
