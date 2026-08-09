from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from bodyos_api.auth import require_owner
from bodyos_api.config import Settings, get_settings
from bodyos_api.crypto import FieldCipher
from bodyos_api.db import get_session
from bodyos_api.enrollment import (
    EnrollmentConflict,
    EnrollmentNotFound,
    ensure_owner_feishu_user,
    find_invited_user_id,
    hash_subject,
    invite_feishu_user,
    issue_pairing_exchange,
    revoke_invited_user,
)
from bodyos_api.models import DeviceBinding, IdentityBinding
from bodyos_api.runtime import get_field_cipher
from bodyos_api.schemas import HealthKind

router = APIRouter(prefix="/v1/owner", tags=["owner"])


class OwnerBootstrapIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feishu_subject: str = Field(min_length=3, max_length=200)
    device_public_id: str = Field(min_length=3, max_length=128)
    categories: set[HealthKind] = Field(min_length=1)
    idempotency_key: str = Field(min_length=32, max_length=200)


class OwnerIdentityRebindIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feishu_subject: str = Field(min_length=3, max_length=200)
    device_public_id: str = Field(min_length=3, max_length=128)


class UserInviteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feishu_subject: str = Field(min_length=3, max_length=200)
    locale: str = Field(default="zh-CN", min_length=2, max_length=16)
    timezone: str = Field(default="Asia/Shanghai", min_length=1, max_length=64)


class UserPairIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feishu_subject: str = Field(min_length=3, max_length=200)
    device_public_id: str = Field(min_length=3, max_length=128)
    categories: set[HealthKind] = Field(min_length=1)
    idempotency_key: str = Field(min_length=32, max_length=200)


class UserRevokeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feishu_subject: str = Field(min_length=3, max_length=200)
    device_public_id: str | None = Field(default=None, min_length=3, max_length=128)


@router.post("/bootstrap")
def bootstrap_owner_device(
    request: OwnerBootstrapIn,
    _: Annotated[None, Depends(require_owner)],
    session: Annotated[Session, Depends(get_session)],
    cipher: Annotated[FieldCipher, Depends(get_field_cipher)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> JSONResponse:
    try:
        user_id = ensure_owner_feishu_user(
            session,
            cipher,
            subject=request.feishu_subject,
            pepper=settings.identity_pepper.get_secret_value(),
        )
        result = issue_pairing_exchange(
            session,
            fitcrew_user_id=user_id,
            device_public_id=request.device_public_id,
            categories=request.categories,
            public_base_url=settings.public_base_url,
            idempotency_key=request.idempotency_key,
        )
    except EnrollmentConflict as error:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error
    return JSONResponse(
        status_code=201 if result.created else 200,
        content={"pairing_url": result.pairing_url, "expires_at": result.expires_at.isoformat()},
    )


@router.post("/users/invite")
def invite_user(
    request: UserInviteIn,
    _: Annotated[None, Depends(require_owner)],
    session: Annotated[Session, Depends(get_session)],
    cipher: Annotated[FieldCipher, Depends(get_field_cipher)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> JSONResponse:
    try:
        result = invite_feishu_user(
            session,
            cipher,
            subject=request.feishu_subject,
            pepper=settings.identity_pepper.get_secret_value(),
            locale=request.locale,
            timezone=request.timezone,
        )
    except EnrollmentConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return JSONResponse(
        status_code=201 if result.created else 200,
        content={"created": result.created, "status": result.status},
    )


@router.post("/users/pair", status_code=status.HTTP_201_CREATED)
def pair_user(
    request: UserPairIn,
    _: Annotated[None, Depends(require_owner)],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    try:
        user_id = find_invited_user_id(
            session,
            subject=request.feishu_subject,
            pepper=settings.identity_pepper.get_secret_value(),
        )
        result = issue_pairing_exchange(
            session,
            fitcrew_user_id=user_id,
            device_public_id=request.device_public_id,
            categories=request.categories,
            public_base_url=settings.public_base_url,
            idempotency_key=request.idempotency_key,
        )
    except EnrollmentNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except EnrollmentConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return JSONResponse(
        status_code=201 if result.created else 200,
        content={"pairing_url": result.pairing_url, "expires_at": result.expires_at.isoformat()},
    )


@router.post("/users/revoke")
def revoke_user(
    request: UserRevokeIn,
    _: Annotated[None, Depends(require_owner)],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    try:
        user_id = find_invited_user_id(
            session,
            subject=request.feishu_subject,
            pepper=settings.identity_pepper.get_secret_value(),
        )
        revoke_invited_user(
            session,
            fitcrew_user_id=user_id,
            device_public_id=request.device_public_id,
        )
    except EnrollmentNotFound as error:
        raise HTTPException(status_code=404, detail="invited user not found") from error
    return {"revoked": True}


@router.post("/identity/rebind")
def rebind_owner_identity(
    request: OwnerIdentityRebindIn,
    _: Annotated[None, Depends(require_owner)],
    session: Annotated[Session, Depends(get_session)],
    cipher: Annotated[FieldCipher, Depends(get_field_cipher)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    device = session.scalar(
        select(DeviceBinding).where(
            DeviceBinding.device_public_id == request.device_public_id,
            DeviceBinding.revoked_at.is_(None),
        )
    )
    if device is None:
        raise HTTPException(status_code=404, detail="active owner device not found")

    now = datetime.now(UTC)
    subject_hash = hash_subject(
        request.feishu_subject, settings.identity_pepper.get_secret_value()
    )
    current = session.scalar(
        select(IdentityBinding).where(
            IdentityBinding.provider == "feishu",
            IdentityBinding.subject_hash == subject_hash,
        )
    )
    if current is not None and current.fitcrew_user_id != device.fitcrew_user_id:
        raise HTTPException(status_code=409, detail="identity is bound to another owner")

    active_identities = session.scalars(
        select(IdentityBinding).where(
            IdentityBinding.provider == "feishu",
            IdentityBinding.fitcrew_user_id == device.fitcrew_user_id,
            IdentityBinding.revoked_at.is_(None),
        )
    ).all()
    changed = current is None or current.revoked_at is not None or any(
        identity.id != current.id for identity in active_identities if current is not None
    )

    for identity in active_identities:
        if current is None or identity.id != current.id:
            identity.revoked_at = now

    if current is None:
        current = IdentityBinding(
            fitcrew_user_id=device.fitcrew_user_id,
            provider="feishu",
            subject_hash=subject_hash,
            encrypted_subject=b"",
            verified_at=now,
        )
        session.add(current)
        session.flush()

    encrypted_subject = cipher.encrypt_json(
        {"subject": request.feishu_subject}, aad=f"identity:{current.id}"
    )
    current.encrypted_subject = encrypted_subject.nonce + encrypted_subject.ciphertext
    current.verified_at = now
    current.revoked_at = None
    session.commit()
    return {"changed": changed}
