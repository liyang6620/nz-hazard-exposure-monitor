# Azure for Students cost record

The deployment uses the student subscription's spending limit as the final
backstop. Three fixed monthly subscription budgets notify the owner; the
separate budget-stop webhook can stop the Function App. Azure for Students
rejected the built-in Action Group test notification with HTTP 409 (`Free
subscription not supported`), so Action Group delivery is not verified.

| NZ date | Actual month-to-date cost | Currency | Interpretation |
|---|---:|---|---|
| 2 Nov 2026 | 0.277 | NZD | First non-empty Cost Management reading; delayed and not a daily run rate. |
| 2 Nov 2026, later query | 0.381775 | NZD | Month-to-date ActualCost; Cost Management data remains delayed. |
| 3 Nov 2026, first query | unavailable | NZD | Cost Management returned HTTP 429; no amount was inferred. |
| 4 Nov 2026 NZDT | 0.535918 | NZD | Month-to-date ActualCost returned by Cost Management; charges are delayed. |

The later reading, grouped by Cost Management `ServiceName`, was Storage
NZD 0.378492, Email NZD 0.001780, Foundry Models NZD 0.001471, and Key Vault
NZD 0.000032. Azure App Service, Azure Monitor, Bandwidth, Functions and Log
Analytics each returned NZD 0.000000. Displayed service amounts are rounded;
the unrounded sum is NZD 0.381775. These are actual billable values as returned
by Azure, not a forecast. Most reported spend is Storage, but this single day
cannot distinguish one-time deployment transactions from steady-state use.
The NZD 1 drill budget will only alert after delayed actual cost crosses NZD 1;
it must not be treated as an immediate stop test.
The 4 Nov NZDT reading grouped by service was Storage NZD 0.526743, Azure
Monitor NZD 0.005859, Email NZD 0.001780, Foundry Models NZD 0.001471 and
Key Vault NZD 0.000064. Azure App Service, Bandwidth, Functions and Log
Analytics each returned zero. Displayed service values are rounded; the
unrounded total was NZD 0.535918. It remains too early to infer a steady-state
monthly cost from deployment-period storage transactions.
The Function App was reported `Running` at the 4 Nov NZDT recheck; no natural
budget notification or Action Group email delivery has been verified yet.
The 3 Nov missing-housekeeping log alert evaluates a two-hour window every
30 minutes. The Azure retail pricing API for Australia East listed system log
alerts at US$0.50/month for 15-minute evaluation; this less frequent rule is
budgeted conservatively at **no more than US$0.50/month** for the alert rule,
plus existing low-volume log ingestion and any email delivery charges. Review
the first actual charge before treating that estimate as a measured cost.
Application Insights previously sampled at 20%, which was unsuitable for an
alert based on only two hourly requests. The approved fallback raised sampling
to 100% while retaining the 0.1 GB daily cap. The workspace previously reported
about 31 MB of application telemetry over the last three days at 20%; a
conservative fivefold estimate is about 1.6 GB/month, below the workspace's
free monthly ingestion allowance. This is a planning estimate, not an Azure
bill, and must be checked after the sampling change.
The preferred Function-host sampling exception did not restore an
`AppRequests` row for the 3 Nov 11:00 UTC scheduled run. A fresh 24-hour
workspace Usage query measured about 3.8 MB; a fivefold projection is about
0.57 GB/month. The earlier 1.6 GB/month figure is retained as a conservative
planning bound for the 100% sampling fallback. Its 0.1 GB daily cap remains
enabled, and actual charges must be checked after deployment.

Query Cost Management once per NZ day during the first operating week. Record
the query date, returned currency and actual month-to-date total; do not
substitute estimates for delayed or missing rows. Watch for charges from
Functions, storage transactions, Application Insights, ACS Email and Azure
OpenAI. The application separately enforces briefing token and monthly-count
limits. No subscription upgrade or payment method is part of this plan.
