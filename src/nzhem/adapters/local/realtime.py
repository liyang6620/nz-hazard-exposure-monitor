from __future__ import annotations

import json
import shutil
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
import requests
import shapely
from shapely.geometry import mapping

from nzhem.adapters.local.resource_guard import ResourceGuard
from nzhem.adapters.local.shaking_layers import CachedShakingEvent, ShakingLayersClient
from nzhem.core.exposure import PAPER_MAX_MAGNITUDE, PAPER_MIN_MAGNITUDE

MMI_BANDS = ("<4", "4", "5", "6", "7", "8+")


def _sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


class LocalRealtimeEventAssessor:
    """Assess current GeoNet events against event-time buildings and 2023 population."""

    def __init__(
        self,
        *,
        reference_root: Path,
        raw_root: Path,
        output_root: Path,
        guard: ResourceGuard,
        memory_limit_mb: int = 512,
        shaking_client: ShakingLayersClient | None = None,
    ) -> None:
        self._reference_root = reference_root.resolve()
        self._output_root = output_root.resolve()
        self._guard = guard
        self._memory_limit_mb = memory_limit_mb
        self._shaking = shaking_client or ShakingLayersClient(raw_root, guard)
        required = (
            self._reference_root / "dim_h3_cell.parquet",
            self._reference_root / "int_population_h3.parquet",
            self._reference_root / "int_buildings_h3",
        )
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise FileNotFoundError(f"Realtime assessment reference data is incomplete: {missing}")

    def assess(self, event: Mapping[str, Any], assessed_at: datetime) -> Mapping[str, Any]:
        self._guard.check()
        event_id = str(event["event_id"])
        magnitude = float(event["magnitude"])
        origin = datetime.fromisoformat(str(event["event_time"]).replace("Z", "+00:00"))
        if origin.tzinfo is None:
            origin = origin.replace(tzinfo=UTC)
        if origin.astimezone(UTC) < assessed_at.astimezone(UTC) - timedelta(days=30):
            return {
                "assessment_status": "expired",
                "assessment_reason": "Event is outside the 30-day monitoring window.",
                "max_mmi": None,
                "buildings_mmi_ge_6": None,
                "population_mmi_ge_6": None,
                "mmi_source": None,
                "source_version": None,
                "shaking_type": "not_assessed",
                "event_time_status": "supported",
                "as_if_today": False,
                "map_summary": "Event is outside the 30-day monitoring window.",
            }
        official = self._try_official(event_id)
        if official is None and not PAPER_MIN_MAGNITUDE <= magnitude <= PAPER_MAX_MAGNITUDE:
            reason = (
                f"Magnitude M{magnitude:.1f} is outside the published M"
                f"{PAPER_MIN_MAGNITUDE:.1f}–{PAPER_MAX_MAGNITUDE:.1f} model range, and no "
                "official shaking layer is available."
            )
            return {
                "assessment_status": "outside_model_range",
                "assessment_reason": reason,
                "max_mmi": None,
                "buildings_mmi_ge_6": None,
                "population_mmi_ge_6": None,
                "mmi_source": None,
                "source_version": None,
                "shaking_type": "unavailable",
                "event_time_status": "supported",
                "as_if_today": False,
                "map_summary": reason,
            }

        connection = duckdb.connect()
        connection.execute(f"set memory_limit='{self._memory_limit_mb}MB'")
        connection.execute("set threads=1")
        connection.execute("set preserve_insertion_order=false")
        connection.execute("load h3")
        try:
            if official is not None:
                connection.execute("load spatial")
            self._prepare_reference(connection, str(event["event_time"]))
            if official is None:
                source = self._build_preliminary(connection, event)
            else:
                source = self._build_official(connection, official)
            summary, features = self._summarise(connection, event, assessed_at, source)
            output = self._write_result(event_id, summary, features)
            return {
                **summary,
                "result_path": output.relative_to(self._output_root).as_posix(),
            }
        finally:
            connection.close()

    def _try_official(self, event_id: str) -> CachedShakingEvent | None:
        try:
            return self._shaking.cache_event(event_id)
        except (requests.RequestException, RuntimeError, json.JSONDecodeError):
            return None

    def _prepare_reference(self, connection: duckdb.DuckDBPyConnection, event_time: str) -> None:
        buildings = _sql_path(self._reference_root / "int_buildings_h3" / "region=*" / "*.parquet")
        population = _sql_path(self._reference_root / "int_population_h3.parquet")
        connection.execute(
            f"""
            create temporary table event_buildings as
            with ranked as (
                select *, row_number() over (
                    partition by building_id
                    order by begin_lifespan desc, building_outline_id desc
                ) as version_rank
                from read_parquet('{buildings}', hive_partitioning=true)
                where begin_lifespan <= cast(? as timestamptz)
                  and (end_lifespan is null or end_lifespan > cast(? as timestamptz))
            )
            select
                h3_res8,
                count(*)::bigint as building_count,
                sum(footprint_area_m2)::double as footprint_area_m2,
                arg_max(coalesce(region_code, 'outside'), footprint_area_m2) as region_code,
                arg_max(coalesce(region_name, 'Outside mapped regions'), footprint_area_m2)
                    as region_name
            from ranked
            where version_rank = 1
            group by h3_res8
            """,
            [event_time, event_time],
        )
        connection.execute(
            f"""
            create temporary table population_counts as
            select h3_res8, sum(allocated_population)::double as population_2023
            from read_parquet('{population}')
            where h3_res8 is not null
            group by h3_res8
            """
        )

    def _build_preliminary(
        self, connection: duckdb.DuckDBPyConnection, event: Mapping[str, Any]
    ) -> dict[str, str]:
        cells = _sql_path(self._reference_root / "dim_h3_cell.parquet")
        depth = min(max(float(event["depth_km"]), 0.0), 300.0)
        connection.execute(
            f"""
            create temporary table shaking as
            with distances as (
                select
                    h3_res8,
                    h3_res6,
                    greatest(
                        2 * 6371.0088 * asin(sqrt(
                            pow(sin(radians(centre_latitude - ?::double) / 2), 2)
                            + cos(radians(?::double)) * cos(radians(centre_latitude))
                            * pow(sin(radians(centre_longitude - ?::double) / 2), 2)
                        )),
                        1.0
                    ) as distance_km
                from read_parquet('{cells}')
            )
            select
                h3_res8,
                h3_res6,
                case when ?::double >= 70 then
                    3.76 + 1.48 * ?::double - 3.50 * log10(distance_km)
                        + 0.0031 * ?::double
                else
                    4.40 + 1.26 * ?::double
                        - 3.67 * log10(pow(pow(distance_km, 3) + pow(11.78, 3), 1.0 / 3.0))
                        + 0.012 * ?::double + 0.409
                end::double as mmi
            from distances
            """,
            [
                float(event["latitude"]),
                float(event["latitude"]),
                float(event["longitude"]),
                depth,
                float(event["magnitude"]),
                depth,
                float(event["magnitude"]),
                depth,
            ],
        )
        model = "deep_region" if depth >= 70 else "main_seismic_region_model_2"
        return {
            "mmi_source": "preliminary",
            "source_version": f"Dowrick–Rhoades 2005 · {model}",
            "shaking_type": "preliminary",
        }

    def _build_official(
        self, connection: duckdb.DuckDBPyConnection, event: CachedShakingEvent
    ) -> dict[str, str]:
        cells = _sql_path(self._reference_root / "dim_h3_cell.parquet")
        polygons = _sql_path(event.polygon_shapefile)
        connection.execute(
            f"""
            create temporary table shaking as
            select
                cells.h3_res8,
                cells.h3_res6,
                max(polygons.PARAMVALUE)::double as mmi
            from read_parquet('{cells}') cells
            inner join st_read('{polygons}') polygons
                on st_covers(
                    polygons.geom,
                    st_point(cells.centre_longitude, cells.centre_latitude)
                )
            group by cells.h3_res8, cells.h3_res6
            """
        )
        return {
            "mmi_source": "official",
            "source_version": str(event.manifest["versionpath"]),
            "shaking_type": str(event.manifest["type"]),
        }

    def _summarise(
        self,
        connection: duckdb.DuckDBPyConnection,
        event: Mapping[str, Any],
        assessed_at: datetime,
        source: Mapping[str, str],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        connection.execute(
            """
            create temporary table exposure as
            select
                shaking.h3_res8,
                shaking.h3_res6,
                shaking.mmi,
                coalesce(event_buildings.building_count, 0)::bigint as building_count,
                coalesce(event_buildings.footprint_area_m2, 0)::double as footprint_area_m2,
                coalesce(population_counts.population_2023, 0)::double as population_2023,
                coalesce(event_buildings.region_code, 'outside')::varchar as region_code,
                coalesce(event_buildings.region_name, 'Outside mapped regions')::varchar
                    as region_name
            from shaking
            left join event_buildings using (h3_res8)
            left join population_counts using (h3_res8)
            where coalesce(event_buildings.building_count, 0) > 0
               or coalesce(population_counts.population_2023, 0) > 0
            """
        )
        max_mmi, buildings, population = connection.execute(
            """
            select
                max(mmi),
                coalesce(sum(building_count) filter (where mmi >= 6), 0),
                coalesce(sum(population_2023) filter (where mmi >= 6), 0)
            from exposure
            """
        ).fetchone()
        max_mmi = float(max_mmi or 0)
        band_rows = connection.execute(
            """
            select
                case
                    when mmi < 4 then '<4'
                    when mmi >= 8 then '8+'
                    else cast(floor(mmi) as integer)::varchar
                end as mmi_band,
                sum(building_count)::bigint as buildings,
                sum(population_2023)::double as population
            from exposure
            group by mmi_band
            """
        ).fetchall()
        band_values = {
            str(row[0]): {
                "mmi_band": str(row[0]),
                "buildings": int(row[1]),
                "population": float(row[2]),
            }
            for row in band_rows
        }
        bands = [
            band_values.get(band, {"mmi_band": band, "buildings": 0, "population": 0.0})
            for band in MMI_BANDS
        ]
        region_rows = connection.execute(
            """
            select
                region_code,
                region_name,
                sum(building_count)::bigint as buildings,
                sum(population_2023)::double as population
            from exposure
            where mmi >= 6
            group by region_code, region_name
            having buildings > 0 or population > 0
            order by buildings desc, region_code
            """
        ).fetchall()
        regions = [
            {
                "region_code": str(row[0]),
                "region_name": str(row[1]),
                "buildings": int(row[2]),
                "population": float(row[3]),
            }
            for row in region_rows
        ]
        top_region = regions[0]["region_name"] if regions else None
        no_damage = max_mmi < 6
        if no_damage:
            map_summary = (
                f"No damaging shaking (MMI < 6). The highest populated intensity was "
                f"MMI {max_mmi:.1f}."
            )
        else:
            map_summary = (
                f"{top_region or 'The mapped area'} was most affected. The highest populated "
                f"intensity was MMI {max_mmi:.1f}. MMI 6 or greater exposed "
                f"{int(buildings):,} buildings and {round(float(population)):,} people."
            )
        features = self._features(connection, source)
        origin = datetime.fromisoformat(str(event["event_time"]).replace("Z", "+00:00"))
        if origin.tzinfo is None:
            origin = origin.replace(tzinfo=UTC)
        summary = {
            "event_id": str(event["event_id"]),
            "name": str(event.get("event_name") or "New Zealand earthquake"),
            "origin_time": origin.astimezone(UTC).isoformat(),
            "magnitude": float(event["magnitude"]),
            "depth_km": float(event["depth_km"]),
            "latitude": float(event["latitude"]),
            "longitude": float(event["longitude"]),
            "assessment_status": "ready",
            "assessment_reason": "Exposure assessment completed.",
            "max_mmi": max_mmi,
            "buildings_mmi_ge_6": int(buildings),
            "population_mmi_ge_6": float(population),
            "no_damaging_shaking": no_damage,
            **dict(source),
            "source_kind": "official" if source["mmi_source"] == "official" else "preliminary",
            "event_time_status": "supported",
            "as_if_today": False,
            "map_summary": map_summary,
            "most_affected_region": top_region,
            "mmi_bands": bands,
            "regions": regions,
            "briefing": {"status": "pending", "title": None, "public_path": None},
            "assessed_at": assessed_at.astimezone(UTC).isoformat(),
        }
        return summary, {"type": "FeatureCollection", "features": features}

    @staticmethod
    def _features(
        connection: duckdb.DuckDBPyConnection, source: Mapping[str, str]
    ) -> list[dict[str, Any]]:
        rows = connection.execute(
            """
            select
                h3_res6,
                max(mmi)::double as mmi,
                sum(building_count)::bigint as buildings,
                sum(population_2023)::double as population,
                h3_cell_to_boundary_wkt(h3_res6) as geometry_wkt
            from exposure
            where mmi >= 5 and building_count > 0
            group by h3_res6
            order by h3_res6
            """
        ).fetchall()
        return [
            {
                "type": "Feature",
                "properties": {
                    "h3_res6": str(row[0]),
                    "mmi": float(row[1]),
                    "mmi_band": "8+" if float(row[1]) >= 8 else str(int(float(row[1]))),
                    "mmi_source": source["mmi_source"],
                    "source_version": source["source_version"],
                    "buildings": int(row[2]),
                    "population": float(row[3]),
                },
                "geometry": mapping(shapely.from_wkt(str(row[4]))),
            }
            for row in rows
        ]

    def _write_result(
        self, event_id: str, summary: Mapping[str, Any], features: Mapping[str, Any]
    ) -> Path:
        final = self._output_root / event_id
        temporary = self._output_root / f".{event_id}.tmp"
        shutil.rmtree(temporary, ignore_errors=True)
        temporary.mkdir(parents=True, exist_ok=True)
        (temporary / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        (temporary / "exposure.geojson").write_text(
            json.dumps(features, ensure_ascii=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        self._guard.check()
        shutil.rmtree(final, ignore_errors=True)
        temporary.replace(final)
        return final
