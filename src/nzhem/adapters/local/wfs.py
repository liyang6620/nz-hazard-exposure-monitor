from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
import random
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import BinaryIO

import requests

from nzhem.adapters.local.resource_guard import ResourceGuard
from nzhem.ports import SecretStore

USER_AGENT = "nz-hazard-exposure-monitor/0.1 reference-refresh"
LOGGER = logging.getLogger(__name__)


class WfsError(RuntimeError):
    """A sanitized WFS failure that never contains a credential-bearing URL."""


@dataclass(frozen=True)
class WfsSource:
    name: str
    base_url: str
    layer: str
    key_name: str
    id_field: str
    geometry_field: str
    properties: tuple[str, ...]

    @property
    def type_name(self) -> str:
        return f"layer-{self.layer}"


@dataclass(frozen=True)
class WfsPartition:
    name: str
    bbox: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class DownloadedPage:
    start_index: int
    expected_count: int
    path: str
    sha256: str
    compressed_bytes: int


LINZ_BUILDINGS = WfsSource(
    name="linz_buildings",
    base_url="https://data.linz.govt.nz",
    layer="101292",
    key_name="LINZ_API_KEY",
    id_field="building_outline_id",
    geometry_field="shape",
    properties=(
        "building_outline_id",
        "building_id",
        "name",
        "use",
        "capture_method",
        "capture_source_group",
        "capture_source_id",
        "capture_source_name",
        "capture_source_from",
        "capture_source_to",
        "building_outline_lifecycle",
        "begin_lifespan",
        "end_lifespan",
        "last_modified",
    ),
)

STATS_POPULATION = WfsSource(
    name="stats_population",
    base_url="https://datafinder.stats.govt.nz",
    layer="120766",
    key_name="STATSNZ_API_KEY",
    id_field="SA12023_V1_00",
    geometry_field="Shape",
    properties=("SA12023_V1_00", "LANDWATER", "LANDWATER_NAME", "VAR_1_3"),
)

STATS_BOUNDARIES = WfsSource(
    name="stats_boundaries",
    base_url="https://datafinder.stats.govt.nz",
    layer="111225",
    key_name="STATSNZ_API_KEY",
    id_field="MB2023_V1_00",
    geometry_field="Shape",
    properties=(
        "MB2023_V1_00",
        "SA12023_V1_00",
        "SA22023_V1_00",
        "SA22023_V1_00_NAME",
        "REGC2023_V1_00",
        "REGC2023_V1_00_NAME",
        "TA2023_V1_00",
        "TA2023_V1_00_NAME",
        "LANDWATER",
        "LANDWATER_NAME",
    ),
)


