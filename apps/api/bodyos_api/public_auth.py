"""Official provider verification; reuse V2 identities and device tokens."""

import hmac
import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Annotated, Literal
from uuid import UUID, uuid4

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from bodyos_api.auth import DevicePrincipal, hash_device_token, require_device
from bodyos_api.config import Settings, get_settings
from bodyos_api.crypto import EncryptedValue, FieldCipher
from bodyos_api.db import get_session
from bodyos_api.enrollment import hash_subject
from bodyos_api.models import Consent, DeviceBinding, IdentityBinding, LoginChallenge, User
from bodyos_api.runtime import get_field_cipher
from bodyos_api.schemas import HealthKind

router = APIRouter(prefix="/v3", tags=["public-auth"])
SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[Session, Depends(get_session)]
CipherDep = Annotated[FieldCipher, Depends(get_field_cipher)]


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    privacy_version: Literal["2026-09-07"]


class WeChatLogin(LoginInput):
    code: str = Field(min_length=1, max_length=512)


class AppleLogin(LoginInput):
    challenge_id: UUID
    identity_token: str = Field(min_length=1, max_length=16000)
    authorization_code: str = Field(min_length=1, max_length=4096)


class ConsentInput(LoginInput):
    categories: list[HealthKind] = Field(max_length=20)


def enabled(settings):
    if not settings.public_auth_enabled or not settings.public_base_url.startswith("https://"):
        raise HTTPException(503, "public sign-in is not configured")
    if not settings.identity_pepper.get_secret_value():
        raise HTTPException(503, "public sign-in is not configured")


