from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import duckdb
import geopandas as gpd
import pandas as pd

from nzhem.adapters.local.resource_guard import ResourceGuard
from nzhem.config import Settings

ROOT = Path(__file__).resolve().parents[1]
KAIKOURA_ID = "2016p858000"


def mmi_band(value: float | None) -> str:
    if value is None or pd.isna(value) or value < 4:
        return "<4"
    if value >= 8:
        return "8+"
    return str(int(value))


def cross_validate(
    reference_root: Path,
    event_root: Path,
    polygon_path: Path,
    output_csv: Path,
    guard: ResourceGuard,
    *,
    batch_size: int = 20000,
) -> dict[str, Any]:
    polygons = gpd.read_file(polygon_path)[["PARAMVALUE", "geometry"]]
    polygons = polygons.set_crs(4326) if polygons.crs is None else polygons.to_crs(4326)
    connection = duckdb.connect()
    connection.execute("set memory_limit='512MB'")
    connection.execute("set threads=1")
    event_time_valid_buildings = int(
        connection.execute(
            "select valid_buildings from read_parquet(?) where event_id = ?",
            [(event_root / "dim_event.parquet").as_posix(), KAIKOURA_ID],
        ).fetchone()[0]
    )
    shaking = dict(
        connection.execute(
            """
            select h3_res8, mmi
            from read_parquet(?)
            where event_id = ?
            """,
            [(event_root / "int_event_shaking_h3.parquet").as_posix(), KAIKOURA_ID],
        ).fetchall()
    )
    buildings_glob = (reference_root / "int_buildings_h3" / "region=*" / "*.parquet").as_posix()
    cursor = connection.execute(
        """
        with ranked as (
            select
                building_id,
                region_code,
                longitude,
                latitude,
                h3_res8,
                row_number() over (
                    partition by building_id
                    order by begin_lifespan desc, building_outline_id desc
                ) as version_rank
            from read_parquet(?)
            where end_lifespan is null
        )
        select building_id, region_code, longitude, latitude, h3_res8
        from ranked
        where version_rank = 1
        order by region_code, building_id
        """,
        [buildings_glob],
    )
    exact_counts: Counter[tuple[str, str]] = Counter()
    h3_counts: Counter[tuple[str, str]] = Counter()
    compared = 0
    numeric_comparisons = 0
    band_matches = 0
    mmi_absolute_error = 0.0
    columns = [description[0] for description in cursor.description]
    while rows := cursor.fetchmany(batch_size):
        frame = pd.DataFrame.from_records(rows, columns=columns)
        points = gpd.GeoDataFrame(
            frame,
            geometry=gpd.points_from_xy(frame.longitude, frame.latitude),
            crs="EPSG:4326",
        )
        joined = gpd.sjoin(points, polygons, how="left", predicate="within")
        exact_mmi = joined.groupby(joined.index)["PARAMVALUE"].max().reindex(points.index)
        h3_mmi = points["h3_res8"].map(shaking)
        for region, exact_value, h3_value in zip(
            points["region_code"], exact_mmi, h3_mmi, strict=True
        ):
            exact_band = mmi_band(exact_value)
            h3_band = mmi_band(h3_value)
            exact_counts[(str(region), exact_band)] += 1
            h3_counts[(str(region), h3_band)] += 1
            compared += 1
            band_matches += exact_band == h3_band
            if not pd.isna(exact_value) and not pd.isna(h3_value):
                numeric_comparisons += 1
                mmi_absolute_error += abs(float(exact_value) - float(h3_value))
        guard.check()
    connection.close()
    keys = sorted(set(exact_counts) | set(h3_counts))
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(["region_code", "mmi_band", "exact_count", "h3_count", "difference"])
        for region, band in keys:
            exact = exact_counts[(region, band)]
            approximate = h3_counts[(region, band)]
            writer.writerow([region, band, exact, approximate, approximate - exact])
    return {
        "event_id": KAIKOURA_ID,
        "comparison_population": "current_building_points_for_spatial_validation_only",
        "event_time_valid_buildings": event_time_valid_buildings,
        "compared_buildings": compared,
        "numeric_mmi_comparisons": numeric_comparisons,
        "matching_mmi_band": band_matches,
        "mmi_band_agreement": band_matches / compared,
        "mean_absolute_mmi_difference": mmi_absolute_error / numeric_comparisons,
        "batch_size": batch_size,
        "peak_rss_mb": guard.peak_rss_mb,
        "maximum_rss_mb": guard.max_rss_mb,
        "minimum_free_disk_gb": guard.minimum_free_disk_gb,
        "free_disk_floor_gb": guard.min_free_disk_gb,
        "output_csv": "evidence/mg/kaikoura-cross-validation.csv",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-validate Kaikoura H3 assignment")
    parser.add_argument(
        "--reference-root",
        type=Path,
        default=ROOT / ".local/data/curated/reference-export/dee5b263952e",
    )
    parser.add_argument("--event-root", type=Path, default=ROOT / ".local/data/curated/events/m3")
    parser.add_argument(
        "--polygon-path",
        type=Path,
        default=(
            ROOT
            / ".local/data/raw/events/shaking-layers/2016p858000"
            / "intensity_mmi_contour_polygons/intensity_mmi.shp"
        ),
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=ROOT / "evidence/mg/kaikoura-cross-validation.csv",
    )
    parser.add_argument("--batch-size", type=int, default=20000)
    arguments = parser.parse_args()
    settings = Settings.from_env()
    guard = ResourceGuard(
        settings.data_root,
        min_free_disk_gb=settings.reference_min_free_disk_gb,
        max_rss_mb=settings.reference_max_rss_mb,
    )
    result = cross_validate(
        arguments.reference_root.resolve(),
        arguments.event_root.resolve(),
        arguments.polygon_path.resolve(),
        arguments.output_csv.resolve(),
        guard,
        batch_size=arguments.batch_size,
    )
    summary = arguments.output_csv.parent / "kaikoura-cross-validation.json"
    summary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
