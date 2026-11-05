"""Build a bounded, local-only Power BI import snapshot from M3 gold outputs."""

# ruff: noqa: E501  -- SQL expressions are kept readable in one piece.

from __future__ import annotations

import argparse
import json
import math
import shutil
import sqlite3
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import requests

ROOT = Path(__file__).resolve().parents[1]
M3 = ROOT / ".local/data/curated/events/m3"
REFERENCE = ROOT / ".local/data/curated/reference-export/dee5b263952e"
OUTPUT = ROOT / ".local/data/powerbi"
MIN_FREE_BYTES = 20 * 1024**3
AZURE_GOLD = ROOT / ".local/data/powerbi-azure/gold"
PUBLIC_SITE = "https://stnzhem8495b7ca.z8.web.core.windows.net"
GOLD_FILES = (
    "dim_event.parquet",
    "fct_event_exposure_cell.parquet",
    "mart_accumulation_cell.parquet",
    "mart_event_exposure_h3r6.parquet",
    "mart_event_summary.parquet",
    "mart_mmi_validation.parquet",
)


def sql_path(path: Path) -> str:
    return str(path).replace("\\", "/").replace("'", "''")


def export(connection: duckdb.DuckDBPyConnection, name: str, query: str) -> int:
    destination = OUTPUT / f"{name}.parquet"
    connection.execute(
        f"COPY ({query}) TO '{sql_path(destination)}' (FORMAT PARQUET, COMPRESSION ZSTD)"
    )
    return connection.execute(
        f"SELECT count(*) FROM read_parquet('{sql_path(destination)}')"
    ).fetchone()[0]


