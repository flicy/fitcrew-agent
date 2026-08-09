#!/usr/bin/env python3
"""Rebuild the private Feishu gateway allowlist from active encrypted identities."""

import os
import sys
from pathlib import Path

from bodyos_api.crypto import EncryptedValue, FieldCipher
from bodyos_api.db import SessionLocal
from bodyos_api.models import IdentityBinding, User
from bodyos_api.runtime import get_field_cipher
from sqlalchemy import select
from sqlalchemy.orm import Session

SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from private_feishu_allowlist import (  # noqa: E402
    ALLOWLIST_FILE_NAME,
    parse_allowed_users,
    validate_allowed_subject,
    write_allowed_users,
)

OWNER_RUNTIME_DIR = Path("/owner-runtime")
ACTIVE_USER_STATUSES = ("invited", "active")


class ReconciliationError(RuntimeError):
    """Raised when an expected active Feishu identity cannot be safely reconstructed."""


def decrypt_subject(identity: IdentityBinding, cipher: FieldCipher) -> str:
    """Decrypt and validate one subject with the identity-bound AAD."""
    try:
        encrypted = identity.encrypted_subject
        if len(encrypted) <= 12:
            raise ValueError("encrypted Feishu identity is unavailable")
        decoded = cipher.decrypt_json(
            EncryptedValue(nonce=encrypted[:12], ciphertext=encrypted[12:]),
            aad=f"identity:{identity.id}",
        )
        if not isinstance(decoded, dict):
            raise ValueError("encrypted Feishu identity is invalid")
        subject = decoded.get("subject")
        if not isinstance(subject, str):
            raise ValueError("encrypted Feishu identity is invalid")
        return validate_allowed_subject(subject)
    except Exception as exc:
        raise ReconciliationError("Feishu allowlist reconciliation failed") from exc


def derive_allowed_users(
    session: Session, cipher: FieldCipher, *, initial_allowed_users: str
) -> tuple[str, ...]:
    """Return the deterministic union of owner baseline and active Feishu identities."""
    try:
        users = set(parse_allowed_users(initial_allowed_users))
        active_identities = session.execute(
            select(IdentityBinding)
            .join(User, User.fitcrew_user_id == IdentityBinding.fitcrew_user_id)
            .where(
                IdentityBinding.provider == "feishu",
                IdentityBinding.revoked_at.is_(None),
                User.status.in_(ACTIVE_USER_STATUSES),
            )
            .order_by(IdentityBinding.id)
        ).scalars()
        for identity in active_identities:
            users.add(decrypt_subject(identity, cipher))
    except ReconciliationError:
        raise
    except Exception as exc:
        raise ReconciliationError("Feishu allowlist reconciliation failed") from exc
    if not users:
        raise ReconciliationError("Feishu allowlist reconciliation failed")
    return tuple(sorted(users))


def reconcile_and_store_allowed_users(
    session: Session,
    cipher: FieldCipher,
    *,
    initial_allowed_users: str,
    path: Path,
) -> tuple[str, ...]:
    """Derive the full closed allowlist before atomically replacing its private file."""
    users = derive_allowed_users(session, cipher, initial_allowed_users=initial_allowed_users)
    write_allowed_users(path, users)
    return users


def main() -> None:
    os.umask(0o077)
    try:
        initial_allowed_users = os.environ["FEISHU_ALLOWED_USERS"]
        cipher = get_field_cipher()
        with SessionLocal() as session:
            reconcile_and_store_allowed_users(
                session,
                cipher,
                initial_allowed_users=initial_allowed_users,
                path=OWNER_RUNTIME_DIR / ALLOWLIST_FILE_NAME,
            )
    except Exception:
        raise SystemExit("Feishu allowlist reconciliation failed") from None
    print("Private Feishu allowlist reconciled.")


if __name__ == "__main__":
    main()
