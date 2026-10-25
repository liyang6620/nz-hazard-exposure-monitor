from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock

from nzhem.ports import TableStore


class EsriToolRejected(RuntimeError):
    """Raised before any request when the Esri MCP policy rejects a tool call."""


@dataclass(frozen=True)
class EsriMapReservation:
    row_key: str
    briefing_id: str


class EsriStaticMapGuard:
    TABLE = "runs"
    PARTITION = "esri_static_map"
    ALLOWED_TOOL = "static_map"

    def __init__(
        self,
        tables: TableStore,
        *,
        per_briefing_limit: int = 2,
        monthly_limit: int = 200,
    ) -> None:
        self._tables = tables
        self._per_briefing_limit = per_briefing_limit
        self._monthly_limit = monthly_limit
        self._lock = Lock()

    def reserve(self, *, tool_name: str, briefing_id: str, now: datetime) -> EsriMapReservation:
        if tool_name != self.ALLOWED_TOOL:
            raise EsriToolRejected("Only the static map tool is allowed")
        with self._lock:
            month = now.astimezone(UTC).strftime("%Y-%m")
            records = self._tables.list_entities(self.TABLE, self.PARTITION)
            monthly = [row for row in records if str(row["attempted_at"]).startswith(month)]
            if len(monthly) >= self._monthly_limit:
                raise EsriToolRejected("Monthly static map limit reached")
            per_briefing = [row for row in monthly if row["briefing_id"] == briefing_id]
            if len(per_briefing) >= self._per_briefing_limit:
                raise EsriToolRejected("Per-briefing static map limit reached")
            row_key = uuid.uuid4().hex
            self._tables.upsert_entity(
                self.TABLE,
                {
                    "PartitionKey": self.PARTITION,
                    "RowKey": row_key,
                    "briefing_id": briefing_id,
                    "tool_name": tool_name,
                    "attempted_at": now.astimezone(UTC).isoformat(),
                    "status": "reserved",
                },
            )
        return EsriMapReservation(row_key, briefing_id)

    def record_result(self, reservation: EsriMapReservation, *, success: bool) -> None:
        entity = self._tables.get_entity(self.TABLE, self.PARTITION, reservation.row_key)
        if entity is None:
            raise KeyError(reservation.row_key)
        entity["status"] = "success" if success else "failed"
        self._tables.upsert_entity(self.TABLE, entity)
