"""Constrained AI action selection through the existing de-identified gateway."""

import json
from datetime import timedelta

from sqlalchemy import select, update

from bodyos_api.model_gateway import HarnessFailure, ModelEnvelopeRejected
from bodyos_api.models import Consent


def capabilities(svc, settings):
    available = bool(
        settings.product_ai_enabled
        and settings.product_ai_provider
        and settings.product_ai_notice_version
    )
    consent = svc.session.scalar(
        select(Consent).where(
            Consent.fitcrew_user_id == svc.user_id,
            Consent.category == "product_ai",
            Consent.purpose == "experiment_selection",
            Consent.granted.is_(True),
            Consent.withdrawn_at.is_(None),
            Consent.receipt_version == settings.product_ai_notice_version,
        )
    )
    return {
        "ai_available": available,
        "ai_provider": settings.product_ai_provider,
        "ai_notice_version": settings.product_ai_notice_version,
        "ai_consent_granted": available and consent is not None,
        "ai_notice": "经你单独同意后，将目标类别、近 7 天记录天数及精力/压力均值"
        "发送给所示 AI 服务，"
        "用于从低风险行动中选择实验。不发送备注、身份或原始 Apple 健康数据；可随时撤回。",
    }


def set_ai_consent(svc, settings, granted, version):
    from fastapi import HTTPException

    svc.lock()
    caps = capabilities(svc, settings)
    if granted and (not caps["ai_available"] or version != caps["ai_notice_version"]):
        raise HTTPException(409, "AI provider disclosure changed or is unavailable")
    svc.session.execute(
        update(Consent)
        .where(Consent.fitcrew_user_id == svc.user_id, Consent.category == "product_ai")
        .values(granted=False, withdrawn_at=svc.now())
    )
    if granted:
        svc.session.add(
            Consent(
                fitcrew_user_id=svc.user_id,
                category="product_ai",
                purpose="experiment_selection",
                granted=True,
                receipt_version=version,
                granted_at=svc.now(),
            )
        )
    svc.session.commit()
    return capabilities(svc, settings)


def select_action(svc, settings, gateway):
    if any(
        svc.read(row)["status"] in {"proposed", "running", "paused"}
        for row in svc.rows("experiment")
    ):
        return {"source": "rule_based", "ai_status": "reused", "choice": "standard"}
    if not capabilities(svc, settings)["ai_consent_granted"]:
        return {"source": "rule_based", "ai_status": "not_authorized", "choice": "standard"}
    journey = svc.read(svc.row("journey", "current"))
    if not journey:
        return {"source": "rule_based", "ai_status": "not_ready", "choice": "standard"}
    start = (svc.now() - timedelta(days=7)).isoformat()
    records = [svc.read(r) for r in svc.rows("log")]
    records = [r for r in records if r["created_at"] >= start]
    features = {
        "goal_category": journey["goal"],
        "observed_days": len({r["date"] for r in records}),
        "energy_mean": round(sum(r["energy"] for r in records) / len(records), 1)
        if records
        else None,
        "stress_mean": round(sum(r["stress"] for r in records) / len(records), 1)
        if records
        else None,
    }
    envelope = {
        "schema_version": "bodyos-model.v1",
        "intent": "choose_low_risk_experiment",
        "channel": "dm",
        "features": features,
        "knowledge": [],
        "constraints": [
            'Return exactly JSON {"choice":"standard"} or {"choice":"gentle"}.',
            "standard means the user's goal-based small action; gentle means observation only.",
            "Prefer gentle if energy is low, stress is high or evidence is missing.",
            "Do not invent observations, add free text, diagnosis or medical claims.",
        ],
    }
    try:
        result = gateway.respond(envelope)
        selected = json.loads(result.text)
        if set(selected) != {"choice"} or selected["choice"] not in {"standard", "gentle"}:
            raise ValueError("not an approved action")
        return {"source": "ai_selected", "ai_status": "available", "choice": selected["choice"]}
    except (HarnessFailure, ModelEnvelopeRejected, ValueError, TypeError):
        return {"source": "rule_based", "ai_status": "unavailable", "choice": "standard"}
