from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from nzhem.core.agent.approval import expire_pending_briefings
from nzhem.core.runlog import RunLog
from nzhem.ports import Clock, EventSource, QueueStore, TableStore


@dataclass(frozen=True)
class HousekeepingResult:
    run_id: str
    catchup_from: str
    events_enqueued: int
    briefings_expired: int


class HousekeepingService:
    """Minimal housekeeping and startup catch-up shared by both hosts."""

    def __init__(
        self,
        *,
        clock: Clock,
        tables: TableStore,
        queues: QueueStore,
        event_source: EventSource,
        default_lookback: timedelta = timedelta(days=30),
    ) -> None:
        self._clock = clock
        self._runlog = RunLog(tables)
        self._tables = tables
        self._queues = queues
        self._event_source = event_source
        self._default_lookback = default_lookback

    def run(self) -> HousekeepingResult:
        run_id = str(uuid.uuid4())
        now = self._clock.now()
        updated_after = self._runlog.last_success("housekeeping") or now - self._default_lookback

        try:
            events = self._event_source.fetch_updated_after(updated_after)
            for event in events:
                self._queues.send("events", dict(event))
                self._tables.upsert_entity(
                    "eventsstate",
                    {
                        "PartitionKey": "recent",
                        "RowKey": str(event["event_id"]),
                        **dict(event),
                        "updated_at": now.isoformat(),
                    },
                )
            briefings_expired = expire_pending_briefings(self._tables, now)
            details = {
                "catchup_from": updated_after.isoformat(),
                "events_enqueued": len(events),
                "briefings_expired": briefings_expired,
            }
            self._runlog.record(
                run_id=run_id,
                operation="housekeeping",
                status="success",
                completed_at=now,
                details=details,
            )
        except Exception as exc:
            self._runlog.record(
                run_id=run_id,
                operation="housekeeping",
                status="failed",
                completed_at=now,
                details={"error_type": type(exc).__name__},
            )
            raise

        return HousekeepingResult(run_id=run_id, **details)
