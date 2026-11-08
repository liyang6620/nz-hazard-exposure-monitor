"""PUT bounded local curated Parquet files into an internal Snowflake stage."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import duckdb

try:
    from .auth import assert_warehouse_guard, connect, suspend_warehouse
except ImportError:
    from auth import assert_warehouse_guard, connect, suspend_warehouse

ROOT = Path(__file__).resolve().parents[2]
DATASETS = {
    "int_buildings_h3": "reference-export/dee5b263952e/int_buildings_h3/region=*/*.parquet",
    "stg_stats__population": "reference/stg_stats__population/*.parquet",
    "stg_stats__boundaries": "reference/stg_stats__boundaries/*.parquet",
    "int_population_h3": "reference-export/dee5b263952e/int_population_h3.parquet",
    "dim_region": "reference-export/dee5b263952e/dim_region.parquet",
    "dim_h3_cell": "reference-export/dee5b263952e/dim_h3_cell.parquet",
    "dim_event": "events/m3/dim_event.parquet",
    "int_event_shaking_h3": "events/m3/int_event_shaking_h3.parquet",
    "fct_event_exposure_cell": "events/m3/fct_event_exposure_cell.parquet",
    "mart_mmi_validation": "events/m3/mart_mmi_validation.parquet",
}
STAGE = "NZHEM_BENCHMARK.CURATED.LOCAL_PARQUET"
FORMAT = "NZHEM_BENCHMARK.CURATED.PARQUET_FORMAT"


def files_for(root: Path, name: str) -> list[Path]:
    files = sorted(root.glob(DATASETS[name]))
    if not files or any(not path.is_file() for path in files):
        raise FileNotFoundError(f"Missing curated Parquet for {name}")
    return files


def validate_schemas(selected: dict[str, list[Path]]) -> None:
    with duckdb.connect(":memory:") as database:
        database.execute("SET memory_limit = '512MB'")
        for name, paths in selected.items():
            expected = None
            for path in paths:
                columns = database.execute(
                    "DESCRIBE SELECT * FROM read_parquet(?, hive_partitioning=false)",
                    [str(path)],
                ).fetchall()
                schema = [(column, dtype) for column, dtype, *_ in columns]
                if expected is None:
                    expected = schema
                elif schema != expected:
                    raise ValueError(f"Parquet schema differs within {name}: {path.name}")


def snowflake_type(duck_type: str) -> str:
    if duck_type in {"UBIGINT", "BIGINT", "INTEGER", "SMALLINT"}:
        return "NUMBER(20,0)"
    if duck_type in {"DOUBLE", "FLOAT", "REAL"}:
        return "FLOAT"
    if duck_type in {"BOOLEAN", "DATE"}:
        return duck_type
    if duck_type == "BLOB":
        return "BINARY"
    if duck_type == "TIMESTAMP WITH TIME ZONE":
        return "TIMESTAMP_TZ"
    if duck_type.startswith("TIMESTAMP"):
        return "TIMESTAMP_NTZ"
    if duck_type.startswith("VARCHAR"):
        return "VARCHAR"
    raise ValueError(f"Unmapped Parquet type: {duck_type}")


def table_ddl(name: str, file: Path) -> str:
    with duckdb.connect(":memory:") as database:
        database.execute("SET memory_limit = '512MB'")
        columns = database.execute(
            "DESCRIBE SELECT * FROM read_parquet(?, hive_partitioning=false)", [str(file)]
        ).fetchall()
    if any(not re.fullmatch(r"[a-z][a-z0-9_]*", column) for column, *_ in columns):
        raise ValueError(f"Unexpected Parquet column name in {name}")
    declarations = ", ".join(
        f"{column.upper()} {snowflake_type(dtype)}" for column, dtype, *_ in columns
    )
    return f"CREATE OR REPLACE TABLE NZHEM_BENCHMARK.CURATED.{name.upper()} ({declarations})"


def put_sql(name: str, path: Path, root: Path) -> str:
    path.relative_to(root)
    partition = path.parent.name.replace("=", "_")
    destination = f"@{STAGE}/{name}/{partition}/"
    local_uri = ("file://" + path.resolve().as_posix()).replace("'", "''")
    return f"PUT '{local_uri}' {destination} AUTO_COMPRESS=FALSE OVERWRITE=TRUE"


def load(root: Path, *, execute: bool, start_at: str | None = None) -> dict[str, object]:
    names = list(DATASETS)
    if start_at is not None:
        if start_at not in DATASETS:
            raise ValueError("Unknown curated table for resume")
        names = names[names.index(start_at) :]
    selected = {name: files_for(root, name) for name in names}
    validate_schemas(selected)
    result: dict[str, object] = {
        "tables": len(selected),
        "files": sum(len(paths) for paths in selected.values()),
        "bytes": sum(path.stat().st_size for paths in selected.values() for path in paths),
    }
    if not execute:
        return result
    assert_warehouse_guard()
    try:
        with connect() as connection, connection.cursor() as cursor:
            for name, paths in selected.items():
                cursor.execute(table_ddl(name, paths[0]))
                cursor.execute(f"REMOVE @{STAGE}/{name}/")
                for path in paths:
                    cursor.execute(put_sql(name, path, root))
                cursor.execute(
                    f"COPY INTO NZHEM_BENCHMARK.CURATED.{name.upper()} "
                    f"FROM @{STAGE}/{name}/ "
                    f"FILE_FORMAT=(FORMAT_NAME={FORMAT}) "
                    "MATCH_BY_COLUMN_NAME=CASE_INSENSITIVE ON_ERROR=ABORT_STATEMENT"
                )
                cursor.execute(f"SELECT COUNT(*) FROM NZHEM_BENCHMARK.CURATED.{name.upper()}")
                result[name] = cursor.fetchone()[0]
    finally:
        suspend_warehouse()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--curated-root", type=Path, default=ROOT / ".local/data/curated")
    parser.add_argument(
        "--execute", action="store_true", help="Upload and COPY; omitted for offline inventory"
    )
    parser.add_argument("--start-at", choices=tuple(DATASETS), help="Resume at this table")
    args = parser.parse_args()
    result = load(args.curated_root.resolve(), execute=args.execute, start_at=args.start_at)
    for name, value in result.items():
        print(f"{name}: {value}")


if __name__ == "__main__":
    main()
