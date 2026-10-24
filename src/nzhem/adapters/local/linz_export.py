from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import struct
import time
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import duckdb

from nzhem.adapters.local.resource_guard import ResourceGuard, ResourceLimitExceeded

EXPECTED_LAYER_ID = 101292
EXPECTED_LAYER_VERSION = 438679
EXPECTED_FEATURE_COUNT = 6_634_223
EXPECTED_PUBLICATION_DATE = "2026-05-18"
IMPORT_SCHEMA_VERSION = 2
GIB = 1024**3


class LinzExportError(RuntimeError):
    """Raised when a manual LINZ export fails validation or reconciliation."""


@dataclass(frozen=True)
class ZipEntry:
    name: str
    compressed_bytes: int
    uncompressed_bytes: int
    crc32: int


@dataclass(frozen=True)
class ZipPreflight:
    archive_bytes: int
    uncompressed_bytes: int
    entries: tuple[ZipEntry, ...]


@dataclass(frozen=True)
class GpkgInfo:
    path: Path
    table_name: str
    geometry_column: str
    srs_id: int
    feature_count: int
    distinct_id_count: int
    null_geometry_count: int
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    metadata_has_layer_id: bool
    metadata_publication_date: str | None

    @property
    def rtree_table(self) -> str:
        return f"rtree_{self.table_name}_{self.geometry_column}"


@dataclass(frozen=True)
class ExportArtifact:
    archive_path: Path
    archive_sha256: str
    archive_bytes: int
    uncompressed_bytes: int
    gpkg: GpkgInfo
    export_reference: str | None
    exported_layer_version: int | None
    version_comparison: str


@dataclass(frozen=True)
class ImportTile:
    key: str
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    include_max_x: bool
    include_max_y: bool
    candidate_count: int

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return self.min_x, self.min_y, self.max_x, self.max_y


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_zip(path: Path, *, maximum_uncompressed_bytes: int = 10 * GIB) -> ZipPreflight:
    if not path.is_file():
        raise LinzExportError(f"Manual export not found: {path}")
    entries: list[ZipEntry] = []
    total = 0
    with zipfile.ZipFile(path) as archive:
        if not archive.infolist():
            raise LinzExportError("Manual export ZIP is empty")
        for info in archive.infolist():
            normalized = info.filename.replace("\\", "/")
            parts = PurePosixPath(normalized).parts
            if (
                not normalized
                or normalized.startswith("/")
                or ".." in parts
                or (parts and ":" in parts[0])
            ):
                raise LinzExportError(f"Unsafe ZIP entry path: {info.filename!r}")
            if info.is_dir():
                continue
            total += info.file_size
            if total > maximum_uncompressed_bytes:
                raise LinzExportError(
                    f"ZIP declares more than {maximum_uncompressed_bytes} uncompressed bytes"
                )
            entries.append(ZipEntry(info.filename, info.compress_size, info.file_size, info.CRC))
    gpkg_count = sum(entry.name.lower().endswith(".gpkg") for entry in entries)
    if gpkg_count != 1:
        raise LinzExportError(f"Expected exactly one GeoPackage, found {gpkg_count}")
    return ZipPreflight(path.stat().st_size, total, tuple(entries))


def stage_manual_export(
    archive_path: Path,
    staging_root: Path,
    guard: ResourceGuard,
    *,
    work_reserve_gb: float = 5.0,
) -> tuple[Path, str, ZipPreflight]:
    preflight = inspect_zip(archive_path)
    guard.check(required_free_bytes=preflight.uncompressed_bytes + int(work_reserve_gb * GIB))
    destination = staging_root / archive_path.stem
    marker = destination / "staging-manifest.json"
    archive_stat = archive_path.stat()
    expected = {entry.name: entry.uncompressed_bytes for entry in preflight.entries}
    if marker.is_file():
        payload = json.loads(marker.read_text(encoding="utf-8"))
        if (
            payload.get("archive_bytes") == archive_stat.st_size
            and payload.get("archive_mtime_ns") == archive_stat.st_mtime_ns
            and isinstance(payload.get("archive_sha256"), str)
            and all(
                (destination / name).is_file() and (destination / name).stat().st_size == size
                for name, size in expected.items()
            )
        ):
            gpkg_name = next(name for name in expected if name.lower().endswith(".gpkg"))
            return destination / gpkg_name, payload["archive_sha256"], preflight

    archive_sha = sha256_file(archive_path)
    if all(
        (destination / name).is_file() and (destination / name).stat().st_size == size
        for name, size in expected.items()
    ):
        _write_staging_manifest(marker, archive_sha, archive_stat, preflight)
        gpkg_name = next(name for name in expected if name.lower().endswith(".gpkg"))
        return destination / gpkg_name, archive_sha, preflight

    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        for entry in preflight.entries:
            guard.check(required_free_bytes=int(work_reserve_gb * GIB))
            target = (destination / entry.name).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise LinzExportError(f"Unsafe ZIP entry path: {entry.name!r}")
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + ".part")
            temporary.unlink(missing_ok=True)
            try:
                with archive.open(entry.name) as source, temporary.open("wb") as output:
                    while chunk := source.read(1024 * 1024):
                        output.write(chunk)
                        guard.check(required_free_bytes=int(work_reserve_gb * GIB))
                    output.flush()
                    os.fsync(output.fileno())
                if temporary.stat().st_size != entry.uncompressed_bytes:
                    raise LinzExportError(f"Extracted size mismatch for {entry.name}")
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)

    _write_staging_manifest(marker, archive_sha, archive_stat, preflight)
    gpkg_name = next(
        entry.name for entry in preflight.entries if entry.name.lower().endswith(".gpkg")
    )
    return destination / gpkg_name, archive_sha, preflight


