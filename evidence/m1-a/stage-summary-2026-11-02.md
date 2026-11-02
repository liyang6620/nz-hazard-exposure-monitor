# Azure deployment stage summary, 2 Nov 2026 NZDT

Public site: <https://stnzhem8495b7ca.z8.web.core.windows.net/>.

## Delivered

- PR [#31](https://github.com/liyang6620/nz-hazard-exposure-monitor/pull/31)
  merged after all required [CI checks](https://github.com/liyang6620/nz-hazard-exposure-monitor/actions/runs/41423041100)
  passed. Bootstrap, three Guardrails budgets and production infrastructure
  are running on Azure for Students. No additional unreviewed resource or role
  was applied in this stage.
- An actual new GeoNet M5.0 event reached `ready` and appeared on the website
  **32 minutes 9 seconds** after origin. Unattended hourly housekeeping and a
  temporary five-minute timer run succeeded; the schedule was restored to
  hourly. Two repeated catch-up runs enqueued zero duplicate events.
- The repository owner personally approved the Kaikōura cloud briefing through
  the ACS email's GET confirmation page and POST button. It is visible on the
  public detail page. A reused link, an altered HMAC and an expired link all
  returned HTTP 400. Two GET previews left a separate test draft pending.
- The approved direct budget webhook wrote the durable stop switch, sent ACS
  mail and stopped the Function. Owner-operated recovery removed the switch
  and restarted it. The Function is running with ArcGIS publishing disabled.
- `scripts/e2e_replay.py` matched all 56 Azure curated/gold Parquet objects to
  local files (216,680,598 bytes), including the Christchurch and Kaikōura
  replay fixtures. A separate full rebuild matched 37 gold Parquet hashes.
- All fixed pages and tested event deep links returned HTTP 200. The browser
  loaded 24 LINZ LDS map tiles with HTTP 200 and showed attribution. The
  Terraform state backup and migration preflight were rehearsed without a new
  subscription or paid resource.

See [the detailed acceptance record](azure-acceptance-2026-11-02.md),
[runbook](../../docs/runbook.md), [cost record](../../docs/cost.md), and
[desktop](azure-home-realtime-desktop.png) / [mobile](azure-home-realtime-mobile.png)
homepage screenshots.

## Not yet accepted

- Azure for Students rejected `Test action group` with HTTP 409 `Free
  subscription not supported`. The direct webhook drill does not prove that
  Azure Monitor will deliver a budget alert. Project-manager decision needed.
- A malformed queue-message poison drill needs a narrowly scoped Queue Data
  role; no unapproved assignment or injection was made.
- The owner must personally reject the separate pending test briefing. Its
  link is private and omitted from evidence.
- Azure ArcGIS handover needs publisher code and an approved Key Vault write
  permission plan. Both deployments' publisher switches remain off.
- The first cloud review-link GET showed "The service is unavailable" to the
  owner, then worked on refresh. Earlier probes also intermittently timed out
  before the function ran. Flex cold start is plausible, not established.
- Cost Management returned **NZD 0.277 actual month-to-date** on 2 November.
  It has not yet accumulated several operating days. Azure OpenAI charges are
  not separately itemized in this reading; no additional real inference calls
  are authorized by this summary.

The owner-only follow-up list is in ignored `tmp/OWNER_TODO.md`. Docker Desktop
was not running during this stage, so there was no local `app` container to
stop; the local ArcGIS publisher setting is false.
