#!/usr/bin/env python3
"""Read-only release diagnostics / 只读发布诊断，不执行升级或清理。"""

import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def query(argv):
    """Never forward arbitrary command output on failure (it may contain secrets)."""
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def nonempty(path):
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def collect(repo):
    report = {
        "checked_at_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "mode": "read_only",
        "deployment_performed": False,
        "restore_verified": False,
        "platform_submission_verified": False,
        "blockers": [],
    }
    blockers = report["blockers"]
    if not repo.is_dir():
        blockers.append("repository_directory_unavailable")
        return report

    disk = shutil.disk_usage(repo)
    report["disk_free_bytes"] = disk.free
    # Conservative local build headroom, not a guarantee that a build will fit.
    if disk.free < 10 * 1024**3:
        blockers.append("less_than_10_GiB_build_headroom")
    revision = query(["git", "-C", str(repo), "rev-parse", "HEAD"])
    report["checkout_revision"] = (
        revision if revision and re.fullmatch(r"[0-9a-f]{40,64}", revision) else None
    )
    status = query(["git", "-C", str(repo), "status", "--porcelain"])
    report["checkout_clean"] = status == "" if status is not None else None
    if report["checkout_revision"] is None or report["checkout_clean"] is not True:
        blockers.append("checkout_not_verified_clean")

    runtime = repo / "infra/tencent/runtime"
    for name, filename in (("runtime_config_present", ".env.runtime"),
                           ("backup_key_present", "backup.key")):
        report[name] = nonempty(runtime / filename)
        if not report[name]:
            blockers.append(name + "_false")
    try:
        backups = [p.stat() for p in (runtime / "backups").glob("bodyos-*.sql.enc")
                   if p.is_file() and p.stat().st_size > 0]
        latest = max(backups, key=lambda s: s.st_mtime) if backups else None
        report["encrypted_backup"] = {
            "nonempty_count": len(backups),
            "latest_size_bytes": latest.st_size if latest else None,
            "latest_modified_utc": datetime.datetime.fromtimestamp(
                latest.st_mtime, datetime.UTC
            ).isoformat() if latest else None,
        }
        if latest is None:
            blockers.append("no_nonempty_encrypted_backup")
    except OSError:
        blockers.append("backup_metadata_unavailable")

    report["containers"] = {}
    template = (
        '{{.Id}}|{{.Image}}|{{.State.Status}}|'
        '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}|{{.State.StartedAt}}'
    )
    container_states = {"created", "running", "paused", "restarting", "removing", "exited", "dead"}
    for service in ("api", "db", "worker", "gateway", "caddy"):
        name = "fitcrew-bodyos-" + service + "-1"
        raw = query(["docker", "inspect", "--format", template, name])
        fields = raw.split("|") if raw else []
        valid = (len(fields) == 5
                 and re.fullmatch(r"[0-9a-f]{64}", fields[0])
                 and re.fullmatch(r"sha256:[0-9a-f]{64}", fields[1])
                 and fields[2] in container_states
                 and fields[3] in {"none", "starting", "healthy", "unhealthy"}
                 and re.fullmatch(r"[0-9T:Z.+-]+", fields[4]))
        if not valid:
            blockers.append(service + "_metadata_unavailable")
            continue
        report["containers"][service] = dict(zip(
            ("container_id", "image_id", "status", "health", "started_at"), fields, strict=True
        ))
        if fields[2] != "running" or fields[3] in {"starting", "unhealthy"}:
            blockers.append(service + "_not_healthy")

    # Force a read-only DB session; select schema revision only, never user rows.
    revision = query([
        "docker", "exec", "--env", "PGOPTIONS=-c default_transaction_read_only=on",
        "fitcrew-bodyos-db-1", "psql", "-X", "-A", "-t", "-w",
        "-U", "bodyos", "-d", "bodyos", "-c", "SELECT version_num FROM alembic_version;",
    ])
    # Only known schema identifiers are safe evidence; arbitrary DB output is not.
    known_revisions = {
        "0001_owner_alpha", "0002_pairing_exchange_sessions", "0003_group_coach_outbox",
        "0004_product_records", "0005_device_only_pairing",
    }
    report["database_revision"] = revision if revision in known_revisions else None
    if report["database_revision"] is None:
        blockers.append("database_revision_unavailable")
    report["remaining_acceptance"] = [
        "fresh_encrypted_backup_and_isolated_restore_test",
        "migration_and_old_api_compatibility",
        "production_HTTPS_and_platform_configuration",
        "real_login_save_relogin_privacy_and_device_acceptance",
    ]
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    # The console runs outside the project's dependency-managed Python environment.
    if sys.version_info < (3, 11):  # noqa: UP036
        parser.error("Python 3.11 or newer is required; no diagnostic commands were run.")
    parser.add_argument("--repo", type=Path, default=Path("/opt/fitcrew-bodyos"))
    args = parser.parse_args()
    result = collect(args.repo)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(2 if result["blockers"] else 0)