def inspect_gpkg(path: Path) -> GpkgInfo:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        contents = connection.execute(
            """
            select c.table_name, g.column_name, g.srs_id,
                   c.min_x, c.min_y, c.max_x, c.max_y
            from gpkg_contents c
            join gpkg_geometry_columns g using (table_name)
            where c.data_type = 'features'
            """
        ).fetchall()
        if len(contents) != 1:
            raise LinzExportError(f"Expected one feature layer, found {len(contents)}")
        table, geometry, srs_id, min_x, min_y, max_x, max_y = contents[0]
        _validate_identifier(table)
        _validate_identifier(geometry)
        rtree = f"rtree_{table}_{geometry}"
        _validate_identifier(rtree)
        if not connection.execute(
            "select 1 from sqlite_master where type='table' and name=?", (rtree,)
        ).fetchone():
            raise LinzExportError("GeoPackage is missing its geometry RTree")
        columns = {row[1]: row for row in connection.execute(f'pragma table_info("{table}")')}
        required = {
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
            geometry,
        }
        missing = sorted(required - columns.keys())
        if missing:
            raise LinzExportError(f"GeoPackage is missing columns: {', '.join(missing)}")
        count, nonnull_ids, distinct_ids, null_geometries = connection.execute(
            f"""
            select count(*), count(building_outline_id),
                   count(distinct building_outline_id),
                   sum(case when "{geometry}" is null then 1 else 0 end)
            from "{table}"
            """
        ).fetchone()
        if nonnull_ids != count:
            raise LinzExportError("GeoPackage contains null building_outline_id values")
        if distinct_ids != count:
            raise LinzExportError(
                f"GeoPackage contains {count - distinct_ids} duplicate building_outline_id values"
            )
        metadata = "\n".join(
            row[0]
            for row in connection.execute("select metadata from gpkg_metadata").fetchall()
            if row[0]
        )
        date_match = re.search(r"<gco:Date>(\d{4}-\d{2}-\d{2})</gco:Date>", metadata)
        return GpkgInfo(
            path=path,
            table_name=table,
            geometry_column=geometry,
            srs_id=int(srs_id),
            feature_count=int(count),
            distinct_id_count=int(distinct_ids),
            null_geometry_count=int(null_geometries or 0),
            min_x=float(min_x),
            min_y=float(min_y),
            max_x=float(max_x),
            max_y=float(max_y),
            metadata_has_layer_id=str(EXPECTED_LAYER_ID) in metadata,
            metadata_publication_date=date_match.group(1) if date_match else None,
        )
    finally:
        connection.close()


def register_manual_export(
    archive_path: Path,
    staging_root: Path,
    guard: ResourceGuard,
    *,
    work_reserve_gb: float = 5.0,
) -> ExportArtifact:
    gpkg_path, archive_sha, preflight = stage_manual_export(
        archive_path,
        staging_root,
        guard,
        work_reserve_gb=work_reserve_gb,
    )
    info = inspect_gpkg(gpkg_path)
    text_path = next(gpkg_path.parent.glob("*.txt"), None)
    text = text_path.read_text(encoding="utf-8") if text_path else ""
    reference_match = re.search(r"reference\s+#(\d+)", text, re.IGNORECASE)
    exported_version = None
    version_match = re.search(r"(?:layer\s+version|version)\s*[:#]\s*(\d+)", text, re.I)
    if version_match:
        exported_version = int(version_match.group(1))
    if exported_version is not None:
        comparison = "match" if exported_version == EXPECTED_LAYER_VERSION else "mismatch"
    elif info.metadata_publication_date == EXPECTED_PUBLICATION_DATE:
        comparison = (
            "numeric version not embedded; export publication date matches the "
            f"{EXPECTED_LAYER_VERSION} metadata date"
        )
    else:
        comparison = "numeric version not embedded and publication date does not match"
    if info.srs_id != 4326:
        raise LinzExportError(f"Expected EPSG:4326, found EPSG:{info.srs_id}")
    return ExportArtifact(
        archive_path=archive_path,
        archive_sha256=archive_sha,
        archive_bytes=preflight.archive_bytes,
        uncompressed_bytes=preflight.uncompressed_bytes,
        gpkg=info,
        export_reference=reference_match.group(1) if reference_match else None,
        exported_layer_version=exported_version,
        version_comparison=comparison,
    )


