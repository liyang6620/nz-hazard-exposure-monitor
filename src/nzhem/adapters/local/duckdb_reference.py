from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

from nzhem.adapters.local.resource_guard import ResourceGuard
from nzhem.adapters.local.wfs import DownloadedPage


@dataclass(frozen=True)
class RegionBounds:
    code: str
    name: str
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return (self.min_lon, self.min_lat, self.max_lon, self.max_lat)


@dataclass(frozen=True)
class RegionTile:
    name: str
    bbox: tuple[float, float, float, float]
    include_max_lon: bool
    include_max_lat: bool


class DuckDbReferenceTransformer:
    """Incremental geospatial transforms with fixed DuckDB memory and temp limits."""

    def __init__(
        self,
        data_root: Path,
        guard: ResourceGuard,
        *,
        memory_limit_mb: int = 512,
        connection: duckdb.DuckDBPyConnection | None = None,
    ) -> None:
        self._data_root = data_root
        self._raw_root = data_root / "raw" / "reference"
        self._curated_root = data_root / "curated" / "reference"
        self._work_root = data_root / ".reference-work"
        self._guard = guard
        self._curated_root.mkdir(parents=True, exist_ok=True)
        self._work_root.mkdir(parents=True, exist_ok=True)
        self._database_path = self._work_root / "reference.duckdb"
        self._memory_limit_mb = memory_limit_mb
        self._owns_connection = connection is None
        self._connection = connection or duckdb.connect(str(self._database_path))
        self._configure_connection()

    @property
    def curated_root(self) -> Path:
        return self._curated_root

    def stage_boundaries(self, pages: Sequence[DownloadedPage]) -> list[Path]:
        destination_root = self._curated_root / "stg_stats__boundaries"
        return self._stage_pages(pages, destination_root, lambda path, _: self._boundary_sql(path))

    def stage_population(self, pages: Sequence[DownloadedPage]) -> list[Path]:
        destination_root = self._curated_root / "stg_stats__population"
        return self._stage_pages(
            pages, destination_root, lambda path, _: self._population_sql(path)
        )

    def region_bounds(self) -> list[RegionBounds]:
        boundary_glob = self._sql_path(self._curated_root / "stg_stats__boundaries" / "*.parquet")
        rows = self._connection.execute(
            f"""
            with boundaries as (
                select
                    region_code,
                    region_name,
                    st_geomfromwkb(geometry_wkb) as geom
                from read_parquet('{boundary_glob}')
                where land_water = '12'
                  and region_code is not null
            )
            select
                region_code,
                min(region_name) as region_name,
                min(st_xmin(geom)) as min_lon,
                min(st_ymin(geom)) as min_lat,
                max(st_xmax(geom)) as max_lon,
                max(st_ymax(geom)) as max_lat
            from boundaries
            group by region_code
            order by region_code
            """
        ).fetchall()
        return [RegionBounds(*row) for row in rows]

    def partition_boundaries_by_region(self, regions: Sequence[RegionBounds]) -> None:
        source_glob = self._sql_path(self._curated_root / "stg_stats__boundaries" / "*.parquet")
        destination_root = self._curated_root / "boundaries_by_region"
        destination_root.mkdir(parents=True, exist_ok=True)
        expected = {f"region-{region.code}.parquet" for region in regions}
        for stale in destination_root.glob("*.parquet"):
            if stale.name not in expected:
                stale.unlink()
        for region in regions:
            escaped = region.code.replace("'", "''")
            self._replace_with_query(
                destination_root / f"region-{region.code}.parquet",
                f"""
                select *
                from read_parquet('{source_glob}')
                where region_code = '{escaped}' and land_water = '12'
                order by meshblock_code
                """,
            )
            self._guard.check()

    def region_tiles(self, region: RegionBounds, *, tile_degrees: float = 0.1) -> list[RegionTile]:
        boundary_path = self._sql_path(
            self._curated_root / "boundaries_by_region" / f"region-{region.code}.parquet"
        )
        self._connection.execute(
            """
            create or replace temporary table selected_region as
            select st_union_agg(st_geomfromwkb(geometry_wkb)) as geom
            from read_parquet(?)
            where land_water = '12'
            """,
            [boundary_path],
        )
        x_count = math.ceil((region.max_lon - region.min_lon) / tile_degrees)
        y_count = math.ceil((region.max_lat - region.min_lat) / tile_degrees)
        tiles: list[RegionTile] = []
        for y_index in range(y_count):
            min_lat = region.min_lat + y_index * tile_degrees
            max_lat = min(region.max_lat, min_lat + tile_degrees)
            for x_index in range(x_count):
                min_lon = region.min_lon + x_index * tile_degrees
                max_lon = min(region.max_lon, min_lon + tile_degrees)
                intersects = self._connection.execute(
                    """
                    select st_intersects(geom, st_makeenvelope(?, ?, ?, ?))
                    from selected_region
                    """,
                    [min_lon, min_lat, max_lon, max_lat],
                ).fetchone()
                if intersects and intersects[0]:
                    tiles.append(
                        RegionTile(
                            name=f"region-{region.code}-tile-{y_index:03d}-{x_index:03d}",
                            bbox=(min_lon, min_lat, max_lon, max_lat),
                            include_max_lon=x_index == x_count - 1,
                            include_max_lat=y_index == y_count - 1,
                        )
                    )
        self._connection.execute("drop table selected_region")
        return tiles

    def stage_buildings_for_region(
        self,
        region: RegionBounds,
        pages: Sequence[DownloadedPage],
        point_partitions: Mapping[str, RegionTile] | None = None,
    ) -> list[Path]:
        destination_root = self._curated_root / "int_buildings_h3" / f"region={region.code}"
        boundary_glob = self._sql_path(
            self._curated_root / "boundaries_by_region" / f"region-{region.code}.parquet"
        )

        def query(source_path: str, page: DownloadedPage) -> str:
            partition_name = Path(page.path).parent.name
            return self._building_sql(
                source_path,
                boundary_glob,
                region.code,
                point_partition=(point_partitions or {}).get(partition_name),
            )

        return self._stage_pages(pages, destination_root, query)

    def build_dimensions_and_population(
        self,
        *,
        buildings_root: Path | None = None,
        output_root: Path | None = None,
    ) -> dict[str, int | float]:
        active_buildings_root = buildings_root or self._curated_root
        active_output_root = output_root or self._curated_root
        active_output_root.mkdir(parents=True, exist_ok=True)
        buildings_glob = self._sql_path(
            active_buildings_root / "int_buildings_h3" / "region=*" / "*.parquet"
        )
        population_glob = self._sql_path(self._curated_root / "stg_stats__population" / "*.parquet")
        boundaries_glob = self._sql_path(self._curated_root / "stg_stats__boundaries" / "*.parquet")
        population_output = active_output_root / "int_population_h3.parquet"
        region_output = active_output_root / "dim_region.parquet"
        cell_output = active_output_root / "dim_h3_cell.parquet"

        self._replace_with_query(
            region_output,
            f"""
            with source as (
                select distinct
                    region_code,
                    region_name,
                    territorial_authority_code,
                    territorial_authority_name,
                    sa2_code,
                    sa2_name
                from read_parquet('{boundaries_glob}')
                where land_water = '12'
            )
            select * from source
            order by region_code, territorial_authority_code, sa2_code
            """,
        )
        self._replace_with_query(
            population_output,
            self._population_allocation_sql(buildings_glob, population_glob, boundaries_glob),
        )
        population_path = self._sql_path(population_output)
        self._replace_with_query(
            cell_output,
            f"""
            with cells as (
                select h3_res8 from read_parquet('{buildings_glob}') where h3_res8 is not null
                union
                select h3_res8 from read_parquet('{population_path}') where h3_res8 is not null
            )
            select
                h3_res8,
                h3_cell_to_parent(h3_res8, 6) as h3_res6,
                h3_cell_to_lat(h3_res8) as centre_latitude,
                h3_cell_to_lng(h3_res8) as centre_longitude
            from cells
            order by h3_res8
            """,
        )

        stats = self._connection.execute(
            f"""
            select
                (select count(*) from read_parquet('{buildings_glob}')) as building_count,
                (select count(*) from read_parquet('{population_glob}')) as population_sa1_count,
                (
                    select coalesce(sum(population), 0)
                    from read_parquet('{population_glob}')
                    where population >= 0
                ) as source_population,
                (
                    select coalesce(sum(allocated_population), 0)
                    from read_parquet('{population_path}')
                ) as allocated_population,
                (
                    select count(*)
                    from read_parquet('{population_glob}')
                    where population in (-997, -999)
                ) as suppressed_sa1,
                (
                    select count(*)
                    from read_parquet('{population_path}')
                    where allocation_method = 'unlocated_no_geometry'
                ) as unlocated_sa1,
                (
                    select coalesce(sum(allocated_population), 0)
                    from read_parquet('{population_path}')
                    where allocation_method = 'unlocated_no_geometry'
                ) as unlocated_population,
                (
                    select count(*)
                    from read_parquet('{population_path}')
                    where allocation_method = 'unlocated_no_geometry'
                      and allocated_population > 0
                ) as unlocated_nonzero_sa1
            """
        ).fetchone()
        assert stats is not None
        return {
            "building_count": int(stats[0]),
            "population_sa1_count": int(stats[1]),
            "source_population": float(stats[2]),
            "allocated_population": float(stats[3]),
            "suppressed_sa1": int(stats[4]),
            "unlocated_sa1": int(stats[5]),
            "unlocated_population": float(stats[6]),
            "unlocated_nonzero_sa1": int(stats[7]),
        }

    def population_invariant_failures(
        self,
        tolerance: float = 1e-6,
        *,
        output_root: Path | None = None,
    ) -> int:
        active_output_root = output_root or self._curated_root
        population_path = self._sql_path(active_output_root / "int_population_h3.parquet")
        source_glob = self._sql_path(self._curated_root / "stg_stats__population" / "*.parquet")
        row = self._connection.execute(
            f"""
            with allocated as (
                select sa1_code, sum(allocated_population) as allocated_population
                from read_parquet('{population_path}')
                group by sa1_code
            )
            select count(*)
            from read_parquet('{source_glob}') source
            left join allocated using (sa1_code)
            where source.population >= 0
              and abs(source.population - coalesce(allocated.allocated_population, 0)) > ?
            """,
            [tolerance],
        ).fetchone()
        return int(row[0]) if row else 0

    def logical_hash(self, path_or_glob: Path, order_by: str) -> str:
        source = self._sql_path(path_or_glob)
        cursor = self._connection.execute(
            f"select * from read_parquet('{source}') order by {order_by}"
        )
        digest = hashlib.sha256()
        columns = [description[0] for description in cursor.description]
        digest.update((json.dumps(columns, separators=(",", ":")) + "\n").encode())
        while rows := cursor.fetchmany(1000):
            for row in rows:
                normalized = [self._json_value(value) for value in row]
                line = json.dumps(normalized, separators=(",", ":"), ensure_ascii=True)
                digest.update((line + "\n").encode())
            self._guard.check()
        return digest.hexdigest()

    def close(self) -> None:
        self._connection.close()

    def _stage_pages(
        self,
        pages: Sequence[DownloadedPage],
        destination_root: Path,
        query_factory: Callable[[str, DownloadedPage], str],
    ) -> list[Path]:
        destination_root.mkdir(parents=True, exist_ok=True)
        outputs: list[Path] = []
        starts_are_unique = len({page.start_index for page in pages}) == len(pages)
        expected_names = {self._page_output_name(page, starts_are_unique) for page in pages}
        for stale in destination_root.glob("*.parquet"):
            if stale.name not in expected_names:
                stale.unlink()
                self._source_marker(stale).unlink(missing_ok=True)
        processed_since_reconnect = 0
        for page in pages:
            self._guard.check()
            destination = destination_root / self._page_output_name(page, starts_are_unique)
            marker = self._source_marker(destination)
            if (
                destination.is_file()
                and marker.is_file()
                and marker.read_text(encoding="ascii").strip() == page.sha256
            ):
                outputs.append(destination)
                continue
            with self._decompressed_page(page) as source_path:
                self._replace_with_query(
                    destination,
                    query_factory(self._sql_path(source_path), page),
                )
            self._write_marker(marker, page.sha256)
            outputs.append(destination)
            self._guard.check()
            processed_since_reconnect += 1
            if processed_since_reconnect >= 50:
                self._reconnect()
                processed_since_reconnect = 0
        return outputs

    def _replace_with_query(self, destination: Path, query: str) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".parquet.part")
        temporary.unlink(missing_ok=True)
        self._connection.execute(
            f"COPY ({query}) TO '{self._sql_path(temporary)}' "
            "(FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 10000)"
        )
        os.replace(temporary, destination)

    def _decompressed_page(self, page: DownloadedPage):
        source = self._raw_root / Path(page.path)
        descriptor, name = tempfile.mkstemp(dir=self._work_root, suffix=".geojson")
        os.close(descriptor)
        destination = Path(name)

        class TemporaryPage:
            def __enter__(inner_self) -> Path:
                with gzip.open(source, "rb") as compressed, destination.open("wb") as output:
                    while chunk := compressed.read(64 * 1024):
                        output.write(chunk)
                        self._guard.check()
                return destination

            def __exit__(inner_self, *_: object) -> None:
                destination.unlink(missing_ok=True)

        return TemporaryPage()

    def _load_extensions(self) -> None:
        for extension, repository in (("spatial", None), ("h3", "community")):
            try:
                self._connection.execute(f"LOAD {extension}")
            except duckdb.Error:
                install = f"INSTALL {extension}"
                if repository:
                    install += f" FROM {repository}"
                self._connection.execute(install)
                self._connection.execute(f"LOAD {extension}")

    def _configure_connection(self) -> None:
        self._connection.execute(f"SET memory_limit='{self._memory_limit_mb}MB'")
        self._connection.execute("SET threads=1")
        self._connection.execute("SET preserve_insertion_order=false")
        spill_path = self._sql_path(self._work_root / "spill")
        self._connection.execute(f"SET temp_directory='{spill_path}'")
        self._load_extensions()

    def _reconnect(self) -> None:
        if not self._owns_connection:
            return
        self._connection.close()
        self._connection = duckdb.connect(str(self._database_path))
        self._configure_connection()
        self._guard.check()

    @staticmethod
    def _source_marker(destination: Path) -> Path:
        return destination.with_suffix(".source-sha256")

    @staticmethod
    def _page_output_name(page: DownloadedPage, starts_are_unique: bool) -> str:
        partition = Path(page.path).parent.name
        prefix = "part" if starts_are_unique else f"part-{partition}"
        return f"{prefix}-{page.start_index:09d}.parquet"

    @staticmethod
    def _write_marker(path: Path, digest: str) -> None:
        temporary = path.with_suffix(".source-sha256.part")
        temporary.write_text(digest + "\n", encoding="ascii")
        os.replace(temporary, path)

    @staticmethod
    def _boundary_sql(source_path: str) -> str:
        return f"""
        select
            cast(MB2023_V1_00 as varchar) as meshblock_code,
            cast(SA12023_V1_00 as varchar) as sa1_code,
            cast(SA22023_V1_00 as varchar) as sa2_code,
            cast(SA22023_V1_00_NAME as varchar) as sa2_name,
            cast(REGC2023_V1_00 as varchar) as region_code,
            cast(REGC2023_V1_00_NAME as varchar) as region_name,
            cast(TA2023_V1_00 as varchar) as territorial_authority_code,
            cast(TA2023_V1_00_NAME as varchar) as territorial_authority_name,
            cast(LANDWATER as varchar) as land_water,
            cast(LANDWATER_NAME as varchar) as land_water_name,
            cast(st_aswkb(geom) as blob) as geometry_wkb
        from st_read('{source_path}')
        order by meshblock_code
        """

    @staticmethod
    def _population_sql(source_path: str) -> str:
        return f"""
        select
            cast(SA12023_V1_00 as varchar) as sa1_code,
            cast(LANDWATER as varchar) as land_water,
            cast(LANDWATER_NAME as varchar) as land_water_name,
            cast(VAR_1_3 as integer) as population,
            case
                when VAR_1_3 = -997 then 'not_available'
                when VAR_1_3 = -999 then 'confidential'
                when VAR_1_3 < 0 then 'unknown_negative_code'
                else 'published'
            end as population_status,
            cast(st_aswkb(geom) as blob) as geometry_wkb
        from st_read('{source_path}')
        order by sa1_code
        """

    @staticmethod
    def _building_sql(
        source_path: str,
        boundary_glob: str,
        region_code: str,
        *,
        point_partition: RegionTile | None = None,
    ) -> str:
        escaped_region = region_code.replace("'", "''")
        point_filter = ""
        if point_partition is not None:
            min_lon, min_lat, max_lon, max_lat = point_partition.bbox
            lon_operator = "<=" if point_partition.include_max_lon else "<"
            lat_operator = "<=" if point_partition.include_max_lat else "<"
            point_filter = f"""
            where st_x(st_pointonsurface(geom)) >= {min_lon!r}
              and st_x(st_pointonsurface(geom)) {lon_operator} {max_lon!r}
              and st_y(st_pointonsurface(geom)) >= {min_lat!r}
              and st_y(st_pointonsurface(geom)) {lat_operator} {max_lat!r}
            """
        return f"""
        with raw as (
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
                geom,
                st_pointonsurface(geom) as point_geom
            from st_read('{source_path}')
            {point_filter}
        ), attributed as (
            select
                raw.* exclude (geom),
                st_area(st_transform(raw.geom, 'EPSG:4326', 'EPSG:2193', always_xy := true))
                    as footprint_area_m2,
                st_x(point_geom) as longitude,
                st_y(point_geom) as latitude,
                boundary.meshblock_code,
                boundary.sa1_code,
                boundary.sa2_code,
                boundary.sa2_name,
                boundary.region_code,
                boundary.region_name,
                boundary.territorial_authority_code,
                boundary.territorial_authority_name
            from raw
            join read_parquet('{boundary_glob}') boundary
              on boundary.region_code = '{escaped_region}'
             and boundary.land_water = '12'
             and st_intersects(st_geomfromwkb(boundary.geometry_wkb), raw.point_geom)
            qualify row_number() over (
                partition by building_outline_id order by boundary.meshblock_code
            ) = 1
        )
        select
            * exclude (point_geom),
            year(begin_lifespan) as valid_from_year,
            year(end_lifespan) as valid_to_year,
            h3_latlng_to_cell(latitude, longitude, 8) as h3_res8,
            h3_cell_to_parent(h3_latlng_to_cell(latitude, longitude, 8), 6) as h3_res6
        from attributed
        order by building_outline_id
        """

    @staticmethod
    def _population_allocation_sql(
        buildings_glob: str,
        population_glob: str,
        boundaries_glob: str,
    ) -> str:
        return f"""
        with current_weights as (
            select
                sa1_code,
                h3_res8,
                sum(footprint_area_m2) as footprint_area_m2
            from read_parquet('{buildings_glob}')
            where valid_to_year is null
            group by sa1_code, h3_res8
        ), weighted as (
            select
                population.sa1_code,
                weights.h3_res8,
                population.population,
                weights.footprint_area_m2,
                weights.footprint_area_m2
                    / sum(weights.footprint_area_m2) over (partition by population.sa1_code)
                    * population.population as unadjusted_population,
                row_number() over (
                    partition by population.sa1_code order by weights.h3_res8 desc
                ) as correction_row
            from read_parquet('{population_glob}') population
            join current_weights weights using (sa1_code)
            where population.population >= 0
        ), adjusted as (
            select
                sa1_code,
                h3_res8,
                h3_cell_to_parent(h3_res8, 6) as h3_res6,
                footprint_area_m2,
                case when correction_row = 1 then
                    unadjusted_population
                    + population
                    - sum(unadjusted_population) over (partition by sa1_code)
                else unadjusted_population end as allocated_population,
                'building_area' as allocation_method
            from weighted
        ), fallback_boundaries as (
            select
                sa1_code,
                st_union_agg(st_geomfromwkb(geometry_wkb)) as geometry
            from read_parquet('{boundaries_glob}')
            where geometry_wkb is not null
            group by sa1_code
        ), no_buildings as (
            select
                population.sa1_code,
                h3_latlng_to_cell(
                    st_y(st_pointonsurface(coalesce(
                        try(st_geomfromwkb(population.geometry_wkb)),
                        fallback_boundaries.geometry
                    ))),
                    st_x(st_pointonsurface(coalesce(
                        try(st_geomfromwkb(population.geometry_wkb)),
                        fallback_boundaries.geometry
                    ))),
                    8
                ) as h3_res8,
                h3_cell_to_parent(
                    h3_latlng_to_cell(
                        st_y(st_pointonsurface(coalesce(
                            try(st_geomfromwkb(population.geometry_wkb)),
                            fallback_boundaries.geometry
                        ))),
                        st_x(st_pointonsurface(coalesce(
                            try(st_geomfromwkb(population.geometry_wkb)),
                            fallback_boundaries.geometry
                        ))),
                        8
                    ),
                    6
                ) as h3_res6,
                cast(0 as double) as footprint_area_m2,
                cast(population.population as double) as allocated_population,
                'sa1_interior_point' as allocation_method
            from read_parquet('{population_glob}') population
            left join current_weights using (sa1_code)
            left join fallback_boundaries using (sa1_code)
            where population.population >= 0
              and current_weights.sa1_code is null
              and coalesce(
                  try(st_geomfromwkb(population.geometry_wkb)),
                  fallback_boundaries.geometry
              ) is not null
              and not st_isempty(coalesce(
                  try(st_geomfromwkb(population.geometry_wkb)),
                  fallback_boundaries.geometry
              ))
        ), unlocated as (
            select
                population.sa1_code,
                cast(null as ubigint) as h3_res8,
                cast(null as ubigint) as h3_res6,
                cast(0 as double) as footprint_area_m2,
                cast(population.population as double) as allocated_population,
                'unlocated_no_geometry' as allocation_method
            from read_parquet('{population_glob}') population
            left join current_weights using (sa1_code)
            left join fallback_boundaries using (sa1_code)
            where population.population >= 0
              and current_weights.sa1_code is null
              and coalesce(
                  try(st_geomfromwkb(population.geometry_wkb)),
                  fallback_boundaries.geometry
              ) is null
        )
        select * from adjusted
        union all
        select * from no_buildings
        union all
        select * from unlocated
        order by sa1_code, h3_res8
        """

    @staticmethod
    def _sql_path(path: Path) -> str:
        return path.resolve().as_posix().replace("'", "''")

    @staticmethod
    def _json_value(value: Any) -> Any:
        if isinstance(value, bytes):
            return value.hex()
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return value
