from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

from nzhem.adapters.local.resource_guard import ResourceGuard
from nzhem.adapters.local.shaking_layers import CachedShakingEvent, ShakingLayersClient
from nzhem.config import Settings
from nzhem.core.exposure import estimate_mmi, haversine_km

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REFERENCE_GENERATION = "dee5b263952e"
FIXED_EVENTS = [
    ("darfield_2010", "3366146"),
    ("christchurch_feb_2011", "3468575"),
    ("christchurch_jun_2011", "3528839"),
    ("cook_strait_2013", "2013p543824"),
    ("lake_grassmere_2013", "2013p613797"),
    ("eketahuna_2014", "2014p051675"),
    ("east_cape_2016", "2016p661332"),
    ("kaikoura_2016", "2016p858000"),
    ("kermadec_2021", "2021p169764"),
]
RECENT_EVENT = ("taumarunui_deep_2026", "2026p776286")


@dataclass(frozen=True)
class EventResult:
    name: str
    event_id: str
    origin_time: str
    magnitude: float
    depth_km: float
    latitude: float
    longitude: float
    shaking_version: str
    shaking_type: str
    valid_buildings: int
    surface_max_mmi: float | None
    populated_max_mmi: float | None
    buildings_mmi_ge_6: int
    population_mmi_ge_6: float
    validation_station_count: int
    validation_mae: float | None


