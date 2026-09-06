from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from bodyos_api.auth import DevicePrincipal, require_device
from bodyos_api.config import Settings, get_settings
from bodyos_api.crypto import FieldCipher
from bodyos_api.db import get_session
from bodyos_api.health_service import HealthIngestionService
from bodyos_api.model_gateway import RoutedModelGateway
from bodyos_api.models import User
from bodyos_api.product import ProductService
from bodyos_api.product_ai import capabilities, select_action, set_ai_consent
from bodyos_api.public_auth import revoke_apple_identity
from bodyos_api.runtime import get_field_cipher, get_model_gateway

router = APIRouter(prefix="/v3", tags=["private-product"])


class Mutation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID


class JourneyInput(Mutation):
    goal: Literal["sleep", "energy", "activity"]


class LogInput(Mutation):
    energy: int = Field(ge=1, le=5)
    stress: int = Field(ge=1, le=3)
    feeling: Literal["充沛", "正常", "有点累", "很累", "不适"]
    note: str = Field(default="", max_length=500)


class TransitionInput(Mutation):
    action: Literal["accept", "pause", "resume", "stop", "evaluate"]
    revision: int = Field(ge=1)


class MissionInput(Mutation):
    action: Literal["done", "lighten", "skip"]


class DeleteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmation: Literal["DELETE"]


class AIConsentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    granted: bool
    provider_notice_version: str = Field(max_length=32)


def service(
    principal: Annotated[DevicePrincipal, Depends(require_device)],
    session: Annotated[Session, Depends(get_session)],
    cipher: Annotated[FieldCipher, Depends(get_field_cipher)],
    response: Response,
) -> ProductService:
    user = session.get(User, principal.fitcrew_user_id)
    if user is None or user.status != "active":
        raise HTTPException(401, "account unavailable")
    response.headers["Cache-Control"] = "no-store"
    return ProductService(
        session,
        cipher,
        principal.fitcrew_user_id,
        principal.data_generation,
        principal.device_binding_id,
    )


Service = Annotated[ProductService, Depends(service)]


@router.get("/state")
def state(svc: Service):
    return svc.state()


@router.put("/journey")
def journey(body: JourneyInput, svc: Service):
    return svc.mutate("journey", body.model_dump(mode="json"), lambda: svc.set_journey(body.goal))


@router.post("/experiments/propose")
def propose(
    body: Mutation,
    svc: Service,
    settings: Annotated[Settings, Depends(get_settings)],
    gateway: Annotated[RoutedModelGateway, Depends(get_model_gateway)],
):
    return svc.mutate(
        "propose",
        body.model_dump(mode="json"),
        lambda: svc.propose(select_action(svc, settings, gateway)),
    )


@router.get("/capabilities")
def ai_capabilities(svc: Service, settings: Annotated[Settings, Depends(get_settings)]):
    return capabilities(svc, settings)


@router.post("/ai-consent")
def ai_consent(
    body: AIConsentInput, svc: Service, settings: Annotated[Settings, Depends(get_settings)]
):
    return set_ai_consent(svc, settings, body.granted, body.provider_notice_version)


@router.post("/experiments/{resource_id}/transition")
def transition(resource_id: UUID, body: TransitionInput, svc: Service):
    return svc.mutate(
        f"transition:{resource_id}",
        body.model_dump(mode="json"),
        lambda: svc.transition(str(resource_id), body.action, body.revision),
    )


@router.post("/logs")
def add_log(body: LogInput, svc: Service):
    return svc.mutate(
        "log",
        body.model_dump(mode="json"),
        lambda: svc.add_log(body.model_dump(exclude={"request_id"})),
    )


@router.delete("/logs/{resource_id}")
def delete_log(resource_id: UUID, svc: Service):
    return svc.delete_log(str(resource_id))


@router.post("/mission")
def mission(body: MissionInput, svc: Service):
    return svc.mutate("mission", body.model_dump(mode="json"), lambda: svc.act(body.action))


@router.get("/export")
def export(svc: Service):
    return {
        **svc.state(),
        "health_export": HealthIngestionService(svc.session, svc.cipher).export_user_health(
            svc.user_id
        ),
    }


@router.delete("/data")
def erase_data(body: DeleteInput, svc: Service):
    return svc.erase()


@router.delete("/account")
def erase_account(
    body: DeleteInput, svc: Service, settings: Annotated[Settings, Depends(get_settings)]
):
    svc.lock()
    revoke_apple_identity(svc.session, svc.cipher, svc.user_id, settings)
    return svc.erase(account=True)
