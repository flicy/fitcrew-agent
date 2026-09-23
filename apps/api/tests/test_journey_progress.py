from datetime import timedelta

from test_product_results import fixture_experiment


def test_journey_calendar_boundaries_and_record_retraction(session, field_cipher):
    svc, _, start = fixture_experiment(session, field_cipher)
    journey = svc.state()["journey"]
    assert svc.journey_progress(None, []) is None
    assert svc.journey_progress(journey, [])["missing_days"] == 1
    first = svc.add_log({"energy": 3, "stress": 1, "feeling": "正常", "note": ""})
    svc.add_log({"energy": 4, "stress": 1, "feeling": "正常", "note": ""})
    assert svc.state()["journey_progress"]["observed_days"] == 1
    for offset, phase, day in [
        (29, 1, 30),
        (30, 2, 31),
        (59, 2, 60),
        (60, 3, 61),
        (89, 3, 90),
        (100, 3, 90),
    ]:
        svc.now = lambda offset=offset: start + timedelta(days=offset)
        progress = svc.state()["journey_progress"]
        assert (progress["phase"], progress["day"]) == (phase, day)
        assert progress["missing_days"] == day - 1
    svc.add_log({"energy": 5, "stress": 1, "feeling": "正常", "note": ""})
    assert svc.state()["journey_progress"]["observed_days"] == 1  # outside original window
    svc.delete_log(first["id"])
    assert svc.state()["journey_progress"]["observed_days"] == 1  # another same-day source
    for record in svc.state()["logs"]:
        svc.delete_log(record["id"])
    assert svc.state()["journey_progress"]["observed_days"] == 0
    assert svc.state()["journey_progress"]["missing_days"] == 90
