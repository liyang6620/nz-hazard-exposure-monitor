# DuckDB and Snowflake: M7 trial comparison

## Scope and status

The benchmark compares rebuilding the same dbt marts from 10 fixed curated
Parquet inputs (387 files, 445,328,129 bytes) and a Kaikōura-only event run.
It does not compare the upstream LINZ geometry import or rebuild curated spatial
attribution. The Snowflake trial is Azure / Australia East / Standard and shows
US$400 for 30 days. `NZHEM_TRIAL_GUARD` uses a **project cap** of 40 credits and
suspends the dedicated X-Small warehouse at 20 credits. This does not mean
Snowflake granted 40 credits.

| Run | DuckDB, local wall time | Snowflake wall time | Snowflake compute credits |
| --- | ---: | ---: | ---: |
| Full dbt rebuild | 22.1 s | 36.1 s | Pending delayed per-query metering |
| Kaikōura-only dbt marts | 6.7 s | 18.2 s | Pending delayed per-query metering |

The DuckDB runs used one thread and a 512 MB memory limit. Timing is from the
`dbt run` process wall clock; initial seed loading and external data preparation
are excluded from both runs. The single-event run was checked to contain only
`2016p858000`. Both Snowflake runs passed strict reconciliation. These are
client-side wall times, including dbt startup, connection and network overhead;
they do not isolate database execution speed. Here, Snowflake took 1.6x the
DuckDB full-run time and 2.7x the single-event time.

The Snowflake warehouse was **Gen2** and suspended at the end of loading,
validation and both benchmark runs. At 8 Nov 2026 23:54 NZDT the resource
monitor displayed **0.22 used credits** for the entire trial work, including
setup, load, build, reconciliation and benchmark. At the project's conservative
US$3/credit planning rate this is about **US$0.66**, an estimate rather than a
Snowflake charge. The monitor reading can lag. Actual per-run compute credits
must be queried from Account Usage after its reporting delay; no per-run credit
figure is inferred from the Gen1 1-credit/hour XS rate.

## SQL and spatial differences

| Concern | DuckDB production path | Snowflake trial path |
| --- | --- | --- |
| Input | Local `read_parquet` | Local `PUT` to internal stage, then `COPY INTO` typed curated tables |
| Parquet binary | DuckDB reads WKB as `BLOB` | `BINARY_AS_TEXT = FALSE` avoids decoding `geometry_wkb` as UTF-8 |
| H3 ID | `UBIGINT` | `NUMBER(20,0)` to preserve integer identity |
| dbt seed H3 type | `UBIGINT` | Adapter-specific `NUMBER(20,0)` seed column type |
| Point-to-cell | DuckDB H3 extension `h3_latlng_to_cell` | Native `H3_LATLNG_TO_CELL` via dbt adapter dispatch |
| Conditional aggregate | DuckDB `FILTER` supported | Shared `CASE WHEN` expression avoids adapter-specific `FILTER` syntax |
| Geometry | DuckDB/GEOS point-on-surface attribution | Reuse approved curated H3 and region IDs; no Snowflake `GEOGRAPHY` reattribution |
| Event time | Timezone-aware timestamp | `TIMESTAMP_TZ`; compare UTC instants |

Reusing curated cell IDs is deliberate. Snowflake's spatial boundary behaviour
is not treated as equivalent to the approved DuckDB/GEOS method. Recomputing
cell attribution in Snowflake would need a separate methodology review.

## Account setup observation

The first Snowsight Workspaces setup changed from `ACCOUNTADMIN` to other roles
and stopped before `NZHEM_BENCHMARK_USER` existed. A later `ALTER USER` failed
with “does not exist or not authorized.” The reviewed setup now runs entirely
as `ACCOUNTADMIN` in one Worksheet, creates the service user if missing and
syncs its public key on rerun. The administrator browser session is not used by
the benchmark scripts; they use the isolated key-pair service user.
The initial resource-monitor creation also needed
`START_TIMESTAMP = IMMEDIATELY` alongside `FREQUENCY = NEVER`; without it,
the first statement failed and no guarded warehouse existed. The final
`ACCOUNTADMIN` `SHOW WAREHOUSES` and `SHOW RESOURCE MONITORS` results verified
X-Small, 60-second auto-suspend, the monitor attachment, 40-credit cap and 50%
immediate suspension. The service role cannot see the monitor name in its
warehouse metadata, so the CLI uses a four-hour, account-bound local attestation
of that administrator check; it fails closed when the attestation expires.

The first Parquet `COPY` stopped on the population WKB column because Snowflake's
default treated binary as UTF-8 text. After changing only this project's file
format, the loader resumed from that table. The full `dbt build` then passed all
48 units (8 seeds, 15 models, 25 tests). Reconciliation matched all 10 source
and four mart row counts, all H3-8/H3-6 grid MMI values, and numeric aggregates
within the unchanged absolute `1e-6` bound. One floating-point engine `SUM`
result differed by `8.11e-6` due to order; recomputing both sums from row
values with the same `math.fsum` algorithm gave difference 0. Individual H3-6
area row differences were at most `1.86e-9`.

## Production choice

Production remains on DuckDB because the approved curated and gold volumes fit
the existing one-thread, 512 MB processing limit, and the measured local rebuild
was faster for both workloads. It uses the already deployed storage and runtime,
without a separately metered warehouse or trial expiry. Snowflake successfully
reproduced the marts and is useful for warehouse SQL and future scaling, but this
trial gives no performance or operating-cost reason to migrate production.
