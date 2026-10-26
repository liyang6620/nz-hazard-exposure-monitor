from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest


def test_core_does_not_import_azure_packages() -> None:
    violations: list[str] = []
    core_root = Path("src/nzhem/core")
    for path in core_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            if any(name == "azure" or name.startswith("azure.") for name in names):
                violations.append(f"{path}:{node.lineno}")
    assert violations == []


def test_azure_function_app_metadata_builds() -> None:
    module_path = Path("hosts/azure_functions/function_app.py")
    spec = importlib.util.spec_from_file_location("nzhem_function_app", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    functions = {function.get_function_name(): function for function in module.app.get_functions()}
    assert set(functions) == {"budget_stop", "housekeeping"}
    trigger = functions["budget_stop"].get_bindings()[0].get_dict_repr()
    assert trigger["name"] == "request"


def test_budget_stop_rejects_an_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    required = {
        "NZHEM_ENV": "azure",
        "STORAGE_ACCOUNT_NAME": "storage",
        "AZURE_SUBSCRIPTION_ID": "subscription",
        "AZURE_RESOURCE_GROUP": "resource-group",
        "AZURE_FUNCTION_APP_NAME": "function",
        "BUDGET_WEBHOOK_TOKEN": "expected-token-value",
        "ACS_ENDPOINT": "https://example.communication.azure.com",
        "ACS_SENDER": "sender@example.invalid",
        "KEY_VAULT_URL": "https://example.vault.azure.net",
        "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
    }
    for name, value in required.items():
        monkeypatch.setenv(name, value)

    module_path = Path("hosts/azure_functions/function_app.py")
    spec = importlib.util.spec_from_file_location("nzhem_function_app_token_test", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class InvalidTokenRequest:
        params = {"token": "wrong-token-value"}

    response = module.budget_stop(InvalidTokenRequest())

    assert response.status_code == 403
