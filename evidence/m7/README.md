# M7 offline Snowflake preparation

Account-free phase. The SQL, key-pair flow, internal-stage Parquet loader,
Snowflake dbt target, full and Kaikōura-only runners, and strict reconciliation
are prepared in `benchmark/snowflake/` and `dbt/`. See
[`docs/snowflake-benchmark.md`](../../docs/snowflake-benchmark.md).

Local inventory (read-only, DuckDB capped at 512 MB): 10 curated input tables,
387 Parquet files and 445,328,129 bytes. Every fragment matched its table's
Parquet column schema. The building source has 6,612,732
curated rows; event exposure has 400,742 H3-8 rows; the H3-6 exposure mart has
25,668 rows. An encrypted key pair was generated in git-ignored
`.local/snowflake/`; no private material or account identifier is committed.

During this offline phase no Snowflake warehouse or trial credit was used.
Offline CI checked syntax, adapter parsing and negative reconciliation tests;
those results alone were not cloud benchmark evidence.

The account-backed second phase is documented in
[`trial-benchmark-2026-11-08.md`](trial-benchmark-2026-11-08.md). It passed
strict parity and both timed workloads. Per-run metered credits remain pending
Account Usage reporting; the X-Small Gen2 warehouse is suspended.
