from unittest.mock import Mock

import nzhem.identity as identity_module


def test_credential_disables_interactive_login(monkeypatch) -> None:
    identity_module.credential.cache_clear()
    constructor = Mock(return_value=Mock())
    monkeypatch.setattr(identity_module, "DefaultAzureCredential", constructor)

    first = identity_module.credential()
    second = identity_module.credential()

    assert first is second
    constructor.assert_called_once_with(exclude_interactive_browser_credential=True)
    identity_module.credential.cache_clear()
