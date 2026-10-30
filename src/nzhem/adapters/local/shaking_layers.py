from __future__ import annotations

import hashlib
import json
import os
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import requests

from nzhem.adapters.local.geonet import USER_AGENT
from nzhem.adapters.local.resource_guard import ResourceGuard


@dataclass(frozen=True)
class CachedShakingEvent:
    event_id: str
    root: Path
    manifest: dict[str, Any]
    param: dict[str, Any]
    station_list: dict[str, Any]
    polygon_shapefile: Path
    checksums: dict[str, str]


class ShakingLayersClient:
    def __init__(
        self,
        raw_root: Path,
        guard: ResourceGuard,
        *,
        base_url: str = "https://shakinglayers.geonet.org.nz/api/v1",
        timeout_seconds: int = 60,
    ) -> None:
        self._raw_root = raw_root
        self._guard = guard
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def cache_event(self, event_id: str) -> CachedShakingEvent:
        event_root = self._raw_root / event_id
        event_root.mkdir(parents=True, exist_ok=True)
        manifest = self._get_json(f"events/{event_id}/latest", event_root / "manifest.json")
        required = {"param.json", "stationlist.json", "intensity_mmi_contour_polygons.zip"}
        missing = required.difference(manifest.get("files", []))
        if missing:
            raise RuntimeError(f"{event_id} Shaking Layers manifest is missing {sorted(missing)}")

        param = self._get_json(f"events/{event_id}/latest/param.json", event_root / "param.json")
        station_list = self._get_json(
            f"events/{event_id}/latest/stationlist.json", event_root / "stationlist.json"
        )
        archive = self._get_file(
            f"events/{event_id}/latest/intensity_mmi_contour_polygons.zip",
            event_root / "intensity_mmi_contour_polygons.zip",
        )
        shapefile = self._extract_polygons(archive, event_root / "intensity_mmi_contour_polygons")
        paths = [
            event_root / "manifest.json",
            event_root / "param.json",
            event_root / "stationlist.json",
            archive,
        ]
        checksums = {path.name: _sha256(path) for path in paths}
        return CachedShakingEvent(
            event_id=event_id,
            root=event_root,
            manifest=manifest,
            param=param,
            station_list=station_list,
            polygon_shapefile=shapefile,
            checksums=checksums,
        )

    def _get_json(self, relative_url: str, destination: Path) -> dict[str, Any]:
        self._get_file(relative_url, destination)
        return json.loads(destination.read_text(encoding="utf-8"))

    def _get_file(self, relative_url: str, destination: Path) -> Path:
        if destination.exists() and destination.stat().st_size > 0:
            return destination
        self._guard.check()
        response = self._request(f"{self._base_url}/{relative_url.lstrip('/')}")
        temporary = destination.with_suffix(destination.suffix + ".part")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with temporary.open("wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output.write(chunk)
                    self._guard.check()
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, destination)
        return destination

    def _request(self, url: str) -> requests.Response:
        last_error: requests.RequestException | None = None
        for attempt in range(3):
            try:
                response = requests.get(
                    url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=self._timeout_seconds,
                    stream=True,
                )
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_error = exc
                if (
                    isinstance(exc, requests.HTTPError)
                    and exc.response is not None
                    and exc.response.status_code in {400, 401, 403, 404}
                ):
                    raise
                if attempt < 2:
                    time.sleep(2**attempt)
        assert last_error is not None
        raise last_error

    def _extract_polygons(self, archive: Path, destination: Path) -> Path:
        shapefile = destination / "intensity_mmi.shp"
        if shapefile.exists():
            return shapefile
        destination.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as source:
            total_size = sum(info.file_size for info in source.infolist())
            if total_size > 128 * 1024 * 1024:
                raise ValueError("Shaking Layers polygon archive exceeds the 128 MB safety limit")
            for info in source.infolist():
                member = PurePosixPath(info.filename)
                if member.is_absolute() or ".." in member.parts:
                    raise ValueError(f"Unsafe Shaking Layers archive path: {info.filename}")
                target = (destination / Path(*member.parts)).resolve()
                if destination.resolve() not in target.parents:
                    raise ValueError(f"Archive member escapes destination: {info.filename}")
                source.extract(info, destination)
                self._guard.check()
        if not shapefile.exists():
            raise RuntimeError(f"No intensity_mmi.shp in {archive}")
        return shapefile


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
