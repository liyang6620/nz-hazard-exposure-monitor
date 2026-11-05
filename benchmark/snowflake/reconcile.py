"""Compare local curated Parquet with Snowflake tables before accepting a run."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import duckdb

try:
    from .auth import connect
    from .load_curated import DATASETS
except ImportError:
    from auth import connect
    from load_curated import DATASETS

ROOT = Path(__file__).resolve().parents[2]
MARTS = {
    "fct_event_exposure_cell": "events/m3/fct_event_exposure_cell.parquet",
    "mart_event_summary": "events/m3/mart_event_summary.parquet",
    "mart_event_exposure_h3r6": "events/m3/mart_event_exposure_h3r6.parquet",
    "mart_accumulation_cell": "events/m3/mart_accumulation_cell.parquet",
}
SUM_COLUMNS = {
    "fct_event_exposure_cell": (
        "EVENT_BUILDING_COUNT",
        "AS_IF_TODAY_BUILDING_COUNT",
        "POPULATION_2023",
    ),
    "mart_event_summary": (
        "BUILDINGS_MMI_GE_6",
        "EVENT_TIME_BUILDINGS_MMI_GE_6",
        "FOOTPRINT_M2_MMI_GE_6",
        "POPULATION_MMI_GE_6",
    ),
    "mart_event_exposure_h3r6": (
        "EVENT_BUILDING_COUNT",
        "EVENT_FOOTPRINT_AREA_M2",
        "AS_IF_TODAY_BUILDING_COUNT",
        "AS_IF_TODAY_FOOTPRINT_AREA_M2",
        "POPULATION_2023",
    ),
    "mart_accumulation_cell": ("STRONG_EVENT_COUNT", "ACCUMULATION_SCORE"),
}
TOLERANCE = 1e-6


def require_equal_count(name: str, local_count: int, remote_count: int) -> None:
    if local_count != remote_count:
        raise AssertionError(f"{name}: row count {local_count} != {remote_count}")


def require_equal_sum(name: str, column: str, local_value: object, remote_value: object) -> None:
    a = float(local_value or 0)
    b = float(remote_value or 0)
    if not math.isfinite(a) or not math.isfinite(b) or abs(a - b) >= TOLERANCE:
        raise AssertionError(f"{name}.{column}: aggregate difference >= {TOLERANCE}")


def require_equal_mmi(local_rows: list[tuple], remote_rows: list[tuple]) -> None:
    require_equal_count("per-grid MMI", len(local_rows), len(remote_rows))
    for local, remote in zip(local_rows, remote_rows, strict=True):
        if local[:2] != remote[:2] or local[2] != remote[2]:
            raise AssertionError(f"Per-grid MMI differs at {local[:2]}")


def parquet_query(database: duckdb.DuckDBPyConnection, path: Path, sql: str):
    quoted = str(path).replace("'", "''").replace("\\", "/")
    return database.execute(sql.replace("{parquet}", f"read_parquet('{quoted}')"))


def reconcile(root: Path, *, schema: str, event_id: str | None = None) -> dict[str, int]:
    if schema not in {"BENCHMARK_FULL", "BENCHMARK_SINGLE"}:
        raise ValueError("Unexpected benchmark schema")
    if event_id and (not event_id.isalnum() or len(event_id) > 32):
        raise ValueError("Invalid event ID")
    result: dict[str, int] = {}
    with duckdb.connect(":memory:") as local, connect() as remote:
        local.execute("SET memory_limit = '512MB'")
        with remote.cursor() as cursor:
            if event_id is None:
                for name, pattern in DATASETS.items():
                    path = root / pattern
                    count = parquet_query(local, path, "SELECT COUNT(*) FROM {parquet}").fetchone()[
                        0
                    ]
                    cursor.execute(f"SELECT COUNT(*) FROM NZHEM_BENCHMARK.CURATED.{name.upper()}")
                    require_equal_count(name, count, cursor.fetchone()[0])
                    result[name] = count
            for name, pattern in MARTS.items():
                if event_id and name == "mart_accumulation_cell":
                    continue
                path = root / pattern
                where = f" WHERE event_id = '{event_id}'" if event_id else ""
                count = parquet_query(
                    local, path, "SELECT COUNT(*) FROM {parquet}" + where
                ).fetchone()[0]
                cursor.execute(
                    f"SELECT COUNT(*) FROM NZHEM_BENCHMARK.{schema}.{name.upper()}" + where
                )
                require_equal_count(name, count, cursor.fetchone()[0])
                result[name] = count
                for column in SUM_COLUMNS[name]:
                    query = f"SELECT SUM({column}) FROM {{parquet}}" + where
                    local_sum = parquet_query(local, path, query).fetchone()[0]
                    cursor.execute(
                        f"SELECT SUM({column}) FROM NZHEM_BENCHMARK.{schema}.{name.upper()}" + where
                    )
                    require_equal_sum(name, column, local_sum, cursor.fetchone()[0])
            for name, grid_column in (
                ("fct_event_exposure_cell", "h3_res8"),
                ("mart_event_exposure_h3r6", "h3_res6"),
            ):
                path = root / MARTS[name]
                sql = (
                    f"SELECT event_id, {grid_column}, mmi FROM {{parquet}}"
                    + (f" WHERE event_id = '{event_id}'" if event_id else "")
                    + f" ORDER BY event_id, {grid_column}"
                )
                local_rows = parquet_query(local, path, sql).fetchall()
                cursor.execute(
                    f"SELECT EVENT_ID, {grid_column.upper()}, MMI FROM "
                    f"NZHEM_BENCHMARK.{schema}.{name.upper()}"
                    + (f" WHERE EVENT_ID = '{event_id}'" if event_id else "")
                    + f" ORDER BY EVENT_ID, {grid_column.upper()}"
                )
                require_equal_mmi(local_rows, cursor.fetchall())
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--curated-root", type=Path, default=ROOT / ".local/data/curated")
    parser.add_argument("--schema", choices=["BENCHMARK_FULL", "BENCHMARK_SINGLE"], required=True)
    parser.add_argument("--event-id")
    args = parser.parse_args()
    results = reconcile(args.curated_root, schema=args.schema, event_id=args.event_id)
    print("Reconciliation passed: exact row counts and grid MMI; aggregate error < 1e-6")
    for name, count in results.items():
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()
