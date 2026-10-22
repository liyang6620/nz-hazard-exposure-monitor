from unittest.mock import Mock

from azure.core.exceptions import ResourceNotFoundError

from nzhem.config import Settings
from nzhem.killswitch import KillSwitch


def settings() -> Settings:
    return Settings("storage", "sub", "rg", "app", "https://acs", "sender", "recipient")


def test_missing_switch_is_disabled(monkeypatch) -> None:
    client = Mock()
    client.get_entity.side_effect = ResourceNotFoundError("missing")
    monkeypatch.setattr("nzhem.killswitch.table_client", lambda *_: client)

    assert KillSwitch(settings()).is_enabled() is False


def test_existing_switch_returns_enabled(monkeypatch) -> None:
    client = Mock()
    client.get_entity.return_value = {"enabled": True}
    monkeypatch.setattr("nzhem.killswitch.table_client", lambda *_: client)

    assert KillSwitch(settings()).is_enabled() is True


def test_enable_replaces_durable_entity(monkeypatch) -> None:
    client = Mock()
    monkeypatch.setattr("nzhem.killswitch.table_client", lambda *_: client)

    KillSwitch(settings()).enable(run_id="run-1", reason="test")

    entity = client.upsert_entity.call_args.args[0]
    assert entity["PartitionKey"] == "control"
    assert entity["RowKey"] == "budget-killswitch"
    assert entity["enabled"] is True
    assert entity["run_id"] == "run-1"
    assert client.upsert_entity.call_args.kwargs["mode"] == "replace"
