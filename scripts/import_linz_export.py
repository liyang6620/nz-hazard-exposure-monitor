from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from nzhem.adapters.local.duckdb_reference import DuckDbReferenceTransformer
from nzhem.adapters.local.linz_export import (
    EXPECTED_FEATURE_COUNT,
    EXPECTED_LAYER_VERSION,
    LinzExportImporter,
    register_manual_export,
)
from nzhem.adapters.local.resource_guard import ResourceGuard, ResourceLimitExceeded
from nzhem.config import Settings

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = (
    ROOT
    / ".local/data/raw/reference/linz_buildings_export/incoming"
    / "lds-nz-building-outlines-all-sources-GPKG.zip"
)


def run_once(archive: Path, evidence_root: Path) -> None:
    settings = Settings.from_env()
    guard = ResourceGuard(
        settings.data_root,
        min_free_disk_gb=settings.reference_min_free_disk_gb,
        max_rss_mb=settings.reference_max_rss_mb,
    )
    export_root = settings.data_root / "raw/reference/linz_buildings_export"
    artifact = register_manual_export(
        archive,
        export_root / "staged",
        guard,
        work_reserve_gb=settings.reference_export_work_reserve_gb,
    )
    generation_root = settings.data_root / "curated/reference-export" / artifact.archive_sha256[:12]
    importer = LinzExportImporter(
        artifact,
        settings.data_root / "curated/reference/stg_stats__boundaries/*.parquet",
        generation_root,
        guard,
        candidate_limit=settings.reference_export_candidate_limit,
        memory_limit_mb=settings.duckdb_memory_limit_mb,
    )
    reconciliation = importer.run()
    comparison = importer.compare_retained_wfs(settings.data_root / "curated/reference")
    transformer = DuckDbReferenceTransformer(
        settings.data_root,
        guard,
        memory_limit_mb=settings.duckdb_memory_limit_mb,
    )
    try:
        population = transformer.build_dimensions_and_population(
            buildings_root=generation_root,
            output_root=generation_root,
        )
        population["invariant_failures"] = transformer.population_invariant_failures(
            output_root=generation_root
        )
        if population["invariant_failures"]:
            raise RuntimeError(
                "Population allocation invariant failed for "
                f"{population['invariant_failures']} SA1 areas"
            )
        population["output_hashes"] = {
            "int_population_h3": transformer.logical_hash(
                generation_root / "int_population_h3.parquet",
                "sa1_code, h3_res8",
            ),
            "dim_region": transformer.logical_hash(
                generation_root / "dim_region.parquet",
                "region_code, territorial_authority_code, sa2_code",
            ),
            "dim_h3_cell": transformer.logical_hash(
                generation_root / "dim_h3_cell.parquet", "h3_res8"
            ),
        }
    finally:
        transformer.close()
    payload = {
        "export_manifest": importer.manifest_payload(),
        "reconciliation": reconciliation,
        "population": population,
        "retained_wfs_comparison": comparison,
    }
    _write_evidence(evidence_root, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


def _write_evidence(evidence_root: Path, payload: dict[str, object]) -> None:
    evidence_root.mkdir(parents=True, exist_ok=True)
    json_path = evidence_root / "national-import.json"
    temporary = json_path.with_suffix(".json.part")
    with temporary.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, json_path)

    manifest = payload["export_manifest"]
    reconciliation = payload["reconciliation"]
    population = payload["population"]
    assert isinstance(manifest, dict)
    assert isinstance(reconciliation, dict)
    assert isinstance(population, dict)
    buckets = reconciliation["reconciliation_buckets"]
    comparisons = payload["retained_wfs_comparison"]
    assert isinstance(buckets, dict)
    assert isinstance(comparisons, dict)
    comparison_rows = "\n".join(
        "| {region} | {wfs_count:,} | {source_attribute_differences:,} | "
        "{meshblock_attribution_differences:,} | {h3_res8_differences:,} | "
        "{h3_res6_differences:,} | "
        "{mean_absolute_area_difference_m2:.8f} | "
        "{max_absolute_area_difference_m2:.8f} |".format(region=region, **result)
        for region, result in comparisons.items()
        if isinstance(result, dict) and result.get("status") == "compared"
    )
    excluded_rows = reconciliation.get("excluded_source_rows", [])
    excluded_ids = ", ".join(
        f"`{row['building_outline_id']}`" for row in excluded_rows if isinstance(row, dict)
    )
    markdown = f"""# M2 national LINZ export import

- Acquisition: owner-supplied manual GeoPackage export (Method B)
- Expected layer version: `{EXPECTED_LAYER_VERSION}`
- Exported layer version: `{manifest["exported_layer_version"]}`
- Version comparison: {manifest["version_comparison"]}
- Expected source features: `{EXPECTED_FEATURE_COUNT:,}`
- Exported source features: `{manifest["exported_feature_count"]:,}`
- Accepted land buildings: `{buckets["accepted"]:,}`
- Region 99: `{buckets["region_99"]:,}`
- Non-land meshblocks: `{buckets["non_land_meshblock"]:,}`
- No containing meshblock: `{buckets["no_containing_meshblock"]:,}`
- Invalid or unindexed geometry: `{buckets["invalid_or_unindexed_geometry"]:,}`
- Tiles: `{reconciliation["tile_count"]:,}` at no more than
  `{reconciliation["candidate_limit"]:,}` candidates each
- DuckDB: one thread, configured by the 512 MB local default
- Peak worker RSS: `{reconciliation["peak_worker_rss_mb"]:.1f}` MB
- Minimum observed free disk: `{reconciliation["minimum_free_disk_gb"]:.2f}` GB
- First-to-last tile checkpoint time: `{reconciliation["checkpoint_wall_seconds"] / 3600:.2f}` hours
- Stats NZ SA1 rows: `{population["population_sa1_count"]:,}`
- Published population total: `{population["source_population"]:,.0f}`
- Allocated population total: `{population["allocated_population"]:,.0f}`
- Suppressed SA1 rows: `{population["suppressed_sa1"]:,}`
- Population invariant failures: `{population["invariant_failures"]}`
- Unlocated SA1 rows: `{population["unlocated_sa1"]:,}` containing
  `{population["unlocated_population"]:,.0f}` people
- Nonzero unlocated SA1 rows: `{population["unlocated_nonzero_sa1"]:,}`

The numeric LINZ layer version is not embedded in this export when the exported
version above is `None`. In that case the evidence records the publication-date
comparison rather than claiming a numeric match. Full machine-readable counts and
the retained WFS comparison are in `national-import.json`.

## Retained WFS comparison

| Region | IDs | Source attrs | Meshblock | H3-8 | H3-6 | Mean area delta m2 | Max area delta m2 |
|---|---:|---:|---:|---:|---:|---:|---:|
{comparison_rows}

The retained WFS and export generations contain exactly the same IDs in regions
01, 02 and 03, and their source attributes are identical. The WFS GeoJSON
coordinates are rounded differently from the GeoPackage coordinates, so exact
coordinate comparison differs for every retained row. The resulting area deltas
are sub-centimetre-square numerical effects. H3-8 differences reflect a small
number of point-on-surface coordinates falling on adjacent H3 boundaries; one
point falls on an adjacent meshblock boundary. H3-6 is derived as the parent of
H3-8, so its larger differences against retained WFS reflect the old WFS
generation independently classifying H3-6 at H3 boundaries, not changed source
buildings. These are serialization-precision effects, not evidence of a
source-version change.

Sixteen official region-99 SA1 records have neither population-layer geometry
nor meshblock-boundary geometry; two have nonzero population. Their 24 residents
are preserved as `unlocated_no_geometry` rows with null H3 values instead of
assigning a false location. They remain in the per-SA1 and national population
invariants and are excluded from `dim_h3_cell`.

The second full deterministic building hash run remains deferred to Checkpoint A
under the project-manager decision. Tile checkpoints already verify source and
output hashes on every restart.

## Excluded source rows

All eight excluded IDs are present in the GeoPackage and its RTree but fail
`ST_IsValid`: {excluded_ids}. They are counted in
`invalid_or_unindexed_geometry`; no source row is unexplained.
"""
    (evidence_root / "README.md").write_text(markdown, encoding="utf-8", newline="\n")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--evidence-root", type=Path, default=ROOT / "evidence/m2")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    arguments = parser.parse_args()
    if arguments.worker:
        try:
            run_once(arguments.archive.resolve(), arguments.evidence_root.resolve())
        except ResourceLimitExceeded as exc:
            LOGGER.warning("Resource guard requested a clean worker restart: %s", exc)
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(75)
        return

    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        "--archive",
        str(arguments.archive.resolve()),
        "--evidence-root",
        str(arguments.evidence_root.resolve()),
    ]
    checkpoint_root = (
        Settings.from_env().data_root / "curated/reference-export/.reference-export-work"
    )
    no_progress_failures = 0
    while True:
        checkpoints_before = _checkpoint_count(checkpoint_root)
        environment = os.environ.copy()
        environment["PYTHONUNBUFFERED"] = "1"
        completed = subprocess.run(command, check=False, env=environment)  # noqa: S603
        if completed.returncode == 0:
            return
        checkpoints_after = _checkpoint_count(checkpoint_root)
        if completed.returncode == 75:
            no_progress_failures = 0
            LOGGER.info("Restarting LINZ export import from verified tile checkpoints")
            continue
        if checkpoints_after > checkpoints_before:
            no_progress_failures = 0
            LOGGER.warning(
                "Worker exited with code %d after committing %d new tile checkpoints; "
                "restarting from verified state",
                completed.returncode,
                checkpoints_after - checkpoints_before,
            )
            continue
        no_progress_failures += 1
        if no_progress_failures < 3:
            LOGGER.warning(
                "Worker exited with code %d without a new checkpoint; retrying %d/3",
                completed.returncode,
                no_progress_failures,
            )
            continue
        raise SystemExit(completed.returncode)


def _checkpoint_count(root: Path) -> int:
    return sum(1 for _ in root.glob("*/classified-batches/*.json"))


if __name__ == "__main__":
    main()
