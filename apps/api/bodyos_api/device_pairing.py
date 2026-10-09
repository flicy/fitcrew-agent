"""Connect an iOS device to an authenticated WeChat account without merging identities."""

import hashlib
import hmac
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select, update

from bodyos_api.auth import DevicePrincipal, require_device
from bodyos_api.enrollment import EnrollmentConflict, issue_pairing_exchange
from bodyos_api.models import DeviceBinding, PairingExchangeSession, User
from bodyos_api.public_auth import LoginInput, SessionDep, SettingsDep, enabled

router = APIRouter(prefix="/v3/device-pairing", tags=["device-pairing"])
Principal = Annotated[DevicePrincipal, Depends(require_device)]


class PairingInput(LoginInput):
    request_id: UUID


def lock_account(session, principal):
    user = session.scalar(
        select(User)
        .where(User.fitcrew_user_id == principal.fitcrew_user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    device = session.get(DeviceBinding, principal.device_binding_id)
    if device is not None:
        session.refresh(device)
    if not user or user.status != "active" or device is None or device.revoked_at:
        raise HTTPException(401, "account unavailable")
    if device.platform != "wechat":
        raise HTTPException(403, "create this connection from the WeChat account")
    if user.data_generation != principal.data_generation:
        raise HTTPException(409, "data changed; refresh before connecting")


@router.post("")
def issue(
    body: PairingInput,
    principal: Principal,
    session: SessionDep,
    settings: SettingsDep,
    response: Response,
):
    enabled(settings)
    lock_account(session, principal)
    key = hmac.new(
        settings.identity_pepper.get_secret_value().encode(),
        f"device-pairing:{principal.fitcrew_user_id}:{body.request_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    session.execute(
        update(PairingExchangeSession)
        .where(
            PairingExchangeSession.fitcrew_user_id == principal.fitcrew_user_id,
            PairingExchangeSession.preserve_consents.is_(True),
            PairingExchangeSession.idempotency_key_hash != key_hash,
            PairingExchangeSession.consumed_at.is_(None),
            PairingExchangeSession.invalidated_at.is_(None),
        )
        .values(invalidated_at=datetime.now(UTC))
    )
    try:
        invitation = issue_pairing_exchange(
            session,
            fitcrew_user_id=principal.fitcrew_user_id,
            device_public_id="wechat-ios-" + key_hash,
            categories=set(),
            public_base_url=settings.public_base_url,
            idempotency_key=key,
            preserve_consents=True,
        )
        # A retry may return an existing invitation without committing.
        session.commit()
    except EnrollmentConflict as error:
        session.rollback()
        raise HTTPException(409, "connection expired or used; create a new connection") from error
    response.headers["Cache-Control"] = "no-store"
    return {"pairing_url": invitation.pairing_url, "expires_at": invitation.expires_at.isoformat()}


@router.delete("")
def cancel(principal: Principal, session: SessionDep, response: Response):
    lock_account(session, principal)
    session.execute(
        update(PairingExchangeSession)
        .where(
            PairingExchangeSession.fitcrew_user_id == principal.fitcrew_user_id,
            PairingExchangeSession.preserve_consents.is_(True),
            PairingExchangeSession.consumed_at.is_(None),
            PairingExchangeSession.invalidated_at.is_(None),
        )
        .values(invalidated_at=datetime.now(UTC))
    )
    session.commit()
    response.headers["Cache-Control"] = "no-store"
    return {"cancelled": True}


@router.get("/devices")
def devices(principal: Principal, session: SessionDep, response: Response):
    lock_account(session, principal)
    rows = session.scalars(
        select(DeviceBinding)
        .where(
            DeviceBinding.fitcrew_user_id == principal.fitcrew_user_id,
            DeviceBinding.device_public_id.startswith("wechat-ios-"),
            DeviceBinding.revoked_at.is_(None),
            DeviceBinding.expires_at > datetime.now(UTC),
        )
        .order_by(DeviceBinding.created_at.desc())
    ).all()
    response.headers["Cache-Control"] = "no-store"
    return {
        "devices": [
            {
                "id": row.id,
                "connected_at": row.created_at.isoformat(),
                "last_sync_at": row.last_sync_at.isoformat() if row.last_sync_at else None,
                "expires_at": row.expires_at.isoformat(),
            }
            for row in rows
        ]
    }


@router.delete("/devices/{device_id}")
def disconnect(device_id: UUID, principal: Principal, session: SessionDep, response: Response):
    lock_account(session, principal)
    device = session.scalar(
        select(DeviceBinding)
        .where(
            DeviceBinding.id == str(device_id),
            DeviceBinding.fitcrew_user_id == principal.fitcrew_user_id,
            DeviceBinding.device_public_id.startswith("wechat-ios-"),
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if device is None:
        raise HTTPException(404, "connected device not found")
    device.revoked_at = datetime.now(UTC)
    session.commit()
    response.headers["Cache-Control"] = "no-store"
    return {"disconnected": True, "device_id": device.id}
