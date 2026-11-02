from __future__ import annotations

import json
import os
import shutil
import threading
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from azure.storage.blob import BlobServiceClient

from nzhem.adapters.local.realtime import LocalRealtimeEventAssessor
from nzhem.adapters.local.resource_guard import ResourceGuard
from nzhem.adapters.local.site_data import LocalSiteDataPublisher
from nzhem.core.site_routes import static_route_blobs
from nzhem.ports import EventAssessor, ObjectStore, TableStore

_publish_lock = threading.Lock()
_MIN_FREE_BYTES = 256 * 1024 * 1024


class AzureDataWorkspace:
    """Bounded local Parquet cache backed by private Azure Blob containers."""

    def __init__(self, service: BlobServiceClient, root: Path) -> None:
        self._service = service
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def sync_prefix(
        self, container: str, prefix: str, destination: Path, *, suffixes: tuple[str, ...]
    ) -> int:
        client = self._service.get_container_client(container)
        count = 0
        for blob in client.list_blobs(name_starts_with=prefix.rstrip("/") + "/"):
            name = str(blob.name)
            if not name.endswith(suffixes):
                continue
            relative = PurePosixPath(name).relative_to(prefix.rstrip("/"))
            if any(part in {"", ".", ".."} for part in relative.parts):
                raise ValueError("Invalid curated blob path")
            target = destination.joinpath(*relative.parts)
            if not target.resolve().is_relative_to(destination.resolve()):
                raise ValueError("Curated blob path escapes workspace")
            etag_path = target.with_name(target.name + ".etag")
            etag = str(blob.etag)
            if target.is_file() and etag_path.is_file() and etag_path.read_text() == etag:
                count += 1
                continue
            size = int(blob.size)
            if shutil.disk_usage(self.root).free - size < _MIN_FREE_BYTES:
                raise OSError("Azure workspace is below its temporary-disk reserve")
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + ".download")
            try:
                with temporary.open("wb") as output:
                    for chunk in client.download_blob(name, max_concurrency=1).chunks():
                        output.write(chunk)
                if temporary.stat().st_size != size:
                    raise OSError("Curated blob download length mismatch")
                os.replace(temporary, target)
                etag_path.write_text(etag, encoding="ascii")
            finally:
                temporary.unlink(missing_ok=True)
            count += 1
        return count

    def latest_reference(self) -> Path:
        root = self.root / "curated" / "reference-export"
        count = self.sync_prefix("curated", "reference-export", root, suffixes=(".parquet",))
        generations = (
            sorted(path for path in root.iterdir() if path.is_dir()) if root.exists() else []
        )
        if not count or not generations:
            raise FileNotFoundError("Approved reference Parquet has not been staged")
        return generations[-1]

    def sync_gold(self) -> Path:
        root = self.root / "curated" / "events" / "m3"
        if not self.sync_prefix("gold", "events/m3", root, suffixes=(".parquet",)):
            raise FileNotFoundError("M3 gold Parquet has not been staged")
        return root

    def sync_realtime(self) -> Path:
        root = self.root / "curated" / "events" / "realtime"
        self.sync_prefix("curated", "events/realtime", root, suffixes=(".json", ".geojson"))
        return root

    def upload_tree(self, container: str, prefix: str, source: Path) -> int:
        count = 0
        client = self._service.get_container_client(container)
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            name = f"{prefix.rstrip('/')}/{path.relative_to(source).as_posix()}"
            with path.open("rb") as stream:
                client.upload_blob(name, stream, overwrite=True, max_concurrency=1)
            count += 1
        return count


class AzureRealtimeEventAssessor(EventAssessor):
    def __init__(self, workspace: AzureDataWorkspace, *, memory_limit_mb: int) -> None:
        self._workspace = workspace
        self._memory_limit_mb = memory_limit_mb

    def assess(self, event: Mapping[str, Any], assessed_at: datetime) -> Mapping[str, Any]:
        reference = self._workspace.latest_reference()
        root = self._workspace.root
        output_root = root / "curated" / "events" / "realtime"
        assessor = LocalRealtimeEventAssessor(
            reference_root=reference,
            raw_root=root / "raw" / "events" / "realtime",
            output_root=output_root,
            guard=ResourceGuard(root, min_free_disk_gb=0.25, max_rss_mb=768),
            memory_limit_mb=self._memory_limit_mb,
        )
        result = assessor.assess(event, assessed_at)
        event_id = str(event["event_id"])
        source = output_root / event_id
        if source.is_dir():
            self._workspace.upload_tree("curated", f"events/realtime/{event_id}", source)
        return result


class AzureSiteDataPublisher:
    def __init__(
        self,
        workspace: AzureDataWorkspace,
        objects: ObjectStore,
        tables: TableStore,
        *,
        memory_limit_mb: int,
    ) -> None:
        self._workspace = workspace
        self._objects = objects
        self._tables = tables
        self._memory_limit_mb = memory_limit_mb

    def publish(self, generated_at: datetime) -> Mapping[str, Any]:
        with _publish_lock:
            reference = self._workspace.latest_reference()
            gold = self._workspace.sync_gold()
            realtime = self._workspace.sync_realtime()
            web = self._workspace.root / "web"
            publisher = LocalSiteDataPublisher(
                event_root=gold,
                reference_root=reference,
                web_root=web,
                tables=self._tables,
                realtime_root=realtime,
                memory_limit_mb=self._memory_limit_mb,
            )
            result = publisher.publish(generated_at)
            generation_id = str(result["generation_id"])
            generation = web / "data" / "generations" / generation_id
            for path in sorted(generation.rglob("*")):
                if path.is_file():
                    relative = path.relative_to(web).as_posix()
                    self._objects.put_bytes("web", relative, path.read_bytes())
            index_html = self._objects.get_bytes("web", "index.html")
            events = json.loads((generation / "events.json").read_text(encoding="utf-8"))
            for route in static_route_blobs(str(event["event_id"]) for event in events):
                self._objects.put_bytes("web", route, index_html)
            for name in (f"manifest-{generation_id}.json", "manifest.json"):
                relative = f"data/{name}"
                self._objects.put_bytes("web", relative, (web / relative).read_bytes())
            return result
