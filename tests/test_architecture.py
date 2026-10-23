from __future__ import annotations

import ast
import importlib.util
from pathlib import Path


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
