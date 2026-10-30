from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from nzhem.adapters.local.realtime import LocalRealtimeEventAssessor
from nzhem.adapters.local.resource_guard import ResourceGuard
from nzhem.adapters.local.sqlite import SqliteQueueStore, SqliteTableStore
from nzhem.core.event_processing import EventProcessingService


class MutableClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


class StubAssessor:
    def __init__(self, outcome: dict[str, Any] | Exception) -> None:
        self.outcome = outcome
        self.calls = 0

    def assess(self, event: dict[str, Any], assessed_at: datetime) -> dict[str, Any]:
        self.calls += 1
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class MissingOfficialLayer:
    def cache_event(self, event_id: str) -> None:
        response = requests.Response()
        response.status_code = 404
        raise requests.HTTPError(response=response)


def _event() -> dict[str, Any]:
    return {
        "event_id": "2026p-test",
        "revision": "r1",
        "event_time": "2026-10-29T00:00:00Z",
        "magnitude": 5.1,
        "depth_km": 12.0,
        "latitude": -41.0,
        "longitude": 174.0,
        "event_name": "Test earthquake",
    }


def _service(tmp_path: Path, assessor: StubAssessor, clock: MutableClock):
    database = tmp_path / "state.sqlite3"
    tables = SqliteTableStore(database)
    queues = SqliteQueueStore(database, max_dequeue_count=3)
    service = EventProcessingService(
        clock=clock,
        tables=tables,
        queues=queues,
        assessor=assessor,
        max_attempts=3,
        timeout=timedelta(minutes=60),
    )
    return service, tables, queues


def test_processes_event_once_and_keeps_terminal_revision(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 10, 29, 1, tzinfo=UTC))
    assessor = StubAssessor(
        {
            "assessment_status": "ready",
            "assessment_reason": "Exposure assessment completed.",
            "max_mmi": 5.3,
        }
    )
    service, tables, queues = _service(tmp_path, assessor, clock)
    queues.send("events", _event())
    queues.send("events", _event())

    result = service.run_pending()

    state = tables.get_entity("eventsstate", "recent", "2026p-test")
    assert result.assessed == 1
    assert result.skipped == 1
    assert assessor.calls == 1
    assert state is not None and state["assessment_status"] == "ready"
    assert state["first_seen_at"] == "2026-10-29T01:00:00+00:00"
    assert tables.get_entity("runtime", "monitor", "event-processing") is not None


def test_three_failures_become_terminal_instead_of_processing_forever(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 10, 29, 1, tzinfo=UTC))
    assessor = StubAssessor(RuntimeError("broken"))
    service, tables, queues = _service(tmp_path, assessor, clock)
    queues.send("events", _event())

    result = service.run_pending()

    state = tables.get_entity("eventsstate", "recent", "2026p-test")
    assert result.retried == 2
    assert result.failed == 1
    assert assessor.calls == 3
    assert state is not None and state["assessment_status"] == "failed"
    assert state["failure_type"] == "RuntimeError"


def test_stale_processing_becomes_timed_out(tmp_path: Path) -> None:
    clock = MutableClock(datetime(2026, 10, 29, 3, tzinfo=UTC))
    assessor = StubAssessor({"assessment_status": "ready"})
    service, tables, _ = _service(tmp_path, assessor, clock)
    tables.upsert_entity(
        "eventsstate",
        {
            "PartitionKey": "recent",
            "RowKey": "stale",
            "event_id": "stale",
            "assessment_status": "processing",
            "processing_started_at": "2026-10-29T01:00:00+00:00",
        },
    )

    result = service.run_pending()

    state = tables.get_entity("eventsstate", "recent", "stale")
    assert result.timed_out == 1
    assert state is not None and state["assessment_status"] == "timed_out"
    assert "60-minute" in state["assessment_reason"]


def test_out_of_range_event_without_official_layer_is_explicit(tmp_path: Path) -> None:
    reference = tmp_path / "reference"
    (reference / "int_buildings_h3").mkdir(parents=True)
    (reference / "dim_h3_cell.parquet").touch()
    (reference / "int_population_h3.parquet").touch()
    assessor = LocalRealtimeEventAssessor(
        reference_root=reference,
        raw_root=tmp_path / "raw",
        output_root=tmp_path / "output",
        guard=ResourceGuard(tmp_path, min_free_disk_gb=0),
        shaking_client=MissingOfficialLayer(),  # type: ignore[arg-type]
    )
    event = {**_event(), "magnitude": 4.2}

    result = assessor.assess(event, datetime(2026, 10, 29, 1, tzinfo=UTC))

    assert result["assessment_status"] == "outside_model_range"
    assert result["as_if_today"] is False
    assert result["max_mmi"] is None
    assert "outside the published" in str(result["assessment_reason"])


def test_event_outside_monitoring_window_is_not_recomputed(tmp_path: Path) -> None:
    reference = tmp_path / "reference"
    (reference / "int_buildings_h3").mkdir(parents=True)
    (reference / "dim_h3_cell.parquet").touch()
    (reference / "int_population_h3.parquet").touch()
    assessor = LocalRealtimeEventAssessor(
        reference_root=reference,
        raw_root=tmp_path / "raw",
        output_root=tmp_path / "output",
        guard=ResourceGuard(tmp_path, min_free_disk_gb=0),
        shaking_client=MissingOfficialLayer(),  # type: ignore[arg-type]
    )
    event = {**_event(), "event_time": "2026-09-01T00:00:00Z"}

    result = assessor.assess(event, datetime(2026, 10, 29, 1, tzinfo=UTC))

    assert result["assessment_status"] == "expired"
    assert result["as_if_today"] is False
