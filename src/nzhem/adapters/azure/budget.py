from __future__ import annotations

from datetime import UTC, datetime

import requests

from nzhem.adapters.azure import AzureMailer, AzureTableStore, credential
from nzhem.config import Settings

ARM_SCOPE = "https://management.azure.com/.default"
API_VERSION = "2024-11-01"


def activate_budget_stop(settings: Settings, run_id: str) -> None:
    tables = AzureTableStore(settings.storage_account_name)
    tables.upsert_entity(
        "runs",
        {
            "PartitionKey": "control",
            "RowKey": "budget-killswitch",
            "enabled": True,
            "reason": "budget_action_group",
            "run_id": run_id,
            "updated_at": datetime.now(UTC).isoformat(),
        },
    )
    AzureMailer(settings.communication_connection_string, settings.email_sender).send(
        settings.notification_email,
        "NZHEM budget stop activated",
        f"The Azure deployment budget stop was activated. Run ID: {run_id}.",
    )
    token = credential().get_token(ARM_SCOPE).token
    url = (
        f"https://management.azure.com/subscriptions/{settings.subscription_id}"
        f"/resourceGroups/{settings.resource_group_name}/providers/Microsoft.Web/sites/"
        f"{settings.function_app_name}/stop?api-version={API_VERSION}"
    )
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    response.raise_for_status()
