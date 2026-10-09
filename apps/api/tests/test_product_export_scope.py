from bodyos_api.models import AuditEvent
from sqlalchemy import select
from test_v3_routes import client_for, rid


def test_exports_enforce_scope_and_issue_generation_receipts(session, field_cipher):
    client, uid = client_for(session, field_cipher)
    client.post("/v3/logs", json=rid(energy=3, stress=1, feeling="正常", note="private note"))
    product = client.get("/v3/export?scope=product").json()
    assert product["logs"][0]["note"] == "private note"
    assert "health_export" not in product
    assert "health_trends" not in product
    assert "health" not in product and "today_context" not in product
    health = client.get("/v3/export?scope=health").json()
    assert set(health) == {"health_export", "export_metadata"}
    assert health["health_export"]["fitcrew_user_id"] == uid
    assert "private note" not in str(health)
    complete = client.get("/v3/export").json()
    assert "logs" in complete and "health_export" in complete
    for value, scope in [(product, "product"), (health, "health"), (complete, "all")]:
        meta = value["export_metadata"]
        assert meta["scope"] == scope
        event = session.scalar(select(AuditEvent).where(AuditEvent.id == meta["receipt_id"]))
        assert event.fitcrew_user_id == uid
        assert event.event_type == "product.export.generated"
    assert client.get("/v3/export?scope=arbitrary").status_code == 422
    other, _ = client_for(session, field_cipher, "other-export-user")
    assert other.get("/v3/export?scope=product").json()["logs"] == []
