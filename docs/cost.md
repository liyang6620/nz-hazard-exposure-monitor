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

The later reading, grouped by Cost Management `ServiceName`, was Storage
NZD 0.378492, Email NZD 0.001780, Foundry Models NZD 0.001471, and Key Vault
NZD 0.000032. Azure App Service, Azure Monitor, Bandwidth, Functions and Log
Analytics each returned NZD 0.000000. Displayed service amounts are rounded;
the unrounded sum is NZD 0.381775. These are actual billable values as returned
by Azure, not a forecast. Most reported spend is Storage, but this single day
cannot distinguish one-time deployment transactions from steady-state use.
The NZD 1 drill budget will only alert after delayed actual cost crosses NZD 1;
it must not be treated as an immediate stop test.

Query Cost Management once per NZ day during the first operating week. Record
the query date, returned currency and actual month-to-date total; do not
substitute estimates for delayed or missing rows. Watch for charges from
Functions, storage transactions, Application Insights, ACS Email and Azure
OpenAI. The application separately enforces briefing token and monthly-count
limits. No subscription upgrade or payment method is part of this plan.
