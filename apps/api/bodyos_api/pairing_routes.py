from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from bodyos_api.db import get_session
from bodyos_api.enrollment import EnrollmentConflict, EnrollmentNotFound, redeem_pairing_exchange

router = APIRouter(prefix="/v1/pairing", tags=["pairing"])
_pairing_bearer = HTTPBearer(auto_error=False)


@router.post("/exchange")
def exchange_pairing(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_pairing_bearer)],
    session: Annotated[Session, Depends(get_session)],
) -> dict:
    if (
        credentials is None
        or credentials.scheme.casefold() != "bearer"
        or not credentials.credentials
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid pairing code")
    try:
        result = redeem_pairing_exchange(session, pairing_code=credentials.credentials)
    except (EnrollmentConflict, EnrollmentNotFound) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="pairing exchange unavailable"
        ) from error
    return {
        "base_url": result.base_url,
        "device_binding_id": result.device_binding_id,
        "consent_ids": result.consent_ids,
        "device_token": result.device_token,
    }
