from __future__ import annotations

from datetime import UTC, datetime

from azure.core.exceptions import ResourceNotFoundError

from nzhem.config import Settings
from nzhem.storage import table_client

PARTITION_KEY = "control"
ROW_KEY = "budget-killswitch"


class KillSwitch:
    def __init__(self, settings: Settings) -> None:
        self._client = table_client(settings, "runs")

    def is_enabled(self) -> bool:
        try:
            entity = self._client.get_entity(PARTITION_KEY, ROW_KEY)
        except ResourceNotFoundError:
            return False
        return bool(entity.get("enabled", False))

    def enable(self, run_id: str, reason: str) -> None:
        self._client.upsert_entity(
            {
                "PartitionKey": PARTITION_KEY,
                "RowKey": ROW_KEY,
                "enabled": True,
                "reason": reason,
                "run_id": run_id,
                "updated_at": datetime.now(UTC).isoformat(),
            },
            mode="replace",
        )
