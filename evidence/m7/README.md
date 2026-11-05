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

No Snowflake warehouse or trial credit has been used. Actual rebuild times,
metered credits and Snowflake parity results remain **not measured** until the
owner creates the trial account. Offline CI checks syntax, adapter parsing and
the negative reconciliation tests; those are not cloud benchmark evidence.
