from types import SimpleNamespace
from unittest.mock import Mock

import azure.functions as func
from hosts.azure_functions import function_app as host


def test_cloud_json_preview_allows_only_site_origin(monkeypatch):
    approval = Mock()
    approval.preview.return_value = SimpleNamespace(title="Kaikōura review", action="approve")
    monkeypatch.setattr(host, "build_container", lambda: SimpleNamespace(approval=lambda: approval))
    monkeypatch.setattr(
        host.Settings,
        "from_env",
        lambda: SimpleNamespace(map_token_allowed_origin="https://site.example"),
    )
    request = func.HttpRequest(
        method="GET",
        url="https://functions.example/api/review-briefing",
        headers={
            "accept": "application/json",
            "origin": "https://site.example",
            "x-review-token": "private-test-token",
        },
        params={},
        body=b"",
    )
    response = host.review_briefing_get(request)
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "https://site.example"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert b"Kaik" in response.get_body()
    approval.decide.assert_not_called()

    other_request = func.HttpRequest(
        method="GET",
        url="https://functions.example/api/review-briefing",
        headers={
            "accept": "application/json",
            "origin": "https://other.example",
            "x-review-token": "private-test-token",
        },
        params={},
        body=b"",
    )
    response = host.review_briefing_get(other_request)
    assert "Access-Control-Allow-Origin" not in response.headers