class HistoricalExposureBuilder:
    def __init__(
        self,
        reference_root: Path,
        raw_root: Path,
        output_root: Path,
        guard: ResourceGuard,
        *,
        memory_limit_mb: int = 512,
    ) -> None:
        if reference_root.name != DEFAULT_REFERENCE_GENERATION:
            raise ValueError(
                "M3 must read the approved LINZ export generation "
                f"{DEFAULT_REFERENCE_GENERATION}; got {reference_root}"
            )
        required = [
            reference_root / "int_buildings_h3",
            reference_root / "int_population_h3.parquet",
            reference_root / "dim_h3_cell.parquet",
        ]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise FileNotFoundError(f"Approved reference generation is incomplete: {missing}")
        self.reference_root = reference_root
        self.output_root = output_root
        self.output_root.mkdir(parents=True, exist_ok=True)
        self._guard = guard
        self._client = ShakingLayersClient(raw_root, guard)
        self._connection = duckdb.connect(str(output_root / "m3.duckdb"))
        self._connection.execute(f"set memory_limit='{memory_limit_mb}MB'")
        self._connection.execute("set threads=1")
        self._connection.execute("set preserve_insertion_order=false")
        self._connection.execute("load spatial")

    def close(self) -> None:
        self._connection.close()

    def run(self) -> dict[str, Any]:
        events = [*FIXED_EVENTS, RECENT_EVENT]
        if not all(self._event_outputs_exist(event_id) for _, event_id in events):
            self._prepare_reference_aggregates()
        results = [self._process_event(name, event_id) for name, event_id in events]
        self._combine_outputs()
        self._build_marts(results)
        overall_station_count = sum(result.validation_station_count for result in results)
        validation_rows = self._connection.execute(
            """
            select count(*), avg(abs(estimated_mmi - observed_mmi))
            from read_parquet(?)
            where estimated_mmi is not null and observed_mmi is not null
            """,
            [(self.output_root / "mart_mmi_validation.parquet").as_posix()],
        ).fetchone()
        return {
            "reference_generation": self.reference_root.name,
            "reference_root": (f".local/data/curated/reference-export/{self.reference_root.name}"),
            "old_wfs_fallback_used": False,
            "water_meshblock_buildings_excluded": 21483,
            "events": [result.__dict__ for result in results],
            "validation_station_count": overall_station_count,
            "validation_mae": validation_rows[1],
        }

    def _event_outputs_exist(self, event_id: str) -> bool:
        return all(
            self._event_path(dataset, event_id).exists()
            for dataset in (
                "int_event_shaking_h3",
                "fct_event_exposure_cell",
                "mart_mmi_validation",
            )
        )

    def _prepare_reference_aggregates(self) -> None:
        buildings_glob = (
            self.reference_root / "int_buildings_h3" / "region=*" / "*.parquet"
        ).as_posix()
        self._connection.execute(
            """
            create or replace temporary table current_counts as
            with ranked as (
                select *, row_number() over (
                    partition by building_id
                    order by begin_lifespan desc, building_outline_id desc
                ) as version_rank
                from read_parquet(?)
                where end_lifespan is null
            )
            select
                h3_res8,
                count(*)::bigint as current_building_count,
                sum(footprint_area_m2)::double as current_footprint_area_m2
            from ranked
            where version_rank = 1
            group by h3_res8
            """,
            [buildings_glob],
        )
        self._connection.execute(
            """
            create or replace temporary table population_counts as
            select h3_res8, sum(allocated_population)::double as population_2023
            from read_parquet(?)
            where h3_res8 is not null
            group by h3_res8
            """,
            [(self.reference_root / "int_population_h3.parquet").as_posix()],
        )

    def _process_event(self, name: str, event_id: str) -> EventResult:
        self._guard.check()
        event = self._client.cache_event(event_id)
        param = event.param
        origin_time = str(param["origin_time"])
        magnitude = float(param["magnitude"])
        depth = float(param["depth"])
        latitude = float(param["latitude"])
        longitude = float(param["longitude"])
        shaking_path = self._event_path("int_event_shaking_h3", event_id)
        exposure_path = self._event_path("fct_event_exposure_cell", event_id)
        validation_path = self._event_path("mart_mmi_validation", event_id)
        if shaking_path.exists() and exposure_path.exists() and validation_path.exists():
            valid_buildings = self._count_valid_buildings(origin_time)
            station_count, mae = self._validation_summary(validation_path)
        else:
            self._build_shaking(event)
            valid_buildings = self._build_exposure(event_id, origin_time)
            station_count, mae = self._build_validation(
                event, magnitude, depth, latitude, longitude
            )
        surface_max = self._connection.execute(
            "select max(PARAMVALUE) from st_read(?)", [event.polygon_shapefile.as_posix()]
        ).fetchone()[0]
        populated_max, buildings, population = self._connection.execute(
            """
            select
                max(mmi),
                coalesce(sum(event_building_count) filter (where mmi >= 6), 0),
                coalesce(sum(population_2023) filter (where mmi >= 6), 0)
            from read_parquet(?)
            """,
            [exposure_path.as_posix()],
        ).fetchone()
        return EventResult(
            name=name,
            event_id=event_id,
            origin_time=origin_time,
            magnitude=magnitude,
            depth_km=depth,
            latitude=latitude,
            longitude=longitude,
            shaking_version=str(event.manifest["versionpath"]),
            shaking_type=str(event.manifest["type"]),
            valid_buildings=valid_buildings,
            surface_max_mmi=surface_max,
            populated_max_mmi=populated_max,
            buildings_mmi_ge_6=int(buildings),
            population_mmi_ge_6=float(population),
            validation_station_count=station_count,
            validation_mae=mae,
        )

    def _count_valid_buildings(self, origin_time: str) -> int:
        buildings_glob = (
            self.reference_root / "int_buildings_h3" / "region=*" / "*.parquet"
        ).as_posix()
        return int(
            self._connection.execute(
                """
                select count(*) from (
                    select building_id
                    from read_parquet(?)
                    where begin_lifespan <= cast(? as timestamptz)
                      and (end_lifespan is null or end_lifespan > cast(? as timestamptz))
                    group by building_id
                )
                """,
                [buildings_glob, origin_time, origin_time],
            ).fetchone()[0]
        )

    def _validation_summary(self, path: Path) -> tuple[int, float | None]:
        count, mae = self._connection.execute(
            """
            select count(*), avg(abs(estimated_mmi - observed_mmi))
            from read_parquet(?)
            where estimated_mmi is not null
            """,
            [path.as_posix()],
        ).fetchone()
        return int(count), mae

    def _build_shaking(self, event: CachedShakingEvent) -> None:
        output = self._event_path("int_event_shaking_h3", event.event_id)
        output.parent.mkdir(parents=True, exist_ok=True)
        self._connection.execute(
            """
            create or replace temporary table event_shaking as
            select
                ?::varchar as event_id,
                cells.h3_res8,
                cells.h3_res6,
                max(polygons.PARAMVALUE)::double as mmi,
                'official'::varchar as mmi_source,
                ?::varchar as source_version,
                ?::varchar as source_status
            from read_parquet(?) cells
            inner join st_read(?) polygons
                on st_covers(
                    polygons.geom,
                    st_point(cells.centre_longitude, cells.centre_latitude)
                )
            group by cells.h3_res8, cells.h3_res6
            order by cells.h3_res8
            """,
            [
                event.event_id,
                event.manifest["versionpath"],
                event.manifest["type"],
                (self.reference_root / "dim_h3_cell.parquet").as_posix(),
                event.polygon_shapefile.as_posix(),
            ],
        )
        self._copy_table("event_shaking", output)

    def _build_exposure(self, event_id: str, origin_time: str) -> int:
        buildings_glob = (
            self.reference_root / "int_buildings_h3" / "region=*" / "*.parquet"
        ).as_posix()
        shaking_path = self._event_path("int_event_shaking_h3", event_id)
        exposure_path = self._event_path("fct_event_exposure_cell", event_id)
        self._connection.execute(
            """
            create or replace temporary table valid_event_buildings as
            with filtered as (
                select *, row_number() over (
                    partition by building_id
                    order by begin_lifespan desc, building_outline_id desc
                ) as version_rank
                from read_parquet(?)
                where begin_lifespan <= cast(? as timestamptz)
                  and (end_lifespan is null or end_lifespan > cast(? as timestamptz))
            )
            select * exclude (version_rank)
            from filtered
            where version_rank = 1
            """,
            [buildings_glob, origin_time, origin_time],
        )
        valid_count = self._connection.execute(
            "select count(*) from valid_event_buildings"
        ).fetchone()[0]
        self._connection.execute(
            """
            create or replace temporary table event_exposure as
            with event_buildings as (
                select
                    h3_res8,
                    count(*)::bigint as event_building_count,
                    sum(footprint_area_m2)::double as event_footprint_area_m2
                from valid_event_buildings
                group by h3_res8
            )
            select
                shaking.event_id,
                shaking.h3_res8,
                shaking.h3_res6,
                shaking.mmi,
                shaking.mmi_source,
                shaking.source_version,
                coalesce(event_buildings.event_building_count, 0)::bigint
                    as event_building_count,
                coalesce(event_buildings.event_footprint_area_m2, 0)::double
                    as event_footprint_area_m2,
                coalesce(current_counts.current_building_count, 0)::bigint
                    as current_building_count,
                coalesce(current_counts.current_footprint_area_m2, 0)::double
                    as current_footprint_area_m2,
                coalesce(population_counts.population_2023, 0)::double as population_2023
            from read_parquet(?) shaking
            left join event_buildings using (h3_res8)
            left join current_counts using (h3_res8)
            left join population_counts using (h3_res8)
            order by shaking.h3_res8
            """,
            [shaking_path.as_posix()],
        )
        self._copy_table("event_exposure", exposure_path)
        return int(valid_count)

    def _build_validation(
        self,
        event: CachedShakingEvent,
        magnitude: float,
        depth: float,
        latitude: float,
        longitude: float,
    ) -> tuple[int, float | None]:
        tectonic = event.param.get(
            "tectonic_weighting_IF_CR_SL", event.param.get("tectonic_weighting", [])
        )
        crustal = bool(len(tectonic) > 1 and float(tectonic[1]) > 0)
        rows: list[list[Any]] = []
        for feature in event.station_list.get("features", []):
            properties = feature.get("properties", {})
            coordinates = feature.get("geometry", {}).get("coordinates", [])
            observed = properties.get("intensity")
            if observed in {None, "", "null"} or len(coordinates) < 2:
                continue
            distance = haversine_km(
                latitude, longitude, float(coordinates[1]), float(coordinates[0])
            )
            estimate = estimate_mmi(
                magnitude=magnitude,
                distance_km=distance,
                depth_km=depth,
                crustal_event=crustal,
            )
            rows.append(
                [
                    event.event_id,
                    str(feature.get("id", properties.get("code", ""))),
                    float(observed),
                    estimate.mmi,
                    distance,
                    estimate.model,
                    estimate.model_reference,
                    estimate.depth_clamped,
                    estimate.distance_clamped,
                    estimate.point_source_approx,
                    estimate.exclusion_reason,
                ]
            )
        self._connection.execute(
            """
            create or replace temporary table event_validation (
                event_id varchar,
                station_id varchar,
                observed_mmi double,
                estimated_mmi double,
                epicentral_distance_km double,
                model varchar,
                model_reference varchar,
                depth_clamped boolean,
                distance_clamped boolean,
                point_source_approx boolean,
                exclusion_reason varchar
            )
            """
        )
        if rows:
            self._connection.executemany(
                "insert into event_validation values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows
            )
        output = self._event_path("mart_mmi_validation", event.event_id)
        self._copy_table("event_validation", output)
        count, mae = self._connection.execute(
            """
            select count(*), avg(abs(estimated_mmi - observed_mmi))
            from event_validation
            where estimated_mmi is not null
            """
        ).fetchone()
        return int(count), mae

    def _combine_outputs(self) -> None:
        for name in ("int_event_shaking_h3", "fct_event_exposure_cell", "mart_mmi_validation"):
            source = (self.output_root / name / "*.parquet").as_posix()
            destination = self.output_root / f"{name}.parquet"
            self._connection.execute(
                f"copy (select * from read_parquet('{source}') order by event_id) "
                f"to '{destination.as_posix()}' (format parquet, compression zstd)"
            )

    def _build_marts(self, results: list[EventResult]) -> None:
        self._connection.execute(
            """
            create or replace table dim_event (
                event_name varchar,
                event_id varchar,
                origin_time timestamptz,
                magnitude double,
                depth_km double,
                latitude double,
                longitude double,
                mmi_source varchar,
                shaking_version varchar,
                shaking_type varchar,
                valid_buildings bigint,
                surface_max_mmi double,
                populated_max_mmi double,
                validation_station_count bigint,
                validation_mae double
            )
            """
        )
        self._connection.executemany(
            "insert into dim_event values (?, ?, ?, ?, ?, ?, ?, 'official', ?, ?, ?, ?, ?, ?, ?)",
            [
                [
                    result.name,
                    result.event_id,
                    result.origin_time,
                    result.magnitude,
                    result.depth_km,
                    result.latitude,
                    result.longitude,
                    result.shaking_version,
                    result.shaking_type,
                    result.valid_buildings,
                    result.surface_max_mmi,
                    result.populated_max_mmi,
                    result.validation_station_count,
                    result.validation_mae,
                ]
                for result in results
            ],
        )
        self._copy_table("dim_event", self.output_root / "dim_event.parquet")
        exposure = (self.output_root / "fct_event_exposure_cell.parquet").as_posix()
        self._connection.execute(
            """
            create or replace temporary table mart_event_summary as
            select
                event.event_name,
                event.event_id,
                event.origin_time,
                event.magnitude,
                event.depth_km,
                event.latitude,
                event.longitude,
                event.mmi_source,
                event.shaking_version,
                event.valid_buildings,
                max(exposure.mmi)::double as max_mmi,
                coalesce(
                    sum(exposure.event_building_count) filter (where exposure.mmi >= 6), 0
                )::bigint as buildings_mmi_ge_6,
                coalesce(
                    sum(exposure.event_footprint_area_m2) filter (where exposure.mmi >= 6), 0
                )::double as footprint_m2_mmi_ge_6,
                coalesce(sum(exposure.population_2023) filter (where exposure.mmi >= 6), 0)::double
                    as population_mmi_ge_6,
                event.validation_station_count,
                event.validation_mae
            from dim_event event
            left join read_parquet(?) exposure using (event_id)
            group by all
            order by event.origin_time
            """,
            [exposure],
        )
        self._copy_table("mart_event_summary", self.output_root / "mart_event_summary.parquet")
        self._connection.execute(
            """
            create or replace temporary table mart_event_exposure_h3r6 as
            select
                event_id,
                h3_res6,
                max(mmi)::double as mmi,
                any_value(mmi_source)::varchar as mmi_source,
                any_value(source_version)::varchar as source_version,
                sum(event_building_count)::bigint as event_building_count,
                sum(event_footprint_area_m2)::double as event_footprint_area_m2,
                sum(current_building_count)::bigint as current_building_count,
                sum(current_footprint_area_m2)::double as current_footprint_area_m2,
                sum(population_2023)::double as population_2023
            from read_parquet(?)
            group by event_id, h3_res6
            order by event_id, h3_res6
            """,
            [exposure],
        )
        self._copy_table(
            "mart_event_exposure_h3r6",
            self.output_root / "mart_event_exposure_h3r6.parquet",
        )
        self._connection.execute(
            """
            create or replace temporary table mart_accumulation_cell as
            select
                h3_res8,
                any_value(h3_res6) as h3_res6,
                count(*) filter (where mmi >= 6)::bigint as strong_event_count,
                max(current_building_count)::bigint as current_building_count,
                count(*) filter (where mmi >= 6)
                    * max(current_building_count)::bigint as accumulation_score
            from read_parquet(?)
            group by h3_res8
            order by h3_res8
            """,
            [exposure],
        )
        self._copy_table(
            "mart_accumulation_cell", self.output_root / "mart_accumulation_cell.parquet"
        )

    def _event_path(self, dataset: str, event_id: str) -> Path:
        return self.output_root / dataset / f"event={event_id}.parquet"

    def _copy_table(self, table: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".parquet.part")
        if temporary.exists():
            temporary.unlink()
        self._connection.execute(
            f"copy {table} to '{temporary.as_posix()}' (format parquet, compression zstd)"
        )
        os.replace(temporary, destination)
        self._guard.check()


