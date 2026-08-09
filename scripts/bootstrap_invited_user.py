#!/usr/bin/env python3
"""Create one private invited-user pairing artifact inside the API container."""

import json
import os
import re
import secrets
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import qrcode

CATEGORIES = [
    "blood_glucose",
    "sleep_asleep",
    "sleep_core",
    "sleep_deep",
    "sleep_rem",
    "heart_rate_variability",
    "resting_heart_rate",
    "workout",
    "active_energy",
    "step_count",
    "stand_hours",
    "activity_summary",
]
LOOPBACK_API = "http://127.0.0.1:8000"
SAFE_SLUG = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")
ALLOWLIST_FILE_NAME = "feishu-allowed-users"


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"required environment variable is missing: {name}")
    return value


def post(path: str, payload: dict, owner_token: str) -> dict:
    request = Request(
        LOOPBACK_API + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "X-Owner-Token": owner_token},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed loopback URL
        return json.load(response)


def read_or_create_idempotency_key(path: Path) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    key = secrets.token_urlsafe(32)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return path.read_text(encoding="utf-8").strip()
    with os.fdopen(descriptor, "w", encoding="utf-8") as key_file:
        key_file.write(key)
    os.chmod(path, 0o600)
    return key


def atomic_write_text(path: Path, value: str) -> None:
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(value)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def validate_allowed_subject(value: str) -> str:
    """Validate one Feishu subject for the private newline-delimited allowlist."""
    if not value:
        raise ValueError("Feishu subject must not be empty")
    if "\n" in value or "\r" in value:
        raise ValueError("Feishu subject must not contain a newline")
    if "," in value:
        raise ValueError("Feishu subject must not contain a comma")
    if any(character.isspace() for character in value):
        raise ValueError("Feishu subject must not contain whitespace")
    return value


def parse_allowed_users(value: str) -> tuple[str, ...]:
    """Read the existing comma-delimited runtime allowlist without widening it."""
    users: list[str] = []
    for raw_user in value.split(","):
        candidate = raw_user.strip()
        if not candidate:
            continue
        subject = validate_allowed_subject(candidate)
        if subject not in users:
            users.append(subject)
    if not users:
        raise ValueError("FEISHU_ALLOWED_USERS must contain an owner subject")
    return tuple(users)


def read_private_allowed_users(path: Path) -> tuple[str, ...]:
    """Read a previous private allowlist so a new invite never removes an existing user."""
    if not path.exists():
        return ()
    users: list[str] = []
    for raw_user in path.read_text(encoding="utf-8").splitlines():
        subject = validate_allowed_subject(raw_user)
        if subject not in users:
            users.append(subject)
    if not users:
        raise ValueError("private Feishu allowlist must not be empty")
    return tuple(users)


def store_allowed_users(
    path: Path, *, initial_allowed_users: str, invited_subject: str
) -> tuple[str, ...]:
    """Atomically persist the closed owner-plus-invitee allowlist outside Git."""
    users = list(parse_allowed_users(initial_allowed_users))
    for existing_subject in read_private_allowed_users(path):
        if existing_subject not in users:
            users.append(existing_subject)
    invited = validate_allowed_subject(invited_subject)
    if invited not in users:
        users.append(invited)

    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    atomic_write_text(path, "\n".join(users) + "\n")
    return tuple(users)


def rotate_idempotency_key(path: Path) -> str:
    key = secrets.token_urlsafe(32)
    atomic_write_text(path, key)
    return key


def pairing_expired(record: Path) -> bool:
    try:
        value = json.loads(record.read_text(encoding="utf-8"))["expires_at"]
        expires_at = datetime.fromisoformat(value)
        if expires_at.tzinfo is None:
            return False
        return expires_at <= datetime.now(UTC)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError):
        return False


def write_pairing_artifact(output_dir: Path, payload: dict) -> None:
    record = output_dir / "pairing.json"
    atomic_write_text(record, json.dumps(payload, ensure_ascii=False, indent=2))
    qr_path = output_dir / "pairing.png"
    temporary = qr_path.with_name(f".{qr_path.stem}.{secrets.token_hex(8)}.png")
    try:
        qrcode.make(payload["pairing_url"]).save(temporary)
        os.chmod(temporary, 0o600)
        os.replace(temporary, qr_path)
    finally:
        if temporary.exists():
            temporary.unlink()


def issue_pairing_with_expiry_rotation(
    *,
    output_dir: Path,
    owner_token: str,
    subject: str,
    device_public_id: str,
    idempotency_key: str,
) -> dict:
    request_payload = {
        "feishu_subject": subject,
        "device_public_id": device_public_id,
        "categories": CATEGORIES,
        "idempotency_key": idempotency_key,
    }
    try:
        return post("/v1/owner/users/pair", request_payload, owner_token)
    except HTTPError:
        if not pairing_expired(output_dir / "pairing.json"):
            raise
        rotated_key = rotate_idempotency_key(output_dir / "pairing-idempotency-key")
        request_payload["idempotency_key"] = rotated_key
        return post("/v1/owner/users/pair", request_payload, owner_token)


def main() -> None:
    os.umask(0o077)
    owner_token = required("BODYOS_OWNER_TOKEN")
    subject = required("BODYOS_INVITEE_FEISHU_SUBJECT")
    device_public_id = required("BODYOS_INVITEE_DEVICE_PUBLIC_ID")
    slug = required("BODYOS_INVITEE_SLUG")
    if not SAFE_SLUG.fullmatch(slug):
        raise SystemExit("BODYOS_INVITEE_SLUG must use lowercase letters, digits, _ or -")

    output_dir = Path("/owner-runtime/invitees") / slug
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output_dir, 0o700)
    idempotency_key = read_or_create_idempotency_key(output_dir / "pairing-idempotency-key")

    post(
        "/v1/owner/users/invite",
        {
            "feishu_subject": subject,
            "locale": "zh-CN",
            "timezone": "Asia/Shanghai",
        },
        owner_token,
    )
    store_allowed_users(
        Path("/owner-runtime") / ALLOWLIST_FILE_NAME,
        initial_allowed_users=required("FEISHU_ALLOWED_USERS"),
        invited_subject=subject,
    )
    payload = issue_pairing_with_expiry_rotation(
        output_dir=output_dir,
        owner_token=owner_token,
        subject=subject,
        device_public_id=device_public_id,
        idempotency_key=idempotency_key,
    )

    write_pairing_artifact(output_dir, payload)
    print("Invited user pairing stored outside Git.")


if __name__ == "__main__":
    main()
