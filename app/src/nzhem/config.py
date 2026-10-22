from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigurationError(ValueError):
    """Raised when required runtime configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    storage_account_name: str
    subscription_id: str
    resource_group_name: str
    function_app_name: str
    communication_endpoint: str
    email_sender: str
    notification_email: str
    llm_reasoning_effort: str = "minimal"
    llm_max_output_tokens: int = 1200
    briefing_total_token_limit: int = 12000
    briefing_monthly_limit: int = 10

    @property
    def table_endpoint(self) -> str:
        return f"https://{self.storage_account_name}.table.core.windows.net"

    @classmethod
    def from_env(cls) -> Settings:
        values = {
            "storage_account_name": _required("STORAGE_ACCOUNT_NAME"),
            "subscription_id": _required("AZURE_SUBSCRIPTION_ID"),
            "resource_group_name": _required("AZURE_RESOURCE_GROUP"),
            "function_app_name": _required("AZURE_FUNCTION_APP_NAME"),
            "communication_endpoint": _required("ACS_ENDPOINT"),
            "email_sender": _required("ACS_SENDER"),
            "notification_email": _required("NOTIFICATION_EMAIL"),
            "llm_reasoning_effort": os.getenv("LLM_REASONING_EFFORT", "minimal").strip(),
            "llm_max_output_tokens": _positive_int("LLM_MAX_OUTPUT_TOKENS", 1200),
            "briefing_total_token_limit": _positive_int("BRIEFING_TOTAL_TOKEN_LIMIT", 12000),
            "briefing_monthly_limit": _positive_int("BRIEFING_MONTHLY_LIMIT", 10),
        }
        if not values["communication_endpoint"].startswith("https://"):
            raise ConfigurationError("ACS_ENDPOINT must use HTTPS")
        if values["llm_reasoning_effort"] != "minimal":
            raise ConfigurationError("LLM_REASONING_EFFORT must be minimal")
        if values["llm_max_output_tokens"] > values["briefing_total_token_limit"]:
            raise ConfigurationError("LLM_MAX_OUTPUT_TOKENS cannot exceed the briefing token limit")
        return cls(**values)


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(f"{name} is required")
    return value


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ConfigurationError(f"{name} must be greater than zero")
    return value
