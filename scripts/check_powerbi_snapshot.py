"""Reconcile the local Power BI snapshot to published M3 gold summaries."""

from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / ".local/data/powerbi"
M3 = ROOT / ".local/data/curated/events/m3"


def main() -> None:
    con = duckdb.connect()
    con.execute("SET memory_limit='512MB'")
    con.execute("SET threads=1")
    rows = con.execute(
        """
        SELECT s.event_id, s.buildings_mmi_ge_6 AS gold_buildings,
               coalesce(sum(e.buildings), 0) AS bi_buildings,
               s.population_mmi_ge_6 AS gold_people,
               coalesce(sum(e.people), 0) AS bi_people
        FROM read_parquet(?) s
        LEFT JOIN read_parquet(?) e
          ON s.event_id = e.event_id AND e.band_key >= 6
        GROUP BY s.event_id, s.buildings_mmi_ge_6, s.population_mmi_ge_6
        ORDER BY s.event_id
        """,
        [str(M3 / "mart_event_summary.parquet"), str(SNAPSHOT / "fct_exposure.parquet")],
    ).fetchall()
    assert len(rows) == 10
    for event_id, gold_buildings, bi_buildings, gold_people, bi_people in rows:
        assert gold_buildings == bi_buildings, (event_id, gold_buildings, bi_buildings)
        assert abs(gold_people - bi_people) < 0.01, (event_id, gold_people, bi_people)
    orphan_count = con.execute(
        """
        SELECT count(*)
        FROM read_parquet(?) f
        LEFT JOIN read_parquet(?) d USING (region_key)
        WHERE d.region_key IS NULL
        """,
        [str(SNAPSHOT / "fct_exposure.parquet"), str(SNAPSHOT / "dim_region.parquet")],
    ).fetchone()[0]
    assert orphan_count == 0, orphan_count
    print("Power BI snapshot reconciles across all 10 events; no orphan regions")


if __name__ == "__main__":
    main()
