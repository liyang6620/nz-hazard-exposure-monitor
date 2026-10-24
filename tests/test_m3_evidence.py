import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_m3_event_time_fields_keep_unsupported_history_nullable() -> None:
    payload = json.loads((ROOT / "evidence/m3/m3-replay.json").read_text(encoding="utf-8"))
    assert payload["as_if_today_buildings"] == 3_219_311
    assert payload["event_time_lifecycle_support_start"] == "2018-10-16T00:00:00Z"

    events = {event["event_id"]: event for event in payload["events"]}
    unsupported = [
        event for event in events.values() if event["event_time_status"] == "not_supported"
    ]
    supported = [event for event in events.values() if event["event_time_status"] == "supported"]

    assert len(events) == 10
    assert len(unsupported) == 8
    assert all(event["valid_buildings"] is None for event in unsupported)
    assert all(event["as_if_today_buildings"] == 3_219_311 for event in events.values())
    assert all(event["valid_buildings"] is not None for event in supported)
