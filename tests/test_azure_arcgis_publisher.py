from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from nzhem.adapters.azure.arcgis_publisher import ArcgisPublishRejected, AzureArcgisPublisher

ITEM_ID = "ce9c69b085584965a236d0c6fdfb7ebc"
LAYER = "https://services1.arcgis.com/owner/arcgis/rest/services/event_exposure_r6/FeatureServer"
EVENT_ID = "2026p824047"
GENERATION = "20261103T010000000000Z"


class MemoryObjects:
    def __init__(self, features: list[dict[str, Any]]) -> None:
        self.data = {
            "data/manifest.json": {"generation_id": GENERATION},
            f"data/generations/{GENERATION}/events.json": [
                {
                    "event_id": EVENT_ID,
                    "is_recent_monitoring": True,
                    "assessment_status": "ready",
                }
            ],
            f"data/generations/{GENERATION}/events/{EVENT_ID}/exposure.geojson": {
                "type": "FeatureCollection",
                "features": features,
            },
        }

    def get_bytes(self, container: str, path: str) -> bytes:
        assert container == "web"
        return json.dumps(self.data[path]).encode()


class MemoryTables:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], dict[str, Any]] = {}

    def get_entity(self, table: str, partition: str, row: str) -> dict[str, Any] | None:
        assert table == "runs"
        return self.rows.get((partition, row))

    def upsert_entity(self, table: str, entity: dict[str, Any]) -> None:
        assert table == "runs"
        self.rows[(entity["PartitionKey"], entity["RowKey"])] = entity

    def list_entities(self, table: str, partition: str) -> list[dict[str, Any]]:
        assert table == "runs"
        return [row for (part, _), row in self.rows.items() if part == partition]


class Secrets:
    def get_secret(self, name: str) -> str:
        assert name == "ARCGIS_API_KEY"
        return "test-secret-never-persisted"


class Response:
    def __init__(self, value: dict[str, Any]) -> None:
        self.value = value

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, Any]:
        return self.value


class ArcgisSession:
    def __init__(self) -> None:
        self.existing: dict[str, int] = {}
        self.edits: list[dict[str, Any]] = []
        self.storage_usage = 3_513_272
        self.fail_edits = False

    def post(self, url: str, *, data: dict[str, Any], timeout: int) -> Response:
        assert timeout == 30
        assert data["token"] == "test-secret-never-persisted"
        if url.endswith(f"items/{ITEM_ID}"):
            return Response(
                {"id": ITEM_ID, "type": "Feature Service", "access": "private", "url": LAYER}
            )
        if url.endswith("community/self"):
            return Response({"storageUsage": self.storage_usage})
        if url == f"{LAYER}/0":
            return Response(
                {
                    "capabilities": "Create,Delete,Query,Update,Editing",
                    "objectIdField": "OBJECTID",
                    "fields": [
                        {"name": name}
                        for name in (
                            "OBJECTID",
                            "event_id",
                            "h3_r6",
                            "mmi",
                            "mmi_source",
                            "source_version",
                            "event_bldg",
                            "event_time_bldg",
                            "pop_2023",
                        )
                    ],
                }
            )
        if url.endswith("/query"):
            assert data["orderByFields"] == "OBJECTID ASC"
            offset = int(data["resultOffset"])
            rows = sorted(self.existing.items(), key=lambda item: item[1])[offset : offset + 1000]
            return Response(
                {
                    "features": [
                        {"attributes": {"h3_r6": h3, "OBJECTID": object_id}}
                        for h3, object_id in rows
                    ],
                    "exceededTransferLimit": offset + len(rows) < len(self.existing),
                }
            )
        assert url.endswith("/applyEdits")
        self.edits.append(data)
        return Response(
            {
                name: [{"success": not self.fail_edits} for _ in values]
                for name, values in (
                    ("addResults", json.loads(data["adds"])),
                    ("updateResults", json.loads(data["updates"])),
                    ("deleteResults", data["deletes"].split(",") if data["deletes"] else []),
                )
            }
        )


