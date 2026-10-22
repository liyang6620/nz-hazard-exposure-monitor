from unittest.mock import Mock

from nzhem.config import Settings
from nzhem.storage import table_client


def test_table_client_uses_token_credential(monkeypatch) -> None:
    identity = Mock()
    constructor = Mock(return_value=Mock())
    monkeypatch.setattr("nzhem.storage.credential", lambda: identity)
    monkeypatch.setattr("nzhem.storage.TableClient", constructor)
    settings = Settings("storage", "sub", "rg", "app", "https://acs", "sender", "recipient")

    table_client(settings, "runs")

    constructor.assert_called_once_with(
        endpoint="https://storage.table.core.windows.net",
        table_name="runs",
        credential=identity,
    )
