"""Run the complete Snowflake dbt build with an explicit warehouse shutdown."""

from __future__ import annotations

import os
import subprocess

try:
    from .auth import assert_warehouse_guard, suspend_warehouse
    from .benchmark import OUTPUT, ROOT, command
    from .env import load_local_env
except ImportError:
    from auth import assert_warehouse_guard, suspend_warehouse
    from benchmark import OUTPUT, ROOT, command
    from env import load_local_env


def main() -> None:
    load_local_env()
    assert_warehouse_guard()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["SNOWFLAKE_SCHEMA"] = "BENCHMARK_FULL"
    env["SNOWFLAKE_QUERY_TAG"] = "nzhem_m7_validate"
    args = command("full")
    args[1] = "build"
    log = OUTPUT / "dbt-build.log"
    try:
        with log.open("w", encoding="utf-8") as stream:
            result = subprocess.run(
                args, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT
            )
    finally:
        suspend_warehouse()
    if result.returncode:
        raise RuntimeError(f"Snowflake dbt build failed; inspect ignored {log}")
    print(f"Snowflake dbt build passed; detailed output in ignored {log}")


if __name__ == "__main__":
    main()
