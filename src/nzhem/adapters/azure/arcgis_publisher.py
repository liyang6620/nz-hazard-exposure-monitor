from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import requests

from nzhem.ports import ObjectStore, SecretStore, TableStore

_ITEM_ID = re.compile(r"[a-f0-9]{32}\Z")
_EVENT_ID = re.compile(r"[0-9]{4}p[0-9]+\Z")
_GENERATION = re.compile(r"[0-9]{8}T[0-9]{6}[0-9]+Z\Z")
_LIMIT_BYTES = 125 * 1024 * 1024
_MAX_EVENT_BYTES = 16 * 1024 * 1024
_BATCH_SIZE = 50


class ArcgisPublishRejected(RuntimeError):
    """Publishing was withheld because the endpoint, quota or edit result was unsafe."""


def _arcgis_error(response: Mapping[str, Any]) -> None:
    if "error" in response:
        code = response["error"].get("code", "unknown")
        raise ArcgisPublishRejected(f"ArcGIS rejected the request (code {code})")


def _clockwise(ring: list[list[float]], *, outer: bool) -> list[list[float]]:
    signed = sum(
        float(a[0]) * float(b[1]) - float(b[0]) * float(a[1])
        for a, b in zip(ring, ring[1:], strict=False)
    )
    if (signed < 0) != outer:
        return list(reversed(ring))
    return ring


def _feature(event_id: str, source: Mapping[str, Any], object_id: int | None) -> dict[str, Any]:
    properties = source["properties"]
    geometry = source["geometry"]
    polygon = geometry["coordinates"]
    if geometry["type"] != "Polygon" or not polygon:
        raise ArcgisPublishRejected("Only bounded polygon exposure features are supported")
    h3 = str(properties["h3_res6"])
    if not h3.isdecimal():
        raise ArcgisPublishRejected("Exposure feature has an invalid H3 cell")
    rings = []
    for index, ring in enumerate(polygon):
        if (
            len(ring) < 4
            or ring[0] != ring[-1]
            or any(
                len(point) != 2 or not all(math.isfinite(float(value)) for value in point)
                for point in ring
            )
        ):
            raise ArcgisPublishRejected("Exposure feature has an invalid polygon ring")
        rings.append(_clockwise(ring, outer=index == 0))
    attributes: dict[str, Any] = {
        "event_id": event_id,
        "h3_r6": h3,
        "mmi": float(properties["mmi"]),
        "mmi_source": str(properties["mmi_source"]),
        "source_version": str(properties["source_version"]),
        "event_bldg": int(properties["buildings"]),
        "event_time_bldg": int(properties["buildings"]),
        "pop_2023": float(properties["population"]),
    }
    if object_id is not None:
        attributes["OBJECTID"] = object_id
    return {
        "attributes": attributes,
        "geometry": {"rings": rings, "spatialReference": {"wkid": 4326}},
    }


