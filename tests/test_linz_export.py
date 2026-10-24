from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import duckdb
import pytest

from nzhem.adapters.local.linz_export import (
    ExportArtifact,
    GpkgInfo,
    GpkgTilePlanner,
    LinzExportError,
    LinzExportImporter,
    _safe_multipolygon_wkb,
    inspect_zip,
)
from nzhem.adapters.local.resource_guard import ResourceGuard


def test_zip_preflight_rejects_traversal_and_declared_expansion(tmp_path: Path) -> None:
    unsafe = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(unsafe, "w") as archive:
        archive.writestr("../escape.gpkg", b"not-a-database")
    with pytest.raises(LinzExportError, match="Unsafe ZIP entry"):
        inspect_zip(unsafe)

    oversized = tmp_path / "oversized.zip"
    with zipfile.ZipFile(oversized, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("buildings.gpkg", b"x" * 1024)
    with pytest.raises(LinzExportError, match="declares more"):
        inspect_zip(oversized, maximum_uncompressed_bytes=512)


def test_wkb_preflight_rejects_nested_count_that_exceeds_available_bytes() -> None:
    valid = bytes.fromhex(
        "01"
        "06000000"
        "01000000"
        "01"
        "03000000"
        "01000000"
        "04000000"
        "0000000000000000"
        "0000000000000000"
        "000000000000f03f"
        "0000000000000000"
        "000000000000f03f"
        "000000000000f03f"
        "0000000000000000"
        "0000000000000000"
    )
    assert _safe_multipolygon_wkb(memoryview(valid))
    corrupt = bytearray(valid)
    corrupt[18:22] = (0x40000000).to_bytes(4, "little")
    assert not _safe_multipolygon_wkb(memoryview(corrupt))


def test_tiles_are_exclusive_crossing_polygons_are_not_duplicated_and_restart_skips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gpkg, boundaries = _synthetic_sources(tmp_path)
    info = _gpkg_info(gpkg)
    artifact = ExportArtifact(
        archive_path=tmp_path / "manual.zip",
        archive_sha256=hashlib.sha256(b"synthetic-export").hexdigest(),
        archive_bytes=1,
        uncompressed_bytes=gpkg.stat().st_size,
        gpkg=info,
        export_reference="test",
        exported_layer_version=438679,
        version_comparison="match",
    )
    importer = LinzExportImporter(
        artifact,
        boundaries,
        tmp_path / "generation",
        ResourceGuard(tmp_path, min_free_disk_gb=0.0001, max_rss_mb=4096),
        candidate_limit=1,
        memory_limit_mb=128,
        connection=duckdb.connect(),
    )
    try:
        importer._prepare_boundary_index()
        tiles = GpkgTilePlanner(info, candidate_limit=1).plan()
        assert len(tiles) > 1
        importer.process_tiles(tiles)
        reconciliation = importer.reconcile(tiles)
        assert reconciliation["source_feature_count"] == 3
        assert reconciliation["reconciliation_buckets"]["accepted"] == 3
        assert reconciliation["reconciled_feature_count"] == 3

        batch_glob = (importer.batch_root / "*.parquet").resolve().as_posix()
        rows = importer.connection.execute(
            f"""
            select building_outline_id, region_code, count(*)
            from read_parquet('{batch_glob}')
            group by building_outline_id, region_code
            order by building_outline_id
            """
        ).fetchall()
        assert rows == [(1, "01", 1), (2, "02", 1), (3, "02", 1)]
        inconsistent_h3_parents = importer.connection.execute(
            f"""
            select count(*)
            from read_parquet('{batch_glob}')
            where h3_res6 != h3_cell_to_parent(h3_res8, 6)
            """
        ).fetchone()[0]
        assert inconsistent_h3_parents == 0

        before = {
            path.name: path.stat().st_mtime_ns for path in importer.batch_root.glob("*.parquet")
        }
        monkeypatch.setattr(
            importer,
            "_tile_sql",
            lambda _: pytest.fail("a completed tile was processed again"),
        )
        importer.process_tiles(tiles)
        after = {
            path.name: path.stat().st_mtime_ns for path in importer.batch_root.glob("*.parquet")
        }
        assert after == before
    finally:
        importer.connection.close()


def test_one_tile_loads_meshblocks_from_every_intersecting_region(tmp_path: Path) -> None:
    gpkg, boundaries = _synthetic_sources(tmp_path)
    info = _gpkg_info(gpkg)
    artifact = ExportArtifact(
        tmp_path / "manual.zip",
        "a" * 64,
        1,
        gpkg.stat().st_size,
        info,
        "test",
        438679,
        "match",
    )
    importer = LinzExportImporter(
        artifact,
        boundaries,
        tmp_path / "generation",
        ResourceGuard(tmp_path, min_free_disk_gb=0.0001, max_rss_mb=4096),
        candidate_limit=5000,
        memory_limit_mb=128,
        connection=duckdb.connect(),
    )
    try:
        importer._prepare_boundary_index()
        tiles = GpkgTilePlanner(info, candidate_limit=5000).plan()
        assert len(tiles) == 1
        importer.process_tiles(tiles)
        batch = next(importer.batch_root.glob("*.parquet"))
        regions = importer.connection.execute(
            "select distinct region_code from read_parquet(?) order by region_code",
            [str(batch)],
        ).fetchall()
        assert regions == [("01",), ("02",)]
    finally:
        importer.connection.close()


def _synthetic_sources(tmp_path: Path) -> tuple[Path, Path]:
    connection = duckdb.connect()
    connection.execute("load spatial")
    gpkg = tmp_path / "buildings.gpkg"
    connection.execute(
        f"""
        copy (
            select
                id::integer as building_outline_id,
                (id + 100)::integer as building_id,
                null::varchar as name,
                null::varchar as use,
                'manual'::varchar as capture_method,
                'test'::varchar as capture_source_group,
                1::integer as capture_source_id,
                'fixture'::varchar as capture_source_name,
                date '2020-01-01' as capture_source_from,
                date '2020-12-31' as capture_source_to,
                'current'::varchar as building_outline_lifecycle,
                date '2020-01-01' as begin_lifespan,
                null::date as end_lifespan,
                date '2024-01-01' as last_modified,
                st_geomfromtext(wkt) as geom
            from (values
                (1, 'POLYGON ((0.10 0.10, 0.40 0.10, 0.40 0.40, 0.10 0.40, 0.10 0.10))'),
                (2, 'POLYGON ((0.80 0.40, 1.40 0.40, 1.40 0.60, 0.80 0.60, 0.80 0.40))'),
                (3, 'POLYGON ((1.60 0.60, 1.90 0.60, 1.90 0.90, 1.60 0.90, 1.60 0.60))')
            ) source(id, wkt)
        ) to '{gpkg.as_posix()}' with (
            format gdal, driver 'GPKG', layer_name 'buildings'
        )
        """
    )
    boundaries = tmp_path / "boundaries.parquet"
    connection.execute(
        f"""
        copy (
            select
                meshblock_code, sa1_code, sa2_code, sa2_name,
                region_code, region_name,
                'TA'::varchar as territorial_authority_code,
                'Test TA'::varchar as territorial_authority_name,
                '12'::varchar as land_water,
                'Land'::varchar as land_water_name,
                cast(st_aswkb(st_geomfromtext(wkt)) as blob) as geometry_wkb
            from (values
                ('mb-left', 'sa1-left', 'sa2-left', 'Left', '01', 'Region One',
                 'POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))'),
                ('mb-right', 'sa1-right', 'sa2-right', 'Right', '02', 'Region Two',
                 'POLYGON ((1 0, 2 0, 2 1, 1 1, 1 0))')
            ) boundary(meshblock_code, sa1_code, sa2_code, sa2_name,
                       region_code, region_name, wkt)
        ) to '{boundaries.as_posix()}' (format parquet)
        """
    )
    connection.close()
    return gpkg, boundaries


def _gpkg_info(path: Path) -> GpkgInfo:
    connection = duckdb.connect()
    connection.execute("load spatial")
    extent = connection.execute(
        f"""
        select min(st_xmin(geom)), min(st_ymin(geom)),
               max(st_xmax(geom)), max(st_ymax(geom)), count(*)
        from st_read('{path.as_posix()}', layer='buildings')
        """
    ).fetchone()
    connection.close()
    return GpkgInfo(
        path,
        "buildings",
        "geom",
        4326,
        int(extent[4]),
        int(extent[4]),
        0,
        float(extent[0]),
        float(extent[1]),
        float(extent[2]),
        float(extent[3]),
        True,
        "2026-05-18",
    )
