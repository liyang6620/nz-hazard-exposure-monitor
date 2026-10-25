from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from typing import Any

import requests

from nzhem.core.agent.esri import EsriStaticMapGuard, EsriToolRejected
from nzhem.ports import SecretStore, TableStore

MCP_ENDPOINT = "https://location-services-mcp.arcgis.com/beta/mcp"
STATIC_MAP_TOOL = "map_with_overlay"


class EsriStaticMapError(RuntimeError):
    """A sanitized error from the server-side Esri static-map adapter."""


class EsriStaticMapsMcpClient:
    """Call only Esri MCP's static-map tool and account for each attempt."""

    def __init__(
        self,
        secrets: SecretStore,
        tables: TableStore,
        *,
        api_key_name: str = "ARCGIS_API_KEY",
        per_briefing_limit: int = 2,
        monthly_limit: int = 200,
        timeout_seconds: float = 30,
    ) -> None:
        self._secrets = secrets
        self._guard = EsriStaticMapGuard(
            tables,
            per_briefing_limit=per_briefing_limit,
            monthly_limit=monthly_limit,
        )
        self._api_key_name = api_key_name
        self._timeout_seconds = timeout_seconds

    def render(self, *, briefing_id: str, longitude: float, latitude: float) -> bytes:
        reservation = self._guard.reserve(
            tool_name=EsriStaticMapGuard.ALLOWED_TOOL,
            briefing_id=briefing_id,
            now=datetime.now(UTC),
        )
        try:
            image = self._call_map_tool(longitude=longitude, latitude=latitude)
        except Exception as exc:
            self._guard.record_result(reservation, success=False)
            if isinstance(exc, EsriToolRejected):
                raise
            if isinstance(exc, EsriStaticMapError):
                raise
            raise EsriStaticMapError("Esri static-map request failed") from None
        self._guard.record_result(reservation, success=True)
        return image

    def _call_map_tool(self, *, longitude: float, latitude: float) -> bytes:
        if not (-179.99 <= longitude <= 179.99 and -85.05 <= latitude <= 85.05):
            raise EsriStaticMapError("Map coordinates are outside the WGS84 service bounds")
        api_key = self._secrets.get_secret(self._api_key_name)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        with requests.Session() as session:
            initialized = self._post(
                session,
                headers,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "nzhem-server", "version": "1.0"},
                    },
                },
            )
            if initialized.get("error"):
                raise EsriStaticMapError("Esri MCP initialization was rejected")
            self._post(
                session,
                headers,
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {},
                },
                allow_empty=True,
            )
            tools = self._post(
                session,
                headers,
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            )
            if tools.get("error"):
                raise EsriStaticMapError("Esri MCP tool discovery was rejected")
            names = {str(tool.get("name")) for tool in tools.get("result", {}).get("tools", [])}
            if STATIC_MAP_TOOL not in names:
                raise EsriStaticMapError("Esri MCP static-map tool is unavailable")

            point = {
                "x": longitude,
                "y": latitude,
                "spatialReference": {"wkid": 4326},
            }
            result = self._post(
                session,
                headers,
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": STATIC_MAP_TOOL,
                        "arguments": {
                            "arcgisStyle": "streets",
                            "center": point,
                            "radius": 20000,
                            "imageWidth": 800,
                            "imageHeight": 500,
                            "points": [
                                {
                                    "geometry": point,
                                    "label": "E",
                                    "style": "pin",
                                    "color": "#D7191C",
                                }
                            ],
                        },
                    },
                },
            )
        if result.get("error"):
            raise EsriStaticMapError("Esri MCP map generation was rejected")
        tool_result = result.get("result", {})
        if tool_result.get("isError"):
            raise EsriStaticMapError("Esri MCP map generation failed")
        for content in tool_result.get("content", []):
            if content.get("type") == "image" and content.get("mimeType") == "image/png":
                try:
                    image = base64.b64decode(content["data"], validate=True)
                except (KeyError, ValueError) as exc:
                    raise EsriStaticMapError("Esri MCP returned an invalid PNG image") from exc
                if not image.startswith(b"\x89PNG\r\n\x1a\n"):
                    raise EsriStaticMapError("Esri MCP response was not a PNG image")
                return image
        raise EsriStaticMapError("Esri MCP response did not contain a PNG image")

    def _post(
        self,
        session: requests.Session,
        headers: dict[str, str],
        payload: dict[str, Any],
        *,
        allow_empty: bool = False,
    ) -> dict[str, Any]:
        try:
            response = session.post(
                MCP_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=self._timeout_seconds,
            )
        except requests.RequestException:
            raise EsriStaticMapError("Esri MCP network request failed") from None
        if response.status_code not in {200, 202}:
            raise EsriStaticMapError(f"Esri MCP returned HTTP {response.status_code}")
        if allow_empty and not response.text.strip():
            return {}
        try:
            if "text/event-stream" in response.headers.get("Content-Type", ""):
                data = [
                    line[5:].strip()
                    for line in response.text.splitlines()
                    if line.startswith("data:") and line[5:].strip()
                ]
                if not data:
                    return {}
                return json.loads(data[-1])
            return response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise EsriStaticMapError("Esri MCP returned an invalid JSON-RPC response") from exc
