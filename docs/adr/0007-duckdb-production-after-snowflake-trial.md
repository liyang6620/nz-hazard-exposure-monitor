# ADR 0007: Keep DuckDB in production after the Snowflake trial

Status: accepted M7 conclusion, 9 Nov 2026 NZDT.

## Context

The approved pipeline uses one DuckDB thread and a 512 MB memory limit. A
30-day Snowflake Standard trial on Azure Australia East tested the same curated
inputs with a guarded Gen2 X-Small warehouse; it was not a production service.
The trial loaded 387 Parquet files through an internal stage and rebuilt the
same dbt marts.

## Decision

Keep DuckDB for local and Azure production processing. Snowflake remains a
reproducible comparison only. Do not put the trial account, warehouse or
credentials in the production dependency chain. Its warehouse is suspended.

## Evidence and trade-off

The Snowflake build passed 48 dbt units and exact row/grid-MMI reconciliation;
numeric aggregates met the unchanged `1e-6` tolerance using stable row sums
when unordered engine sums differed. The full rebuild took 22.062 seconds on
DuckDB and 36.141 seconds on Snowflake; the Kaikōura-only run took 6.666 and
18.172 seconds respectively. These are client wall times, not isolated engine
benchmarks. Snowflake's monitor showed a provisional 0.22 aggregate used
credits; actual per-run credits await Account Usage. These results give no
measured speed or cost reason to migrate the current volume.

See [the platform comparison](../platform-comparison.md) and
[trial evidence](../../evidence/m7/trial-benchmark-2026-11-08.md).