def verify_wechat(code, settings):
    if not settings.wechat_app_id or not settings.wechat_app_secret.get_secret_value():
        raise HTTPException(503, "WeChat sign-in is not configured")
    try:
        # Never log this URL: it contains the server-only application secret.
        with httpx.Client(timeout=10, follow_redirects=False) as client:
            response = client.get(
                "https://api.weixin.qq.com/sns/jscode2session",
                params={
                    "appid": settings.wechat_app_id,
                    "secret": settings.wechat_app_secret.get_secret_value(),
                    "js_code": code,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise HTTPException(503, "WeChat sign-in temporarily unavailable") from error
    if not isinstance(data, dict) or data.get("errcode") or not isinstance(data.get("openid"), str):
        raise HTTPException(401, "WeChat login expired; please sign in again")
    if not data["openid"]:
        raise HTTPException(401, "invalid WeChat identity")
    return data["openid"]


@lru_cache
def apple_keys():
    return jwt.PyJWKClient("https://appleid.apple.com/auth/keys", timeout=10, lifespan=3600)


def apple_claims(token, nonce, settings):
    try:
        key = apple_keys().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            key.key,
            algorithms=["RS256"],
            audience=settings.apple_client_id,
            issuer="https://appleid.apple.com",
            options={"require": ["exp", "iat", "sub", "aud", "iss", "nonce"]},
        )
    except jwt.PyJWTError as error:
        raise HTTPException(401, "invalid Apple identity") from error
    if not isinstance(claims["nonce"], str) or not hmac.compare_digest(claims["nonce"], nonce):
        raise HTTPException(401, "Apple login nonce mismatch")
    return claims


def verify_apple(body, nonce, settings):
    if not settings.apple_client_id or not settings.apple_client_secret.get_secret_value():
        raise HTTPException(503, "Apple sign-in is not configured")
    original = apple_claims(body.identity_token, nonce, settings)
    try:
        with httpx.Client(timeout=10, follow_redirects=False) as client:
            response = client.post(
                "https://appleid.apple.com/auth/token",
                data={
                    "client_id": settings.apple_client_id,
                    "client_secret": settings.apple_client_secret.get_secret_value(),
                    "code": body.authorization_code,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise HTTPException(503, "Apple sign-in temporarily unavailable; try again") from error
    if not isinstance(data, dict) or not data.get("id_token") or not data.get("refresh_token"):
        raise HTTPException(401, "Apple authorization code expired")
    verified = apple_claims(data["id_token"], nonce, settings)
    if original["sub"] != verified["sub"]:
        raise HTTPException(401, "Apple identity mismatch")
    return {"subject": verified["sub"], "refresh_token": data["refresh_token"]}


def provision(session, cipher, settings, provider, subject, refresh_token=None):
    digest = hash_subject(subject, settings.identity_pepper.get_secret_value())
    identity = session.scalar(
        select(IdentityBinding).where(
            IdentityBinding.provider == provider, IdentityBinding.subject_hash == digest
        )
    )
    if identity is None:
        user = User(fitcrew_user_id=str(uuid4()), status="active")
        session.add(user)
        session.flush()
        identity = IdentityBinding(
            id=str(uuid4()),
            fitcrew_user_id=user.fitcrew_user_id,
            provider=provider,
            subject_hash=digest,
            encrypted_subject=b"",
            verified_at=datetime.now(UTC),
        )
        session.add(identity)
    else:
        user = session.scalar(
            select(User)
            .where(User.fitcrew_user_id == identity.fitcrew_user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        identity = session.scalar(
            select(IdentityBinding)
            .where(IdentityBinding.provider == provider, IdentityBinding.subject_hash == digest)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if not identity or identity.revoked_at or not user or user.status != "active":
            raise HTTPException(403, "account unavailable")
    private = {"subject": subject}
    if refresh_token:
        private["refresh_token"] = refresh_token
    encrypted = cipher.encrypt_json(private, aad=f"identity:{identity.id}")
    identity.encrypted_subject = encrypted.nonce + encrypted.ciphertext
    token = secrets.token_urlsafe(48)
    device = DeviceBinding(
        id=str(uuid4()),
        fitcrew_user_id=user.fitcrew_user_id,
        device_public_id=str(uuid4()),
        token_hash=hash_device_token(token),
        platform="ios" if provider == "apple" else "wechat",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    session.add(device)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(409, "sign-in changed concurrently; please retry") from error
    return {
        "base_url": settings.public_base_url,
        "device_binding_id": device.id,
        "device_token": token,
        "consent_ids": {},
    }


@router.post("/auth/wechat")
def wechat_login(
    body: WeChatLogin,
    settings: SettingsDep,
    session: SessionDep,
    cipher: CipherDep,
    response: Response,
):
    enabled(settings)
    response.headers["Cache-Control"] = "no-store"
    subject = verify_wechat(body.code, settings)
    return provision(session, cipher, settings, "wechat:" + settings.wechat_app_id, subject)


@router.post("/auth/apple/challenge")
def challenge(settings: SettingsDep, session: SessionDep, response: Response):
    enabled(settings)
    if not settings.apple_client_id or not settings.apple_client_secret.get_secret_value():
        raise HTTPException(503, "Apple sign-in is not configured")
    now = datetime.now(UTC)
    session.execute(delete(LoginChallenge).where(LoginChallenge.expires_at < now))
    row = LoginChallenge(
        id=str(uuid4()), nonce=secrets.token_urlsafe(32), expires_at=now + timedelta(minutes=5)
    )
    session.add(row)
    session.commit()
    response.headers["Cache-Control"] = "no-store"
    return {"challenge_id": row.id, "nonce": row.nonce}


@router.post("/auth/apple")
def apple_login(
    body: AppleLogin,
    settings: SettingsDep,
    session: SessionDep,
    cipher: CipherDep,
    response: Response,
):
    enabled(settings)
    now = datetime.now(UTC)
    row = session.scalar(
        select(LoginChallenge).where(
            LoginChallenge.id == str(body.challenge_id),
            LoginChallenge.consumed_at.is_(None),
            LoginChallenge.expires_at > now,
        )
    )
    if row is None:
        raise HTTPException(401, "Apple sign-in expired; start again")
    verified = verify_apple(body, row.nonce, settings)
    claimed = session.execute(
        update(LoginChallenge)
        .where(
            LoginChallenge.id == row.id,
            LoginChallenge.consumed_at.is_(None),
            LoginChallenge.expires_at > datetime.now(UTC),
        )
        .values(consumed_at=now)
        .execution_options(synchronize_session=False)
    )
    if claimed.rowcount != 1:
        session.rollback()
        raise HTTPException(401, "Apple sign-in already used")
    response.headers["Cache-Control"] = "no-store"
    return provision(
        session, cipher, settings, "apple", verified["subject"], verified["refresh_token"]
    )


@router.post("/consents")
def consents(
    body: ConsentInput,
    principal: Annotated[DevicePrincipal, Depends(require_device)],
    session: SessionDep,
    response: Response,
):
    device = session.get(DeviceBinding, principal.device_binding_id)
    if device.platform != "ios":
        raise HTTPException(403, "HealthKit consent must be granted from the iOS app")
    user = session.scalar(
        select(User)
        .where(User.fitcrew_user_id == principal.fitcrew_user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    session.refresh(device)
    if not user or user.status != "active" or device.revoked_at:
        raise HTTPException(401, "account unavailable")
    if user.data_generation != principal.data_generation:
        raise HTTPException(409, "data was erased; refresh before granting consent")
    now = datetime.now(UTC)
    # Explicit replacement: omitted categories are withdrawn, never silently retained.
    session.execute(
        update(Consent)
        .where(
            Consent.fitcrew_user_id == principal.fitcrew_user_id,
            Consent.purpose == "private_coaching",
        )
        .values(granted=False, withdrawn_at=now)
    )
    result = {}
    for category in sorted(set(body.categories)):
        consent = Consent(
            id=str(uuid4()),
            fitcrew_user_id=principal.fitcrew_user_id,
            category=category.value,
            purpose="private_coaching",
            granted=True,
            receipt_version=body.privacy_version,
            granted_at=now,
        )
        session.add(consent)
        result[category.value] = consent.id
    session.commit()
    response.headers["Cache-Control"] = "no-store"
    return {"consent_ids": result}


def revoke_apple_identity(session, cipher, user_id, settings):
    identities = session.scalars(
        select(IdentityBinding).where(
            IdentityBinding.fitcrew_user_id == user_id,
            IdentityBinding.provider == "apple",
            IdentityBinding.revoked_at.is_(None),
        )
    ).all()
    for identity in identities:
        private = cipher.decrypt_json(
            EncryptedValue(identity.encrypted_subject[:12], identity.encrypted_subject[12:]),
            aad=f"identity:{identity.id}",
        )
        token = private.get("refresh_token")
        if not token:
            continue
        if not settings.apple_client_secret.get_secret_value():
            raise HTTPException(503, "Apple account revocation temporarily unavailable")
        try:
            with httpx.Client(timeout=10, follow_redirects=False) as client:
                response = client.post(
                    "https://appleid.apple.com/auth/revoke",
                    data={
                        "client_id": settings.apple_client_id,
                        "client_secret": settings.apple_client_secret.get_secret_value(),
                        "token": token,
                        "token_type_hint": "refresh_token",
                    },
                )
                response.raise_for_status()
        except httpx.HTTPError as error:
            raise HTTPException(
                503, "Apple revocation failed; no deletion claimed, please retry"
            ) from error
