# Local deployment

The Docker Compose deployment is a supported deployment target, not a mock of
Azure. It uses the same core functions as the Azure Functions host.

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

## Boundaries

- The local deployment does not use Terraform, managed identity, Key Vault,
  Azure budgets, or the Azure budget stop.
- `terraform-plan.yml` and `deploy.yml` remain disabled until M1-A.
- Local results are local evidence only. They are never represented as Azure
  deployment evidence.
- The OpenAI key and any other secret stay in `.env`, which Git ignores.