def utc_naive(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Run timestamp must include a timezone")
    return parsed.astimezone(UTC).replace(tzinfo=None)


def latest_taumarunui_magnitude() -> float | None:
    generations = ROOT / ".local/data/web/data/generations"
    candidates = sorted(generations.glob("*/replays/2026p776286/summary.json"), reverse=True)
    for summary_path in candidates:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        magnitude = summary.get("magnitude")
        if (
            summary.get("event_id") == "2026p776286"
            and isinstance(magnitude, int | float)
            and math.isfinite(magnitude)
        ):
            return round(float(magnitude), 1)
    return None


def azure_snapshot() -> tuple[Path, list[dict[str, object]], int, list[dict[str, object]]]:
    from azure.data.tables import TableServiceClient
    from azure.identity import AzureCliCredential
    from azure.storage.blob import BlobServiceClient
    from azure.storage.queue import QueueServiceClient

    result = subprocess.run(
        ["terraform", "-chdir=infra/terraform", "output", "-raw", "storage_account_name"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    account = result.stdout.strip()
    if not account or not account.isalnum():
        raise RuntimeError("Azure data account output is unavailable")
    credential = AzureCliCredential()
    blob = BlobServiceClient(f"https://{account}.blob.core.windows.net", credential)
    AZURE_GOLD.mkdir(parents=True, exist_ok=True)
    for filename in GOLD_FILES:
        source = blob.get_blob_client("gold", f"events/m3/{filename}")
        if source.get_blob_properties().size > 32 * 1024**2:
            raise RuntimeError(f"Power BI source exceeds 32 MiB: {filename}")
        destination = AZURE_GOLD / filename
        with destination.open("wb") as output:
            source.download_blob(max_concurrency=1).readinto(output)
    table = TableServiceClient(f"https://{account}.table.core.windows.net", credential=credential)
    runs = [
        dict(row)
        for row in table.get_table_client("runs").query_entities(
            query_filter="PartitionKey eq 'housekeeping'"
        )
    ]
    queue = QueueServiceClient(f"https://{account}.queue.core.windows.net", credential)
    poison = int(
        queue.get_queue_client("events-poison").get_queue_properties().approximate_message_count
        or 0
    )
    manifest = requests.get(f"{PUBLIC_SITE}/data/manifest.json", timeout=15)
    manifest.raise_for_status()
    base_path = manifest.json()["base_path"]
    if not base_path.startswith("/data/generations/"):
        raise RuntimeError("Unexpected public data generation path")
    response = requests.get(f"{PUBLIC_SITE}{base_path}/events.json", timeout=15)
    response.raise_for_status()
    events = response.json()
    if not isinstance(events, list):
        raise RuntimeError("Public event index has an unexpected shape")
    return AZURE_GOLD, runs, poison, events


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--azure", action="store_true", help="read-only Azure gold and run snapshot"
    )
    args = parser.parse_args()
    if shutil.disk_usage(ROOT).free < MIN_FREE_BYTES + 1024**3:
        raise RuntimeError("C: free space is too close to the 20 GiB floor")
    m3_root, cloud_runs, poison_count, cloud_events = (
        azure_snapshot() if args.azure else (M3, [], 0, [])
    )
    for path in (m3_root / "mart_event_summary.parquet", REFERENCE / "dim_h3_cell.parquet"):
        if not path.exists():
            raise FileNotFoundError(path)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("SET memory_limit='512MB'")
    con.execute("SET threads=1")
    con.execute("SET TimeZone='Pacific/Auckland'")
    con.execute(f"SET temp_directory='{sql_path(OUTPUT / 'tmp')}'")
    m3 = sql_path(m3_root)
    ref = sql_path(REFERENCE)
    counts: dict[str, int] = {}
    revised_magnitude = latest_taumarunui_magnitude()
    magnitude_expression = (
        f"CASE WHEN event_id = '2026p776286' THEN {revised_magnitude} ELSE magnitude END"
        if revised_magnitude is not None
        else "magnitude"
    )

    # Cell ownership uses the same majority-building convention as the public site.
    counts["cell_owner"] = export(
        con,
        "cell_owner",
        f"""
        WITH owners AS (
            SELECT h3_res8, region_code, region_name,
                   territorial_authority_code AS ta_code,
                   territorial_authority_name AS ta_name,
                   count(*) AS buildings
            FROM read_parquet('{ref}/int_buildings_h3/region=*/*.parquet')
            WHERE lifecycle = 'Current'
            GROUP BY ALL
        )
        SELECT h3_res8, region_code, region_name, ta_code, ta_name
        FROM owners
        QUALIFY row_number() OVER (
            PARTITION BY h3_res8 ORDER BY buildings DESC, region_code, ta_code
        ) = 1
    """,
    )
    owner = sql_path(OUTPUT / "cell_owner.parquet")
    counts["dim_region"] = export(
        con,
        "dim_region",
        f"""
        SELECT coalesce(region_code, 'unknown') || ':' || coalesce(ta_code, 'unknown') AS region_key,
               coalesce(region_name, 'Outside mapped regions') AS region_name,
               replace(coalesce(ta_name, 'Outside mapped authorities'), 'Kaikoura', 'Kaikōura') AS territorial_authority,
               sum(buildings)::BIGINT AS region_buildings
        FROM (
            SELECT region_code, region_name, territorial_authority_code AS ta_code,
                   territorial_authority_name AS ta_name, count(*) AS buildings
            FROM read_parquet('{ref}/int_buildings_h3/region=*/*.parquet')
            WHERE lifecycle = 'Current'
            GROUP BY ALL
        )
        GROUP BY ALL
        UNION ALL
        SELECT 'unknown:unknown', 'Outside mapped regions',
               'Outside mapped authorities', 0::BIGINT
    """,
    )
    counts["dim_event"] = export(
        con,
        "dim_event",
        f"""
        SELECT event_id,
               CASE event_id
                   WHEN '3366146' THEN 'Darfield, 2010'
                   WHEN '3468575' THEN 'Christchurch, Feb 2011'
                   WHEN '3528839' THEN 'Christchurch, Jun 2011'
                   WHEN '2013p543824' THEN 'Cook Strait, 2013'
                   WHEN '2013p613797' THEN 'Lake Grassmere, 2013'
                   WHEN '2014p051675' THEN 'Eketāhuna, 2014'
                   WHEN '2016p661332' THEN 'East Cape, 2016'
                   WHEN '2016p858000' THEN 'Kaikōura, 2016'
                   WHEN '2021p169764' THEN 'Kermadec Islands, 2021'
                   WHEN '2026p776286' THEN 'Taumarunui, Oct 2026'
                   ELSE event_name END AS event_name,
               CAST(origin_time AS DATE) AS event_date,
               CAST(day(origin_time) AS VARCHAR) || ' ' || strftime(origin_time, '%b %Y') AS event_date_label,
               origin_time,
               strftime(origin_time, '%Y-%m-%d %H:%M') ||
                 CASE WHEN strftime(origin_time, '%z') IN ('+13', '+1300')
                      THEN ' NZDT' ELSE ' NZST' END
                 AS origin_time_label,
               year(origin_time) + (dayofyear(origin_time) - 1) / 366.0 AS timeline_year,
               {magnitude_expression} AS magnitude,
               depth_km,
               mmi_source, shaking_version,
               'As-if-today' AS exposure_basis
        FROM read_parquet('{m3}/mart_event_summary.parquet')
    """,
    )
    counts["fct_event_summary"] = export(
        con,
        "fct_event_summary",
        f"""
        SELECT event_id, CAST(origin_time AS DATE) AS event_date,
               max_mmi, buildings_mmi_ge_6, population_mmi_ge_6,
               footprint_m2_mmi_ge_6, validation_station_count, validation_mae
        FROM read_parquet('{m3}/mart_event_summary.parquet')
    """,
    )
    counts["dim_date"] = export(
        con,
        "dim_date",
        """
        SELECT date_value::DATE AS date_value,
               year(date_value)::INTEGER AS year,
               month(date_value)::INTEGER AS month_number,
               strftime(date_value, '%b %Y') AS month_label
        FROM generate_series(DATE '2010-01-01', DATE '2030-12-31', INTERVAL 1 DAY) AS d(date_value)
    """,
    )
    counts["dim_mmi_band"] = export(
        con,
        "dim_mmi_band",
        """
        SELECT * FROM (VALUES (4, 'MMI 4', 4), (5, 'MMI 5', 5),
                              (6, 'MMI 6', 6), (7, 'MMI 7', 7),
                              (8, 'MMI 8+', 8)) AS t(band_key, band_label, minimum_mmi)
    """,
    )
    counts["mmi_threshold"] = export(
        con,
        "mmi_threshold",
        """
        SELECT value AS threshold FROM generate_series(4, 8) AS t(value)
    """,
    )
    counts["fct_exposure"] = export(
        con,
        "fct_exposure",
        f"""
        SELECT e.event_id,
               coalesce(o.region_code, 'unknown') || ':' || coalesce(o.ta_code, 'unknown') AS region_key,
               least(floor(e.mmi)::INTEGER, 8) AS band_key,
               sum(e.as_if_today_building_count)::BIGINT AS buildings,
               sum(e.as_if_today_footprint_area_m2) AS footprint_m2,
               sum(e.population_2023) AS people
        FROM read_parquet('{m3}/fct_event_exposure_cell.parquet') e
        LEFT JOIN read_parquet('{owner}') o USING (h3_res8)
        WHERE e.mmi >= 4
        GROUP BY ALL
    """,
    )
    counts["fct_map"] = export(
        con,
        "fct_map",
        f"""
        WITH centres AS (
            SELECT h3_res6, avg(centre_latitude) AS latitude,
                   avg(centre_longitude) AS longitude
            FROM read_parquet('{ref}/dim_h3_cell.parquet') GROUP BY h3_res6
        )
        SELECT e.event_id, e.h3_res6::VARCHAR AS h3_cell,
               least(floor(e.mmi)::INTEGER, 8) AS band_key,
               round(e.mmi, 1) AS mmi, e.as_if_today_building_count AS buildings,
               e.population_2023 AS people, c.latitude, c.longitude
        FROM read_parquet('{m3}/mart_event_exposure_h3r6.parquet') e
        JOIN centres c USING (h3_res6)
        WHERE e.mmi >= 4 AND (e.as_if_today_building_count > 0 OR e.population_2023 > 0)
    """,
    )
    counts["fct_accumulation"] = export(
        con,
        "fct_accumulation",
        f"""
        SELECT coalesce(o.region_code, 'unknown') || ':' || coalesce(o.ta_code, 'unknown') AS region_key,
               sum(a.accumulation_score)::BIGINT AS accumulation_score,
               sum(CASE WHEN a.strong_event_count > 0 THEN a.current_building_count ELSE 0 END)::BIGINT
                   AS buildings_in_strong_cells,
               max(a.strong_event_count)::INTEGER AS maximum_strong_events,
               avg(c.centre_latitude) AS latitude,
               avg(c.centre_longitude) AS longitude
        FROM read_parquet('{m3}/mart_accumulation_cell.parquet') a
        LEFT JOIN read_parquet('{owner}') o USING (h3_res8)
        LEFT JOIN read_parquet('{ref}/dim_h3_cell.parquet') c USING (h3_res8)
        GROUP BY 1
    """,
    )
    counts["fct_validation"] = export(
        con,
        "fct_validation",
        f"""
        SELECT event_id, station_id, observed_mmi, estimated_mmi,
               abs(observed_mmi - estimated_mmi) AS absolute_error
        FROM read_parquet('{m3}/mart_mmi_validation.parquet')
        WHERE exclusion_reason IS NULL AND observed_mmi IS NOT NULL
          AND estimated_mmi IS NOT NULL
    """,
    )

    state = ROOT / ".local/state/nzhem.sqlite3"
    runs: list[dict[str, object]] = cloud_runs
    if not args.azure and state.exists():
        with sqlite3.connect(f"file:{state.as_posix()}?mode=ro", uri=True) as db:
            for (payload,) in db.execute(
                "SELECT payload FROM table_entities WHERE table_name = 'runs'"
            ):
                run = json.loads(payload)
                if run.get("PartitionKey") == "housekeeping":
                    runs.append(run)
    successful = [
        r["completed_at"] for r in runs if r.get("status") == "success" and r.get("completed_at")
    ]
    failed = sum(r.get("status") != "success" for r in runs)
    now = datetime.now(UTC).replace(tzinfo=None)
    last_run = max((utc_naive(value) for value in successful), default=None)
    health = OUTPUT / "fct_health.parquet"
    con.execute(
        "COPY (SELECT ?::TIMESTAMP AS snapshot_at, ?::TIMESTAMP AS last_successful_run, "
        "?::INTEGER AS failed_runs, ?::INTEGER AS recorded_runs, "
        "?::INTEGER AS poison_messages, ? AS scope) TO '" + sql_path(health) + "' (FORMAT PARQUET)",
        [
            now,
            last_run,
            failed,
            len(runs),
            poison_count,
            "Azure gold, runs and public event index" if args.azure else "Local SQLite snapshot",
        ],
    )
    counts["fct_health"] = 1
    statuses: dict[str, int] = {}
    sources: dict[str, int] = {}
    for event in cloud_events:
        if not event.get("is_recent_monitoring"):
            continue
        status = str(event.get("assessment_status") or "unknown")
        status = {"outside_model_range": "Outside range"}.get(
            status, status.replace("_", " ").title()
        )
        source = str(event.get("mmi_source") or "unavailable").replace("_", " ").title()
        statuses[status] = statuses.get(status, 0) + 1
        sources[source] = sources.get(source, 0) + 1
    for table_name, column, values in (
        ("fct_status", "assessment_status", statuses),
        ("fct_source", "shaking_source", sources),
    ):
        rows = [(key, value) for key, value in sorted(values.items())] or [("No cloud data", 0)]
        con.execute(
            f"COPY (SELECT col0 AS {column}, col1::INTEGER AS event_count "
            f"FROM (VALUES {', '.join(['(?, ?)'] * len(rows))})) "
            f"TO '{sql_path(OUTPUT / (table_name + '.parquet'))}' (FORMAT PARQUET)",
            [item for row in rows for item in row],
        )
        counts[table_name] = len(rows)
    counts.pop("cell_owner")
    (OUTPUT / "snapshot.json").write_text(
        json.dumps(
            {
                "created_at": now.replace(tzinfo=UTC).isoformat(),
                "source": "Azure gold and runtime"
                if args.azure
                else "M3 local gold and reference export",
                "rows": counts,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    if shutil.disk_usage(ROOT).free < MIN_FREE_BYTES:
        raise RuntimeError("C: free space fell below 20 GiB")
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
