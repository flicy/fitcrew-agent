#!/usr/bin/env python3
"""Create owner identity, consent, and a one-time private iOS pairing artifact."""

import json
import os
import secrets
from pathlib import Path
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
    request = Request(
        "http://127.0.0.1:8000/v1/owner/bootstrap",
        data=json.dumps(
            {
                "feishu_subject": subject,
                "device_public_id": "owner-iphone-healthkit",
                "categories": CATEGORIES,
                "idempotency_key": idempotency_key,
            }
        ).encode(),
        headers={"Content-Type": "application/json", "X-Owner-Token": owner_token},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed loopback URL
        payload = json.load(response)
    record = output_dir / "owner-bootstrap.json"
    record.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(record, 0o600)
    pairing = qrcode.make(payload["pairing_url"])
    qr_path = output_dir / "owner-pairing.png"
    pairing.save(qr_path)
    os.chmod(qr_path, 0o600)
    print("Owner bootstrap completed; private JSON and pairing QR stored outside Git.")


if __name__ == "__main__":
    main()
