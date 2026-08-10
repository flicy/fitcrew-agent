#!/usr/bin/env python3
"""Create the untracked production environment without echoing credentials."""

import argparse
import base64
import getpass
import ipaddress
import os
import secrets
from datetime import date
from pathlib import Path

PROACTIVE_DEFAULTS = {
    "BODYOS_PROACTIVE_GROUP_ENABLED": "true",
    "BODYOS_GROUP_TIMEZONE": "Asia/Shanghai",
    "BODYOS_GROUP_MORNING_TIME": "09:00",
    "BODYOS_GROUP_EVENING_TIME": "20:30",
    "BODYOS_GROUP_WEEKLY_WEEKDAY": "2",
    "BODYOS_GROUP_WEEKLY_TIME": "12:15",
    "BODYOS_GROUP_QUIET_START": "22:00",
    "BODYOS_GROUP_QUIET_END": "08:00",
}


def prompt(name: str, *, secret: bool = False, optional: bool = False) -> str:
    reader = getpass.getpass if secret else input
    while True:
        value = reader(f"{name}{' (optional)' if optional else ''}: ").strip()
        if value or optional:
            return value


def token(bytes_count: int = 32) -> str:
    return secrets.token_urlsafe(bytes_count)


def append_missing_defaults(path: Path) -> int:
    if not path.is_file():
        raise SystemExit(f"runtime file is missing: {path}")
    original = path.read_text(encoding="utf-8")
    existing = {
        line.split("=", 1)[0]
        for line in original.splitlines()
        if line and not line.startswith("#") and "=" in line
    }
    missing = [(key, value) for key, value in PROACTIVE_DEFAULTS.items() if key not in existing]
    if not missing:
        return 0
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    suffix = "" if not original or original.endswith("\n") else "\n"
    temporary.write_text(
        original + suffix + "".join(f"{key}={value}\n" for key, value in missing),
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    return len(missing)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("runtime/.env.runtime"))
    parser.add_argument("--append-defaults", action="store_true")
    args = parser.parse_args()
    if args.append_defaults:
        count = append_missing_defaults(args.output)
        print(f"runtime defaults present; added {count} non-secret values")
        return
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite existing runtime file: {args.output}")
    public_host = prompt("Tencent Lighthouse public IPv4")
    ipaddress.ip_address(public_host)
    feishu_app_id = prompt("Feishu App ID")
    feishu_app_secret = prompt("Feishu App Secret", secret=True)
    feishu_owner = prompt("Owner Feishu open_id")
    feishu_group = prompt("Allowed test group chat_id", optional=True)
    feishu_home = prompt("Owner DM/home chat_id")
    acme_email = prompt("ACME email", optional=True)
    encryption_key = base64.urlsafe_b64encode(os.urandom(32)).decode()
    values = {
        "FITCREW_PUBLIC_HOST": public_host,
        "FITCREW_PUBLIC_BASE_URL": f"https://{public_host}",
        "FITCREW_IMAGE_TAG": "local",
        "FITCREW_ACME_EMAIL": acme_email,
        "POSTGRES_DB": "bodyos",
        "POSTGRES_USER": "bodyos",
        "POSTGRES_PASSWORD": token(36),
        "BODYOS_ENVIRONMENT": "production",
        "BODYOS_ENCRYPTION_KEY": encryption_key,
        "BODYOS_OWNER_TOKEN": token(),
        "BODYOS_IDENTITY_PEPPER": token(),
        "BODYOS_INTERNAL_TOKEN": token(),
        "BODYOS_MODEL_PROXY_TOKEN": token(),
        "BODYOS_PUBLIC_BASE_URL": f"https://{public_host}",
        "BODYOS_CODEX_COMMAND": "codex",
        "BODYOS_HERMES_COMMAND": "hermes",
        "BODYOS_HERMES_MODEL": "gpt-5.3-codex-spark",
        "BODYOS_STUDY_START_DATE": date.today().isoformat(),
        **PROACTIVE_DEFAULTS,
        "FEISHU_APP_ID": feishu_app_id,
        "FEISHU_APP_SECRET": feishu_app_secret,
        "FEISHU_DOMAIN": "feishu",
        "FEISHU_CONNECTION_MODE": "websocket",
        "FEISHU_ALLOW_ALL_USERS": "false",
        "GATEWAY_ALLOW_ALL_USERS": "false",
        "FEISHU_ALLOWED_USERS": feishu_owner,
        "FEISHU_ALLOWED_GROUP_ID": feishu_group,
        "FEISHU_HOME_CHANNEL": feishu_home,
        "FEISHU_HOME_CHANNEL_NAME": "FitCrew BodyOS",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text("".join(f"{key}={value}\n" for key, value in values.items()))
    os.chmod(args.output, 0o600)
    backup_key = args.output.parent / "backup.key"
    backup_key.write_text(token(48) + "\n")
    os.chmod(backup_key, 0o600)
    print(f"created {args.output} and backup key with mode 0600")


if __name__ == "__main__":
    main()
