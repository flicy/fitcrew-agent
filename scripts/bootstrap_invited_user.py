#!/usr/bin/env python3
"""Create one private invited-user pairing artifact inside the API container."""

import json
import os
import re
import secrets
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import qrcode

SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from private_feishu_allowlist import (  # noqa: E402
    ALLOWLIST_FILE_NAME,
    atomic_write_text,
    prepare_allowed_users,
    store_allowed_users,  # noqa: F401 - retained as the invitation script's tested public helper
    validate_allowed_subject,
    write_allowed_users,
)

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
OWNER_RUNTIME_DIR = Path("/owner-runtime")


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value.strip():
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
        return validate_idempotency_key(path.read_text(encoding="utf-8").strip())
    key = secrets.token_urlsafe(32)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return validate_idempotency_key(path.read_text(encoding="utf-8").strip())
    with os.fdopen(descriptor, "w", encoding="utf-8") as key_file:
        key_file.write(key)
    os.chmod(path, 0o600)
    return validate_idempotency_key(key)


def validate_device_public_id(value: str) -> str:
    """Match the device identifier bounds before the invitation API is mutated."""
    if not 3 <= len(value) <= 128:
        raise ValueError("public device identifier must contain 3 to 128 characters")
    return value


def validate_idempotency_key(value: str) -> str:
    """Match pairing idempotency bounds before the invitation API is mutated."""
    if not 32 <= len(value) <= 200:
        raise ValueError("pairing idempotency key must contain 32 to 200 characters")
    return value


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
    subject = validate_allowed_subject(required("BODYOS_INVITEE_FEISHU_SUBJECT"))
    device_public_id = validate_device_public_id(required("BODYOS_INVITEE_DEVICE_PUBLIC_ID"))
    slug = required("BODYOS_INVITEE_SLUG")
    if not SAFE_SLUG.fullmatch(slug):
        raise SystemExit("BODYOS_INVITEE_SLUG must use lowercase letters, digits, _ or -")

    allowlist_path = OWNER_RUNTIME_DIR / ALLOWLIST_FILE_NAME
    allowed_users = prepare_allowed_users(
        allowlist_path,
        initial_allowed_users=required("FEISHU_ALLOWED_USERS"),
        invited_subject=subject,
    )

    output_dir = OWNER_RUNTIME_DIR / "invitees" / slug
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
    write_allowed_users(allowlist_path, allowed_users)
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
