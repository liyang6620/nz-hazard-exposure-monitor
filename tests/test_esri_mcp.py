from __future__ import annotations

import base64
import json as jsonlib
from pathlib import Path

import pytest

from nzhem.adapters.local.esri_static_maps import EsriStaticMapsMcpClient
from nzhem.adapters.local.sqlite import SqliteTableStore
from nzhem.core.agent.esri import EsriToolRejected


class FakeResponse:
    def __init__(
        self, status_code: int, body: str, content_type: str = "text/event-stream"
    ) -> None:
        self.status_code = status_code
        self.text = body
        self.headers = {"Content-Type": content_type}

    def json(self):
        return jsonlib.loads(self.text)


class FakeSession:
    calls: list[dict] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def post(self, url, *, headers, json, timeout):
        payload = json
        self.calls.append(
            {
                "payload": payload,
                "authorization": headers.get("Authorization"),
                "url": url,
                "timeout": timeout,
            }
        )
        if payload["method"] == "initialize":
            result = {"protocolVersion": "2024-11-05", "capabilities": {}}
        elif payload["method"] == "notifications/initialized":
            return FakeResponse(202, "", "application/json")
        elif payload["method"] == "tools/list":
            result = {"tools": [{"name": "map_with_overlay"}, {"name": "solve_route"}]}
        elif payload["method"] == "tools/call":
            image = base64.b64encode(b"\x89PNG\r\n\x1a\nunit-test").decode("ascii")
            result = {"content": [{"type": "image", "mimeType": "image/png", "data": image}]}
        else:  # pragma: no cover - makes accidental extra calls obvious
            raise AssertionError(payload["method"])
        return FakeResponse(200, f"data: {jsonlib.dumps({'jsonrpc': '2.0', 'result': result})}\n\n")


class SecretStore:
    def get_secret(self, name: str) -> str:
        assert name == "ARCGIS_API_KEY"
        return "server-only-test-key"


def test_mcp_adapter_calls_only_static_map_and_records_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    FakeSession.calls = []
    monkeypatch.setattr("nzhem.adapters.local.esri_static_maps.requests.Session", FakeSession)
    tables = SqliteTableStore(tmp_path / "state.sqlite3")
    client = EsriStaticMapsMcpClient(SecretStore(), tables)

    image = client.render(briefing_id="briefing-1", longitude=172.6, latitude=-43.5)

    assert image.startswith(b"\x89PNG")
    payloads = [call["payload"] for call in FakeSession.calls]
    assert [call["method"] for call in payloads] == [
        "initialize",
        "notifications/initialized",
        "tools/list",
        "tools/call",
    ]
    assert payloads[-1]["params"]["name"] == "map_with_overlay"
    assert all(call["authorization"] == "Bearer server-only-test-key" for call in FakeSession.calls)
    assert all("token=" not in call["url"] for call in FakeSession.calls)
    assert all(call.get("params", {}).get("name") != "solve_route" for call in payloads)
    records = tables.list_entities("runs", "esri_static_map")
    assert records[0]["status"] == "success"


def test_mcp_adapter_enforces_two_maps_per_briefing_before_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    FakeSession.calls = []
    monkeypatch.setattr("nzhem.adapters.local.esri_static_maps.requests.Session", FakeSession)
    tables = SqliteTableStore(tmp_path / "state.sqlite3")
    client = EsriStaticMapsMcpClient(SecretStore(), tables)

    client.render(briefing_id="briefing-1", longitude=172.6, latitude=-43.5)
    client.render(briefing_id="briefing-1", longitude=172.6, latitude=-43.5)
    with pytest.raises(EsriToolRejected, match="Per-briefing"):
        client.render(briefing_id="briefing-1", longitude=172.6, latitude=-43.5)

    assert sum(call["payload"]["method"] == "tools/call" for call in FakeSession.calls) == 2
