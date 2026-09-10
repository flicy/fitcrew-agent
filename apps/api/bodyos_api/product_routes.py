from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from bodyos_api.auth import DevicePrincipal, require_device
from bodyos_api.config import Settings, get_settings
from bodyos_api.crypto import FieldCipher
from bodyos_api.db import get_session
from bodyos_api.health_service import HealthIngestionService
from bodyos_api.model_gateway import RoutedModelGateway
from bodyos_api.models import AuditEvent, User
from bodyos_api.product import ProductService
from bodyos_api.product_ai import capabilities, select_action, set_ai_consent
from bodyos_api.public_auth import revoke_apple_identity
from bodyos_api.runtime import get_field_cipher, get_model_gateway

router = APIRouter(prefix="/v3", tags=["private-product"])


class Mutation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID


class OnboardingInput(Mutation):
    step: Literal[1, 2, 3, 4, 5, 6]
    route: Literal["manual", "health"] | None = None


class JourneyInput(Mutation):
    goal: Literal["sleep", "energy", "activity"]


class LogInput(Mutation):
    energy: int = Field(ge=1, le=5)
    stress: int = Field(ge=1, le=3)
    feeling: Literal["充沛", "正常", "有点累", "很累", "不适"]
    note: str = Field(default="", max_length=500)
    sleep_feeling: Literal["醒后清爽", "一般", "醒后疲惫"] | None = None
    training_feeling: Literal["完成", "偏累", "恢复良好"] | None = None
    stress_source: Literal["工作", "学习", "人际", "其他"] | None = None


class TransitionInput(Mutation):
    action: Literal["accept", "pause", "resume", "stop", "evaluate"]
    revision: int = Field(ge=1)


class FeedbackInput(Mutation):
    revision: int = Field(ge=1)
    assessment: Literal["fits", "not_fit", "uncertain"]
    confirm_memory: bool = False


class MissionInput(Mutation):
    action: Literal["done", "lighten", "skip"]
    alternative: Literal["brief_check", "quiet_minute"] = "brief_check"
    mission_id: str | None = Field(default=None, max_length=10)
    revision: int | None = Field(default=None, ge=0)


class DeleteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmation: Literal["DELETE"]


class DataDeleteInput(DeleteInput):
    scope: Literal["all", "logs"] = "all"


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


@router.post("/onboarding")
def onboarding(body: OnboardingInput, svc: Service):
    return svc.mutate(
        "onboarding",
        body.model_dump(mode="json"),
        lambda: svc.advance_onboarding(body.step, body.route),
    )


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


@router.post("/experiments/{resource_id}/feedback")
def feedback(resource_id: UUID, body: FeedbackInput, svc: Service):
    return svc.mutate(
        f"feedback:{resource_id}",
        body.model_dump(mode="json"),
        lambda: svc.feedback(str(resource_id), body.revision, body.assessment, body.confirm_memory),
    )


@router.delete("/memories/{resource_id}")
def delete_memory(resource_id: UUID, svc: Service):
    return svc.delete_memory(str(resource_id))


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
    return svc.mutate(
        "mission",
        body.model_dump(mode="json"),
        lambda: svc.act(body.action, body.alternative, body.mission_id, body.revision),
    )


@router.get("/export")
def export(svc: Service, scope: Literal["all", "product", "health"] = "all"):
    result = {}
    if scope in {"all", "product"}:
        result = svc.state()
        if scope == "product":
            for key in ("health", "today_context", "health_trends"):
                result.pop(key, None)
            for item in result["experiments"]:
                item.pop("health_observation", None)
    if scope in {"all", "health"}:
        result["health_export"] = HealthIngestionService(
            svc.session, svc.cipher
        ).export_user_health(svc.user_id)
    receipt = str(uuid4())
    svc.session.add(
        AuditEvent(
            id=receipt,
            fitcrew_user_id=svc.user_id,
            event_type="product.export.generated",
            resource_type="private_data",
            policy_result="allowed",
            trace_id=receipt,
        )
    )
    svc.session.commit()
    result["export_metadata"] = {
        "scope": scope,
        "generated_at": svc.now().isoformat(),
        "receipt_id": receipt,
        "notice": "仅证明服务器生成此范围的数据，不证明文件已保存或发送。",
    }
    return result


@router.delete("/data")
def erase_data(body: DataDeleteInput, svc: Service):
    return svc.erase_logs() if body.scope == "logs" else svc.erase()


@router.delete("/account")
def erase_account(
    body: DeleteInput, svc: Service, settings: Annotated[Settings, Depends(get_settings)]
):
    svc.lock()
    revoke_apple_identity(svc.session, svc.cipher, svc.user_id, settings)
    return svc.erase(account=True)


@router.delete("/milestones/{resource_id}")
def withdraw_milestone(resource_id: UUID, svc: Service):
    return svc.withdraw_milestone(str(resource_id))
