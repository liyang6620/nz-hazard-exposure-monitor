# Local deployment

The Docker Compose deployment is a supported deployment target, not a mock of
Azure. It uses the same core functions as the Azure Functions host.

All published Compose ports bind to `127.0.0.1` by default. This includes the
Mailpit UI, which can contain approval links. Exposing the deployment from a VM
requires an authenticated reverse proxy and project-manager approval at the
security hard stop; do not change the bind address directly.

## Services

| Service | Implementation | Persistent state |
|---|---|---|
| Scheduler and HTTP | APScheduler and FastAPI | SQLite and structured container logs |
| Object storage | Local folders matching `raw`, `curated`, `gold`, `briefings`, and `web` | `nzhem-data` volume |
| Queue and tables | SQLite | `nzhem-state` volume |
| Mail | Mailpit SMTP and web UI | Development inbox only |
| Static website | Caddy | Reads `web/` from `nzhem-data` |
| LLM | OpenAI Responses API | Key supplied only through ignored `.env` |

Queue messages have a visibility timeout and a receipt. A failed message can be
retried three times; after the third lease expires, the next receive operation
moves it to `<queue>-poison`. These semantics match the Azure host contract.

## Startup catch-up

At startup the local host runs the shared `housekeeping` function. It finds the
latest successful housekeeping row in SQLite and passes that timestamp to the
GeoNet FDSN `updatedafter` parameter. With no previous row it uses a 48-hour
lookback. The same call is then scheduled at `POLL_INTERVAL_MINUTES` (default
60, minimum 5).

## ArcGIS single-writer rule

`ARCGIS_PUBLISHER_ENABLED` defaults to `false`. Only one deployment may set it
to `true`. Once Azure is live, Azure owns publishing and the local deployment
must remain disabled. This prevents conflicting edits and duplicated free-tier
usage.

## Reference-data refresh

The normal building path is an owner-created whole-layer GeoPackage export.
Keep its original filename, do not unzip it manually, and place it at:

`/data/raw/reference/linz_buildings_export/incoming/lds-nz-building-outlines-all-sources-GPKG.zip`

Then run:

```bash
docker compose exec app python scripts/import_linz_export.py
```

The importer rejects unsafe ZIP paths and an archive whose declared extraction
would breach the disk budget. It verifies the GeoPackage schema, CRS, RTree,
source count and unique building IDs. RTree-driven tiles contain no more than
5,000 candidate polygons. Point ownership uses half-open tile boundaries, while
the spatial join loads all meshblocks intersecting the tile without a region
filter. Completed tile output and its source/checkpoint hashes are verified on
restart before work is skipped.

Defaults are intentionally conservative: one process and thread, a 512 MB
DuckDB limit, a 768 MB process RSS ceiling, a 20 GB free-disk floor and a 5 GB
work/spill reserve. DuckDB may spill below its memory limit. A resource-limit
stop preserves completed tiles and the supervisor resumes them in a clean
worker. WFS paging remains available as a fallback through
`scripts/refresh_reference.py`; it is not the normal full-building path.

## Boundaries

- The local deployment does not use Terraform, managed identity, Key Vault,
  Azure budgets, or the Azure budget stop.
- `terraform-plan.yml` and `deploy.yml` remain disabled until M1-A.
- Local results are local evidence only. They are never represented as Azure
  deployment evidence.
- The OpenAI key and any other secret stay in `.env`, which Git ignores.
