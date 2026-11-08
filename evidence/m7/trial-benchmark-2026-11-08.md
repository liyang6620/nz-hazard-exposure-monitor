# M7 Snowflake trial benchmark, 8 Nov 2026

## Guard and environment

- Trial: Azure / Australia East / Standard, displayed US$400 for 30 days. No
  payment card, upgrade, external stage or Azure SAS was used.
- Dedicated `NZHEM_XS` Gen2 X-Small warehouse, 60-second auto-suspend.
  `NZHEM_TRIAL_GUARD` has a 40-credit **project cap** and suspends immediately
  at 50% (20 credits). `ACCOUNTADMIN` query results verified attachment.
- Only the local machine uploaded 387 Parquet files (445,328,129 bytes) to an
  internal stage. Service access used the encrypted local key pair. The
  warehouse was verified `SUSPENDED` after the final run.
- At 23:54 NZDT, `SHOW RESOURCE MONITORS` displayed 0.22 used credits. This is
  a provisional aggregate for all trial activity, not a billed or per-run
  attribution. Per-run actuals await Account Usage reporting.

## Build and parity

| Check | Result |
| --- | --- |
| `dbt build --target snowflake_benchmark` | 8 seeds, 15 models, 25 tests; 48 PASS, 0 ERROR |
| Curated source rows | Exact for all 10 tables, including 6,612,732 buildings |
| Gold mart rows | Exact for four marts: exposure cell 400,742; summary 10; H3-6 25,668; accumulation 104,721 |
| Numeric aggregates | Absolute difference < `1e-6` using stable row sums when unordered engine `SUM` differed |
| Grid shaking | Every event/H3-8 and event/H3-6 MMI matched exactly |
| Single-event run | Kaikōura only: 104,712 exposure cells; one summary; 6,342 H3-6 cells; passed reconciliation |

One H3-6 footprint area `SUM` differed by `8.10623169e-6` from aggregation
order. The same row values summed with `math.fsum` on both sides differed by 0;
the largest individual row difference was `1.862645149230957e-9`. The absolute
acceptance threshold was unchanged. Full and single-run query tags were
`nzhem_m7_full` and `nzhem_m7_single`.

## Timings

| Run | DuckDB local | Snowflake trial | Snowflake UTC window |
| --- | ---: | ---: | --- |
| Full dbt rebuild | 22.062 s | 36.141 s | 10:51:02-10:51:45 |
| Kaikōura-only marts | 6.666 s | 18.172 s | 10:51:45-10:52:07 |

Wall times include dbt process and connection overhead. DuckDB used one thread
and a 512 MB limit. The first local attempt without seeds and the first cloud
attempt with DuckDB-only `UBIGINT` seed types are excluded from accepted timings.

## Setup repairs

The initial Snowsight multi-role setup did not complete. A single
`ACCOUNTADMIN` Worksheet was used. Its first run failed because `FREQUENCY =
NEVER` required `START_TIMESTAMP = IMMEDIATELY`; after correcting that, all
environment statements succeeded. The service user was then created and its
public key synchronized. The first Parquet load encountered WKB interpreted as
UTF-8; setting `BINARY_AS_TEXT = FALSE` corrected the format, and loading
resumed at the failed table. No monitor limit or permission scope was widened.

The service role sees `resource_monitor = null` in `SHOW WAREHOUSES` even though
the administrator sees the attachment. A four-hour ignored local attestation
of the administrator's monitor and warehouse results permits this run and
expires closed. No account identifier, user email, key or passphrase is in this
evidence.

## Follow-up

After Account Usage catches up, an administrator must query
`QUERY_ATTRIBUTION_HISTORY` joined to `QUERY_HISTORY` for the two query tags
and windows above, inspect warehouse metering for idle time, and record actual
credits separately. Until then, the 0.22-credit monitor reading and roughly
US$0.66 at the planning rate are provisional, aggregate figures.
