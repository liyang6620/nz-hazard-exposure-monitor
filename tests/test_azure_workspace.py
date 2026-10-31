from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from nzhem.adapters.azure import AzureObjectStore, AzureTableStore
from nzhem.adapters.azure.workspace import AzureDataWorkspace, AzureSiteDataPublisher
from nzhem.adapters.local.duckdb_extensions import load_extension


def test_duckdb_extension_loader_rejects_missing_offline_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NZHEM_DUCKDB_EXTENSIONS_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        load_extension(SimpleNamespace(execute=lambda _: None), "h3")


def test_duckdb_extension_loader_keeps_local_install(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NZHEM_DUCKDB_EXTENSIONS_DIR", raising=False)
    statements: list[str] = []
    load_extension(SimpleNamespace(execute=statements.append), "h3")
    assert statements == ["load h3"]


def test_azure_table_adapter_round_trips_structured_fields() -> None:
    saved: dict = {}

    class TableClient:
        def upsert_entity(self, entity: dict, mode: str) -> None:
            assert mode == "replace"
            saved.update(entity)

        def get_entity(self, partition_key: str, row_key: str) -> dict:
            assert partition_key == "recent" and row_key == "event"
            return saved

    adapter = AzureTableStore.__new__(AzureTableStore)
    adapter._service = SimpleNamespace(get_table_client=lambda _: TableClient())
    adapter.upsert_entity(
        "eventsstate",
        {
            "PartitionKey": "recent",
            "RowKey": "event",
            "regions": [{"name": "Canterbury", "buildings": 2}],
            "max_mmi": None,
        },
    )

    assert "max_mmi" not in saved
    assert adapter.get_entity("eventsstate", "recent", "event")["regions"] == [
        {"name": "Canterbury", "buildings": 2}
    ]


def test_azure_object_store_publishes_exact_event_route_as_html() -> None:
    saved: dict = {}

    class Blob:
        def upload_blob(self, data: bytes, **kwargs: object) -> None:
            saved.update(data=data, **kwargs)

    store = AzureObjectStore.__new__(AzureObjectStore)
    store._service = SimpleNamespace(
        get_blob_client=lambda container, path: (
            Blob() if (container, path) == ("$web", "events/2016p858000") else None
        )
    )
    store.put_bytes("web", "events/2016p858000", b"<html>app</html>")

    assert saved["data"] == b"<html>app</html>"
    assert saved["content_settings"].content_type == "text/html"
    assert saved["content_settings"].cache_control == "no-cache"


def test_workspace_rejects_blob_path_traversal(tmp_path: Path) -> None:
    class Container:
        def list_blobs(self, name_starts_with: str) -> list[SimpleNamespace]:
            assert name_starts_with == "reference-export/"
            return [
                SimpleNamespace(name="reference-export/../outside.parquet", etag="etag", size=10)
            ]

    workspace = AzureDataWorkspace(
        SimpleNamespace(get_container_client=lambda _: Container()), tmp_path
    )
    with pytest.raises(ValueError, match="path"):
        workspace.sync_prefix(
            "curated", "reference-export", tmp_path / "curated", suffixes=(".parquet",)
        )


def test_site_publisher_uploads_manifest_last(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Workspace:
        root = tmp_path

        def latest_reference(self) -> Path:
            return tmp_path / "reference"

        def sync_gold(self) -> Path:
            return tmp_path / "gold"

        def sync_realtime(self) -> Path:
            return tmp_path / "realtime"

    class Publisher:
        def __init__(self, **kwargs: object) -> None:
            pass

        def publish(self, generated_at: datetime) -> dict[str, str]:
            root = tmp_path / "web" / "data"
            generation = root / "generations" / "generation"
            generation.mkdir(parents=True)
            (generation / "events.json").write_text('[{"event_id":"2026p123456"}]')
            (root / "manifest-generation.json").write_text("{}")
            (root / "manifest.json").write_text("{}")
            return {"generation_id": "generation"}

    monkeypatch.setattr("nzhem.adapters.azure.workspace.LocalSiteDataPublisher", Publisher)
    uploads: list[str] = []
    objects = SimpleNamespace(
        put_bytes=lambda container, path, data: uploads.append(path),
        get_bytes=lambda container, path: b"<html>app</html>",
    )
    publisher = AzureSiteDataPublisher(Workspace(), objects, None, memory_limit_mb=512)

    publisher.publish(datetime(2026, 10, 31, tzinfo=UTC))

    assert uploads == [
        "data/generations/generation/events.json",
        "history",
        "history/index.html",
        "method",
        "method/index.html",
        "about",
        "about/index.html",
        "events/2026p123456",
        "events/2026p123456/index.html",
        "data/manifest-generation.json",
        "data/manifest.json",
    ]
