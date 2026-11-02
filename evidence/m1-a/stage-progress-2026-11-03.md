# Azure follow-up stage, 3 Nov 2026

Public site: <https://stnzhem8495b7ca.z8.web.core.windows.net/>.

## Completed and verified

- PR #37 deployed the static review page, HTML/plain-text approval email and
  revised populated-grid MMI briefing trigger. PR #38 deployed a bounded GET
  retry for cold starts; POST remains a human, single-attempt decision.
- PR #39 created the NZD 1 November drill budget from a one-creation plan.
  It remains in place pending a natural Cost Management alert.
- PR #40 prepared a queue-scoped, disabled temporary message-sender role for
  the owner-supervised poison drill. No role grant or malformed message has
  been applied yet.
- The repository owner personally rejected test briefing `2026p824047`.
  The current public summary reports `rejected` with no public path; direct
  access to its briefing HTML returns 404. See
  `rejected-test-briefing-2026-11-03.md`.
- PR #41 merged the disabled-by-default Azure ArcGIS incremental publisher
  and temporary Key Vault role switch. All PR CI checks passed; 165 Python
  tests passed locally with 80.62% coverage. PR #42 documented the deployment
  attempt and the exact verification gap.
- The current Azure app settings still show the 60-minute timer and poll
  interval, with ArcGIS publishing off. The Function was Running, all six
  triggers were enumerable and the public manifest returned HTTP 200.

## Plans and cloud status

The owner Key Vault Secrets Officer saved plan is ignored at
`tmp/arcgis-vault-role.tfplan`. Its SHA-256 is
`07DA257F6093286D7DE18AF1B6DE519660636E3CEEC7DA7E7032552FE999E3EF`.
The plan has one creation, `owner_arcgis_key_write[0]`, scoped to this
project's Key Vault; zero updates and zero deletions. It adds no network
exposure or recurring resource charge. It has not been applied.

Two submissions of PR #41's main-branch CI Function ZIP were accepted by the
Azure deployment endpoint, but CLI trigger-sync/health checks failed. Azure
reported completed deployment records, while Function and website remained
available. Package activation is not independently proven. Do not enable the
ArcGIS writer until deployment is verified.

Cost Management's last usable month-to-date ActualCost was NZD 0.381775 on
2 Nov, predominantly Storage; see `docs/cost.md` for the service split. The
3 Nov read returned HTTP 429, so no 3 Nov actual or monthly run rate is
asserted. Known OpenAI direct-call budget accounting remains US$0.02307375
against the US$1 cap; no new direct OpenAI call was made in this stage.

## Remaining acceptance

- Wait for the NZD 1 budget's natural alert; record budget notification,
  Action Group, budget-stop and Function stop timestamps, then use the owner
  recovery runbook and remove only that drill budget with a one-deletion plan.
- With the owner present, apply the previously prepared queue-sender role,
  inject one malformed message, verify `events-poison`, alert and unchanged
  gold hashes, then remove only that role with a one-deletion plan.
- With the owner present, apply the vault-scoped role plan, have the owner
  write the ArcGIS key directly to Key Vault, and remove the temporary role.
  Verify package activation and quotas before enabling the Azure writer;
  keep the local writer off and confirm the hosted item ID stays unchanged.
- Obtain a redacted screenshot of a real 163 HTML approval email from the
  owner. The Mailpit rendering screenshot already exists but is not evidence
  for the external inbox.
- Recheck Cost Management after the 429 delay and record daily actual costs by
  service. If steady-state spend appears to exceed US$3/month, submit a
  proposed reduction for project-manager review before changing resources.

Owner-specific instructions and pending actions are in ignored
`tmp/OWNER_TODO.md`. No subscription ID, tenant ID, address, secret or approval
token is included in this evidence.
