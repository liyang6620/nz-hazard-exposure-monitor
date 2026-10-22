from unittest.mock import Mock

from nzhem.config import Settings
from nzhem.notify import send_budget_stop_email


def test_send_budget_stop_email(monkeypatch) -> None:
    poller = Mock()
    client = Mock()
    client.begin_send.return_value = poller
    email_client = Mock(return_value=client)
    monkeypatch.setattr("nzhem.notify.EmailClient", email_client)
    identity = Mock()
    monkeypatch.setattr("nzhem.notify.credential", lambda: identity)
    settings = Settings("storage", "sub", "rg", "app", "https://acs", "sender", "recipient")

    send_budget_stop_email(settings, "run-1")

    email_client.assert_called_once_with("https://acs", identity)
    message = client.begin_send.call_args.args[0]
    assert message["senderAddress"] == "sender"
    assert message["recipients"]["to"] == [{"address": "recipient"}]
    assert "run-1" in message["content"]["plainText"]
    poller.result.assert_called_once()
