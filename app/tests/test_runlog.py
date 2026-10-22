from unittest.mock import Mock

from nzhem.config import Settings
from nzhem.runlog import RunLog


def test_record_success(monkeypatch) -> None:
    client = Mock()
    monkeypatch.setattr("nzhem.runlog.table_client", lambda *_: client)
    settings = Settings("storage", "sub", "rg", "app", "https://acs", "sender", "recipient")

    RunLog(settings).record_success("run-1", "housekeeping")

    entity = client.upsert_entity.call_args.args[0]
    assert entity["PartitionKey"] == "housekeeping"
    assert entity["RowKey"] == "run-1"
    assert entity["status"] == "success"
