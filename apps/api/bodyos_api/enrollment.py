import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode, urlparse

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from bodyos_api.auth import hash_device_token
from bodyos_api.crypto import FieldCipher
from bodyos_api.models import Consent, DeviceBinding, IdentityBinding, PairingExchangeSession, User
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
class PairingInvitation:
    pairing_url: str
    expires_at: datetime
    created: bool


@dataclass(frozen=True, slots=True)
class PairingExchangeResult:
    base_url: str
    device_binding_id: str
    consent_ids: dict[str, str]
    device_token: str


def hash_subject(subject: str, pepper: str) -> str:
    if not pepper:
        raise RuntimeError("BODYOS_IDENTITY_PEPPER is required")
    return hmac.new(pepper.encode(), subject.encode(), hashlib.sha256).hexdigest()


def build_pairing_url(payload: dict) -> str:
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).decode().rstrip("=")
    return f"fitcrew-health://configure?{urlencode({'payload': encoded})}"


def _hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _categories_json(categories: set[HealthKind]) -> str:
    return json.dumps(sorted(category.value for category in categories), separators=(",", ":"))


def _pairing_code(
    *, idempotency_key: str, fitcrew_user_id: str, device_public_id: str, categories_json: str
) -> str:
    message = f"{fitcrew_user_id}:{device_public_id}:{categories_json}".encode()
    return base64.urlsafe_b64encode(
        hmac.new(idempotency_key.encode("utf-8"), message, hashlib.sha256).digest()
    ).decode("ascii").rstrip("=")


def _require_https(base_url: str) -> None:
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise EnrollmentConflict("pairing base URL must use HTTPS")


def _build_exchange_url(*, base_url: str, pairing_code: str, expires_at: datetime) -> str:
    return build_pairing_url(
        {
            "baseURL": base_url,
            "pairingCode": pairing_code,
            "expiresAt": _as_utc(expires_at).isoformat(),
        }
    )


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

    try:
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
    except IntegrityError as error:
        session.rollback()
        identity = session.scalar(
            select(IdentityBinding).where(
                IdentityBinding.provider == "feishu",
                IdentityBinding.subject_hash == subject_hash,
            )
        )
        if identity is None:
            raise EnrollmentConflict("identity invitation could not be created") from error
        if identity.revoked_at is not None:
            raise EnrollmentConflict("identity is revoked") from error
        user = session.get(User, identity.fitcrew_user_id)
        if user is None:
            raise EnrollmentConflict("identity user is unavailable") from error
        return InvitationResult(user.fitcrew_user_id, False, user.status)


def ensure_owner_feishu_user(
    session: Session,
    cipher: FieldCipher,
    *,
    subject: str,
    pepper: str,
) -> str:
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
        if user is None or user.status == "revoked":
            raise EnrollmentConflict("identity user is unavailable")
        return user.fitcrew_user_id

    user = User()
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
    return user.fitcrew_user_id


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


def issue_pairing_exchange(
    session: Session,
    *,
    fitcrew_user_id: str,
    device_public_id: str,
    categories: set[HealthKind],
    public_base_url: str,
    idempotency_key: str,
) -> PairingInvitation:
    _require_https(public_base_url)
    categories_json = _categories_json(categories)
    key_hash = _hash_secret(idempotency_key)
    existing = session.scalar(
        select(PairingExchangeSession).where(
            PairingExchangeSession.idempotency_key_hash == key_hash
        )
    )
    if existing is not None:
        if (
            existing.fitcrew_user_id != fitcrew_user_id
            or existing.device_public_id != device_public_id
            or existing.categories_json != categories_json
            or existing.base_url != public_base_url
        ):
            raise EnrollmentConflict("idempotency key was reused with different pairing details")
        if existing.consumed_at is not None or existing.invalidated_at is not None:
            raise EnrollmentConflict("pairing exchange is no longer pending")
        if _as_utc(existing.expires_at) <= datetime.now(UTC):
            raise EnrollmentConflict("pairing exchange is no longer pending")
        return PairingInvitation(
            pairing_url=_build_exchange_url(
                base_url=existing.base_url,
                pairing_code=_pairing_code(
                    idempotency_key=idempotency_key,
                    fitcrew_user_id=fitcrew_user_id,
                    device_public_id=device_public_id,
                    categories_json=categories_json,
                ),
                expires_at=_as_utc(existing.expires_at),
            ),
            expires_at=_as_utc(existing.expires_at),
            created=False,
        )

    binding = session.scalar(
        select(DeviceBinding).where(DeviceBinding.device_public_id == device_public_id)
    )
    if binding is not None and binding.fitcrew_user_id != fitcrew_user_id:
        raise EnrollmentConflict("device is bound to another user")
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=15)
    pairing_code = _pairing_code(
        idempotency_key=idempotency_key,
        fitcrew_user_id=fitcrew_user_id,
        device_public_id=device_public_id,
        categories_json=categories_json,
    )
    exchange = PairingExchangeSession(
        fitcrew_user_id=fitcrew_user_id,
        device_public_id=device_public_id,
        categories_json=categories_json,
        base_url=public_base_url,
        idempotency_key_hash=key_hash,
        pairing_code_hash=_hash_secret(pairing_code),
        expires_at=expires_at,
    )
    try:
        session.add(exchange)
        session.commit()
    except IntegrityError as error:
        session.rollback()
        conflicting = session.scalar(
            select(PairingExchangeSession).where(
                PairingExchangeSession.idempotency_key_hash == key_hash
            )
        )
        if conflicting is None:
            raise EnrollmentConflict("pairing exchange could not be created") from error
        if (
            conflicting.fitcrew_user_id != fitcrew_user_id
            or conflicting.device_public_id != device_public_id
            or conflicting.categories_json != categories_json
            or conflicting.base_url != public_base_url
        ):
            raise EnrollmentConflict(
                "idempotency key was reused with different pairing details"
            ) from error
        if conflicting.consumed_at is not None or conflicting.invalidated_at is not None:
            raise EnrollmentConflict("pairing exchange is no longer pending") from error
        return PairingInvitation(
            pairing_url=_build_exchange_url(
                base_url=conflicting.base_url,
                pairing_code=pairing_code,
                expires_at=_as_utc(conflicting.expires_at),
            ),
            expires_at=_as_utc(conflicting.expires_at),
            created=False,
        )
    return PairingInvitation(
        pairing_url=_build_exchange_url(
            base_url=public_base_url, pairing_code=pairing_code, expires_at=expires_at
        ),
        expires_at=_as_utc(exchange.expires_at),
        created=True,
    )


