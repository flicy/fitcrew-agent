import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from bodyos_api.config import Settings, get_settings
from bodyos_api.db import get_session
from bodyos_api.models import DeviceBinding, User

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class DevicePrincipal:
    fitcrew_user_id: str
    device_binding_id: str
    data_generation: int = 0


def require_owner(
    settings: Annotated[Settings, Depends(get_settings)],
    owner_token: Annotated[str | None, Header(alias="X-Owner-Token")] = None,
) -> None:
    configured = settings.owner_token.get_secret_value()
    if not configured or not owner_token or not hmac.compare_digest(configured, owner_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid owner token")


def require_internal(
    settings: Annotated[Settings, Depends(get_settings)],
    token: Annotated[str | None, Header(alias="X-BodyOS-Token")] = None,
) -> None:
    configured = settings.internal_token.get_secret_value()
    if not configured or not token or not hmac.compare_digest(configured, token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid internal token"
        )


def require_model_proxy(
    settings: Annotated[Settings, Depends(get_settings)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> None:
    configured = settings.model_proxy_token.get_secret_value()
    supplied = credentials.credentials if credentials else ""
    if not configured or not supplied or not hmac.compare_digest(configured, supplied):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid proxy token")


def hash_device_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def require_device(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[Session, Depends(get_session)],
) -> DevicePrincipal:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid device token")
    candidate_hash = hash_device_token(credentials.credentials)
    bindings = session.scalars(
        select(DeviceBinding).where(DeviceBinding.revoked_at.is_(None))
    ).all()
    binding = next(
        (item for item in bindings if hmac.compare_digest(item.token_hash, candidate_hash)),
        None,
    )
    if binding is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid device token")
    if binding.expires_at is not None:
        expiry = binding.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)
        if expiry <= datetime.now(UTC):
            raise HTTPException(status_code=401, detail="device session expired")
    user = session.get(User, binding.fitcrew_user_id)
    if user is None or user.status != "active":
        raise HTTPException(status_code=401, detail="account unavailable")
    return DevicePrincipal(
        fitcrew_user_id=binding.fitcrew_user_id,
        device_binding_id=binding.id,
        data_generation=user.data_generation,
    )
