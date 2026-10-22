from __future__ import annotations

import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
EXTENSIONS = ROOT / "app" / "vendor" / "duckdb_extensions"


def main() -> None:
    connection = duckdb.connect()
    connection.execute("SET autoinstall_known_extensions=false")
    connection.execute("SET autoload_known_extensions=false")
    for name in ("azure", "httpfs", "spatial", "h3"):
        path = (EXTENSIONS / f"{name}.duckdb_extension").as_posix()
        connection.execute(f"LOAD '{path}'")

    cell = connection.execute("SELECT h3_latlng_to_cell(-41.2865, 174.7762, 8)").fetchone()[0]
    expected = 615782128600219647
    if cell != expected:
        raise RuntimeError(f"Unexpected H3 cell: {cell}")
    print(json.dumps({"h3_latlng_to_cell": cell, "offline_load": True}))


if __name__ == "__main__":
    main()
