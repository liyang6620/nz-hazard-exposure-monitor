from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from nzhem.ports import Clock, EventAssessor, QueueStore, TableStore

TERMINAL_STATUSES = {"ready", "outside_model_range", "expired", "timed_out", "failed"}


@dataclass(frozen=True)
class EventProcessingResult:
    received: int
    assessed: int
    skipped: int
    retried: int
    failed: int
    timed_out: int


class EventProcessingService:
    """Consume event work with bounded retries and explicit terminal states."""

    def __init__(
        self,
        *,
        clock: Clock,
        tables: TableStore,
        queues: QueueStore,
        assessor: EventAssessor,
        max_attempts: int = 3,
        timeout: timedelta = timedelta(minutes=60),
    ) -> None:
        self._clock = clock
        self._tables = tables
        self._queues = queues
        self._assessor = assessor
        self._max_attempts = max_attempts
        self._timeout = timeout

    def run_pending(self, *, limit: int = 100) -> EventProcessingResult:
        self._ensure_monitor_started(self._clock.now().astimezone(UTC))
        counts = {
            "received": 0,
            "assessed": 0,
            "skipped": 0,
            "retried": 0,
            "failed": 0,
        }
        for _ in range(limit):
            message = self._queues.receive("events")
            if message is None:
                break
            counts["received"] += 1
            event = dict(message.payload)
            event_id = str(event["event_id"])
            existing = self._tables.get_entity("eventsstate", "recent", event_id) or {}
            if self._is_current_terminal(existing, event):
                self._queues.complete("events", message.message_id, message.receipt)
                counts["skipped"] += 1
                continue

            now = self._clock.now().astimezone(UTC)
            processing = self._processing_state(existing, event, now, message.dequeue_count)
            self._tables.upsert_entity("eventsstate", processing)
            try:
                outcome = dict(self._assessor.assess(event, now))
                status = str(outcome.get("assessment_status", ""))
                if status not in TERMINAL_STATUSES:
                    raise ValueError(f"Assessor returned non-terminal status: {status}")
                completed = {
                    **processing,
                    **outcome,
                    "assessment_completed_at": now.isoformat(),
                    "assessment_attempts": message.dequeue_count,
                    "updated_at": now.isoformat(),
                }
                self._tables.upsert_entity("eventsstate", completed)
                self._queues.complete("events", message.message_id, message.receipt)
                counts["assessed"] += 1
            except Exception as exc:
                if message.dequeue_count >= self._max_attempts:
                    failed = {
                        **processing,
                        "assessment_status": "failed",
                        "assessment_reason": "Assessment failed after three attempts.",
                        "failure_type": type(exc).__name__,
                        "assessment_completed_at": now.isoformat(),
                        "assessment_attempts": message.dequeue_count,
                        "updated_at": now.isoformat(),
                    }
                    self._tables.upsert_entity("eventsstate", failed)
                    self._queues.complete("events", message.message_id, message.receipt)
                    counts["failed"] += 1
                else:
                    self._queues.abandon("events", message.message_id, message.receipt)
                    counts["retried"] += 1

        timed_out = self._expire_stale_processing(self._clock.now().astimezone(UTC))
        return EventProcessingResult(timed_out=timed_out, **counts)

    def _ensure_monitor_started(self, now: datetime) -> None:
        if self._tables.get_entity("runtime", "monitor", "event-processing") is not None:
            return
        self._tables.upsert_entity(
            "runtime",
            {
                "PartitionKey": "monitor",
                "RowKey": "event-processing",
                "started_at": now.isoformat(),
            },
        )

    @staticmethod
    def _is_current_terminal(existing: Mapping[str, Any], event: Mapping[str, Any]) -> bool:
        return existing.get("assessment_status") in TERMINAL_STATUSES and str(
            existing.get("revision", "")
        ) == str(event.get("revision", ""))

    @staticmethod
    def _processing_state(
        existing: Mapping[str, Any],
        event: Mapping[str, Any],
        now: datetime,
        attempt: int,
    ) -> dict[str, Any]:
        first_seen = existing.get("first_seen_at") or now.isoformat()
        started = existing.get("processing_started_at") or now.isoformat()
        return {
            **dict(existing),
            **dict(event),
            "PartitionKey": "recent",
            "RowKey": str(event["event_id"]),
            "first_seen_at": first_seen,
            "assessment_status": "processing",
            "assessment_reason": "Exposure assessment is running.",
            "processing_started_at": started,
            "assessment_attempts": attempt,
            "updated_at": now.isoformat(),
        }

    def _expire_stale_processing(self, now: datetime) -> int:
        expired = 0
        cutoff = now - self._timeout
        for row in self._tables.list_entities("eventsstate", "recent"):
            if row.get("assessment_status") != "processing":
                continue
            try:
                started = datetime.fromisoformat(
                    str(row["processing_started_at"]).replace("Z", "+00:00")
                ).astimezone(UTC)
            except (KeyError, ValueError):
                started = cutoff - timedelta(seconds=1)
            if started > cutoff:
                continue
            self._tables.upsert_entity(
                "eventsstate",
                {
                    **row,
                    "assessment_status": "timed_out",
                    "assessment_reason": "Assessment exceeded the 60-minute processing limit.",
                    "assessment_completed_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                },
            )
            expired += 1
        return expired
