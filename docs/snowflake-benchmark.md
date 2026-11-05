# M7 Snowflake benchmark: offline preparation

This phase prepares a trial-only comparison. No Snowflake account, warehouse,
user, stage, data upload or credit usage was created during offline work.
The local source is the immutable curated reference export
`reference-export/dee5b263952e` plus the fixed M3 event Parquet files. The
private key, rendered SQL, dbt logs and measurements stay under ignored
`.local/snowflake/`.

## Trial boundary

After this PR is merged, the repository owner may register a **Snowflake free
trial**, select **Azure** as the cloud, **Australia East** as the region and
**Standard** as the edition. Snowflake manages its SQL engine version; there is
no engine-version selector. Do not upgrade or add a payment card. Confirm the
trial credit grant in **credits**, not its displayed currency value, before
rendering setup SQL. If the trial screen does not state a credit quota, stop
and ask for a quota decision; do not infer one from currency.

Set these only in ignored `.env` or the local shell, never in a commit:
The M7 Python commands load `.env` without echoing its values and pass them to
dbt as process environment variables.

| Variable | Value after registration |
| --- | --- |
| `SNOWFLAKE_ACCOUNT` | Account identifier from Snowflake's connection details, without a URL scheme. |
| `SNOWFLAKE_USER` | `NZHEM_BENCHMARK_USER`. |
| `SNOWFLAKE_PRIVATE_KEY_PATH` | Absolute path to ignored `.local/snowflake/rsa_key.p8`. |
| `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` | Contents of ignored `.local/snowflake/key_passphrase.txt`. |
| `SNOWFLAKE_RSA_PUBLIC_KEY` | Single-line contents of ignored `.local/snowflake/rsa_key.pub.b64`; this is public material. |
| `SNOWFLAKE_TRIAL_CREDIT_QUOTA` | Trial grant in credits. The monitor suspends the warehouse immediately at 50% of this quota. |

`python benchmark/snowflake/generate_keypair.py` creates an encrypted 3072-bit
RSA private key locally, public key and random passphrase. Protect the local
passphrase file like the private key. The scripts authenticate by key pair only;
no password or browser session is needed for the benchmark service user.

## Setup and run, after registration

1. Install `benchmark/snowflake/requirements.txt` into the project venv. Run
   `python benchmark/snowflake/render_setup.py`. Inspect the ignored rendered
   SQL and have an account administrator execute it once. The monitor must
   exist and be attached to `NZHEM_XS` before any data load.
2. Run `python benchmark/snowflake/load_curated.py` without `--execute` for the
   offline file/byte inventory. Then run with `--execute` to create source
   tables, `PUT file://...` from this machine to the Snowflake **internal**
   stage, and `COPY INTO` the tables. The loader uses no Azure SAS or external
   stage. Do not run it twice without reviewing the replace-and-reload effect.
3. Run `dbt parse --project-dir dbt --profiles-dir dbt/profiles --target
   snowflake_benchmark` locally first. This offline parse uses profile defaults
   unless Snowflake variables have been exported into the shell; it does not
   load `.env`. The benchmark Python runner loads ignored `.env` before starting
   dbt. Then run
   `python benchmark/snowflake/benchmark.py --execute`. It performs a full dbt
   rebuild in `BENCHMARK_FULL`, then a Kaikōura-only event mart rebuild in
   `BENCHMARK_SINGLE`, with separate query tags and schemas. Each run must pass
   `reconcile.py` before its timing is accepted.
4. After Snowflake's usage delay, an account administrator can join
   `SNOWFLAKE.ACCOUNT_USAGE.QUERY_ATTRIBUTION_HISTORY` to
   `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY` on `QUERY_ID`, filter the latter's
   `QUERY_TAG` to `nzhem_m7_full` or `nzhem_m7_single` and the recorded run
   windows, then sum `CREDITS_ATTRIBUTED_COMPUTE`. Account Usage has reporting
   latency and excludes idle warehouse time; also inspect warehouse metering
   before reporting total credits. The benchmark role has no account-wide usage
   visibility. Run `python benchmark/snowflake/record_credits.py --full <credits>
   --single <credits>` to attach those measured values locally.
   `xs_compute_credit_estimate` in the ignored JSON is **only** a 1-credit/hour
   XS estimate with a 60-second minimum, not a billed credit measurement.
   Report the measured credits, timings and both reconciliation results in a
   later evidence update; never call an estimate an actual charge.

The monitor limits only this warehouse. The benchmark role cannot create
another warehouse. Keep all runs on `NZHEM_XS`. An administrator should verify
`SHOW RESOURCE MONITORS`, `SHOW WAREHOUSES` and the remaining trial balance
before the first `PUT`.

## Engine adaptation

| Concern | DuckDB | Snowflake benchmark |
| --- | --- | --- |
| Curated input | `read_parquet` on local files | `PUT` to internal stage, `COPY INTO` typed `CURATED` tables, dbt `source()` |
| H3 integer | `UBIGINT` | `NUMBER(20,0)`; no floating conversion of cell IDs |
| Conditional aggregates | `SUM/COUNT ... FILTER (WHERE ...)` | `SUM/COUNT(CASE WHEN ... THEN ... END)` in shared SQL |
| H3 point lookup | `h3_latlng_to_cell` | adapter dispatch to `H3_LATLNG_TO_CELL`; compare numeric cell IDs before accepting results |
| Spatial type | DuckDB `GEOMETRY` from WKB | Snowflake `GEOGRAPHY` has different axis and boundary semantics; source `geometry_wkb` remains `BINARY` |
| Point-on-surface, cell/region assignment | Locally curated with DuckDB/GEOS and H3 | Reuse the approved curated IDs; do not silently recompute attribution using Snowflake spatial predicates |
| Time | DuckDB timezone-aware timestamps | `TIMESTAMP_TZ` for event origins; compare UTC instants |

The Snowflake dbt run rebuilds the dimensional and exposure **dbt models from
the uploaded curated layer**. It does not replay the 3.07 GB LINZ GeoPackage,
rebuild raw geometry attribution or claim Snowflake's `GEOGRAPHY` is equivalent
to the local point-on-surface algorithm. Any later spatial-method comparison
requires a separately reviewed method change.

`reconcile.py` requires exact row counts for all uploaded inputs and four
gold marts, absolute numeric aggregate difference below `1e-6`, and an exact
event/H3-8 and H3-6 MMI match for every grid row. Single-event mode compares only the
Kaikōura event marts. A failure stops the benchmark; no tolerance is silently
expanded.
