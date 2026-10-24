from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import duckdb
import geopandas as gpd
import pandas as pd
import pyogrio
import shapely

ROOT = Path(__file__).resolve().parents[1]


FIELD_METADATA = [
    ("nzhem_events", "event_id", "GeoNet public event identifier", "GeoNet Shaking Layers"),
    ("nzhem_events", "origin_time", "UTC earthquake origin time", "GeoNet Shaking Layers"),
    ("nzhem_events", "magnitude", "GeoNet event magnitude", "GeoNet Shaking Layers"),
    ("nzhem_events", "max_mmi", "Maximum MMI on a populated H3 cell", "NZHEM derived"),
    ("nzhem_events", "valid_bldg", "Buildings valid at the event timestamp", "LINZ/NZHEM"),
    ("event_exposure_r6", "event_id", "GeoNet public event identifier", "GeoNet"),
    ("event_exposure_r6", "h3_r6", "H3 resolution 6 cell", "H3"),
    ("event_exposure_r6", "mmi", "Official Shaking Layers MMI at cell", "GeoNet"),
    ("event_exposure_r6", "event_bldg", "Event-time deduplicated buildings", "LINZ/NZHEM"),
    ("event_exposure_r6", "current_bldg", "Current deduplicated buildings", "LINZ/NZHEM"),
    ("event_exposure_r6", "pop_2023", "Allocated 2023 Census population", "Stats NZ/NZHEM"),
]


def build_file_geodatabase(event_root: Path, destination: Path) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        shutil.rmtree(destination)
    connection = duckdb.connect()
    connection.execute("set memory_limit='512MB'")
    connection.execute("set threads=1")
    connection.execute("load h3")
    events = connection.execute(
        """
        select
            event_id,
            event_name,
            origin_time,
            magnitude,
            depth_km,
            valid_buildings,
            populated_max_mmi as max_mmi,
            validation_mae,
            longitude,
            latitude
        from read_parquet(?)
        order by origin_time
        """,
        [(event_root / "dim_event.parquet").as_posix()],
    ).fetch_df()
    event_geometry = gpd.points_from_xy(events.pop("longitude"), events.pop("latitude"))
    event_gdf = gpd.GeoDataFrame(events, geometry=event_geometry, crs="EPSG:4326").to_crs(2193)
    event_gdf = event_gdf.rename(columns={"valid_buildings": "valid_bldg"})
    pyogrio.write_dataframe(
        event_gdf,
        destination,
        layer="nzhem_events",
        driver="OpenFileGDB",
        layer_options={"TARGET_ARCGIS_VERSION": "ARCGIS_PRO_3_2_OR_LATER"},
    )

    exposure = connection.execute(
        """
        select
            event_id,
            h3_res6 as h3_r6,
            mmi,
            mmi_source,
            source_version,
            event_building_count as event_bldg,
            current_building_count as current_bldg,
            population_2023 as pop_2023,
            h3_cell_to_boundary_wkt(h3_res6) as geometry_wkt
        from read_parquet(?)
        where mmi >= 5 and current_building_count > 0
        order by event_id, h3_res6
        """,
        [(event_root / "mart_event_exposure_h3r6.parquet").as_posix()],
    ).fetch_df()
    exposure["h3_r6"] = exposure["h3_r6"].astype(str)
    geometry = shapely.from_wkt(exposure.pop("geometry_wkt").to_numpy())
    exposure_gdf = gpd.GeoDataFrame(exposure, geometry=geometry, crs="EPSG:4326").to_crs(2193)
    pyogrio.write_dataframe(
        exposure_gdf,
        destination,
        layer="event_exposure_r6",
        driver="OpenFileGDB",
        append=True,
        layer_options={"TARGET_ARCGIS_VERSION": "ARCGIS_PRO_3_2_OR_LATER"},
    )

    metadata = pd.DataFrame(
        FIELD_METADATA, columns=["layer_name", "field_name", "description", "source"]
    )
    pyogrio.write_dataframe(
        metadata,
        destination,
        layer="nzhem_metadata",
        driver="OpenFileGDB",
        append=True,
    )
    connection.close()
    return verify_file_geodatabase(destination)


def verify_file_geodatabase(path: Path) -> dict[str, Any]:
    layers = {name: geometry_type for name, geometry_type in pyogrio.list_layers(path)}
    required = {"nzhem_events", "event_exposure_r6", "nzhem_metadata"}
    if not required.issubset(layers):
        raise RuntimeError(f"FileGDB is missing layers: {sorted(required.difference(layers))}")
    details: dict[str, Any] = {}
    for layer in sorted(required):
        info = pyogrio.read_info(path, layer=layer)
        details[layer] = {
            "feature_count": int(info["features"]),
            "geometry_type": info["geometry_type"],
            "crs": info["crs"],
            "fields": list(info["fields"]),
        }
    for layer in ("nzhem_events", "event_exposure_r6"):
        crs = details[layer]["crs"] or ""
        if "2193" not in crs:
            raise RuntimeError(f"{layer} is not EPSG:2193: {crs}")
    return {
        "driver": "OpenFileGDB",
        "gdal_version": ".".join(str(part) for part in pyogrio.__gdal_version__),
        "path": path.as_posix(),
        "layers": details,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export MG sample File Geodatabase")
    parser.add_argument("--event-root", type=Path, default=ROOT / ".local/data/curated/events/m3")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / ".local/artifacts/mg/nzhem_mg_sample.gdb",
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=ROOT / "evidence/mg/file-geodatabase.json",
    )
    arguments = parser.parse_args()
    result = build_file_geodatabase(arguments.event_root.resolve(), arguments.output.resolve())
    result["path"] = ".local/artifacts/mg/nzhem_mg_sample.gdb"
    arguments.evidence.parent.mkdir(parents=True, exist_ok=True)
    arguments.evidence.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
