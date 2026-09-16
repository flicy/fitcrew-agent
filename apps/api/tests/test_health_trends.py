from uuid import uuid4

from bodyos_api.health_service import HealthIngestionService
from bodyos_api.health_trends import health_trends
from bodyos_api.models import Consent
from bodyos_api.schemas import HealthSyncBatchIn
from test_health_ingest import CONSENT_ID, USER_ID, glucose_batch, seed_authorized_owner


def test_health_trends_deduplicate_preserve_zero_and_hide_source_conflicts(session, field_cipher):
    seed_authorized_owner(session)
    session.get(Consent, CONSENT_ID).category = "step_count"
    session.commit()
    data = glucose_batch().model_dump(mode="json")
    sample = data["samples"][0]
    sample.update(
        kind="step_count",
        value=0,
        unit="count",
        start_at="2026-08-01T09:00:00+08:00",
        end_at="2026-08-01T09:00:00+08:00",
    )
    data["samples"].append({**sample, "sample_id": str(uuid4())})
    service = HealthIngestionService(session, field_cipher)
    service.ingest(USER_ID, HealthSyncBatchIn.model_validate(data))

    def read(categories, uid=USER_ID):
        return health_trends(session, field_cipher, uid, categories, "2026-08-01", "Asia/Shanghai")

    points = read(["step_count"])["points"]
    assert len(points) == 90
    assert points[-2]["metrics"]["steps"]["value"] is None
    assert points[-1]["metrics"]["steps"]["value"] == 0
    assert points[-1]["metrics"]["steps"]["sample_count"] == 2
    assert points[-1]["metrics"]["sleep"]["status"] == "not_authorized"
    data["batch_id"] = str(uuid4())
    data["samples"] = [
        {**sample, "sample_id": str(uuid4()), "source": "second-device", "value": 100}
    ]
    service.ingest(USER_ID, HealthSyncBatchIn.model_validate(data))
    metric = read(["step_count"])["points"][-1]["metrics"]["steps"]
    assert metric["value"] is None and metric["status"] == "source_conflict"
    assert len(metric["sources"]) == 2
    assert read([])["points"][-1]["metrics"]["steps"]["sources"] == []
    assert read(["step_count"], str(uuid4()))["points"][-1]["metrics"]["steps"]["value"] is None
