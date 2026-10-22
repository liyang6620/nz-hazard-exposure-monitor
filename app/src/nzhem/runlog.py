from datetime import UTC, datetime

from nzhem.config import Settings
from nzhem.storage import table_client


class RunLog:
    def __init__(self, settings: Settings) -> None:
        self._client = table_client(settings, "runs")

    def record_success(self, run_id: str, operation: str) -> None:
        now = datetime.now(UTC)
        self._client.upsert_entity(
            {
                "PartitionKey": operation,
                "RowKey": run_id,
                "status": "success",
                "completed_at": now.isoformat(),
            }
        )
