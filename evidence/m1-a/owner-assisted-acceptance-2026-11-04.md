# Owner-assisted Azure acceptance, 4 Nov 2026 NZDT

## ArcGIS handover

The repository owner created the server-side publisher secret in the project
Key Vault. The vault-scoped temporary Secrets Officer assignment was applied
from a one-creation plan, then removed with a one-deletion plan. No secret
value was copied into the repository or evidence. Azure publication was enabled
only after the deployed build was checked; the local publisher stayed off.
One housekeeping run recorded an ArcGIS edit batch. The private hosted item
retained its item ID, grew from 4,011 to 4,014 features and used 3,521,464
bytes of account storage, below the 125 MiB free allowance. A Terraform
Function setting update recreated a plain host-storage setting; it was removed
and managed-identity host settings remain in place. Every future Function
setting apply must recheck this invariant.

## Poison queue and TEST mail

A one-creation Terraform plan temporarily granted the owner Message Sender on
`events`. One malformed message moved to `events-poison` (count 22 to 23).
The 56 Azure curated/gold Parquet files, 216,680,598 bytes, matched the
pre-drill aggregate SHA-256
`adcfc2ea9a29a5b22ef0006514b9ea1cdce23dc41c1b591eb4a06147e91eea10`.
The sender grant was removed with a one-deletion plan. No corresponding
failure-alert instance was observed, so email alert delivery is unverified.

PR #48 added a non-publishable TEST review: its email contains only Reject,
and even a forged Approve action is rejected by the service. PR #50 permits
this TEST path for a published historical replay while preserving the normal
populated-grid MMI trigger. PR #51 excludes TEST records from public briefing
status, preserving an earlier approved briefing after a TEST rejection.
An administrator-triggered queue invocation returned HTTP 202 but did not run
the consumer. A Windows `az.cmd` JSON send produced another malformed poison
message (count 23 to 24). A correctly JSON-serialized Azure Queue SDK send
then produced the TEST draft; the owner confirmed receiving the HTML message
at the real 163 mailbox and personally selected Reject. The temporary
queue-scoped sender grant was removed after each exercise. No automated
request made the owner's decision. The redacted inbox screenshot is still
pending from the owner; no address, link or token is included here.

At 12:00 UTC, the next scheduled website generation still reported the
Kaikōura briefing as `approved` with its original public path. The original
HTML returned 200, contained no TEST notice, and the index retained one
non-TEST entry. This confirms the rejected TEST revision did not replace or
publish over the approved briefing.

After enabling 100% sampling, one further malformed SDK message reached
`events-poison` (count 24 to 25). Application Insights recorded three failed
`process_event` requests and six exceptions. All 56 curated/gold Parquet
objects still matched the pre-drill hash. The temporary sender role was
deleted again; Terraform state lacks it and Azure returned 404 for the
assignment. Exception telemetry and the metric were observed; Action Group
email delivery awaits independent confirmation.

## Hourly monitoring and cost

PR #49 excluded Request and Exception telemetry from Function-host sampling.
The 11:00 UTC housekeeping run published a new manifest, but `AppRequests`
still had no row after 28 minutes. The approved fallback PR #47 changed only
the existing Application Insights sampling from 20% to 100%; its saved plan
had one update, zero creations or deletions, and preserved the 0.1 GB daily
cap. The alert is not accepted until two consecutive hourly execution records
and an Action Group email exercise are observed.
The 12:00 UTC housekeeping request is present in `AppRequests` with success,
and the manifest was generated at 12:00:00 UTC. Read-only recheck at 21:16 UTC
found successful scheduled requests at every hour from 12:00 through 21:00 UTC,
including 13:00 and 21:00. The public manifest had advanced to 21:00 UTC and
the Function was Running. Each hour also had an earlier successful request
near :58; the Function timer has `run_on_startup=True`, so these extra
requests are consistent with host startup and are not counted as the hourly
schedule evidence. The two-consecutive-hour telemetry gate is met. The
missing-housekeeping alert rule remained enabled with its original query, and
Azure Alerts Management reported its earlier Fired instances as Resolved.

The function-execution-failure metric alert fired at 12:01 UTC during the
malformed-message drill, then resolved. Its Action Group email receiver was
enabled and matched the owner-confirmed masked address; Azure reported no
suppression rule. The owner checked the 163 inbox and reported no alert email.
Azure's alert record did not expose a delivery receipt, and the built-in
Action Group test remains unavailable on this student subscription. Thus
alert delivery remains unverified despite the successful metric and alert
state transitions. No new resource or permission was added to investigate it.

Cost Management returned a delayed November ActualCost of NZD 0.535918 on
4 Nov NZDT: Storage 0.526743, Azure Monitor 0.005859, Email 0.001780,
Foundry Models 0.001471 and Key Vault 0.000064; the other listed services
were zero. See [cost.md](../../docs/cost.md). The NZD 1 budget drill still
awaits a natural Cost Management notification.

Public site: <https://stnzhem8495b7ca.z8.web.core.windows.net/>.
