from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from nzhem.adapters.local.site_data import LocalSiteDataPublisher, _event_label, _mmi_band
from nzhem.adapters.local.sqlite import SqliteTableStore


def _publisher(tmp_path: Path) -> tuple[LocalSiteDataPublisher, SqliteTableStore]:
    tables = SqliteTableStore(tmp_path / "state.db")
    return (
        LocalSiteDataPublisher(
            event_root=tmp_path / "events",
            reference_root=tmp_path / "reference",
            web_root=tmp_path / "web",
            tables=tables,
        ),
        tables,
    )


def test_mmi_bands_and_event_labels_are_stable() -> None:
    assert [_mmi_band(value) for value in (3.9, 4, 5.9, 6, 7, 8.1)] == [
        "<4",
        "4",
        "5",
        "6",
        "7",
        "8+",
    ]
    assert _event_label("kaikoura_2016") == "Kaikōura 2016"
    assert _event_label("eketahuna_2014") == "Eketāhuna 2014"


def test_builds_summary_map_alternative_and_regional_exposure(tmp_path: Path) -> None:
    publisher, _ = _publisher(tmp_path)
    event = {
        "event_id": "event-1",
        "event_name": "test_event",
        "origin_time": datetime(2026, 10, 26, tzinfo=UTC),
        "magnitude": 6.5,
        "depth_km": 12,
        "latitude": -41,
        "longitude": 174,
        "max_mmi": 7.2,
        "buildings_mmi_ge_6": 12,
        "population_mmi_ge_6": 21.4,
        "mmi_source": "official",
        "shaking_version": "v1",
        "shaking_type": "reviewed",
        "event_time_status": "supported",
    }
    exposure = [
        {
            "event_id": "event-1",
            "h3_res8": 123,
            "h3_res6": 123,
            "mmi": 7.2,
            "as_if_today_building_count": 12,
            "current_building_count": 12,
            "population_2023": 21.4,
            "mmi_source": "official",
            "source_version": "v1",
            "geometry_wkt": "POLYGON ((174 -41, 174.1 -41, 174.1 -41.1, 174 -41.1, 174 -41))",
        }
    ]

    payload = publisher._build_event_payloads(  # noqa: SLF001
        [event], exposure, {123: ("WGN", "Wellington Region")}, {}
    )["event-1"]

    summary = payload["summary"]
    assert summary["name"] == "Test Event"
    assert summary["regions"][0]["buildings"] == 12
    assert summary["most_affected_region"] == "Wellington Region"
    assert sum(row["buildings"] for row in summary["regions"]) == summary["buildings_mmi_ge_6"]
    assert "Wellington Region was most affected" in summary["map_summary"]
    assert "12 buildings and 21 people" in summary["map_summary"]
    assert payload["features"]["features"][0]["properties"]["mmi_band"] == "7"


def test_merges_recent_geonet_events_and_preserves_ready_results(tmp_path: Path) -> None:
    publisher, tables = _publisher(tmp_path)
    tables.upsert_entity(
        "eventsstate",
        {
            "PartitionKey": "recent",
            "RowKey": "new-event",
            "event_id": "new-event",
            "event_time": "2026-10-25T00:00:00Z",
            "magnitude": 4.3,
            "depth_km": 20,
            "latitude": -42,
            "longitude": 173,
            "event_name": "Near Kaikoura",
        },
    )
    tables.upsert_entity(
        "eventsstate",
        {
            "PartitionKey": "recent",
            "RowKey": "old-event",
            "event_id": "old-event",
            "event_time": "2026-01-01T00:00:00Z",
            "magnitude": 5,
        },
    )
    ready = {
        "event_id": "ready-event",
        "origin_time": "2026-10-24T00:00:00Z",
        "assessment_status": "ready",
    }

    merged = publisher._merge_recent_events(  # noqa: SLF001
        {"ready-event": {"summary": ready}}, datetime(2026, 10, 26, tzinfo=UTC)
    )

    assert [event["event_id"] for event in merged] == ["new-event", "ready-event"]
    pending = merged[0]
    assert pending["assessment_status"] == "processing"
    assert pending["map_summary"] == "Exposure assessment is pending."
    assert pending["as_if_today"] is False
    assert pending["buildings_mmi_ge_6"] is None
    assert pending["is_recent_monitoring"] is True
    assert merged[1]["is_historical_replay"] is False


def test_latest_geonet_revision_updates_event_and_replay_magnitude(tmp_path: Path) -> None:
    publisher, tables = _publisher(tmp_path)
    summary = {
        "event_id": "2026p776286",
        "origin_time": "2026-10-15T05:25:34Z",
        "magnitude": 5.5,
        "magnitude_type": None,
        "magnitude_revision_time": None,
        "depth_km": 268.7,
        "latitude": -38.623,
        "longitude": 175.452,
        "as_if_today": False,
    }
    payloads = {
        "2026p776286": {
            "summary": summary,
            "features": {"type": "FeatureCollection", "features": []},
        }
    }
    replay_payloads = {
        "2026p776286": {
            "summary": {**deepcopy(summary), "as_if_today": True},
            "features": {"type": "FeatureCollection", "features": []},
        }
    }
    tables.upsert_entity(
        "eventsstate",
        {
            "PartitionKey": "recent",
            "RowKey": "2026p776286",
            "event_id": "2026p776286",
            "event_time": "2026-10-15T05:25:34Z",
            "magnitude": 5.65806,
            "magnitude_type": "M",
            "magnitude_revision_time": "2026-10-15T05:53:42Z",
            "depth_km": 268.7,
            "latitude": -38.623,
            "longitude": 175.452,
        },
    )

    merged = publisher._merge_recent_events(  # noqa: SLF001
        payloads,
        datetime(2026, 10, 30, tzinfo=UTC),
        replay_payloads=replay_payloads,
    )

    assert merged[0]["magnitude"] == 5.65806
    assert payloads["2026p776286"]["summary"]["magnitude"] == 5.65806
    replay = replay_payloads["2026p776286"]["summary"]
    assert replay["magnitude"] == 5.65806
    assert replay["magnitude_type"] == "M"
    assert replay["magnitude_revision_time"] == "2026-10-15T05:53:42Z"
    assert replay["as_if_today"] is True


