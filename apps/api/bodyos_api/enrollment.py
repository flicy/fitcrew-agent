import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.orm import Session

from bodyos_api.auth import hash_device_token
from bodyos_api.crypto import FieldCipher
from bodyos_api.models import Consent, DeviceBinding, IdentityBinding, User
from bodyos_api.schemas import HealthKind


class EnrollmentConflict(ValueError):
    pass


class EnrollmentNotFound(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class InvitationResult:
    fitcrew_user_id: str
    created: bool
    status: str


@dataclass(frozen=True, slots=True)
class PairingResult:
    device_binding_id: str
    consent_ids: dict[str, str]
    device_token: str
    pairing_url: str


def hash_subject(subject: str, pepper: str) -> str:
    if not pepper:
        raise RuntimeError("BODYOS_IDENTITY_PEPPER is required")
    return hmac.new(pepper.encode(), subject.encode(), hashlib.sha256).hexdigest()


def build_pairing_url(payload: dict) -> str:
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).decode().rstrip("=")
    return f"fitcrew-health://configure?{urlencode({'payload': encoded})}"


def invite_feishu_user(
    session: Session,
    cipher: FieldCipher,
    *,
    subject: str,
    pepper: str,
    locale: str,
    timezone: str,
) -> InvitationResult:
    subject_hash = hash_subject(subject, pepper)
    identity = session.scalar(
        select(IdentityBinding).where(
            IdentityBinding.provider == "feishu",
            IdentityBinding.subject_hash == subject_hash,
        )
    )
    if identity is not None:
        if identity.revoked_at is not None:
            raise EnrollmentConflict("identity is revoked")
        user = session.get(User, identity.fitcrew_user_id)
        if user is None:
            raise EnrollmentConflict("identity user is unavailable")
        return InvitationResult(user.fitcrew_user_id, False, user.status)

    user = User(status="invited", locale=locale, timezone=timezone)
    session.add(user)
    session.flush()
    identity = IdentityBinding(
        fitcrew_user_id=user.fitcrew_user_id,
        provider="feishu",
        subject_hash=subject_hash,
        encrypted_subject=b"",
        verified_at=datetime.now(UTC),
    )
    session.add(identity)
    session.flush()
    encrypted = cipher.encrypt_json({"subject": subject}, aad=f"identity:{identity.id}")
    identity.encrypted_subject = encrypted.nonce + encrypted.ciphertext
    session.commit()
    return InvitationResult(user.fitcrew_user_id, True, user.status)


def find_invited_user_id(session: Session, *, subject: str, pepper: str) -> str:
    subject_hash = hash_subject(subject, pepper)
    identity = session.scalar(
        select(IdentityBinding).where(
            IdentityBinding.provider == "feishu",
            IdentityBinding.subject_hash == subject_hash,
            IdentityBinding.revoked_at.is_(None),
        )
    )
    if identity is None:
        raise EnrollmentNotFound("invited identity not found")
    user = session.get(User, identity.fitcrew_user_id)
    if user is None or user.status not in {"invited", "active"}:
        raise EnrollmentNotFound("invited user not found")
    return user.fitcrew_user_id


def pair_invited_user(
    session: Session,
    *,
    fitcrew_user_id: str,
    device_public_id: str,
    categories: set[HealthKind],
    public_base_url: str,
) -> PairingResult:
    binding = session.scalar(
        select(DeviceBinding).where(DeviceBinding.device_public_id == device_public_id)
    )
    if binding is not None and binding.fitcrew_user_id != fitcrew_user_id:
        raise EnrollmentConflict("device is bound to another user")

    device_token = secrets.token_urlsafe(32)
    if binding is None:
        binding = DeviceBinding(
            fitcrew_user_id=fitcrew_user_id,
            device_public_id=device_public_id,
            token_hash=hash_device_token(device_token),
        )
        session.add(binding)
        session.flush()
    else:
        binding.token_hash = hash_device_token(device_token)
        binding.revoked_at = None

    now = datetime.now(UTC)
    requested = {category.value for category in categories}
    existing_consents = session.scalars(
        select(Consent).where(
            Consent.fitcrew_user_id == fitcrew_user_id,
            Consent.category.in_(requested),
            Consent.granted.is_(True),
            Consent.withdrawn_at.is_(None),
        )
    ).all()
    for consent in existing_consents:
        consent.granted = False
        consent.withdrawn_at = now

    consent_ids: dict[str, str] = {}
    for category in sorted(categories, key=lambda item: item.value):
        consent = Consent(
            fitcrew_user_id=fitcrew_user_id,
            category=category.value,
            purpose="private_coaching",
            granted=True,
            receipt_version="invite-alpha.v1",
            granted_at=now,
        )
        session.add(consent)
        session.flush()
        consent_ids[category.value] = consent.id

    user = session.get(User, fitcrew_user_id)
    if user is None:
        raise EnrollmentNotFound("invited user not found")
    user.status = "active"
    session.commit()

    payload = {
        "baseURL": public_base_url,
        "deviceBindingID": binding.id,
        "consentIDs": consent_ids,
        "deviceToken": device_token,
    }
    return PairingResult(
        device_binding_id=binding.id,
        consent_ids=consent_ids,
        device_token=device_token,
        pairing_url=build_pairing_url(payload),
    )