class AzureArcgisPublisher:
    """Single-timer, bounded publisher for the existing private NZHEM layer."""

    def __init__(
        self,
        objects: ObjectStore,
        tables: TableStore,
        secrets: SecretStore,
        *,
        item_id: str,
        key_name: str,
        session: requests.Session | None = None,
    ) -> None:
        if not _ITEM_ID.fullmatch(item_id):
            raise ValueError("Invalid ArcGIS item ID")
        self._objects = objects
        self._tables = tables
        self._key = secrets.get_secret(key_name)
        self._item_id = item_id
        self._session = session or requests.Session()
        self._layer_url: str | None = None

    def _request(self, url: str, **data: Any) -> dict[str, Any]:
        response = self._session.post(
            url,
            data={"f": "json", "token": self._key, **data},
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict):
            raise ArcgisPublishRejected("ArcGIS returned an invalid response")
        _arcgis_error(result)
        return result

    def _endpoint_and_quota(self) -> str:
        item = self._request(f"https://www.arcgis.com/sharing/rest/content/items/{self._item_id}")
        url = str(item.get("url", ""))
        if (
            item.get("id") != self._item_id
            or item.get("type") != "Feature Service"
            or item.get("access") != "private"
            or not re.fullmatch(
                r"https://services[0-9]*\.arcgis\.com/[A-Za-z0-9]+/arcgis/rest/services/"
                r"event_exposure_r6/FeatureServer",
                url,
            )
        ):
            raise ArcgisPublishRejected("The configured item is not the private NZHEM layer")
        usage = self._request("https://www.arcgis.com/sharing/rest/community/self")
        if int(usage.get("storageUsage", _LIMIT_BYTES)) >= _LIMIT_BYTES:
            raise ArcgisPublishRejected("ArcGIS project storage has reached 125 MiB")
        layer = self._request(f"{url}/0")
        capabilities = set(str(layer.get("capabilities", "")).split(","))
        if not {"Create", "Delete", "Query", "Update"}.issubset(capabilities):
            raise ArcgisPublishRejected("The NZHEM layer does not support all incremental edits")
        if layer.get("objectIdField") != "OBJECTID":
            raise ArcgisPublishRejected("The NZHEM layer object ID field changed")
        fields = {str(field.get("name")) for field in layer.get("fields", [])}
        if not {
            "OBJECTID",
            "event_id",
            "h3_r6",
            "mmi",
            "mmi_source",
            "source_version",
            "event_bldg",
            "event_time_bldg",
            "pop_2023",
        }.issubset(fields):
            raise ArcgisPublishRejected("The NZHEM layer field contract changed")
        self._layer_url = f"{url}/0"
        return self._layer_url

    def _existing(self, event_id: str) -> dict[str, int]:
        assert self._layer_url is not None
        existing: dict[str, int] = {}
        offset = 0
        while True:
            page = self._request(
                f"{self._layer_url}/query",
                where=f"event_id='{event_id}'",
                outFields="OBJECTID,h3_r6",
                returnGeometry="false",
                resultOffset=offset,
                resultRecordCount=1000,
                orderByFields="OBJECTID ASC",
            )
            features = page.get("features", [])
            if not isinstance(features, list):
                raise ArcgisPublishRejected("ArcGIS query returned invalid features")
            for feature in features:
                attributes = feature["attributes"]
                h3 = str(attributes["h3_r6"])
                if h3 in existing:
                    raise ArcgisPublishRejected("Duplicate H3 cell in the hosted event layer")
                existing[h3] = int(attributes["OBJECTID"])
            offset += len(features)
            if not features and page.get("exceededTransferLimit"):
                raise ArcgisPublishRejected("ArcGIS query pagination did not advance")
            if not page.get("exceededTransferLimit") and len(features) < 1000:
                return existing

    def _reserve(self, payload_bytes: int, *, event_id: str, now: datetime) -> None:
        if payload_bytes > 1024 * 1024:
            raise ArcgisPublishRejected("ArcGIS edit batch exceeds 1 MiB")
        month = now.astimezone(UTC).strftime("%Y-%m")
        spent = sum(
            int(row.get("byte_count", 0))
            for row in self._tables.list_entities("runs", "arcgis_feature_edit")
            if str(row.get("attempted_at", "")).startswith(month)
        )
        if spent + payload_bytes > _LIMIT_BYTES:
            raise ArcgisPublishRejected("ArcGIS monthly feature-edit allowance is exhausted")
        self._tables.upsert_entity(
            "runs",
            {
                "PartitionKey": "arcgis_feature_edit",
                "RowKey": uuid.uuid4().hex,
                "event_id": event_id,
                "attempted_at": now.astimezone(UTC).isoformat(),
                "byte_count": payload_bytes,
            },
        )

    def _apply_batch(
        self,
        event_id: str,
        *,
        adds: list[dict[str, Any]],
        updates: list[dict[str, Any]],
        deletes: list[int],
        now: datetime,
    ) -> int:
        assert self._layer_url is not None
        data = {
            "adds": json.dumps(adds, separators=(",", ":")),
            "updates": json.dumps(updates, separators=(",", ":")),
            "deletes": ",".join(map(str, deletes)),
            "rollbackOnFailure": "true",
        }
        byte_count = sum(len(value.encode("utf-8")) for value in data.values())
        self._reserve(byte_count, event_id=event_id, now=now)
        response = self._request(f"{self._layer_url}/applyEdits", **data)
        for key, expected in (
            ("addResults", len(adds)),
            ("updateResults", len(updates)),
            ("deleteResults", len(deletes)),
        ):
            results = response.get(key, [])
            if len(results) != expected or any(not item.get("success") for item in results):
                raise ArcgisPublishRejected("ArcGIS returned a failed or incomplete edit batch")
        return len(adds) + len(updates) + len(deletes)

    def publish(self, now: datetime) -> dict[str, int]:
        self._endpoint_and_quota()
        manifest = json.loads(self._objects.get_bytes("web", "data/manifest.json"))
        generation = str(manifest.get("generation_id", ""))
        if not _GENERATION.fullmatch(generation):
            raise ArcgisPublishRejected("Published site manifest has an invalid generation")
        prefix = f"data/generations/{generation}"
        events = json.loads(self._objects.get_bytes("web", f"{prefix}/events.json"))
        edited = 0
        completed = 0
        for event in events:
            if not event.get("is_recent_monitoring") or event.get("assessment_status") != "ready":
                continue
            event_id = str(event["event_id"])
            if not _EVENT_ID.fullmatch(event_id):
                raise ArcgisPublishRejected("Published site data has an invalid event ID")
            raw = self._objects.get_bytes("web", f"{prefix}/events/{event_id}/exposure.geojson")
            if len(raw) > _MAX_EVENT_BYTES:
                raise ArcgisPublishRejected("One event exposure file exceeds 16 MiB")
            digest = hashlib.sha256(raw).hexdigest()
            prior = self._tables.get_entity("runs", "arcgis_published_event", event_id)
            if prior is not None and prior.get("sha256") == digest:
                continue
            feature_collection = json.loads(raw)
            if feature_collection.get("type") != "FeatureCollection":
                raise ArcgisPublishRejected("Published event geometry is not a feature collection")
            features = feature_collection.get("features", [])
            if not isinstance(features, list) or len(features) > 10000:
                raise ArcgisPublishRejected("One event exceeds the ArcGIS feature batch limit")
            existing = self._existing(event_id)
            seen: set[str] = set()
            adds: list[dict[str, Any]] = []
            updates: list[dict[str, Any]] = []
            for source in features:
                h3 = str(source["properties"]["h3_res6"])
                if h3 in seen:
                    raise ArcgisPublishRejected("Duplicate H3 cell in published event data")
                seen.add(h3)
                object_id = existing.get(h3)
                target = updates if object_id is not None else adds
                target.append(_feature(event_id, source, object_id))
            deletes = [value for key, value in existing.items() if key not in seen]
            for index in range(0, max(len(adds), len(updates), len(deletes)), _BATCH_SIZE):
                edited += self._apply_batch(
                    event_id,
                    adds=adds[index : index + _BATCH_SIZE],
                    updates=updates[index : index + _BATCH_SIZE],
                    deletes=deletes[index : index + _BATCH_SIZE],
                    now=now,
                )
            self._endpoint_and_quota()
            self._tables.upsert_entity(
                "runs",
                {
                    "PartitionKey": "arcgis_published_event",
                    "RowKey": event_id,
                    "sha256": digest,
                    "published_at": now.astimezone(UTC).isoformat(),
                    "edited_features": len(adds) + len(updates) + len(deletes),
                },
            )
            completed += 1
        return {"events": completed, "features_edited": edited}
