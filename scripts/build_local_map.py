from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb
import shapely
from shapely.geometry import mapping

ROOT = Path(__file__).resolve().parents[1]


def mmi_band(value: float) -> str:
    if value >= 8:
        return "8+"
    if value < 4:
        return "<4"
    return str(int(value))


def build_map_data(event_root: Path, reference_root: Path, output_root: Path) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
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
            longitude,
            latitude,
            populated_max_mmi as max_mmi,
            shaking_version
        from read_parquet(?)
        order by origin_time
        """,
        [(event_root / "dim_event.parquet").as_posix()],
    ).fetchall()
    event_columns = [description[0] for description in connection.description]
    event_payload = []
    event_feature_counts: dict[str, int] = {}
    total_features = 0
    for row in events:
        event = dict(zip(event_columns, row, strict=True))
        event_id = str(event["event_id"])
        exposure = connection.execute(
            """
            select
                h3_res6,
                mmi,
                mmi_source,
                source_version,
                event_building_count,
                event_time_building_count,
                as_if_today_building_count,
                current_building_count,
                population_2023,
                h3_cell_to_boundary_wkt(h3_res6) as geometry_wkt
            from read_parquet(?)
            where event_id = ? and mmi >= 5 and current_building_count > 0
            order by h3_res6
            """,
            [(event_root / "mart_event_exposure_h3r6.parquet").as_posix(), event_id],
        ).fetchall()
        columns = [description[0] for description in connection.description]
        features = []
        for exposure_row in exposure:
            record = dict(zip(columns, exposure_row, strict=True))
            geometry = shapely.from_wkt(record.pop("geometry_wkt"))
            record["h3_res6"] = str(record["h3_res6"])
            record["mmi_band"] = mmi_band(float(record["mmi"]))
            features.append(
                {"type": "Feature", "properties": record, "geometry": mapping(geometry)}
            )
        filename = f"exposure-{event_id}.geojson"
        (output_root / filename).write_text(
            json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")),
            encoding="utf-8",
        )
        event["origin_time"] = str(event["origin_time"])
        event["data_file"] = f"data/{filename}"
        event_payload.append(event)
        event_feature_counts[event_id] = len(features)
        total_features += len(features)

    h3_rows = connection.execute(
        """
        select distinct h3_cell_to_boundary_wkt(h3_res6)
        from read_parquet(?)
        where h3_res6 is not null
        """,
        [(reference_root / "dim_h3_cell.parquet").as_posix()],
    ).fetchall()
    outline = shapely.unary_union([shapely.from_wkt(row[0]) for row in h3_rows]).simplify(
        0.03, preserve_topology=True
    )
    (output_root / "nz-outline.geojson").write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"name": "NZHEM H3 coverage outline"},
                        "geometry": mapping(outline),
                    }
                ],
            },
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    (output_root / "events.json").write_text(
        json.dumps(event_payload, indent=2, default=str) + "\n", encoding="utf-8"
    )
    connection.close()
    static_bytes = sum(path.stat().st_size for path in output_root.iterdir() if path.is_file())
    return {
        "events": len(event_payload),
        "exposure_features": total_features,
        "event_feature_counts": event_feature_counts,
        "static_bytes": static_bytes,
        "architecture": "ArcGIS Maps SDK with local static GeoJSON and no token",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build token-free local ArcGIS map data")
    parser.add_argument("--event-root", type=Path, default=ROOT / ".local/data/curated/events/m3")
    parser.add_argument(
        "--reference-root",
        type=Path,
        default=ROOT / ".local/data/curated/reference-export/dee5b263952e",
    )
    parser.add_argument("--output-root", type=Path, default=ROOT / "hosts/local/site/map/data")
    parser.add_argument(
        "--evidence",
        type=Path,
        default=ROOT / "evidence/mg/local-map.json",
    )
    arguments = parser.parse_args()
    result = build_map_data(
        arguments.event_root.resolve(),
        arguments.reference_root.resolve(),
        arguments.output_root.resolve(),
    )
    arguments.evidence.parent.mkdir(parents=True, exist_ok=True)
    arguments.evidence.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