class GpkgTilePlanner:
    def __init__(self, info: GpkgInfo, *, candidate_limit: int = 5000) -> None:
        if candidate_limit <= 0 or candidate_limit > 5000:
            raise ValueError("candidate_limit must be between 1 and 5000")
        self._info = info
        self._limit = candidate_limit

    def plan(self) -> list[ImportTile]:
        connection = sqlite3.connect(
            f"file:{self._info.path.resolve().as_posix()}?mode=ro", uri=True
        )
        try:
            connection.execute("pragma query_only=on")
            root = ImportTile(
                "root",
                self._info.min_x,
                self._info.min_y,
                self._info.max_x,
                self._info.max_y,
                True,
                True,
                self._info.feature_count,
            )
            pending: list[tuple[ImportTile, int]] = [(root, 0)]
            leaves: list[ImportTile] = []
            while pending:
                tile, depth = pending.pop()
                count = self._candidate_count(connection, tile)
                tile = ImportTile(
                    tile.key,
                    tile.min_x,
                    tile.min_y,
                    tile.max_x,
                    tile.max_y,
                    tile.include_max_x,
                    tile.include_max_y,
                    count,
                )
                if count == 0:
                    continue
                if count <= self._limit:
                    leaves.append(tile)
                    continue
                if depth >= 24:
                    raise LinzExportError(f"Unable to split dense tile {tile.key} below limit")
                pending.extend(reversed([(child, depth + 1) for child in self._split(tile)]))
            return sorted(leaves, key=lambda tile: tile.key)
        finally:
            connection.close()

    def plan_cached(self, path: Path, *, source_sha256: str) -> list[ImportTile]:
        if path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if (
                payload.get("source_sha256") == source_sha256
                and payload.get("candidate_limit") == self._limit
            ):
                return [ImportTile(**item) for item in payload["tiles"]]
        tiles = self.plan()
        self.write_cached(path, tiles, source_sha256=source_sha256)
        return tiles

    def write_cached(self, path: Path, tiles: list[ImportTile], *, source_sha256: str) -> None:
        _write_json_atomic(
            path,
            {
                "source_sha256": source_sha256,
                "candidate_limit": self._limit,
                "tiles": [asdict(tile) for tile in tiles],
            },
        )

    def refine(self, tile: ImportTile) -> list[ImportTile]:
        connection = sqlite3.connect(
            f"file:{self._info.path.resolve().as_posix()}?mode=ro", uri=True
        )
        try:
            children: list[ImportTile] = []
            for child in self._split(tile):
                count = self._candidate_count(connection, child)
                if count:
                    children.append(
                        ImportTile(
                            child.key,
                            child.min_x,
                            child.min_y,
                            child.max_x,
                            child.max_y,
                            child.include_max_x,
                            child.include_max_y,
                            count,
                        )
                    )
            return children
        finally:
            connection.close()

    def _candidate_count(self, connection: sqlite3.Connection, tile: ImportTile) -> int:
        row = connection.execute(
            f"""
            select count(*) from "{self._info.rtree_table}"
            where maxx >= ? and minx <= ? and maxy >= ? and miny <= ?
            """,
            (tile.min_x, tile.max_x, tile.min_y, tile.max_y),
        ).fetchone()
        return int(row[0])

    @staticmethod
    def _split(tile: ImportTile) -> list[ImportTile]:
        mid_x = (tile.min_x + tile.max_x) / 2
        mid_y = (tile.min_y + tile.max_y) / 2
        specs = (
            (tile.min_x, tile.min_y, mid_x, mid_y, False, False),
            (mid_x, tile.min_y, tile.max_x, mid_y, tile.include_max_x, False),
            (tile.min_x, mid_y, mid_x, tile.max_y, False, tile.include_max_y),
            (mid_x, mid_y, tile.max_x, tile.max_y, tile.include_max_x, tile.include_max_y),
        )
        return [ImportTile(f"{tile.key}-{index}", *spec, 0) for index, spec in enumerate(specs)]


ACCEPTED_COLUMNS = (
    "building_outline_id",
    "building_id",
    "building_name",
    "building_use",
    "capture_method",
    "capture_source_group",
    "capture_source_id",
    "capture_source_name",
    "capture_source_from",
    "capture_source_to",
    "lifecycle",
    "begin_lifespan",
    "end_lifespan",
    "last_modified",
    "footprint_area_m2",
    "longitude",
    "latitude",
    "meshblock_code",
    "sa1_code",
    "sa2_code",
    "sa2_name",
    "region_code",
    "region_name",
    "territorial_authority_code",
    "territorial_authority_name",
    "valid_from_year",
    "valid_to_year",
    "h3_res8",
    "h3_res6",
)


