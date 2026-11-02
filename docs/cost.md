# Azure for Students cost record

The deployment uses the student subscription's spending limit as the final
backstop. Three fixed monthly subscription budgets notify the owner; the
separate budget-stop webhook can stop the Function App. Azure for Students
rejected the built-in Action Group test notification with HTTP 409 (`Free
subscription not supported`), so Action Group delivery is not verified.

| NZ date | Actual month-to-date cost | Currency | Interpretation |
|---|---:|---|---|
| 2 Nov 2026 | 0.277 | NZD | First non-empty Cost Management reading; delayed and not a daily run rate. |

Query Cost Management once per NZ day during the first operating week. Record
the query date, returned currency and actual month-to-date total; do not
substitute estimates for delayed or missing rows. Watch for charges from
Functions, storage transactions, Application Insights, ACS Email and Azure
OpenAI. The application separately enforces briefing token and monthly-count
limits. No subscription upgrade or payment method is part of this plan.
