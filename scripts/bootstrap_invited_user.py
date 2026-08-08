#!/usr/bin/env python3
"""Create one private invited-user pairing artifact inside the API container."""

import json
import os
import re
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
LOOPBACK_API = "http://127.0.0.1:8000"
SAFE_SLUG = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")


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


def main() -> None:
    os.umask(0o077)
    owner_token = required("BODYOS_OWNER_TOKEN")
    subject = required("BODYOS_INVITEE_FEISHU_SUBJECT")
    device_public_id = required("BODYOS_INVITEE_DEVICE_PUBLIC_ID")
    slug = required("BODYOS_INVITEE_SLUG")
    if not SAFE_SLUG.fullmatch(slug):
        raise SystemExit("BODYOS_INVITEE_SLUG must use lowercase letters, digits, _ or -")

    post(
        "/v1/owner/users/invite",
        {
            "feishu_subject": subject,
            "locale": "zh-CN",
            "timezone": "Asia/Shanghai",
        },
        owner_token,
    )
    payload = post(
        "/v1/owner/users/pair",
        {
            "feishu_subject": subject,
            "device_public_id": device_public_id,
            "categories": CATEGORIES,
        },
        owner_token,
    )

    output_dir = Path("/owner-runtime/invitees") / slug
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output_dir, 0o700)
    record = output_dir / "pairing.json"
    record.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(record, 0o600)
    qr_path = output_dir / "pairing.png"
    qrcode.make(payload["pairing_url"]).save(qr_path)
    os.chmod(qr_path, 0o600)
    print("Invited user pairing stored outside Git.")


if __name__ == "__main__":
    main()
