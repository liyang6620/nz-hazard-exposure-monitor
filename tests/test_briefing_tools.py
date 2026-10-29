from __future__ import annotations

import json
from pathlib import Path

import duckdb

from nzhem.adapters.local.briefing_tools import DuckDbBriefingTools


def _write_fixture(root: Path) -> tuple[Path, Path, Path]:
    event_root = root / "events"
    reference_root = root / "reference"
    building_root = reference_root / "int_buildings_h3" / "region=01"
    event_root.mkdir(parents=True)
    building_root.mkdir(parents=True)
    connection = duckdb.connect()
    connection.execute(
        """
        create table events as select * from (values
          ('event-1', 'Test event', timestamptz '2026-10-26 00:00:00+00', 6.0, 10.0,
           -41.0, 174.0, 'official', 'v1', 'polygon', 'supported', 2::bigint,
           2::bigint, 7.0, 10::bigint, 0.5)
        ) t(event_id,event_name,origin_time,magnitude,depth_km,latitude,longitude,
            mmi_source,shaking_version,shaking_type,event_time_status,valid_buildings,
            as_if_today_buildings,populated_max_mmi,validation_station_count,validation_mae)
        """
    )
    connection.execute(
        """
        create table exposure as select * from (values
          ('event-1', 1::ubigint, 6.5, 'official', 'v1', 2::bigint, 50.0,
           2::bigint, 50.0, 2::bigint, 50.0, 2::bigint, 50.0, 20.0)
        ) t(event_id,h3_res6,mmi,mmi_source,source_version,event_building_count,
            event_footprint_area_m2,event_time_building_count,event_time_footprint_area_m2,
            as_if_today_building_count,as_if_today_footprint_area_m2,current_building_count,
            current_footprint_area_m2,population_2023)
        """
    )
    connection.execute(
        """
        create table buildings as select * from (values
          (1::bigint, 100::bigint, 'Current', 10::ubigint, 1::ubigint, '01', 'Region A'),
          (2::bigint, 101::bigint, 'Current', 11::ubigint, 1::ubigint, '01', 'Region A')
        ) t(building_outline_id,building_id,lifecycle,h3_res8,h3_res6,region_code,region_name)
        """
    )
    connection.execute(
        """
        create table population as select * from (values
          ('sa1', 10::ubigint, 1::ubigint, 20.0, 12.0, 'building_area'),
          ('sa2', 11::ubigint, 1::ubigint, 30.0, 8.0, 'building_area')
        ) t(sa1_code,h3_res8,h3_res6,footprint_area_m2,allocated_population,allocation_method)
        """
    )
    outputs = {
        "events": event_root / "dim_event.parquet",
        "exposure": event_root / "mart_event_exposure_h3r6.parquet",
        "buildings": building_root / "part.parquet",
        "population": reference_root / "int_population_h3.parquet",
    }
    for table, path in outputs.items():
        connection.execute(f"copy {table} to '{path.as_posix()}' (format parquet)")
    connection.close()
    site_root = root / "site"
    generation_root = site_root / "data/generations/test/events/event-1"
    generation_root.mkdir(parents=True)
    (site_root / "data/manifest.json").write_text(
        json.dumps({"base_path": "/data/generations/test"}), encoding="utf-8"
    )
    (generation_root / "summary.json").write_text(
        json.dumps({"event_id": "event-1", "name": "Test event"}), encoding="utf-8"
    )
    return event_root, reference_root, site_root


def test_duckdb_tools_return_event_exposure_comparison_and_context(tmp_path: Path) -> None:
    event_root, reference_root, site_root = _write_fixture(tmp_path)
    tools = DuckDbBriefingTools(event_root, reference_root, site_root=site_root)
    try:
        assert tools.get_event("event-1")["magnitude"] == 6.0
        assert tools.get_event("event-1")["origin_time_utc"].endswith("+00:00")
        assert tools.get_event("event-1")["origin_time_nzt"].endswith("+13:00")
        assert tools.get_published_summary("event-1")["name"] == "Test event"
        exposure = tools.get_exposure_summary("event-1", 6.0)
        assert exposure[0]["buildings"] == 2
        assert exposure[0]["population_2023"] == 20.0
        comparison = tools.compare_then_now("event-1", 6.0)
        assert comparison[0]["then_buildings"] == 2
        context = tools.get_region_context("01")
        assert context == {
            "region_code": "01",
            "total_buildings": 2,
            "population_2023": 20.0,
            "strong_event_count": 1,
        }
    finally:
        tools.close()