def feature(h3: int, *, buildings: int = 2) -> dict[str, Any]:
    return {
        "type": "Feature",
        "properties": {
            "h3_res6": str(h3),
            "mmi": 5.4,
            "mmi_source": "preliminary",
            "source_version": "reviewed",
            "buildings": buildings,
            "population": 3.5,
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[172.0, -41.0], [173.0, -41.0], [173.0, -42.0], [172.0, -41.0]]],
        },
    }


def publisher(
    features: list[dict[str, Any]], session: ArcgisSession | None = None
) -> tuple[AzureArcgisPublisher, MemoryTables, ArcgisSession]:
    tables = MemoryTables()
    session = session or ArcgisSession()
    return (
        AzureArcgisPublisher(
            MemoryObjects(features),
            tables,
            Secrets(),
            item_id=ITEM_ID,
            key_name="ARCGIS_API_KEY",
            session=session,
        ),
        tables,
        session,
    )


def test_incremental_edits_and_digest_skip() -> None:
    session = ArcgisSession()
    session.existing = {"606773022073815039": 10, "606773031200620543": 11}
    service, tables, _ = publisher(
        [feature(606773022073815039), feature(606773031469055999)], session
    )
    now = datetime(2026, 11, 3, tzinfo=UTC)

    assert service.publish(now) == {"events": 1, "features_edited": 3}
    edit = session.edits[0]
    assert len(json.loads(edit["adds"])) == 1
    assert len(json.loads(edit["updates"])) == 1
    assert edit["deletes"] == "11"
    attributes = json.loads(edit["updates"])[0]["attributes"]
    assert attributes["OBJECTID"] == 10
    assert attributes["event_time_bldg"] == 2
    assert "asif_bldg" not in attributes
    assert tables.get_entity("runs", "arcgis_published_event", EVENT_ID) is not None
    assert service.publish(now) == {"events": 0, "features_edited": 0}
    assert len(session.edits) == 1


def test_failed_batch_is_not_marked_published() -> None:
    session = ArcgisSession()
    session.fail_edits = True
    service, tables, _ = publisher([feature(606773022073815039)], session)
    with pytest.raises(ArcgisPublishRejected, match="failed or incomplete"):
        service.publish(datetime(2026, 11, 3, tzinfo=UTC))
    assert tables.get_entity("runs", "arcgis_published_event", EVENT_ID) is None


def test_storage_quota_rejects_without_edits() -> None:
    session = ArcgisSession()
    session.storage_usage = 125 * 1024 * 1024
    service, _, _ = publisher([feature(606773022073815039)], session)
    with pytest.raises(ArcgisPublishRejected, match="storage"):
        service.publish(datetime(2026, 11, 3, tzinfo=UTC))
    assert session.edits == []


def test_edits_are_batched_at_fifty_features() -> None:
    service, _, session = publisher([feature(606773022073815039 + cell) for cell in range(51)])
    assert service.publish(datetime(2026, 11, 3, tzinfo=UTC)) == {
        "events": 1,
        "features_edited": 51,
    }
    assert [len(json.loads(batch["adds"])) for batch in session.edits] == [50, 1]


def test_monthly_edit_quota_rejects_without_edits() -> None:
    service, tables, session = publisher([feature(606773022073815039)])
    tables.upsert_entity(
        "runs",
        {
            "PartitionKey": "arcgis_feature_edit",
            "RowKey": "prior",
            "attempted_at": "2026-11-01T00:00:00+00:00",
            "byte_count": 125 * 1024 * 1024,
        },
    )
    with pytest.raises(ArcgisPublishRejected, match="monthly feature-edit"):
        service.publish(datetime(2026, 11, 3, tzinfo=UTC))
    assert session.edits == []


def test_rejects_duplicate_cells_and_invalid_geometry() -> None:
    service, _, session = publisher([feature(606773022073815039)] * 2)
    with pytest.raises(ArcgisPublishRejected, match="Duplicate H3"):
        service.publish(datetime(2026, 11, 3, tzinfo=UTC))
    invalid = feature(606773022073815039)
    invalid["geometry"]["coordinates"][0][-1] = [174.0, -41.0]
    service, _, _ = publisher([invalid])
    with pytest.raises(ArcgisPublishRejected, match="invalid polygon"):
        service.publish(datetime(2026, 11, 3, tzinfo=UTC))
    assert session.edits == []
