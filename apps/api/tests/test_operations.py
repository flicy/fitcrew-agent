import importlib.util
import json
import os
import shlex
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError

import pytest
from bodyos_api.models import IdentityBinding, User

ROOT = Path(__file__).parents[3]


def _load_reconciliation_module(name: str):
    script_path = ROOT / "scripts/reconcile_feishu_allowlist.py"
    spec = importlib.util.spec_from_file_location(name, script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _add_feishu_identity(
    session, cipher, *, binding_id: str, user_id: str, status: str, subject: str, revoked: bool
) -> None:
    user = User(fitcrew_user_id=user_id, status=status)
    session.add(user)
    identity = IdentityBinding(
        id=binding_id,
        fitcrew_user_id=user_id,
        provider="feishu",
        subject_hash=f"hash-{binding_id}",
        encrypted_subject=b"",
        verified_at=datetime.now(UTC),
        revoked_at=datetime.now(UTC) if revoked else None,
    )
    session.add(identity)
    encrypted = cipher.encrypt_json({"subject": subject}, aad=f"identity:{binding_id}")
    identity.encrypted_subject = encrypted.nonce + encrypted.ciphertext
    session.flush()


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
    assert '["bodyos-jobs", "loop", "--interval-seconds", "60"]' in compose
    worker_service = compose.split("  worker:\n", maxsplit=1)[1].split(
        "\n  gateway:\n", maxsplit=1
    )[0]
    assert "codex_auth:/home/bodyos/.codex" in worker_service
    assert "hermes_home:/home/bodyos/.hermes" in worker_service
    jobs_source = (ROOT / "apps/api/bodyos_api/jobs.py").read_text()
    assert "time.sleep(max(30, args.interval_seconds))" in jobs_source

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
    assert "BODYOS_PROACTIVE_GROUP_ENABLED" in example
    assert "BODYOS_GROUP_TIMEZONE" in example


def test_deploy_atomically_adds_only_missing_non_secret_group_defaults() -> None:
    generator = (ROOT / "infra/tencent/generate-runtime-env.py").read_text()
    deploy = (ROOT / "infra/tencent/deploy.sh").read_text()

    for name in (
        "BODYOS_PROACTIVE_GROUP_ENABLED",
        "BODYOS_GROUP_TIMEZONE",
        "BODYOS_GROUP_MORNING_TIME",
        "BODYOS_GROUP_EVENING_TIME",
        "BODYOS_GROUP_WEEKLY_WEEKDAY",
        "BODYOS_GROUP_WEEKLY_TIME",
        "BODYOS_GROUP_QUIET_START",
        "BODYOS_GROUP_QUIET_END",
    ):
        assert name in generator
    assert "os.replace" in generator
    assert "--append-defaults" in generator
    assert "generate-runtime-env.py --append-defaults" in deploy


def test_shared_book_publication_command_is_content_free_and_private_to_the_api() -> None:
    python_script = ROOT / "scripts/publish_shared_books.py"
    wrapper = ROOT / "infra/tencent/publish-shared-books.sh"

    assert python_script.is_file()
    assert wrapper.is_file()
    assert wrapper.stat().st_mode & 0o111
    script_source = python_script.read_text()
    wrapper_source = wrapper.read_text()
    assert "published_count" in script_source
    assert "already_published_count" in script_source
    assert "excerpt" not in script_source
    assert "content_ciphertext" not in script_source
    assert "exec -T api python scripts/publish_shared_books.py" in wrapper_source
    assert "bootstrap" not in wrapper_source


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


def _load_invited_bootstrap_module(name: str):
    script_path = ROOT / "scripts/bootstrap_invited_user.py"
    spec = importlib.util.spec_from_file_location(name, script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_invited_bootstrap_atomically_preserves_owner_and_adds_subject_to_private_allowlist(
    tmp_path: Path,
) -> None:
    module = _load_invited_bootstrap_module("bootstrap_invited_user_allowlist")
    owner_runtime = tmp_path / "owner-runtime"
    allowlist = owner_runtime / "feishu-allowed-users"

    allowed = module.store_allowed_users(
        allowlist,
        initial_allowed_users="ou_owner",
        invited_subject="ou_invited",
    )

    assert allowed == ("ou_owner", "ou_invited")
    assert allowlist.read_text(encoding="utf-8") == "ou_owner\nou_invited\n"
    assert allowlist.stat().st_mode & 0o777 == 0o600
    assert owner_runtime.stat().st_mode & 0o777 == 0o700

    repeated = module.store_allowed_users(
        allowlist,
        initial_allowed_users="ou_owner",
        invited_subject="ou_invited",
    )

    assert repeated == allowed
    assert allowlist.read_text(encoding="utf-8") == "ou_owner\nou_invited\n"

    expanded = module.store_allowed_users(
        allowlist,
        initial_allowed_users="ou_owner",
        invited_subject="ou_second_invited",
    )

    assert expanded == ("ou_owner", "ou_invited", "ou_second_invited")
    assert allowlist.read_text(encoding="utf-8") == (
        "ou_owner\nou_invited\nou_second_invited\n"
    )


def test_invited_bootstrap_rejects_newline_subject_before_writing_allowlist(tmp_path: Path) -> None:
    module = _load_invited_bootstrap_module("bootstrap_invited_user_invalid_subject")
    allowlist = tmp_path / "owner-runtime" / "feishu-allowed-users"

    import pytest

    with pytest.raises(ValueError, match="newline"):
        module.store_allowed_users(
            allowlist,
            initial_allowed_users="ou_owner",
            invited_subject="ou_invalid\nnext",
        )

    assert not allowlist.exists()


def test_invited_bootstrap_preflights_invalid_subject_before_any_api_call_or_write(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_invited_bootstrap_module("bootstrap_invited_user_preflight_subject")
    api_calls: list[tuple[str, dict]] = []
    writes: list[Path] = []
    monkeypatch.setattr(module, "OWNER_RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(
        module,
        "post",
        lambda path, payload, owner_token: api_calls.append((path, payload)) or {},
    )
    monkeypatch.setattr(
        module,
        "atomic_write_text",
        lambda path, value: writes.append(path),
    )
    monkeypatch.setenv("BODYOS_OWNER_TOKEN", "owner-token")
    monkeypatch.setenv("BODYOS_INVITEE_FEISHU_SUBJECT", "ou_invalid\nnext")
    monkeypatch.setenv("BODYOS_INVITEE_DEVICE_PUBLIC_ID", "device-public-id")
    monkeypatch.setenv("BODYOS_INVITEE_SLUG", "second_user")
    monkeypatch.setenv("FEISHU_ALLOWED_USERS", "ou_owner")

    import pytest

    with pytest.raises(ValueError, match="newline"):
        module.main()

    assert api_calls == []
    assert writes == []
    assert not (tmp_path / "invitees").exists()


def test_invited_bootstrap_preflights_bad_initial_allowlist_before_any_api_call_or_write(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_invited_bootstrap_module("bootstrap_invited_user_preflight_allowlist")
    api_calls: list[tuple[str, dict]] = []
    writes: list[Path] = []
    monkeypatch.setattr(module, "OWNER_RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(
        module,
        "post",
        lambda path, payload, owner_token: api_calls.append((path, payload)) or {},
    )
    monkeypatch.setattr(
        module,
        "atomic_write_text",
        lambda path, value: writes.append(path),
    )
    monkeypatch.setenv("BODYOS_OWNER_TOKEN", "owner-token")
    monkeypatch.setenv("BODYOS_INVITEE_FEISHU_SUBJECT", "ou_invited")
    monkeypatch.setenv("BODYOS_INVITEE_DEVICE_PUBLIC_ID", "device-public-id")
    monkeypatch.setenv("BODYOS_INVITEE_SLUG", "second_user")
    monkeypatch.setenv("FEISHU_ALLOWED_USERS", "ou_owner,bad user")

    import pytest

    with pytest.raises(ValueError, match="whitespace"):
        module.main()

    assert api_calls == []
    assert writes == []
    assert not (tmp_path / "invitees").exists()


def test_invited_bootstrap_preflights_bad_private_allowlist_before_any_api_call_or_write(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_invited_bootstrap_module("bootstrap_invited_user_preflight_private_list")
    api_calls: list[tuple[str, dict]] = []
    writes: list[Path] = []
    private_allowlist = tmp_path / "feishu-allowed-users"
    private_allowlist.write_text("bad user\n", encoding="utf-8")
    private_allowlist.chmod(0o600)
    monkeypatch.setattr(module, "OWNER_RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(
        module,
        "post",
        lambda path, payload, owner_token: api_calls.append((path, payload)) or {},
    )
    monkeypatch.setattr(
        module,
        "atomic_write_text",
        lambda path, value: writes.append(path),
    )
    monkeypatch.setenv("BODYOS_OWNER_TOKEN", "owner-token")
    monkeypatch.setenv("BODYOS_INVITEE_FEISHU_SUBJECT", "ou_invited")
    monkeypatch.setenv("BODYOS_INVITEE_DEVICE_PUBLIC_ID", "device-public-id")
    monkeypatch.setenv("BODYOS_INVITEE_SLUG", "second_user")
    monkeypatch.setenv("FEISHU_ALLOWED_USERS", "ou_owner")

    import pytest

    with pytest.raises(ValueError, match="whitespace"):
        module.main()

    assert api_calls == []
    assert writes == []
    assert not (tmp_path / "invitees").exists()


def test_gateway_uses_private_read_only_allowlist_and_fails_closed_when_it_is_invalid() -> None:
    compose = (ROOT / "infra/tencent/compose.yaml").read_text()
    entrypoint = (ROOT / "infra/tencent/gateway-entrypoint.sh").read_text()

    assert "./runtime/owner:/owner-runtime:ro" in compose
    assert "ALLOWLIST_FILE=/owner-runtime/feishu-allowed-users" in entrypoint
    assert "Invalid private Feishu allowlist; gateway refused to start." in entrypoint
    assert 'export FEISHU_ALLOWED_USERS="$allowed_users"' in entrypoint
    assert "if [ -e \"$ALLOWLIST_FILE\" ]" in entrypoint
    assert 'stat -c %a "$ALLOWLIST_FILE"' in entrypoint
    assert "hermes --profile bodyos gateway --accept-hooks run" in entrypoint


def test_gateway_allowlist_falls_back_when_missing_and_rejects_invalid_private_file(
    tmp_path: Path,
) -> None:
    source = (ROOT / "infra/tencent/gateway-entrypoint.sh").read_text()
    allowlist = tmp_path / "feishu-allowed-users"
    entrypoint = tmp_path / "gateway-entrypoint.sh"
    entrypoint.write_text(
        source.replace(
            "ALLOWLIST_FILE=/owner-runtime/feishu-allowed-users",
            f"ALLOWLIST_FILE={shlex.quote(str(allowlist))}",
        ),
        encoding="utf-8",
    )
    entrypoint.chmod(0o700)
    command_dir = tmp_path / "bin"
    command_dir.mkdir()
    for name, body in {
        "python": "#!/bin/sh\nexit 0\n",
        "hermes": "#!/bin/sh\nprintf '%s' \"$FEISHU_ALLOWED_USERS\"\n",
        "stat": "#!/bin/sh\nprintf '600\\n'\n",
    }.items():
        command = command_dir / name
        command.write_text(body, encoding="utf-8")
        command.chmod(0o700)
    environment = {
        **os.environ,
        "PATH": f"{command_dir}{os.pathsep}{os.environ['PATH']}",
        "FEISHU_ALLOWED_USERS": "ou_owner",
    }

    missing_file = subprocess.run(
        ["sh", str(entrypoint)],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )

    assert missing_file.returncode == 0
    assert missing_file.stdout == "ou_owner"

    allowlist.write_text("ou_owner\nou_invited\n", encoding="utf-8")
    allowlist.chmod(0o600)
    valid_file = subprocess.run(
        ["sh", str(entrypoint)],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )

    assert valid_file.returncode == 0
    assert valid_file.stdout == "ou_owner,ou_invited"

    allowlist.write_text("ou_owner\nnot valid\n", encoding="utf-8")
    allowlist.chmod(0o600)
    invalid_file = subprocess.run(
        ["sh", str(entrypoint)],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )

    assert invalid_file.returncode != 0
    assert invalid_file.stdout == ""
    assert invalid_file.stderr == "Invalid private Feishu allowlist; gateway refused to start.\n"


def test_controlled_invitation_wrapper_uses_ephemeral_no_echo_inputs_and_restarts_gateway_only(
) -> None:
    wrapper = (ROOT / "infra/tencent/bootstrap-invited-user.sh").read_text()
    document = (ROOT / "docs/operations/deployment-and-rollback.md").read_text()

    assert "read_private" in wrapper
    assert "stty -echo" in wrapper
    assert "BODYOS_INVITEE_FEISHU_SUBJECT" in wrapper
    assert "BODYOS_INVITEE_DEVICE_PUBLIC_ID" in wrapper
    assert "BODYOS_INVITEE_SLUG" in wrapper
    assert "$COMPOSE restart gateway" in wrapper
    assert "--force-recreate api gateway" not in wrapper
    assert "docker compose config" not in wrapper
    assert 'echo "$SUBJECT"' not in wrapper
    assert 'echo "$DEVICE_PUBLIC_ID"' not in wrapper
    assert "./bootstrap-invited-user.sh" in document
    assert "不得根据姓名猜测" in document
    assert "must never be guessed from a person’s name" in document


def test_reconciliation_derives_a_canonical_private_allowlist_from_active_identities(
    session, field_cipher, tmp_path: Path
) -> None:
    module = _load_reconciliation_module("reconcile_allowlist_active")
    _add_feishu_identity(
        session,
        field_cipher,
        binding_id="owner-binding",
        user_id="owner-user",
        status="active",
        subject="ou_owner",
        revoked=False,
    )
    _add_feishu_identity(
        session,
        field_cipher,
        binding_id="invited-binding",
        user_id="invited-user",
        status="invited",
        subject="ou_invited",
        revoked=False,
    )
    _add_feishu_identity(
        session,
        field_cipher,
        binding_id="revoked-binding",
        user_id="revoked-user",
        status="active",
        subject="ou_revoked",
        revoked=True,
    )

    allowlist = tmp_path / "owner-runtime" / "feishu-allowed-users"
    users = module.reconcile_and_store_allowed_users(
        session,
        field_cipher,
        initial_allowed_users="ou_owner",
        path=allowlist,
    )

    assert users == ("ou_invited", "ou_owner")
    assert allowlist.read_text(encoding="utf-8") == "ou_invited\nou_owner\n"
    assert allowlist.stat().st_mode & 0o777 == 0o600
    assert allowlist.parent.stat().st_mode & 0o777 == 0o700


def test_reconciliation_fails_closed_without_writing_for_an_unreadable_active_identity(
    session, field_cipher, tmp_path: Path
) -> None:
    module = _load_reconciliation_module("reconcile_allowlist_unreadable")
    user = User(fitcrew_user_id="unreadable-user", status="active")
    session.add(user)
    session.add(
        IdentityBinding(
            id="unreadable-binding",
            fitcrew_user_id=user.fitcrew_user_id,
            provider="feishu",
            subject_hash="unreadable-hash",
            encrypted_subject=b"not-an-encrypted-subject",
            verified_at=datetime.now(UTC),
        )
    )
    session.flush()
    allowlist = tmp_path / "owner-runtime" / "feishu-allowed-users"

    with pytest.raises(module.ReconciliationError, match="reconciliation failed"):
        module.reconcile_and_store_allowed_users(
            session,
            field_cipher,
            initial_allowed_users="ou_owner",
            path=allowlist,
        )

    assert not allowlist.exists()


def test_reconciliation_does_not_reauthorize_a_revoked_subject_left_in_environment(
    session, field_cipher
) -> None:
    module = _load_reconciliation_module("reconcile_allowlist_rebind")
    _add_feishu_identity(
        session,
        field_cipher,
        binding_id="old-owner-binding",
        user_id="old-owner-user",
        status="active",
        subject="ou_old_owner",
        revoked=True,
    )
    _add_feishu_identity(
        session,
        field_cipher,
        binding_id="current-owner-binding",
        user_id="current-owner-user",
        status="active",
        subject="ou_current_owner",
        revoked=False,
    )
    _add_feishu_identity(
        session,
        field_cipher,
        binding_id="invited-binding",
        user_id="invited-user",
        status="invited",
        subject="ou_invited",
        revoked=False,
    )

    users = module.derive_allowed_users(
        session,
        field_cipher,
        initial_allowed_users="ou_old_owner",
    )

    assert users == ("ou_current_owner", "ou_invited")


def test_reconciliation_excludes_unverified_active_identity(session, field_cipher) -> None:
    module = _load_reconciliation_module("reconcile_allowlist_unverified")
    _add_feishu_identity(
        session,
        field_cipher,
        binding_id="owner-binding",
        user_id="owner-user",
        status="active",
        subject="ou_owner",
        revoked=False,
    )
    unverified_user = User(fitcrew_user_id="unverified-user", status="invited")
    session.add(unverified_user)
    identity = IdentityBinding(
        id="unverified-binding",
        fitcrew_user_id=unverified_user.fitcrew_user_id,
        provider="feishu",
        subject_hash="unverified-hash",
        encrypted_subject=b"",
        verified_at=None,
    )
    session.add(identity)
    encrypted = field_cipher.encrypt_json(
        {"subject": "ou_unverified"}, aad=f"identity:{identity.id}"
    )
    identity.encrypted_subject = encrypted.nonce + encrypted.ciphertext
    session.flush()

    users = module.derive_allowed_users(
        session,
        field_cipher,
        initial_allowed_users="ou_owner",
    )

    assert users == ("ou_owner",)


def test_reconciliation_wrapper_runs_api_then_restarts_only_gateway(tmp_path: Path) -> None:
    source_path = ROOT / "infra/tencent/reconcile-feishu-allowlist.sh"
    assert source_path.stat().st_mode & 0o111
    source = source_path.read_text(encoding="utf-8")
    script = tmp_path / "reconcile-feishu-allowlist.sh"
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / ".env.runtime").write_text(
        "FEISHU_ALLOWED_USERS=ou_owner\nBODYOS_ENCRYPTION_KEY=test-key\n",
        encoding="utf-8",
    )
    script.write_text(
        source.replace(
            'HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)',
            f"HERE={shlex.quote(str(tmp_path))}",
        ),
        encoding="utf-8",
    )
    script.chmod(0o700)

    command_dir = tmp_path / "bin"
    command_dir.mkdir()
    calls = tmp_path / "docker-calls"
    docker = command_dir / "docker"
    docker.write_text(
        "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$CALLS\"\n",
        encoding="utf-8",
    )
    docker.chmod(0o700)

    environment = {
        **os.environ,
        "PATH": f"{command_dir}{os.pathsep}{os.environ['PATH']}",
        "CALLS": str(calls),
    }
    result = subprocess.run(
        ["sh", str(script)],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout == "Private Feishu allowlist reconciliation completed.\n"
    assert result.stderr == ""
    compose_prefix = (
        f"compose --env-file {tmp_path}/runtime/.env.runtime -f {tmp_path}/compose.yaml"
    )
    assert calls.read_text(encoding="utf-8").splitlines() == [
        f"{compose_prefix} exec -T api python /app/scripts/reconcile_feishu_allowlist.py",
        f"{compose_prefix} restart gateway",
    ]


def test_reconciliation_wrapper_and_api_script_do_not_accept_or_print_subject_values() -> None:
    wrapper = (ROOT / "infra/tencent/reconcile-feishu-allowlist.sh").read_text(encoding="utf-8")
    script = (ROOT / "scripts/reconcile_feishu_allowlist.py").read_text(encoding="utf-8")

    assert "read " not in wrapper
    assert "open_id" not in wrapper
    assert "docker compose config" not in wrapper
    assert 'echo "Private Feishu allowlist reconciliation completed."' in wrapper
    assert "print(subject" not in script
    assert "print(users" not in script
    assert 'print("Private Feishu allowlist reconciled.")' in script
