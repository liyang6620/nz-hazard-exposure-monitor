import pytest

from nzhem.config import ConfigurationError, Settings

ENV = {
    "STORAGE_ACCOUNT_NAME": "stnzhemtest",
    "AZURE_SUBSCRIPTION_ID": "subscription-value",
    "AZURE_RESOURCE_GROUP": "rg-nzhem-prod",
    "AZURE_FUNCTION_APP_NAME": "func-nzhem-test",
    "ACS_ENDPOINT": "https://example.communication.azure.com",
    "ACS_SENDER": "DoNotReply@example.azurecomm.net",
    "NOTIFICATION_EMAIL": "owner@example.com",
}


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)

    settings = Settings.from_env()

    assert settings.storage_account_name == "stnzhemtest"
    assert settings.table_endpoint == "https://stnzhemtest.table.core.windows.net"


def test_settings_rejects_missing_value(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("NOTIFICATION_EMAIL")

    with pytest.raises(ConfigurationError, match="NOTIFICATION_EMAIL"):
        Settings.from_env()


def test_settings_requires_https_acs_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("ACS_ENDPOINT", "http://example.invalid")

    with pytest.raises(ConfigurationError, match="HTTPS"):
        Settings.from_env()


def test_settings_enforces_minimal_reasoning(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("LLM_REASONING_EFFORT", "high")

    with pytest.raises(ConfigurationError, match="must be minimal"):
        Settings.from_env()


def test_settings_rejects_invalid_token_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("LLM_MAX_OUTPUT_TOKENS", "unlimited")

    with pytest.raises(ConfigurationError, match="must be an integer"):
        Settings.from_env()
