from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path

from nzhem.adapters.local.sqlite import SqliteQueueStore, SqliteTableStore
from nzhem.core.housekeeping import HousekeepingService


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


class RecordingSource:
    def __init__(self, events: list[dict] | None = None) -> None:
        self.updated_after: datetime | None = None
        self.events = events or []

    def fetch_updated_after(self, updated_after: datetime) -> list[dict]:
        self.updated_after = updated_after
        return self.events


def test_first_run_uses_30_day_catchup_and_records_success(tmp_path: Path) -> None:
    now = datetime(2026, 10, 23, 12, tzinfo=UTC)
    source = RecordingSource([{"event_id": "event-1", "action": "upsert"}])
    tables = SqliteTableStore(tmp_path / "state.db")
    queues = SqliteQueueStore(tmp_path / "state.db")
    service = HousekeepingService(
        clock=FixedClock(now), tables=tables, queues=queues, event_source=source
    )

    result = service.run()

    assert source.updated_after == now - timedelta(days=30)
    assert result.events_enqueued == 1
    assert tables.get_entity("runs", "housekeeping", result.run_id)["status"] == "success"
    assert queues.receive("events").payload["event_id"] == "event-1"
    recent = tables.get_entity("eventsstate", "recent", "event-1")
    assert recent["event_id"] == "event-1"
    assert recent["updated_at"] == now.isoformat()


def test_next_run_catches_up_from_last_success(tmp_path: Path) -> None:
    first_time = datetime(2026, 10, 23, 12, tzinfo=UTC)
    clock = FixedClock(first_time)
    source = RecordingSource()
    tables = SqliteTableStore(tmp_path / "state.db")
    service = HousekeepingService(
        clock=clock,
        tables=tables,
        queues=SqliteQueueStore(tmp_path / "state.db"),
        event_source=source,
    )
    service.run()
    clock.value += timedelta(hours=3)

    service.run()

    assert source.updated_after == first_time


def test_failure_is_recorded_without_exposing_message(tmp_path: Path) -> None:
    class FailingSource:
        def fetch_updated_after(self, updated_after: datetime) -> list[dict]:
            raise RuntimeError("sensitive upstream detail")

    tables = SqliteTableStore(tmp_path / "state.db")
    service = HousekeepingService(
        clock=FixedClock(datetime(2026, 10, 23, tzinfo=UTC)),
        tables=tables,
        queues=SqliteQueueStore(tmp_path / "state.db"),
        event_source=FailingSource(),
    )

    with suppress(RuntimeError):
        service.run()

    failed = tables.list_entities("runs", "housekeeping")[0]
    assert failed["status"] == "failed"
    assert failed["error_type"] == "RuntimeError"
    assert "sensitive" not in str(failed)
