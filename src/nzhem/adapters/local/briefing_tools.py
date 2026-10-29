from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import duckdb


def _sql_path(path: Path | str) -> str:
    return str(path).replace("\\", "/").replace("'", "''")


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


class DuckDbBriefingTools:
    """Read-only M6 tools over the M3 gold and approved reference Parquet."""

    def __init__(
        self,
        event_root: Path,
        reference_root: Path,
        *,
        site_root: Path | None = None,
        memory_limit_mb: int = 512,
    ) -> None:
        self._connection = duckdb.connect()
        self._connection.execute(f"set memory_limit = '{memory_limit_mb}MB'")
        self._connection.execute("set threads = 1")
        self._event_root = event_root.resolve()
        self._reference_root = reference_root.resolve()
        self._site_root = site_root.resolve() if site_root is not None else None
        self._create_views()
        self._events: dict[str, dict[str, Any]] = {}
        for row in self._rows(
            """
            select event_id, event_name, cast(origin_time as varchar) as origin_time,
                   magnitude, depth_km, latitude, longitude, mmi_source,
                   shaking_version, shaking_type, event_time_status, valid_buildings,
                   as_if_today_buildings, populated_max_mmi, validation_station_count,
                   validation_mae
            from events
            """,
            [],
        ):
            origin = datetime.fromisoformat(str(row.pop("origin_time")))
            row["origin_time_utc"] = origin.astimezone(UTC).isoformat()
            row["origin_time_nzt"] = origin.astimezone(ZoneInfo("Pacific/Auckland")).isoformat()
            self._events[str(row["event_id"])] = row
        self._regions = {
            int(row["h3_res6"]): (
                str(row["region_code"] or "unknown"),
                str(row["region_name"] or "Unknown"),
            )
            for row in self._rows("select h3_res6, region_code, region_name from region_cell", [])
        }
        self._exposure = self._rows(
            """
            select event_id, h3_res6, mmi, event_time_building_count,
                   as_if_today_building_count, as_if_today_footprint_area_m2,
                   current_building_count, population_2023
            from exposure
            """,
            [],
        )
        self._building_totals = {
            str(row["region_code"]): int(row["total_buildings"])
            for row in self._rows(
                """
                select region_code, count(*)::bigint as total_buildings
                from buildings where lifecycle = 'Current' group by region_code
                """,
                [],
            )
        }
        self._population_totals = {
            str(row["region_code"]): float(row["population_2023"])
            for row in self._rows(
                """
                select region_cell.region_code,
                       sum(population.allocated_population) as population_2023
                from population join region_cell using (h3_res6)
                group by region_cell.region_code
                """,
                [],
            )
        }
        self._strong_events: dict[str, set[str]] = {}
        for row in self._exposure:
            if float(row["mmi"]) < 6:
                continue
            region_code, _ = self._regions.get(int(row["h3_res6"]), ("unknown", "Unknown"))
            self._strong_events.setdefault(region_code, set()).add(str(row["event_id"]))

    def close(self) -> None:
        self._connection.close()

    def _create_views(self) -> None:
        events = _sql_path(self._event_root / "dim_event.parquet")
        exposure = _sql_path(self._event_root / "mart_event_exposure_h3r6.parquet")
        buildings = _sql_path(self._reference_root / "int_buildings_h3/region=*/*.parquet")
        population = _sql_path(self._reference_root / "int_population_h3.parquet")
        self._connection.execute(
            f"create view events as select * from read_parquet('{events}')"
        ).fetchall()
        self._connection.execute(
            f"create view exposure as select * from read_parquet('{exposure}')"
        ).fetchall()
        self._connection.execute(
            "create view buildings as select * from "
            f"read_parquet('{buildings}', hive_partitioning=true)"
        ).fetchall()
        self._connection.execute(
            f"create view population as select * from read_parquet('{population}')"
        ).fetchall()
        self._connection.execute(
            """
            create temp view region_cell as
            select
                h3_res6,
                arg_max(region_code, building_count) as region_code,
                arg_max(region_name, building_count) as region_name
            from (
                select h3_res6, region_code, region_name, count(*) as building_count
                from buildings
                where lifecycle = 'Current'
                group by h3_res6, region_code, region_name
            ) grouped
            group by h3_res6
            """
        ).fetchall()

    def _rows(self, sql: str, parameters: list[Any]) -> list[dict[str, Any]]:
        cursor = self._connection.execute(sql, parameters)
        columns = [item[0] for item in cursor.description]
        return [
            {column: _json_value(value) for column, value in zip(columns, row, strict=True)}
            for row in cursor.fetchall()
        ]

    def get_event(self, event_id: str) -> dict[str, Any]:
        if event_id not in self._events:
            raise KeyError(f"Unknown event: {event_id}")
        return dict(self._events[event_id])

    def get_published_summary(self, event_id: str) -> dict[str, Any]:
        if self._site_root is None:
            raise RuntimeError("Published site data root is required for briefing generation")
        manifest_path = self._site_root / "data" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        base_path = str(manifest["base_path"]).lstrip("/")
        summary_path = self._site_root / base_path / "events" / event_id / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if str(summary.get("event_id")) != event_id:
            raise ValueError("Published event summary does not match the requested event")
        return summary

    def get_exposure_summary(self, event_id: str, mmi_threshold: float) -> list[dict[str, Any]]:
        grouped: dict[tuple[str, str], dict[str, Any]] = {}
        for row in self._matching_exposure(event_id, mmi_threshold):
            region = self._regions.get(int(row["h3_res6"]), ("unknown", "Unknown"))
            result = grouped.setdefault(
                region,
                {
                    "region_code": region[0],
                    "region_name": region[1],
                    "buildings": 0,
                    "footprint_area_m2": 0.0,
                    "population_2023": 0.0,
                },
            )
            result["buildings"] += int(row["as_if_today_building_count"] or 0)
            result["footprint_area_m2"] += float(row["as_if_today_footprint_area_m2"] or 0)
            result["population_2023"] += float(row["population_2023"] or 0)
        return sorted(grouped.values(), key=lambda row: (-row["buildings"], row["region_code"]))

    def compare_then_now(self, event_id: str, mmi_threshold: float) -> list[dict[str, Any]]:
        grouped: dict[tuple[str, str], dict[str, Any]] = {}
        for row in self._matching_exposure(event_id, mmi_threshold):
            region = self._regions.get(int(row["h3_res6"]), ("unknown", "Unknown"))
            result = grouped.setdefault(
                region,
                {
                    "region_code": region[0],
                    "region_name": region[1],
                    "then_buildings": None,
                    "now_buildings": 0,
                    "change_buildings": None,
                },
            )
            then = row["event_time_building_count"]
            if then is not None:
                result["then_buildings"] = int(result["then_buildings"] or 0) + int(then)
            result["now_buildings"] += int(row["current_building_count"] or 0)
        for result in grouped.values():
            if result["then_buildings"] is not None:
                result["change_buildings"] = result["now_buildings"] - result["then_buildings"]
        return sorted(grouped.values(), key=lambda row: (-row["now_buildings"], row["region_code"]))

    def get_region_context(self, region_code: str) -> dict[str, Any]:
        return {
            "region_code": region_code,
            "total_buildings": self._building_totals.get(region_code, 0),
            "population_2023": self._population_totals.get(region_code, 0.0),
            "strong_event_count": len(self._strong_events.get(region_code, set())),
        }

    def _matching_exposure(self, event_id: str, mmi_threshold: float) -> list[dict[str, Any]]:
        return [
            row
            for row in self._exposure
            if row["event_id"] == event_id and float(row["mmi"]) >= mmi_threshold
        ]