class WfsPageDownloader:
    def __init__(
        self,
        secrets: SecretStore,
        raw_root: Path,
        guard: ResourceGuard,
        *,
        page_size: int = 250,
        timeout_seconds: int = 120,
        max_attempts: int = 5,
        session: requests.Session | None = None,
    ) -> None:
        if not 1 <= page_size <= 1000:
            raise ValueError("page_size must be between 1 and 1000")
        self._secrets = secrets
        self._raw_root = raw_root
        self._guard = guard
        self._page_size = page_size
        self._timeout = timeout_seconds
        self._max_attempts = max_attempts
        self._owns_session = session is None
        self._session = session or requests.Session()

    def count(self, source: WfsSource, partition: WfsPartition) -> int:
        response = self._get(
            source,
            {
                "service": "WFS",
                "version": "2.0.0",
                "request": "GetFeature",
                "typeNames": source.type_name,
                "resultType": "hits",
                **self._bbox_params(partition),
            },
            stream=False,
        )
        try:
            root = ET.fromstring(response.content)
            return int(root.attrib["numberMatched"])
        except (ET.ParseError, KeyError, ValueError) as exc:
            raise WfsError(f"Invalid hits response for {source.name}") from exc
        finally:
            response.close()

    def download(self, source: WfsSource, partition: WfsPartition) -> list[DownloadedPage]:
        partition_root = self._raw_root / source.name / partition.name
        partition_root.mkdir(parents=True, exist_ok=True)
        manifest_path = partition_root / "manifest.json"
        previous = self._read_manifest(manifest_path, source, partition)
        total = self.count(source, partition)
        pages: list[DownloadedPage] = []
        LOGGER.info(
            "WFS partition started source=%s partition=%s features=%d page_size=%d",
            source.name,
            partition.name,
            total,
            self._page_size,
        )

        for page_number, start in enumerate(range(0, total, self._page_size), start=1):
            expected = min(self._page_size, total - start)
            destination = partition_root / f"page-{start:09d}.geojson.gz"
            known = previous.get(start)
            if known and self._valid_existing(destination, known):
                pages.append(known)
                continue
            page = self._download_page(source, partition, start, expected, destination)
            pages.append(page)
            self._write_manifest(manifest_path, source, partition, total, pages)
            if page_number == 1 or page_number % 100 == 0:
                LOGGER.info(
                    "WFS partition progress source=%s partition=%s downloaded=%d total=%d "
                    "rss_mb=%.1f free_disk_gb=%.1f",
                    source.name,
                    partition.name,
                    min(start + expected, total),
                    total,
                    self._guard.peak_rss_mb,
                    self._guard.minimum_free_disk_gb,
                )
            if self._owns_session and page_number % 100 == 0:
                self._session.close()
                self._session = requests.Session()

        final_total = self.count(source, partition)
        if final_total != total:
            raise WfsError(
                f"{source.name} changed during paging ({total} to {final_total}); rerun safely"
            )
        self._write_manifest(manifest_path, source, partition, total, pages)
        LOGGER.info(
            "WFS partition complete source=%s partition=%s features=%d pages=%d",
            source.name,
            partition.name,
            total,
            len(pages),
        )
        return pages

    def _download_page(
        self,
        source: WfsSource,
        partition: WfsPartition,
        start: int,
        expected: int,
        destination: Path,
    ) -> DownloadedPage:
        self._guard.check()
        response = self._get(
            source,
            {
                "service": "WFS",
                "version": "2.0.0",
                "request": "GetFeature",
                "typeNames": source.type_name,
                "count": expected,
                "startIndex": start,
                "sortBy": source.id_field,
                "srsName": "EPSG:4326",
                "outputFormat": "application/json",
                "propertyName": ",".join((*source.properties, source.geometry_field)),
                **self._bbox_params(partition),
            },
            stream=True,
        )
        descriptor, temporary_name = tempfile.mkstemp(dir=destination.parent, suffix=".part")
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            with (
                temporary.open("wb") as raw_output,
                gzip.GzipFile(filename="", fileobj=raw_output, mode="wb", mtime=0) as output,
            ):
                response.raw.decode_content = True
                self._copy_response(response.raw, output)
            self._validate_geojson_prefix(temporary, source.name)
            os.replace(temporary, destination)
        finally:
            response.close()
            temporary.unlink(missing_ok=True)
        self._guard.check()
        return DownloadedPage(
            start_index=start,
            expected_count=expected,
            path=destination.relative_to(self._raw_root).as_posix(),
            sha256=self._sha256(destination),
            compressed_bytes=destination.stat().st_size,
        )

    def _copy_response(self, source: BinaryIO, destination: BinaryIO) -> None:
        while chunk := source.read(64 * 1024):
            destination.write(chunk)
            self._guard.check()

    def _get(
        self, source: WfsSource, params: dict[str, object], *, stream: bool
    ) -> requests.Response:
        key = self._secrets.get_secret(source.key_name)
        endpoint = f"{source.base_url}/services;key={key}/wfs/layer-{source.layer}/"
        for attempt in range(1, self._max_attempts + 1):
            self._guard.check()
            response: requests.Response | None = None
            try:
                response = self._session.get(
                    endpoint,
                    params=params,
                    headers={"User-Agent": USER_AGENT},
                    timeout=(15, self._timeout),
                    stream=stream,
                )
                if response.status_code < 400:
                    return response
                retryable = response.status_code in {408, 429, 500, 502, 503, 504}
            except requests.RequestException:
                retryable = True
            if response is not None:
                response.close()
            if not retryable or attempt == self._max_attempts:
                raise WfsError(f"WFS request failed for {source.name} after {attempt} attempt(s)")
            time.sleep(min(16.0, 2 ** (attempt - 1)) + random.random() / 4)
        raise AssertionError("unreachable")

    @staticmethod
    def _bbox_params(partition: WfsPartition) -> dict[str, str]:
        if partition.bbox is None:
            return {}
        return {"bbox": ",".join(str(value) for value in (*partition.bbox, "EPSG:4326"))}

    def _write_manifest(
        self,
        path: Path,
        source: WfsSource,
        partition: WfsPartition,
        total: int,
        pages: list[DownloadedPage],
    ) -> None:
        payload = {
            "schema_version": 2,
            "source": source.name,
            "layer": source.layer,
            "partition": partition.name,
            "bbox": partition.bbox,
            "sort_by": source.id_field,
            "properties": [*source.properties, source.geometry_field],
            "page_size": self._page_size,
            "source_count": total,
            "pages": [asdict(page) for page in pages],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, suffix=".part")
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
                json.dump(payload, output, indent=2, sort_keys=True)
                output.write("\n")
            os.replace(temporary_name, path)
        finally:
            Path(temporary_name).unlink(missing_ok=True)

    def _read_manifest(
        self, path: Path, source: WfsSource, partition: WfsPartition
    ) -> dict[int, DownloadedPage]:
        if not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        expected_bbox = list(partition.bbox) if partition.bbox is not None else None
        expected_properties = [*source.properties, source.geometry_field]
        if (
            payload.get("schema_version") != 2
            or payload.get("layer") != source.layer
            or payload.get("partition") != partition.name
            or payload.get("bbox") != expected_bbox
            or payload.get("sort_by") != source.id_field
            or payload.get("page_size") != self._page_size
            or payload.get("properties") != expected_properties
        ):
            return {}
        return {item["start_index"]: DownloadedPage(**item) for item in payload.get("pages", [])}

    def _valid_existing(self, path: Path, page: DownloadedPage) -> bool:
        return (
            path.is_file()
            and path.stat().st_size == page.compressed_bytes
            and self._sha256(path) == page.sha256
        )

    @staticmethod
    def _validate_geojson_prefix(path: Path, source_name: str) -> None:
        with gzip.open(path, "rb") as source:
            prefix = source.read(512).lstrip()
        if not prefix.startswith(b"{") or b'"FeatureCollection"' not in prefix:
            raise WfsError(f"Non-GeoJSON response for {source_name}")

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()
