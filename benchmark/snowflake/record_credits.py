"""Attach delayed Snowflake per-query credit attribution to local results."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / ".local/snowflake/benchmark-results.json"


def nonnegative_credits(raw: str) -> str:
    try:
        value = Decimal(raw)
    except InvalidOperation as error:
        raise ValueError("Credits must be numeric") from error
    if not value.is_finite() or value < 0:
        raise ValueError("Credits must be finite and nonnegative")
    return str(value)


def record(path: Path, full: str, single: str) -> None:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if [row["mode"] for row in rows] != ["full", "single"]:
        raise ValueError("Expected completed full and single benchmark results")
    for row, credits in zip(rows, (full, single), strict=True):
        row["metered_compute_credits"] = nonnegative_credits(credits)
        row["credits_status"] = "Snowflake QUERY_ATTRIBUTION_HISTORY, measured after usage delay"
    path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", required=True, help="Metered full-run compute credits")
    parser.add_argument("--single", required=True, help="Metered single-event compute credits")
    args = parser.parse_args()
    record(RESULTS, args.full, args.single)
    print(f"Recorded metered credits in ignored {RESULTS}")


if __name__ == "__main__":
    main()
