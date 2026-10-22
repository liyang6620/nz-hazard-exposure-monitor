from azure.data.tables import TableClient

from nzhem.config import Settings
from nzhem.identity import credential


def table_client(settings: Settings, table_name: str) -> TableClient:
    return TableClient(
        endpoint=settings.table_endpoint,
        table_name=table_name,
        credential=credential(),
    )
