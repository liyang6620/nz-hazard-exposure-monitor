from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


class ConfigurationError(ValueError):
    """Raised when runtime configuration is missing or invalid."""


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name, str(default)).strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} must be true or false")


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ConfigurationError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True)
class Settings:
    environment: Literal["local", "azure"] = "local"
    data_root: Path = Path(".local/data")
    sqlite_path: Path = Path(".local/state/nzhem.sqlite3")
    poll_interval_minutes: int = 60
    queue_visibility_timeout_seconds: int = 30
    queue_max_dequeue_count: int = 3
    geonet_poll_enabled: bool = True
    geonet_fdsn_url: str = "https://service.geonet.org.nz/fdsnws/event/1/query"
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    mail_from: str = "nzhem@example.invalid"
    notification_email: str = "owner@example.invalid"
    openai_model: str = "gpt-5-mini"
    openai_api_key_name: str = "OPENAI_API_KEY"
    arcgis_publisher_enabled: bool = False
    run_startup_housekeeping: bool = True
    llm_reasoning_effort: str = "minimal"
    llm_max_output_tokens: int = 1200
    briefing_total_token_limit: int = 12000
    briefing_monthly_limit: int = 10
    storage_account_name: str = ""
    subscription_id: str = ""
    resource_group_name: str = ""
    function_app_name: str = ""
    communication_endpoint: str = ""
    email_sender: str = ""
    key_vault_url: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = "gpt-5-mini"

    @classmethod
    def from_env(cls) -> Settings:
        environment = os.getenv("NZHEM_ENV", "local").strip().lower()
        if environment not in {"local", "azure"}:
            raise ConfigurationError("NZHEM_ENV must be local or azure")

        settings = cls(
            environment=environment,
            data_root=Path(os.getenv("NZHEM_DATA_ROOT", ".local/data")),
            sqlite_path=Path(os.getenv("NZHEM_SQLITE_PATH", ".local/state/nzhem.sqlite3")),
            poll_interval_minutes=_positive_int("POLL_INTERVAL_MINUTES", 60),
            queue_visibility_timeout_seconds=_positive_int("QUEUE_VISIBILITY_TIMEOUT_SECONDS", 30),
            queue_max_dequeue_count=_positive_int("QUEUE_MAX_DEQUEUE_COUNT", 3),
            geonet_poll_enabled=_bool("GEONET_POLL_ENABLED", True),
            geonet_fdsn_url=os.getenv(
                "GEONET_FDSN_URL", "https://service.geonet.org.nz/fdsnws/event/1/query"
            ).strip(),
            smtp_host=os.getenv("SMTP_HOST", "mailpit").strip(),
            smtp_port=_positive_int("SMTP_PORT", 1025),
            mail_from=os.getenv("MAIL_FROM", "nzhem@example.invalid").strip(),
            notification_email=os.getenv("NOTIFICATION_EMAIL", "owner@example.invalid").strip(),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini").strip(),
            openai_api_key_name=os.getenv("OPENAI_API_KEY_NAME", "OPENAI_API_KEY").strip(),
            arcgis_publisher_enabled=_bool("ARCGIS_PUBLISHER_ENABLED", False),
            run_startup_housekeeping=_bool("RUN_STARTUP_HOUSEKEEPING", True),
            llm_reasoning_effort=os.getenv("LLM_REASONING_EFFORT", "minimal").strip(),
            llm_max_output_tokens=_positive_int("LLM_MAX_OUTPUT_TOKENS", 1200),
            briefing_total_token_limit=_positive_int("BRIEFING_TOTAL_TOKEN_LIMIT", 12000),
            briefing_monthly_limit=_positive_int("BRIEFING_MONTHLY_LIMIT", 10),
            storage_account_name=os.getenv("STORAGE_ACCOUNT_NAME", "").strip(),
            subscription_id=os.getenv("AZURE_SUBSCRIPTION_ID", "").strip(),
            resource_group_name=os.getenv("AZURE_RESOURCE_GROUP", "").strip(),
            function_app_name=os.getenv("AZURE_FUNCTION_APP_NAME", "").strip(),
            communication_endpoint=os.getenv("ACS_ENDPOINT", "").strip(),
            email_sender=os.getenv("ACS_SENDER", "").strip(),
            key_vault_url=os.getenv("KEY_VAULT_URL", "").strip(),
            azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", "").strip(),
            azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5-mini").strip(),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.poll_interval_minutes < 5:
            raise ConfigurationError("POLL_INTERVAL_MINUTES must be at least 5")
        if self.llm_reasoning_effort != "minimal":
            raise ConfigurationError("LLM_REASONING_EFFORT must be minimal")
        if self.llm_max_output_tokens > self.briefing_total_token_limit:
            raise ConfigurationError("LLM_MAX_OUTPUT_TOKENS cannot exceed the briefing token limit")
        if self.environment == "azure":
            required = {
                "STORAGE_ACCOUNT_NAME": self.storage_account_name,
                "AZURE_SUBSCRIPTION_ID": self.subscription_id,
                "AZURE_RESOURCE_GROUP": self.resource_group_name,
                "AZURE_FUNCTION_APP_NAME": self.function_app_name,
                "ACS_ENDPOINT": self.communication_endpoint,
                "ACS_SENDER": self.email_sender,
                "KEY_VAULT_URL": self.key_vault_url,
                "AZURE_OPENAI_ENDPOINT": self.azure_openai_endpoint,
            }
            missing = [name for name, value in required.items() if not value]
            if missing:
                raise ConfigurationError(f"Azure mode requires: {', '.join(missing)}")
            if not self.communication_endpoint.startswith("https://"):
                raise ConfigurationError("ACS_ENDPOINT must use HTTPS")