class LinzExportImporter:
    """Resumable, bounded-memory importer for an owner-supplied LINZ GeoPackage."""

    def __init__(
        self,
        artifact: ExportArtifact,
        boundary_glob: Path,
        generation_root: Path,
        guard: ResourceGuard,
        *,
        candidate_limit: int = 5000,
        memory_limit_mb: int = 512,
        max_tiles_per_worker: int = 10,
        connection: duckdb.DuckDBPyConnection | None = None,
    ) -> None:
        self.artifact = artifact
        self.boundary_glob = boundary_glob
        self.generation_root = generation_root
        self.guard = guard
        self.candidate_limit = candidate_limit
        self.work_root = (
            generation_root.parent
            / ".reference-export-work"
            / f"{artifact.archive_sha256[:12]}-v{IMPORT_SCHEMA_VERSION}"
        )
        self.batch_root = self.work_root / "classified-batches"
        self.batch_root.mkdir(parents=True, exist_ok=True)
        self.generation_root.mkdir(parents=True, exist_ok=True)
        self.invalid_geometry_ids: tuple[int, ...] = ()
        self._database_path = self.work_root / "import.duckdb"
        self._memory_limit_mb = memory_limit_mb
        self._max_tiles_per_worker = max_tiles_per_worker
        self._owns_connection = connection is None
        self.connection = connection or duckdb.connect(str(self._database_path))
        self._configure(memory_limit_mb)

    def close(self) -> None:
        if self._owns_connection:
            self.connection.close()

    def run(self) -> dict[str, Any]:
        started = time.monotonic()
        self.invalid_geometry_ids = self._scan_geometry_safety()
        self._prepare_boundary_index()
        planner = GpkgTilePlanner(self.artifact.gpkg, candidate_limit=self.candidate_limit)
        plan_path = self.work_root / "tile-plan.json"
        tiles = planner.plan_cached(
            plan_path,
            source_sha256=self.artifact.archive_sha256,
        )
        self.process_tiles(tiles, planner=planner, plan_path=plan_path)
        reconciliation = self.reconcile(tiles)
        self._write_regional_outputs()
        reconciliation["elapsed_seconds"] = time.monotonic() - started
        reconciliation.update(self._run_metrics())
        _write_json_atomic(self.generation_root / "reconciliation.json", reconciliation)
        _write_json_atomic(self.generation_root / "export-manifest.json", self.manifest_payload())
        return reconciliation

    def manifest_payload(self) -> dict[str, Any]:
        info = self.artifact.gpkg
        return {
            "schema_version": IMPORT_SCHEMA_VERSION,
            "acquisition_method": "owner_supplied_manual_export",
            "original_filename": self.artifact.archive_path.name,
            "archive_bytes": self.artifact.archive_bytes,
            "archive_sha256": self.artifact.archive_sha256,
            "declared_uncompressed_bytes": self.artifact.uncompressed_bytes,
            "export_reference": self.artifact.export_reference,
            "layer_id": EXPECTED_LAYER_ID,
            "expected_layer_version": EXPECTED_LAYER_VERSION,
            "exported_layer_version": self.artifact.exported_layer_version,
            "version_comparison": self.artifact.version_comparison,
            "expected_feature_count": EXPECTED_FEATURE_COUNT,
            "exported_feature_count": info.feature_count,
            "feature_count_difference": info.feature_count - EXPECTED_FEATURE_COUNT,
            "metadata_publication_date": info.metadata_publication_date,
            "metadata_has_layer_id": info.metadata_has_layer_id,
            "crs": f"EPSG:{info.srs_id}",
            "table_name": info.table_name,
            "geometry_column": info.geometry_column,
            "source_path": info.path.name,
            "candidate_limit": self.candidate_limit,
        }

    def process_tiles(
        self,
        tiles: list[ImportTile],
        *,
        planner: GpkgTilePlanner | None = None,
        plan_path: Path | None = None,
    ) -> None:
        processed_this_worker = 0
        index = 0
        while index < len(tiles):
            tile = tiles[index]
            self.guard.check()
            output = self.batch_root / f"{tile.key}.parquet"
            marker = self.batch_root / f"{tile.key}.json"
            if self._checkpoint_valid(tile, output, marker):
                index += 1
                continue
            temporary = output.with_suffix(".parquet.part")
            temporary.unlink(missing_ok=True)
            try:
                self.connection.execute(
                    f"COPY ({self._tile_sql(tile)}) TO '{_sql_path(temporary)}' "
                    "(FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 5000)"
                )
            except duckdb.OutOfMemoryException as exc:
                temporary.unlink(missing_ok=True)
                if planner is None or plan_path is None:
                    raise
                children = planner.refine(tile)
                if len(children) < 2:
                    raise LinzExportError(f"Unable to refine OOM tile {tile.key}") from exc
                tiles[index : index + 1] = children
                planner.write_cached(
                    plan_path,
                    tiles,
                    source_sha256=self.artifact.archive_sha256,
                )
                raise ResourceLimitExceeded(
                    f"Tile {tile.key} exceeded 512 MB and was split into "
                    f"{len(children)} smaller tiles"
                ) from exc
            os.replace(temporary, output)
            output_sha = sha256_file(output)
            row_count = int(
                self.connection.execute(
                    "select count(*) from read_parquet(?)", [str(output)]
                ).fetchone()[0]
            )
            _write_json_atomic(
                marker,
                {
                    "import_schema_version": IMPORT_SCHEMA_VERSION,
                    "archive_sha256": self.artifact.archive_sha256,
                    "tile": asdict(tile),
                    "output_sha256": output_sha,
                    "row_count": row_count,
                },
            )
            self.guard.check()
            self._record_resource_metrics()
            processed_this_worker += 1
            if index % 25 == 0 or index == len(tiles):
                print(f"processed tiles {index + 1}/{len(tiles)}")
            index += 1
            if processed_this_worker >= self._max_tiles_per_worker:
                raise ResourceLimitExceeded(
                    f"Completed {processed_this_worker} tiles; requesting a clean worker restart"
                )

    def _record_resource_metrics(self) -> None:
        path = self.work_root / "resource-metrics.json"
        previous: dict[str, Any] = {}
        if path.is_file():
            previous = json.loads(path.read_text(encoding="utf-8"))
        _write_json_atomic(
            path,
            {
                "peak_worker_rss_mb": max(
                    float(previous.get("peak_worker_rss_mb", 0)),
                    self.guard.peak_rss_mb,
                ),
                "minimum_free_disk_gb": min(
                    float(previous.get("minimum_free_disk_gb", float("inf"))),
                    self.guard.minimum_free_disk_gb,
                ),
            },
        )

    def _run_metrics(self) -> dict[str, Any]:
        path = self.work_root / "resource-metrics.json"
        resources = (
            json.loads(path.read_text(encoding="utf-8"))
            if path.is_file()
            else {
                "peak_worker_rss_mb": self.guard.peak_rss_mb,
                "minimum_free_disk_gb": self.guard.minimum_free_disk_gb,
            }
        )
        timestamps = [marker.stat().st_mtime for marker in self.batch_root.glob("*.json")]
        resources["checkpoint_wall_seconds"] = (
            max(timestamps) - min(timestamps) if timestamps else 0.0
        )
        return resources

    def reconcile(self, tiles: list[ImportTile]) -> dict[str, Any]:
        batch_glob = _sql_path(self.batch_root / "*.parquet")
        counts = dict(
            self.connection.execute(
                f"""
                select reconciliation_bucket, count(*)
                from read_parquet('{batch_glob}')
                group by reconciliation_bucket
                """
            ).fetchall()
        )
        processed = sum(int(value) for value in counts.values())
        invalid_or_unindexed = self.artifact.gpkg.feature_count - processed
        if invalid_or_unindexed < 0:
            raise LinzExportError(
                f"Tile ownership duplicated {-invalid_or_unindexed} source features"
            )
        counts["invalid_or_unindexed_geometry"] = invalid_or_unindexed
        normalized = {
            "accepted": int(counts.get("accepted", 0)),
            "region_99": int(counts.get("region_99", 0)),
            "non_land_meshblock": int(counts.get("non_land_meshblock", 0)),
            "no_containing_meshblock": int(counts.get("no_containing_meshblock", 0)),
            "invalid_or_unindexed_geometry": int(invalid_or_unindexed),
            "duplicate_building_outline_id": 0,
        }
        excluded_source_rows: list[dict[str, Any]] = []
        if invalid_or_unindexed:
            excluded_source_rows = self._excluded_source_rows(batch_glob)
            if len(excluded_source_rows) != invalid_or_unindexed:
                raise LinzExportError(
                    "Excluded source detail does not match the reconciliation count"
                )
        reconciled = sum(normalized.values())
        if reconciled != self.artifact.gpkg.feature_count:
            raise LinzExportError(
                f"National reconciliation failed: source={self.artifact.gpkg.feature_count} "
                f"buckets={reconciled}"
            )
        return {
            "source_feature_count": self.artifact.gpkg.feature_count,
            "expected_feature_count": EXPECTED_FEATURE_COUNT,
            "feature_count_difference": self.artifact.gpkg.feature_count - EXPECTED_FEATURE_COUNT,
            "reconciliation_buckets": normalized,
            "reconciled_feature_count": reconciled,
            "tile_count": len(tiles),
            "candidate_limit": self.candidate_limit,
            "duckdb_threads": 1,
            "excluded_source_rows": excluded_source_rows,
        }

    def compare_retained_wfs(self, retained_root: Path) -> dict[str, Any]:
        comparisons: dict[str, Any] = {}
        for region in ("01", "02", "03"):
            old_glob = retained_root / "int_buildings_h3" / f"region={region}" / "*.parquet"
            new_glob = self.generation_root / "int_buildings_h3" / f"region={region}" / "*.parquet"
            if not list(old_glob.parent.glob("*.parquet")):
                comparisons[region] = {"status": "retained_wfs_not_available"}
                continue
            row = self.connection.execute(
                f"""
                with old as (select * from read_parquet('{_sql_path(old_glob)}')),
                new as (select * from read_parquet('{_sql_path(new_glob)}')),
                joined as (
                    select
                        old.building_outline_id as old_id,
                        new.building_outline_id as new_id,
                        old.footprint_area_m2 as old_area,
                        new.footprint_area_m2 as new_area,
                        hash(old.building_id, old.building_name, old.building_use,
                             old.capture_method, old.capture_source_group,
                             old.capture_source_id, old.capture_source_name,
                             old.capture_source_from, old.capture_source_to, old.lifecycle,
                             old.begin_lifespan, old.end_lifespan, old.last_modified,
                             old.valid_from_year, old.valid_to_year) as old_source_hash,
                        hash(new.building_id, new.building_name, new.building_use,
                             new.capture_method, new.capture_source_group,
                             new.capture_source_id, new.capture_source_name,
                             new.capture_source_from, new.capture_source_to, new.lifecycle,
                             new.begin_lifespan, new.end_lifespan, new.last_modified,
                             new.valid_from_year, new.valid_to_year) as new_source_hash,
                        hash(old.meshblock_code, old.sa1_code, old.sa2_code,
                             old.sa2_name, old.region_code, old.region_name,
                             old.territorial_authority_code,
                             old.territorial_authority_name) as old_attribution_hash,
                        hash(new.meshblock_code, new.sa1_code, new.sa2_code,
                             new.sa2_name, new.region_code, new.region_name,
                             new.territorial_authority_code,
                             new.territorial_authority_name) as new_attribution_hash,
                        old.longitude as old_longitude,
                        new.longitude as new_longitude,
                        old.latitude as old_latitude,
                        new.latitude as new_latitude,
                        old.h3_res8 as old_h3_res8,
                        new.h3_res8 as new_h3_res8,
                        old.h3_res6 as old_h3_res6,
                        new.h3_res6 as new_h3_res6
                    from old full join new using (building_outline_id)
                )
                select
                    (select count(*) from old),
                    (select count(*) from new),
                    count(*) filter (where old_id is null),
                    count(*) filter (where new_id is null),
                    count(*) filter (
                        where old_id is not null and new_id is not null
                          and old_source_hash != new_source_hash
                    ),
                    count(*) filter (
                        where old_id is not null and new_id is not null
                          and old_attribution_hash != new_attribution_hash
                    ),
                    count(*) filter (
                        where old_id is not null and new_id is not null
                          and old_h3_res8 != new_h3_res8
                    ),
                    count(*) filter (
                        where old_id is not null and new_id is not null
                          and old_h3_res6 != new_h3_res6
                    ),
                    count(*) filter (
                        where old_id is not null and new_id is not null
                          and (old_longitude != new_longitude or old_latitude != new_latitude)
                    ),
                    count(*) filter (
                        where old_id is not null and new_id is not null
                          and abs(old_area - new_area) > 0.000001
                    ),
                    avg(abs(old_area - new_area)) filter (
                        where old_id is not null and new_id is not null
                    ),
                    max(abs(old_area - new_area)) filter (
                        where old_id is not null and new_id is not null
                    )
                from joined
                """
            ).fetchone()
            comparisons[region] = {
                "status": "compared",
                "wfs_count": int(row[0]),
                "export_count": int(row[1]),
                "export_only": int(row[2]),
                "wfs_only": int(row[3]),
                "source_attribute_differences": int(row[4]),
                "meshblock_attribution_differences": int(row[5]),
                "h3_res8_differences": int(row[6]),
                "h3_res6_differences": int(row[7]),
                "coordinate_differences": int(row[8]),
                "area_differences_over_1e-6_m2": int(row[9]),
                "mean_absolute_area_difference_m2": float(row[10]),
                "max_absolute_area_difference_m2": float(row[11]),
            }
        return comparisons

    def _excluded_source_rows(self, batch_glob: str) -> list[dict[str, Any]]:
        info = self.artifact.gpkg
        gpkg = _sql_path(info.path)
        rows = self.connection.execute(
            f"""
            with source as (
                select building_outline_id, try(st_geomfromwkb(geom)) as geom
                from st_read(
                    '{gpkg}',
                    layer = '{info.table_name}',
                    keep_wkb = true
                )
            ), excluded as (
                select source.*
                from source
                anti join read_parquet('{batch_glob}') imported
                using (building_outline_id)
            )
            select
                building_outline_id,
                case
                    when geom is null then 'unparseable_geometry'
                    when st_isempty(geom) then 'empty_geometry'
                    when not st_isvalid(geom) then 'invalid_geometry'
                    else 'unindexed_geometry'
                end as reason
            from excluded
            order by building_outline_id
            """
        ).fetchall()
        return [
            {"building_outline_id": int(identifier), "reason": reason}
            for identifier, reason in rows
        ]

    def _prepare_boundary_index(self) -> None:
        destination = self.work_root / "meshblocks-with-bbox.parquet"
        if destination.is_file():
            return
        temporary = destination.with_suffix(".parquet.part")
        source = _sql_path(self.boundary_glob)
        self.connection.execute(
            f"""
            COPY (
                with source as (
                    select *, st_geomfromwkb(geometry_wkb) as boundary_geom
                    from read_parquet('{source}')
                )
                select
                    * exclude (boundary_geom),
                    st_xmin(boundary_geom) as min_x,
                    st_ymin(boundary_geom) as min_y,
                    st_xmax(boundary_geom) as max_x,
                    st_ymax(boundary_geom) as max_y
                from source
            ) TO '{_sql_path(temporary)}'
            (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 5000)
            """
        )
        os.replace(temporary, destination)

    def _tile_sql(self, tile: ImportTile) -> str:
        gpkg = _sql_path(self.artifact.gpkg.path)
        boundaries = _sql_path(self.work_root / "meshblocks-with-bbox.parquet")
        layer = self.artifact.gpkg.table_name.replace("'", "''")
        max_x_operator = "<=" if tile.include_max_x else "<"
        max_y_operator = "<=" if tile.include_max_y else "<"
        min_x, min_y, max_x, max_y = tile.bbox
        invalid_ids = ", ".join(str(identifier) for identifier in self.invalid_geometry_ids)
        safe_geometry = "try(st_geomfromwkb(geom))"
        if invalid_ids:
            safe_geometry = (
                f"case when building_outline_id not in ({invalid_ids}) "
                "then try(st_geomfromwkb(geom)) end"
            )
        return f"""
        with tile_boundaries as (
            select *, st_geomfromwkb(geometry_wkb) as boundary_geom
            from read_parquet('{boundaries}')
            where max_x >= {min_x!r} and min_x <= {max_x!r}
              and max_y >= {min_y!r} and min_y <= {max_y!r}
        ), source_wkb as (
            select *
            from st_read(
                '{gpkg}',
                layer = '{layer}',
                keep_wkb = true,
                spatial_filter_box = st_makebox2d(
                    st_point({min_x!r}, {min_y!r}),
                    st_point({max_x!r}, {max_y!r})
                )
            )
        ), source as (
            select * exclude (geom), {safe_geometry} as geom
            from source_wkb
        ), valid as (
            select *, st_pointonsurface(geom) as point_geom
            from source
            where geom is not null and not st_isempty(geom) and st_isvalid(geom)
        ), owned as (
            select *
            from valid
            where st_x(point_geom) >= {min_x!r}
              and st_x(point_geom) {max_x_operator} {max_x!r}
              and st_y(point_geom) >= {min_y!r}
              and st_y(point_geom) {max_y_operator} {max_y!r}
        ), candidates as (
            select
                owned.*,
                boundary.meshblock_code,
                boundary.sa1_code,
                boundary.sa2_code,
                boundary.sa2_name,
                boundary.region_code,
                boundary.region_name,
                boundary.territorial_authority_code,
                boundary.territorial_authority_name,
                boundary.land_water,
                row_number() over (
                    partition by building_outline_id
                    order by case when boundary.land_water = '12' then 0 else 1 end,
                             boundary.meshblock_code
                ) as boundary_rank
            from owned
            left join tile_boundaries boundary
              on st_intersects(boundary.boundary_geom, owned.point_geom)
        ), attributed as (
            select
                cast(building_outline_id as bigint) as building_outline_id,
                cast(building_id as bigint) as building_id,
                cast(name as varchar) as building_name,
                cast(use as varchar) as building_use,
                cast(capture_method as varchar) as capture_method,
                cast(capture_source_group as varchar) as capture_source_group,
                cast(capture_source_id as integer) as capture_source_id,
                cast(capture_source_name as varchar) as capture_source_name,
                try_cast(capture_source_from as date) as capture_source_from,
                try_cast(capture_source_to as date) as capture_source_to,
                cast(building_outline_lifecycle as varchar) as lifecycle,
                try_cast(begin_lifespan as date) as begin_lifespan,
                try_cast(end_lifespan as date) as end_lifespan,
                try_cast(last_modified as date) as last_modified,
                st_area(st_transform(geom, 'EPSG:4326', 'EPSG:2193', always_xy := true))
                    as footprint_area_m2,
                st_x(point_geom) as longitude,
                st_y(point_geom) as latitude,
                meshblock_code,
                sa1_code,
                sa2_code,
                sa2_name,
                region_code,
                region_name,
                territorial_authority_code,
                territorial_authority_name,
                land_water
            from candidates
            where boundary_rank = 1
        )
        select
            * exclude (land_water),
            year(begin_lifespan) as valid_from_year,
            year(end_lifespan) as valid_to_year,
            h3_latlng_to_cell(latitude, longitude, 8) as h3_res8,
            h3_cell_to_parent(h3_latlng_to_cell(latitude, longitude, 8), 6) as h3_res6,
            case
                when meshblock_code is null then 'no_containing_meshblock'
                when land_water != '12' then 'non_land_meshblock'
                when region_code = '99' then 'region_99'
                else 'accepted'
            end as reconciliation_bucket
        from attributed
        order by building_outline_id
        """

    def _scan_geometry_safety(self) -> tuple[int, ...]:
        marker = self.work_root / "geometry-safety.json"
        if marker.is_file():
            payload = json.loads(marker.read_text(encoding="utf-8"))
            if (
                payload.get("archive_sha256") == self.artifact.archive_sha256
                and payload.get("scanned_count") == self.artifact.gpkg.feature_count
            ):
                return tuple(int(value) for value in payload.get("invalid_ids", []))

        info = self.artifact.gpkg
        connection = sqlite3.connect(f"file:{info.path.resolve().as_posix()}?mode=ro", uri=True)
        invalid: list[int] = []
        scanned = 0
        try:
            cursor = connection.execute(
                f'select building_outline_id, "{info.geometry_column}" '
                f'from "{info.table_name}" order by fid'
            )
            while rows := cursor.fetchmany(2000):
                for identifier, gpkg_blob in rows:
                    if not _safe_gpkg_multipolygon(gpkg_blob):
                        invalid.append(int(identifier))
                scanned += len(rows)
                if scanned % 250_000 == 0:
                    self.guard.check()
                    print(
                        f"validated geometry headers {scanned}/{info.feature_count} "
                        f"invalid={len(invalid)}"
                    )
        finally:
            connection.close()
        if scanned != info.feature_count:
            raise LinzExportError(
                f"Geometry safety scan read {scanned} of {info.feature_count} rows"
            )
        _write_json_atomic(
            marker,
            {
                "archive_sha256": self.artifact.archive_sha256,
                "scanned_count": scanned,
                "invalid_ids": invalid,
            },
        )
        return tuple(invalid)

    def _checkpoint_valid(self, tile: ImportTile, output: Path, marker: Path) -> bool:
        if not output.is_file() or not marker.is_file():
            return False
        try:
            payload = json.loads(marker.read_text(encoding="utf-8"))
            return (
                payload.get("archive_sha256") == self.artifact.archive_sha256
                and payload.get("import_schema_version") == IMPORT_SCHEMA_VERSION
                and payload.get("tile") == asdict(tile)
                and payload.get("output_sha256") == sha256_file(output)
            )
        except (OSError, ValueError, TypeError):
            return False

    def _write_regional_outputs(self) -> None:
        final_root = self.generation_root / "int_buildings_h3"
        completion = final_root / "_SUCCESS.json"
        if completion.is_file():
            payload = json.loads(completion.read_text(encoding="utf-8"))
            if (
                payload.get("archive_sha256") == self.artifact.archive_sha256
                and payload.get("import_schema_version") == IMPORT_SCHEMA_VERSION
            ):
                return
        temporary_root = self.generation_root / "int_buildings_h3.part"
        if temporary_root.exists():
            shutil.rmtree(temporary_root)
        temporary_root.mkdir(parents=True)
        batch_glob = _sql_path(self.batch_root / "*.parquet")
        regions = [
            row[0]
            for row in self.connection.execute(
                f"""
                select distinct region_code
                from read_parquet('{batch_glob}')
                where reconciliation_bucket = 'accepted'
                order by region_code
                """
            ).fetchall()
        ]
        selected = ", ".join(ACCEPTED_COLUMNS)
        for region in regions:
            escaped = region.replace("'", "''")
            destination = temporary_root / f"region={region}" / "part-00000.parquet"
            destination.parent.mkdir(parents=True)
            self.connection.execute(
                f"""
                COPY (
                    select {selected}
                    from read_parquet('{batch_glob}')
                    where reconciliation_bucket = 'accepted'
                      and region_code = '{escaped}'
                    order by building_outline_id
                ) TO '{_sql_path(destination)}'
                (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 5000)
                """
            )
            self.guard.check()
        _write_json_atomic(
            temporary_root / "_SUCCESS.json",
            {
                "archive_sha256": self.artifact.archive_sha256,
                "import_schema_version": IMPORT_SCHEMA_VERSION,
                "regions": regions,
            },
        )
        if final_root.exists():
            shutil.rmtree(final_root)
        os.replace(temporary_root, final_root)

    def _configure(self, memory_limit_mb: int) -> None:
        self.connection.execute(f"set memory_limit='{memory_limit_mb}MB'")
        self.connection.execute("set threads=1")
        self.connection.execute("set preserve_insertion_order=false")
        spill = self.work_root / "spill"
        self.connection.execute(f"set temp_directory='{_sql_path(spill)}'")
        for extension, repository in (("spatial", None), ("h3", "community")):
            try:
                self.connection.execute(f"load {extension}")
            except duckdb.Error:
                install = f"install {extension}"
                if repository:
                    install += f" from {repository}"
                self.connection.execute(install)
                self.connection.execute(f"load {extension}")


