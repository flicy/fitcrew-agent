#!/usr/bin/env python3
"""Create owner identity, consent, and a one-time private iOS pairing artifact."""

import json
import os
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


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"required environment variable is missing: {name}")
    return value


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


def post(payload: dict, owner_token: str) -> dict:
    request = Request(
        "http://127.0.0.1:8000/v1/owner/bootstrap",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "X-Owner-Token": owner_token},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed loopback URL
        return json.load(response)


def issue_owner_pairing_with_expiry_rotation(
    *, output_dir: Path, owner_token: str, subject: str, idempotency_key: str
) -> dict:
    request_payload = {
        "feishu_subject": subject,
        "device_public_id": "owner-iphone-healthkit",
        "categories": CATEGORIES,
        "idempotency_key": idempotency_key,
    }
    try:
        return post(request_payload, owner_token)
    except HTTPError:
        if not pairing_expired(output_dir / "owner-bootstrap.json"):
            raise
        rotated_key = rotate_idempotency_key(output_dir / "owner-pairing-idempotency-key")
        request_payload["idempotency_key"] = rotated_key
        return post(request_payload, owner_token)


def write_owner_pairing_artifact(output_dir: Path, payload: dict) -> None:
    record = output_dir / "owner-bootstrap.json"
    atomic_write_text(record, json.dumps(payload, ensure_ascii=False, indent=2))
    qr_path = output_dir / "owner-pairing.png"
    temporary = qr_path.with_name(f".{qr_path.stem}.{secrets.token_hex(8)}.png")
    try:
        qrcode.make(payload["pairing_url"]).save(temporary)
        os.chmod(temporary, 0o600)
        os.replace(temporary, qr_path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> None:
    os.umask(0o077)
    owner_token = required("BODYOS_OWNER_TOKEN")
    subject = required("FEISHU_ALLOWED_USERS").split(",", maxsplit=1)[0]
    output_dir = Path("/owner-runtime")
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output_dir, 0o700)
    idempotency_key = read_or_create_idempotency_key(
        output_dir / "owner-pairing-idempotency-key"
    )
    payload = issue_owner_pairing_with_expiry_rotation(
        output_dir=output_dir,
        owner_token=owner_token,
        subject=subject,
        idempotency_key=idempotency_key,
    )
    write_owner_pairing_artifact(output_dir, payload)
    print("Owner bootstrap completed; private JSON and pairing QR stored outside Git.")


if __name__ == "__main__":
    main()
