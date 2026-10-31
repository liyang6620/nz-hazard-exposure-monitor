from __future__ import annotations

import os
from pathlib import Path

import duckdb


def load_extension(connection: duckdb.DuckDBPyConnection, name: str) -> None:
    directory = os.getenv("NZHEM_DUCKDB_EXTENSIONS_DIR", "").strip()
    if directory:
        path = Path(directory, f"{name}.duckdb_extension").resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        connection.execute("set autoinstall_known_extensions=false")
        connection.execute("set autoload_known_extensions=false")
        escaped_path = path.as_posix().replace("'", "''")
        connection.execute(f"load '{escaped_path}'")
    else:
        connection.execute(f"load {name}")
