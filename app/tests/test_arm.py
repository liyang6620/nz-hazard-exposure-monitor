from unittest.mock import Mock

from nzhem.arm import stop_function_app
from nzhem.config import Settings


def test_stop_function_app_uses_managed_identity_token(monkeypatch) -> None:
    token = Mock(token="test-token")
    identity = Mock()
    identity.get_token.return_value = token
    response = Mock()
    monkeypatch.setattr("nzhem.arm.credential", lambda: identity)
    post = Mock(return_value=response)
    monkeypatch.setattr("nzhem.arm.requests.post", post)
    settings = Settings("storage", "sub", "rg", "app", "https://acs", "sender", "recipient")

    stop_function_app(settings)

    url = post.call_args.args[0]
    assert "/subscriptions/sub/resourceGroups/rg/" in url
    assert "/sites/app/stop" in url
    assert post.call_args.kwargs["timeout"] == 30
    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer test-token"
    response.raise_for_status.assert_called_once()
