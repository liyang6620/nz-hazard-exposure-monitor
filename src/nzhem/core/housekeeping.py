from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from nzhem.core.agent.approval import expire_pending_briefings
from nzhem.core.runlog import RunLog
from nzhem.ports import Clock, EventSource, QueueStore, TableStore


@dataclass(frozen=True)
class HousekeepingResult:
    run_id: str
    catchup_from: str
    events_enqueued: int
    events_requeued: int
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
            fetched_ids = {str(event["event_id"]) for event in events}
            for event in events:
                self._queues.send("events", dict(event))
                existing = (
                    self._tables.get_entity("eventsstate", "recent", str(event["event_id"])) or {}
                )
                self._tables.upsert_entity(
                    "eventsstate",
                    {
                        **existing,
                        "PartitionKey": "recent",
                        "RowKey": str(event["event_id"]),
                        **dict(event),
                        "first_seen_at": existing.get("first_seen_at") or now.isoformat(),
                        "assessment_status": existing.get("assessment_status", "queued"),
                        "assessment_reason": existing.get(
                            "assessment_reason", "Waiting for exposure assessment."
                        ),
                        "updated_at": now.isoformat(),
                    },
                )
            requeued = 0
            cutoff = now - timedelta(minutes=5)
            required_fields = (
                "event_id",
                "revision",
                "event_time",
                "magnitude",
                "depth_km",
                "latitude",
                "longitude",
                "event_name",
                "action",
            )
            event_fields = (*required_fields, "magnitude_type", "magnitude_revision_time")
            for row in self._tables.list_entities("eventsstate", "recent"):
                if row.get("assessment_status") != "queued" or str(row["RowKey"]) in fetched_ids:
                    continue
                try:
                    updated_at = datetime.fromisoformat(
                        str(row["updated_at"]).replace("Z", "+00:00")
                    )
                except (KeyError, ValueError):
                    continue
                if updated_at > cutoff or any(field not in row for field in required_fields):
                    continue
                self._queues.send("events", {field: row.get(field) for field in event_fields})
                self._tables.upsert_entity("eventsstate", {**row, "updated_at": now.isoformat()})
                requeued += 1
            briefings_expired = expire_pending_briefings(self._tables, now)
            details = {
                "catchup_from": updated_after.isoformat(),
                "events_enqueued": len(events) + requeued,
                "events_requeued": requeued,
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
