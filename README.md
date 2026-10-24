# NZ Hazard Exposure Monitor

A dual-deployment demonstration system for estimating New Zealand earthquake
exposure using building count, building footprint and 2023 Census population.
The primary target is Azure; the second, fully supported target runs locally
with Docker Compose and requires no Azure or Microsoft account.

## Status

M1-L, M2 and M3 are complete locally. The no-account portion of MG is also
complete; hosted ArcGIS publishing remains deferred. The shared core, local
Docker host and Azure Functions host are kept separate. No Azure infrastructure
is created until M1-A plans are approved. Milestone evidence is under
[`evidence/`](evidence/).

## Important limitations

- The system has no insurance policy data. "Exposure" means building count,
  building footprint and population.
- Estimated Modified Mercalli Intensity is illustrative, not an actuarial,
  engineering or emergency-management conclusion.
- Building appearance and disappearance dates are approximate inferences from
  aerial imagery and source lifecycle metadata.
- Population is published 2023 SA1 population distributed within each SA1 by
  current building footprint. SA1 is coarser than meshblock and Stats NZ applies
  confidentiality treatment to small-area counts.

## Repository layout

```text
src/nzhem/core/       cloud-independent business logic (no azure.* imports)
src/nzhem/ports/      storage, queue, table, mail, LLM and website contracts
src/nzhem/adapters/   local and Azure implementations
hosts/local/          FastAPI + APScheduler Docker host
hosts/azure_functions Azure Functions trigger bindings
dbt/                  DuckDB/dbt transformation project
infra/bootstrap/      one-time remote-state storage
infra/providers/      explicitly approved Azure provider registrations
infra/identity/       Entra applications and GitHub OIDC bootstrap
infra/guardrails/     independent subscription budget root module
infra/terraform/      production Azure infrastructure
scripts/              build and verification tooling
docs/                 method, architecture and operating documentation
evidence/              sanitized milestone evidence
```

## Run the local deployment

Requirements: Docker Desktop with Docker Compose v2. No Microsoft account is
needed.

```bash
docker compose up --build
```

The services are then available at:

- API and health: <http://localhost:8000/health>
- Static site: <http://localhost:8080/>
- Token-free historical event map: <http://localhost:8080/map/>
- Mailpit inbox: <http://localhost:8025/>

The application runs `housekeeping` once at startup and then every 60 minutes.
It reads the last successful poll from SQLite and sends GeoNet FDSN an
`updatedafter` query so events published while the computer was off are caught
up. Persistent data lives in the `nzhem-data` and `nzhem-state` Docker volumes.

Optional local secrets and overrides belong in `.env`:

```bash
cp .env.example .env
```

Never commit `.env`. `OPENAI_API_KEY` is not needed for M1-L housekeeping. The
local ArcGIS publisher defaults to off. Keep `ARCGIS_PUBLISHER_ENABLED=false`
locally when Azure is the active publisher; exactly one deployment may publish.

Stop the services without deleting data:

```bash
docker compose down
```

Place the untouched owner-created LINZ ZIP at
`.local/data/raw/reference/linz_buildings_export/incoming/lds-nz-building-outlines-all-sources-GPKG.zip`.
The export must be the complete layer in GeoPackage format, EPSG:4326, with no
crop, filter or simplification. Copy it into the persistent data volume and run
the bounded, resumable importer:

```bash
docker compose exec app mkdir -p /data/raw/reference/linz_buildings_export/incoming
docker compose cp .local/data/raw/reference/linz_buildings_export/incoming/lds-nz-building-outlines-all-sources-GPKG.zip app:/data/raw/reference/linz_buildings_export/incoming/
docker compose exec app python scripts/import_linz_export.py
```

The importer validates ZIP paths and declared expansion before extraction, then
uses the GeoPackage RTree to create small national tiles. Each tile loads every
intersecting meshblock regardless of region, so cross-region tiles cannot drop
boundary buildings. It uses one thread, a 512 MB DuckDB limit, a 768 MB process
RSS ceiling, and preserves at least 20 GB free plus a 5 GB work reserve. Verified
tile checkpoints persist in `nzhem-data`, so the same command resumes after a
controlled worker restart. The WFS downloader remains an explicit fallback.

## Azure host local check

The Azure Functions host can be indexed locally without deploying resources.
Install Azure Functions Core Tools v4, create an ignored settings file from the
example, install the host requirements, and start from the host directory:

```bash
cp hosts/azure_functions/local.settings.example.json hosts/azure_functions/local.settings.json
python -m pip install -r hosts/azure_functions/requirements.txt
python -m pip install -e .
cd hosts/azure_functions
PYTHONPATH=../../src func start
```

In PowerShell, use `$env:PYTHONPATH=(Resolve-Path ../../src); func start` for
the final command.

The example uses `NZHEM_ENV=local`; `AzureWebJobsStorage=UseDevelopmentStorage=true`
requires Azurite if trigger storage is requested by Core Tools. This is a local
host check, not evidence of an Azure deployment. Start it with
`docker compose --profile azure-dev up -d azurite`. If ports 10000-10002 are
already occupied, set `AZURITE_BLOB_PORT`, `AZURITE_QUEUE_PORT`, and
`AZURITE_TABLE_PORT`, then put matching explicit endpoints in the ignored
`local.settings.json` connection string.

## Development checks

```bash
python -m pip install -r requirements-dev.txt
ruff check src hosts tests scripts
pytest
python scripts/e2e_replay.py --gold-root tests/fixtures/e2e/gold --manifest tests/fixtures/e2e/manifest.json
sqlfluff lint dbt/models --dialect duckdb
dbt build --project-dir dbt --profiles-dir dbt/profiles --target duckdb_local
```

The parity fixture contains locked real GeoNet Kaikoura and Christchurch M3
summary outputs. Terraform roots remain validation-only. `terraform-plan.yml`
and `deploy.yml` are hard-disabled until the Microsoft account is restored and
M1-A is approved.

Runtime secrets come from local environment variables or Azure Key Vault. No
long-lived credentials belong in this repository or GitHub CI.

## Data attribution

- Earthquakes and intensity: GeoNet / Earth Sciences New Zealand, CC BY 3.0 NZ.
- Shaking Layers Dataset: Earth Sciences New Zealand, DOI 10.21420/J856-2J84.
- Building outlines: Land Information New Zealand, CC BY 4.0.
- Census and boundaries: Stats NZ, CC BY 4.0. Counts may be randomly rounded or
  suppressed for confidentiality.

## Licence

Project code is licensed under the [MIT License](LICENSE). Third-party data and
generated data products retain their source licences and attribution terms.
