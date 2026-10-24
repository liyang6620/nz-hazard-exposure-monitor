from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from pathlib import Path

from nzhem.adapters.local.duckdb_reference import DuckDbReferenceTransformer
from nzhem.adapters.local.resource_guard import ResourceGuard
from nzhem.adapters.local.wfs import (
    LINZ_BUILDINGS,
    STATS_BOUNDARIES,
    STATS_POPULATION,
    WfsPageDownloader,
    WfsPartition,
)
from nzhem.config import Settings
from nzhem.ports import ReferenceRefreshResult, SecretStore

LOGGER = logging.getLogger(__name__)


class LocalReferenceDataRefresher:
    def __init__(self, settings: Settings, secrets: SecretStore) -> None:
        self._settings = settings
        self._secrets = secrets

    def refresh(self) -> ReferenceRefreshResult:
        started = time.monotonic()
        guard = ResourceGuard(
            self._settings.data_root,
            min_free_disk_gb=self._settings.reference_min_free_disk_gb,
            max_rss_mb=self._settings.reference_max_rss_mb,
        )
        raw_root = self._settings.data_root / "raw" / "reference"
        downloader = WfsPageDownloader(
            self._secrets,
            raw_root,
            guard,
            page_size=self._settings.reference_page_size,
        )
        transformer = DuckDbReferenceTransformer(
            self._settings.data_root,
            guard,
            memory_limit_mb=self._settings.duckdb_memory_limit_mb,
        )
        try:
            nationwide = WfsPartition("nationwide")
            population_pages = downloader.download(STATS_POPULATION, nationwide)
            boundary_pages = downloader.download(STATS_BOUNDARIES, nationwide)
            transformer.stage_population(population_pages)
            transformer.stage_boundaries(boundary_pages)

            source_buildings = downloader.count(LINZ_BUILDINGS, nationwide)
            regions = transformer.region_bounds()
            transformer.partition_boundaries_by_region(regions)
            for region in regions:
                LOGGER.info(
                    "Regional building refresh started region=%s name=%s",
                    region.code,
                    region.name,
                )
                partition = WfsPartition(f"region-{region.code}", region.bbox)
                bbox_count = downloader.count(LINZ_BUILDINGS, partition)
                if bbox_count > 1_000_000:
                    pages = []
                    tiles = transformer.region_tiles(region)
                    point_partitions = {tile.name: tile for tile in tiles}
                    LOGGER.info(
                        "Large regional bbox split region=%s bbox_features=%d tiles=%d",
                        region.code,
                        bbox_count,
                        len(tiles),
                    )
                    for tile in tiles:
                        pages.extend(
                            downloader.download(
                                LINZ_BUILDINGS,
                                WfsPartition(tile.name, tile.bbox),
                            )
                        )
                else:
                    pages = downloader.download(LINZ_BUILDINGS, partition)
                    point_partitions = None
                transformer.stage_buildings_for_region(
                    region,
                    pages,
                    point_partitions=point_partitions,
                )
                LOGGER.info("Regional building refresh complete region=%s", region.code)

            stats = transformer.build_dimensions_and_population()
            invariant_failures = transformer.population_invariant_failures()
            if invariant_failures:
                raise RuntimeError(
                    f"Population allocation invariant failed for {invariant_failures} SA1 areas"
                )

            building_glob = transformer.curated_root / "int_buildings_h3" / "region=*" / "*.parquet"
            hashes = {
                "int_buildings_h3": transformer.logical_hash(building_glob, "building_outline_id"),
                "int_population_h3": transformer.logical_hash(
                    transformer.curated_root / "int_population_h3.parquet",
                    "sa1_code, h3_res8",
                ),
                "dim_region": transformer.logical_hash(
                    transformer.curated_root / "dim_region.parquet",
                    "region_code, territorial_authority_code, sa2_code",
                ),
                "dim_h3_cell": transformer.logical_hash(
                    transformer.curated_root / "dim_h3_cell.parquet", "h3_res8"
                ),
            }
            curated_buildings = int(stats["building_count"])
            result = ReferenceRefreshResult(
                source_buildings=source_buildings,
                curated_buildings=curated_buildings,
                source_population=int(stats["source_population"]),
                allocated_population=float(stats["allocated_population"]),
                rejected_buildings=max(0, source_buildings - curated_buildings),
                suppressed_sa1=int(stats["suppressed_sa1"]),
                elapsed_seconds=time.monotonic() - started,
                peak_rss_mb=guard.peak_rss_mb,
                minimum_free_disk_gb=guard.minimum_free_disk_gb,
                output_hashes=hashes,
            )
            self._write_result(transformer.curated_root / "refresh-manifest.json", result)
            return result
        finally:
            transformer.close()

    @staticmethod
    def _write_result(path: Path, result: ReferenceRefreshResult) -> None:
        payload = {
            "schema_version": 1,
            "source_buildings": result.source_buildings,
            "curated_buildings": result.curated_buildings,
            "source_population": result.source_population,
            "allocated_population": result.allocated_population,
            "rejected_buildings": result.rejected_buildings,
            "suppressed_sa1": result.suppressed_sa1,
            "elapsed_seconds": result.elapsed_seconds,
            "peak_rss_mb": result.peak_rss_mb,
            "minimum_free_disk_gb": result.minimum_free_disk_gb,
            "output_hashes": dict(result.output_hashes),
        }
        descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, suffix=".part")
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
                json.dump(payload, output, indent=2, sort_keys=True)
                output.write("\n")
            os.replace(temporary_name, path)
        finally:
            Path(temporary_name).unlink(missing_ok=True)
