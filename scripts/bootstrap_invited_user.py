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
    if not 3 <= len(value) <= 200:
        raise ValueError("Feishu subject must contain 3 to 200 characters")
    return value


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


def parse_allowed_users(value: str) -> tuple[str, ...]:
    """Read the existing comma-delimited runtime allowlist without widening it."""
    users: list[str] = []
    for raw_user in value.split(","):
        subject = validate_allowed_subject(raw_user)
        if subject not in users:
            users.append(subject)
    if not users:
        raise ValueError("FEISHU_ALLOWED_USERS must contain an owner subject")
    return tuple(users)


def read_private_allowed_users(path: Path) -> tuple[str, ...]:
    """Read a previous private allowlist so a new invite never removes an existing user."""
    if path.is_symlink():
        raise ValueError("private Feishu allowlist must be a regular file")
    if not path.exists():
        return ()
    if not path.is_file():
        raise ValueError("private Feishu allowlist must be a regular file")
    if path.stat().st_mode & 0o777 != 0o600:
        raise ValueError("private Feishu allowlist must have mode 0600")
    users: list[str] = []
    for raw_user in path.read_text(encoding="utf-8").splitlines():
        subject = validate_allowed_subject(raw_user)
        if subject in users:
            raise ValueError("private Feishu allowlist must not contain duplicates")
        users.append(subject)
    if not users:
        raise ValueError("private Feishu allowlist must not be empty")
    return tuple(users)


def prepare_allowed_users(
    path: Path, *, initial_allowed_users: str, invited_subject: str
) -> tuple[str, ...]:
    """Validate and merge the closed allowlist without changing private runtime state."""
    users = list(parse_allowed_users(initial_allowed_users))
    for existing_subject in read_private_allowed_users(path):
        if existing_subject not in users:
            users.append(existing_subject)
    invited = validate_allowed_subject(invited_subject)
    if invited not in users:
        users.append(invited)
    return tuple(users)


def write_allowed_users(path: Path, users: tuple[str, ...]) -> None:
    """Atomically persist an already validated closed allowlist outside Git."""
    if not users:
        raise ValueError("private Feishu allowlist must not be empty")
    for subject in users:
        validate_allowed_subject(subject)

    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    atomic_write_text(path, "\n".join(users) + "\n")


def store_allowed_users(
    path: Path, *, initial_allowed_users: str, invited_subject: str
) -> tuple[str, ...]:
    """Validate, merge, and atomically persist the closed allowlist for one invite."""
    users = prepare_allowed_users(
        path,
        initial_allowed_users=initial_allowed_users,
        invited_subject=invited_subject,
    )
    write_allowed_users(path, users)
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