def _validate_identifier(value: str) -> None:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise LinzExportError(f"Unsafe GeoPackage identifier: {value!r}")


def _write_staging_manifest(
    marker: Path,
    archive_sha256: str,
    archive_stat: os.stat_result,
    preflight: ZipPreflight,
) -> None:
    _write_json_atomic(
        marker,
        {
            "archive_sha256": archive_sha256,
            "archive_bytes": preflight.archive_bytes,
            "archive_mtime_ns": archive_stat.st_mtime_ns,
            "uncompressed_bytes": preflight.uncompressed_bytes,
            "entries": [asdict(entry) for entry in preflight.entries],
        },
    )


def _safe_gpkg_multipolygon(value: bytes | None) -> bool:
    if value is None or len(value) < 13 or value[:2] != b"GP":
        return False
    flags = value[3]
    envelope_indicator = (flags >> 1) & 0b111
    envelope_bytes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}.get(envelope_indicator)
    if envelope_bytes is None or flags & 0b00010000:
        return False
    offset = 8 + envelope_bytes
    if offset >= len(value):
        return False
    return _safe_multipolygon_wkb(memoryview(value)[offset:])


def _safe_multipolygon_wkb(value: memoryview) -> bool:
    try:
        offset, geometry_type, dimensions = _wkb_header(value, 0)
        if geometry_type != 6:
            return False
        polygon_count, offset = _wkb_uint32(value, offset, value[0])
        if polygon_count > (len(value) - offset) // 9:
            return False
        for _ in range(polygon_count):
            polygon_start = offset
            offset, polygon_type, polygon_dimensions = _wkb_header(value, offset)
            if polygon_type != 3 or polygon_dimensions != dimensions:
                return False
            ring_count, offset = _wkb_uint32(value, offset, value[polygon_start])
            if ring_count > (len(value) - offset) // 4:
                return False
            for _ in range(ring_count):
                point_count, offset = _wkb_uint32(value, offset, value[polygon_start])
                coordinate_bytes = point_count * dimensions * 8
                if coordinate_bytes > len(value) - offset:
                    return False
                offset += coordinate_bytes
        return offset == len(value)
    except (IndexError, struct.error, ValueError):
        return False


def _wkb_header(value: memoryview, offset: int) -> tuple[int, int, int]:
    if offset + 5 > len(value):
        raise ValueError("short WKB header")
    byte_order = value[offset]
    if byte_order not in (0, 1):
        raise ValueError("invalid WKB byte order")
    endian = "<" if byte_order == 1 else ">"
    encoded_type = struct.unpack_from(f"{endian}I", value, offset + 1)[0]
    offset += 5
    dimensions = 2
    if encoded_type & 0x80000000:
        dimensions += 1
    if encoded_type & 0x40000000:
        dimensions += 1
    if encoded_type & 0x20000000:
        offset += 4
    base_type = encoded_type & 0x0FFFFFFF
    if 1000 <= base_type < 4000:
        dimension_code, base_type = divmod(base_type, 1000)
        dimensions = 2 + (2 if dimension_code == 3 else 1)
    return offset, base_type, dimensions


def _wkb_uint32(value: memoryview, offset: int, byte_order: int) -> tuple[int, int]:
    if offset + 4 > len(value):
        raise ValueError("short WKB count")
    endian = "<" if byte_order == 1 else ">"
    return struct.unpack_from(f"{endian}I", value, offset)[0], offset + 4


def _sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    with temporary.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)
