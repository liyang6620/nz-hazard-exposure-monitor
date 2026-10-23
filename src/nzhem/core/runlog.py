from __future__ import annotations

from datetime import datetime
from typing import Any

from nzhem.ports import TableStore


class RunLog:
    def __init__(self, tables: TableStore) -> None:
        self._tables = tables

    def record(
        self,
        *,
        run_id: str,
        operation: str,
        status: str,
        completed_at: datetime,
        details: dict[str, Any] | None = None,
    ) -> None:
        entity: dict[str, Any] = {
            "PartitionKey": operation,
            "RowKey": run_id,
            "status": status,
            "completed_at": completed_at.isoformat(),
        }
        entity.update(details or {})
        self._tables.upsert_entity("runs", entity)

    def last_success(self, operation: str) -> datetime | None:
        timestamps = [
            datetime.fromisoformat(str(entity["completed_at"]))
            for entity in self._tables.list_entities("runs", operation)
            if entity.get("status") == "success" and entity.get("completed_at")
        ]
        return max(timestamps, default=None)
