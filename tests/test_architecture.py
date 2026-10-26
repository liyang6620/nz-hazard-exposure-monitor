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
    assert set(functions) == {
        "budget_stop",
        "housekeeping",
        "map_token",
        "review_briefing_get",
        "review_briefing_post",
    }
    trigger = functions["budget_stop"].get_bindings()[0].get_dict_repr()
    assert trigger["name"] == "request"
    http_methods = {
        name: {
            str(method.value)
            for method in functions[name].get_bindings()[0].get_dict_repr()["methods"]
        }
        for name in functions
        if name != "housekeeping"
    }
    assert http_methods == {
        "budget_stop": {"POST"},
        "map_token": {"GET"},
        "review_briefing_get": {"GET"},
        "review_briefing_post": {"POST"},
    }


def test_budget_stop_rejects_an_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    required = {
        "NZHEM_ENV": "azure",
        "STORAGE_ACCOUNT_NAME": "storage",
        "AZURE_SUBSCRIPTION_ID": "subscription",
        "AZURE_RESOURCE_GROUP": "resource-group",
        "AZURE_FUNCTION_APP_NAME": "function",
        "BUDGET_WEBHOOK_TOKEN": "expected-token-value",
        "ACS_CONNECTION_STRING": (
            "endpoint=https://example.communication.azure.com;accesskey=test-key"
        ),
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


def test_map_token_is_disabled_and_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAP_TOKEN_ENABLED", "false")

    module_path = Path("hosts/azure_functions/function_app.py")
    spec = importlib.util.spec_from_file_location("nzhem_function_app_map_test", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class Request:
        params: dict[str, str] = {}
        headers: dict[str, str] = {}

    response = module.map_token(Request())

    assert response.status_code == 404


def test_map_token_rejects_wrong_origin_before_broker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAP_TOKEN_ENABLED", "true")
    monkeypatch.setenv("MAP_TOKEN_ALLOWED_ORIGIN", "https://public.example")

    module_path = Path("hosts/azure_functions/function_app.py")
    spec = importlib.util.spec_from_file_location("nzhem_function_app_origin_test", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class Request:
        params: dict[str, str] = {}
        headers = {"origin": "https://attacker.example"}

    response = module.map_token(Request())

    assert response.status_code == 403


def test_map_token_rate_limit_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAP_TOKEN_ENABLED", "true")
    monkeypatch.setenv("MAP_TOKEN_ALLOWED_ORIGIN", "https://public.example")
    monkeypatch.setenv("MAP_TOKEN_RATE_LIMIT_PER_MINUTE", "1")

    module_path = Path("hosts/azure_functions/function_app.py")
    spec = importlib.util.spec_from_file_location("nzhem_function_app_rate_test", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class Request:
        params: dict[str, str] = {}
        headers = {
            "origin": "https://public.example",
            "referer": "https://public.example/map/",
            "x-forwarded-for": "192.0.2.1",
        }

    assert module.map_token(Request()).status_code == 503
    assert module.map_token(Request()).status_code == 429