def test_realtime_payload_rounds_all_published_mmi_values(tmp_path: Path) -> None:
    publisher, _ = _publisher(tmp_path)
    realtime = tmp_path / "realtime"
    event_root = realtime / "event-1"
    event_root.mkdir(parents=True)
    (event_root / "summary.json").write_text(
        '{"event_id":"event-1","max_mmi":1.6429645130874582}', encoding="utf-8"
    )
    (event_root / "exposure.geojson").write_text(
        '{"type":"FeatureCollection","features":[{"type":"Feature",'
        '"properties":{"mmi":5.678},"geometry":null}]}',
        encoding="utf-8",
    )
    publisher._realtime_root = realtime  # noqa: SLF001

    payload = publisher._realtime_payloads({})["event-1"]  # noqa: SLF001

    assert payload["summary"]["max_mmi"] == 1.6
    assert payload["features"]["features"][0]["properties"]["mmi"] == 5.7


def test_only_approved_briefing_paths_are_published_and_generations_are_bounded(
    tmp_path: Path,
) -> None:
    publisher, tables = _publisher(tmp_path)
    for event_id, status in (("approved", "approved"), ("pending", "pending")):
        tables.upsert_entity(
            "briefings",
            {
                "PartitionKey": "briefing",
                "RowKey": event_id,
                "event_id": event_id,
                "status": status,
                "title": "Internal draft",
                "created_at": "2026-10-26T00:00:00Z",
            },
        )

    states = publisher._briefing_states()  # noqa: SLF001
    assert states["approved"]["public_path"] == "/briefings/approved.html"
    assert states["pending"]["public_path"] is None
    assert states["pending"]["title"] is None

    root = tmp_path / "generations"
    for name in ("001", "002", "003"):
        (root / name).mkdir(parents=True)
    publisher._remove_old_generations(root, keep=2)  # noqa: SLF001
    assert sorted(path.name for path in root.iterdir()) == ["002", "003"]


def test_loads_realtime_payload_and_records_only_post_start_event(tmp_path: Path) -> None:
    publisher, tables = _publisher(tmp_path)
    realtime = tmp_path / "realtime"
    event_root = realtime / "new-event"
    event_root.mkdir(parents=True)
    (event_root / "summary.json").write_text(
        '{"event_id":"new-event","briefing":{"status":"pending"}}', encoding="utf-8"
    )
    (event_root / "exposure.geojson").write_text(
        '{"type":"FeatureCollection","features":[]}', encoding="utf-8"
    )
    publisher._realtime_root = realtime  # noqa: SLF001
    tables.upsert_entity(
        "runtime",
        {
            "PartitionKey": "monitor",
            "RowKey": "event-processing",
            "started_at": "2026-10-29T00:00:00+00:00",
        },
    )
    tables.upsert_entity(
        "eventsstate",
        {
            "PartitionKey": "recent",
            "RowKey": "new-event",
            "event_id": "new-event",
            "event_time": "2026-10-29T00:10:00+00:00",
            "assessment_status": "ready",
        },
    )

    payloads = publisher._realtime_payloads({})  # noqa: SLF001
    record = publisher._processing_record(datetime(2026, 10, 29, 0, 25, tzinfo=UTC))  # noqa: SLF001

    assert payloads["new-event"]["features"]["features"] == []
    assert record == {
        "event_id": "new-event",
        "assessment_status": "ready",
        "earthquake_at": "2026-10-29T00:10:00+00:00",
        "published_at": "2026-10-29T00:25:00+00:00",
        "elapsed_seconds": 900,
    }


def test_outside_model_range_event_records_publication_latency(tmp_path: Path) -> None:
    publisher, tables = _publisher(tmp_path)
    tables.upsert_entity(
        "runtime",
        {
            "PartitionKey": "monitor",
            "RowKey": "event-processing",
            "started_at": "2026-10-29T00:00:00+00:00",
        },
    )
    tables.upsert_entity(
        "eventsstate",
        {
            "PartitionKey": "recent",
            "RowKey": "offshore-event",
            "event_id": "offshore-event",
            "event_time": "2026-10-29T00:10:00+00:00",
            "assessment_status": "outside_model_range",
        },
    )

    record = publisher._processing_record(datetime(2026, 10, 29, 0, 35, tzinfo=UTC))  # noqa: SLF001

    assert record == {
        "event_id": "offshore-event",
        "assessment_status": "outside_model_range",
        "earthquake_at": "2026-10-29T00:10:00+00:00",
        "published_at": "2026-10-29T00:35:00+00:00",
        "elapsed_seconds": 1500,
    }