def redeem_pairing_exchange(session: Session, *, pairing_code: str) -> PairingExchangeResult:
    now = datetime.now(UTC)
    try:
        exchange = session.scalar(
            select(PairingExchangeSession)
            .where(PairingExchangeSession.pairing_code_hash == _hash_secret(pairing_code))
            .with_for_update()
        )
        if exchange is None:
            raise EnrollmentNotFound("pairing exchange is unavailable")
        consumed = session.execute(
            update(PairingExchangeSession)
            .where(
                PairingExchangeSession.id == exchange.id,
                PairingExchangeSession.consumed_at.is_(None),
                PairingExchangeSession.invalidated_at.is_(None),
                PairingExchangeSession.expires_at > now,
            )
            .values(consumed_at=now)
            .execution_options(synchronize_session=False)
        )
        if consumed.rowcount != 1:
            raise EnrollmentConflict("pairing exchange is unavailable")

        binding = session.scalar(
            select(DeviceBinding)
            .where(DeviceBinding.device_public_id == exchange.device_public_id)
            .with_for_update()
        )
        if binding is not None and binding.fitcrew_user_id != exchange.fitcrew_user_id:
            raise EnrollmentConflict("device is bound to another user")

        device_token = secrets.token_urlsafe(32)
        if binding is None:
            binding = DeviceBinding(
                fitcrew_user_id=exchange.fitcrew_user_id,
                device_public_id=exchange.device_public_id,
                token_hash=hash_device_token(device_token),
            )
            session.add(binding)
            session.flush()
        else:
            binding.token_hash = hash_device_token(device_token)
            binding.revoked_at = None

        current_consents = session.scalars(
            select(Consent).where(
                Consent.fitcrew_user_id == exchange.fitcrew_user_id,
                Consent.purpose == "private_coaching",
                Consent.granted.is_(True),
                Consent.withdrawn_at.is_(None),
            )
        ).all()
        for consent in current_consents:
            consent.granted = False
            consent.withdrawn_at = now

        consent_ids: dict[str, str] = {}
        for category in json.loads(exchange.categories_json):
            consent = Consent(
                fitcrew_user_id=exchange.fitcrew_user_id,
                category=category,
                purpose="private_coaching",
                granted=True,
                receipt_version="invite-alpha.v2",
                granted_at=now,
            )
            session.add(consent)
            session.flush()
            consent_ids[category] = consent.id

        user = session.get(User, exchange.fitcrew_user_id)
        if user is None or user.status == "revoked":
            raise EnrollmentNotFound("invited user not found")
        user.status = "active"
        session.commit()
    except (EnrollmentConflict, EnrollmentNotFound):
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise
    return PairingExchangeResult(
        base_url=exchange.base_url,
        device_binding_id=binding.id,
        consent_ids=consent_ids,
        device_token=device_token,
    )


def revoke_invited_user(
    session: Session, *, fitcrew_user_id: str, device_public_id: str | None = None
) -> None:
    now = datetime.now(UTC)
    try:
        if device_public_id is not None:
            requested = session.scalar(
                select(DeviceBinding).where(
                    DeviceBinding.fitcrew_user_id == fitcrew_user_id,
                    DeviceBinding.device_public_id == device_public_id,
                )
            )
            if requested is None:
                raise EnrollmentNotFound("invited device not found")
        devices = session.scalars(
            select(DeviceBinding).where(
                DeviceBinding.fitcrew_user_id == fitcrew_user_id,
                DeviceBinding.revoked_at.is_(None),
            )
        ).all()
        for device in devices:
            device.revoked_at = now
        consents = session.scalars(
            select(Consent).where(
                Consent.fitcrew_user_id == fitcrew_user_id,
                Consent.purpose == "private_coaching",
                Consent.granted.is_(True),
                Consent.withdrawn_at.is_(None),
            )
        ).all()
        for consent in consents:
            consent.granted = False
            consent.withdrawn_at = now
        exchanges = session.scalars(
            select(PairingExchangeSession).where(
                PairingExchangeSession.fitcrew_user_id == fitcrew_user_id,
                PairingExchangeSession.consumed_at.is_(None),
                PairingExchangeSession.invalidated_at.is_(None),
            )
        ).all()
        for exchange in exchanges:
            exchange.invalidated_at = now
        user = session.get(User, fitcrew_user_id)
        if user is None:
            raise EnrollmentNotFound("invited user not found")
        user.status = "revoked"
        identities = session.scalars(
            select(IdentityBinding).where(
                IdentityBinding.fitcrew_user_id == fitcrew_user_id,
                IdentityBinding.provider == "feishu",
                IdentityBinding.revoked_at.is_(None),
            )
        ).all()
        for identity in identities:
            identity.revoked_at = now
        session.commit()
    except (EnrollmentConflict, EnrollmentNotFound):
        session.rollback()
        raise
    except Exception:
        session.rollback()
        raise
