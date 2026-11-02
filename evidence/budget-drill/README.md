# Azure for Students Action Group budget drill

3 Nov 2026 saved Terraform plan, generated against the existing guardrails
remote state: **one create, zero update, zero delete**. The one new resource is
`azurerm_consumption_budget_subscription.action_group_drill`, named
`nzhem-action-group-drill-2026-11`. It is a NZD 1 Monthly budget for November
2026, with an Actual 100% notification to the existing budget-stop Action
Group. It has no `prevent_destroy`. The three permanent budgets are untouched.
The saved plan and all account identifiers remain under ignored `tmp/`.

The latest available Cost Management ActualCost reading was NZD 0.381775
month-to-date on 2 November. A 3 November query received HTTP 429, so there
is no newer usable cost reading yet. The Action Group path can only be marked
verified after Azure naturally evaluates this budget above NZD 1 and the
alert, Action Group, budget-stop handler, durable switch and Function stop are
observed in order. Record timestamps without personal or Azure identifiers.

After that stop, the owner follows `docs/runbook.md` to clear the switch and
restart the Function. Remove this temporary resource in a later PR; its saved
deletion plan must contain only this one deletion. Do not change the permanent
budget thresholds to run the drill.
