from pathlib import Path

import pytest

from nzhem.config import ConfigurationError, Settings


def test_local_settings_have_safe_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NZHEM_ENV", "local")
    monkeypatch.setenv("ARCGIS_PUBLISHER_ENABLED", "false")

    settings = Settings.from_env()

    assert settings.environment == "local"
    assert settings.data_root == Path(".local/data")
    assert settings.arcgis_publisher_enabled is False
    assert settings.arcgis_static_maps_enabled is False
    assert settings.arcgis_api_key_name == "ARCGIS_API_KEY"


def test_settings_reject_unknown_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NZHEM_ENV", "desktop")
    with pytest.raises(ConfigurationError, match="local or azure"):
        Settings.from_env()


def test_settings_reject_short_poll_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POLL_INTERVAL_MINUTES", "4")
    with pytest.raises(ConfigurationError, match="at least 5"):
        Settings.from_env()


def test_azure_settings_require_platform_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NZHEM_ENV", "azure")
    for name in (
        "STORAGE_ACCOUNT_NAME",
        "AZURE_SUBSCRIPTION_ID",
        "AZURE_RESOURCE_GROUP",
        "AZURE_FUNCTION_APP_NAME",
        "BUDGET_WEBHOOK_TOKEN",
        "ACS_CONNECTION_STRING",
        "ACS_SENDER",
        "KEY_VAULT_URL",
        "AZURE_OPENAI_ENDPOINT",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ConfigurationError, match="Azure mode requires"):
        Settings.from_env()


def test_invalid_boolean_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARCGIS_PUBLISHER_ENABLED", "sometimes")
    with pytest.raises(ConfigurationError, match="true or false"):
        Settings.from_env()


def test_static_maps_require_a_secret_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARCGIS_STATIC_MAPS_ENABLED", "true")
    monkeypatch.setenv("ARCGIS_API_KEY_NAME", "")

    with pytest.raises(ConfigurationError, match="ARCGIS_API_KEY_NAME"):
        Settings.from_env()