def write_evidence(payload: dict[str, Any], evidence_root: Path) -> None:
    evidence_root.mkdir(parents=True, exist_ok=True)
    (evidence_root / "m3-replay.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    event_rows = "\n".join(_event_markdown_row(event) for event in payload["events"])
    fixed_counts = "\n".join(
        f"- `{event['event_id']}` at `{event['origin_time']}`: `{event['valid_buildings']:,}`"
        for event in payload["events"][:9]
    )
    markdown = f"""# M3 historical event replay

## Input lineage

- Reference data: `.local/data/curated/reference-export/{payload["reference_generation"]}`.
- The retained WFS generation at `.local/data/curated/reference` was not read and was not deleted.
- The 21,483 buildings attributed to water meshblocks remain excluded, as approved.
- Building validity is the exact half-open interval `begin_lifespan <= event_time < end_lifespan`.
- Simultaneously valid source versions are deterministically reduced to one row per `building_id`.

## Ten-event replay

| Event | ID | UTC | Valid buildings | Max MMI | Bldgs >= 6 | Pop >= 6 | Source | MAE |
|---|---|---|---:|---:|---:|---:|---|---:|
{event_rows}

## Nine fixed-event lifecycle counts

{fixed_counts}

The source lifecycle begins on 2018-10-16. The eight fixed events before that
date therefore have zero source-supported historical buildings; the pipeline
does not substitute current buildings. Population remains the approved fixed
2023 allocation. This is a source-coverage limitation, not a processing error.

## Validation

- Station rows evaluated: `{payload["validation_station_count"]:,}`.
- Overall point-source attenuation MAE: `{payload["validation_mae"]:.3f}` MMI.
- MAE above 1.0 is explicitly escalated for project-manager review and does not
  replace the official Shaking Layers surfaces used for exposure.

Kermadec is evaluated only where its official surface intersects populated New
Zealand H3 cells. Exposure remains close to zero by design.
"""
    (evidence_root / "README.md").write_text(markdown, encoding="utf-8", newline="\n")


def _event_markdown_row(event: dict[str, Any]) -> str:
    maximum = (
        f"{event['populated_max_mmi']:.1f}" if event["populated_max_mmi"] is not None else "n/a"
    )
    mae = f"{event['validation_mae']:.3f}" if event["validation_mae"] is not None else "n/a"
    return (
        f"| {event['name']} | `{event['event_id']}` | {event['origin_time']} | "
        f"{event['valid_buildings']:,} | {maximum} | {event['buildings_mmi_ge_6']:,} | "
        f"{event['population_mmi_ge_6']:,.0f} | official | {mae} |"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay the ten M3 historical events")
    parser.add_argument(
        "--reference-root",
        type=Path,
        default=ROOT / ".local/data/curated/reference-export" / DEFAULT_REFERENCE_GENERATION,
    )
    parser.add_argument(
        "--raw-root", type=Path, default=ROOT / ".local/data/raw/events/shaking-layers"
    )
    parser.add_argument("--output-root", type=Path, default=ROOT / ".local/data/curated/events/m3")
    parser.add_argument("--evidence-root", type=Path, default=ROOT / "evidence/m3")
    arguments = parser.parse_args()
    settings = Settings.from_env()
    guard = ResourceGuard(
        settings.data_root,
        min_free_disk_gb=settings.reference_min_free_disk_gb,
        max_rss_mb=settings.reference_max_rss_mb,
    )
    builder = HistoricalExposureBuilder(
        arguments.reference_root.resolve(),
        arguments.raw_root.resolve(),
        arguments.output_root.resolve(),
        guard,
        memory_limit_mb=settings.duckdb_memory_limit_mb,
    )
    try:
        payload = builder.run()
    finally:
        builder.close()
    write_evidence(payload, arguments.evidence_root.resolve())
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
