"""Timed dbt rebuilds; credit estimates are labelled until metering is available."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

try:
    from .env import load_local_env
    from .reconcile import reconcile
except ImportError:
    from env import load_local_env
    from reconcile import reconcile

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".local/snowflake"
KAIKOURA_ID = "2016p858000"
SINGLE_MODELS = (
    "dim_event",
    "int_event_shaking_h3",
    "fct_event_exposure_cell",
    "mart_event_summary",
    "mart_event_exposure_h3r6",
    "mart_accumulation_cell",
    "mart_mmi_validation",
)


def command(mode: str) -> list[str]:
    local_executable = ROOT / ".venv/Scripts/dbt.exe"
    executable = str(local_executable) if local_executable.exists() else shutil.which("dbt")
    if executable is None:
        raise FileNotFoundError("Install benchmark/snowflake/requirements.txt first")
    base = [
        executable,
        "run",
        "--project-dir",
        str(ROOT / "dbt"),
        "--profiles-dir",
        str(ROOT / "dbt/profiles"),
        "--target",
        "snowflake_benchmark",
        "--full-refresh",
    ]
    if mode == "single":
        base += [
            "--select",
            *SINGLE_MODELS,
            "--vars",
            json.dumps({"benchmark_event_id": KAIKOURA_ID}),
        ]
    return base


def execute(mode: str) -> dict[str, object]:
    schema = "BENCHMARK_FULL" if mode == "full" else "BENCHMARK_SINGLE"
    env = os.environ.copy()
    env["SNOWFLAKE_SCHEMA"] = schema
    env["SNOWFLAKE_QUERY_TAG"] = f"nzhem_m7_{mode}"
    started = datetime.now(UTC)
    clock = time.monotonic()
    log = OUTPUT / f"dbt-{mode}.log"
    with log.open("w", encoding="utf-8") as stream:
        process = subprocess.run(
            command(mode), cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT
        )
    elapsed = time.monotonic() - clock
    if process.returncode:
        raise RuntimeError(f"dbt {mode} failed; inspect ignored {log}")
    counts = reconcile(
        ROOT / ".local/data/curated",
        schema=schema,
        event_id=KAIKOURA_ID if mode == "single" else None,
    )
    return {
        "mode": mode,
        "started_at_utc": started.isoformat(),
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "elapsed_seconds": round(elapsed, 3),
        "xs_compute_credit_estimate": round(max(elapsed, 60) / 3600, 6),
        "credits_status": (
            "estimate only; replace with Snowflake metered credits after billing delay"
        ),
        "reconciled_rows": counts,
    }


def main() -> None:
    load_local_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    for mode in ("full", "single"):
        print(f"{mode}: {' '.join(command(mode))}")
    if not args.execute:
        print("Offline plan only; no Snowflake connection was made")
        return
    OUTPUT.mkdir(parents=True, exist_ok=True)
    results = [execute("full"), execute("single")]
    output = OUTPUT / "benchmark-results.json"
    output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"Reconciled both runs; measurements saved to ignored {output}")


if __name__ == "__main__":
    main()
