# Temporary budget removal, 6 Nov 2026

At the repository owner's request, the November NZD 1 Action Group drill budget
was removed before a natural alert could stop unattended service. The saved
Guardrails plan contained exactly one deletion,
`azurerm_consumption_budget_subscription.action_group_drill`, and `no-op` for
the three permanent NZD 2, 5 and 8 budgets. The saved plan applied successfully;
remote Terraform state then contained only those three permanent budgets.

At 5 Nov 23:51 UTC, the Function ARM state was `Running`. The public manifest
reported `generated_at` 5 Nov 23:00:03 UTC, consistent with the latest hourly
publication. There was no evidence of a budget-triggered stop at removal time.

The direct `budget-stop` drill passed earlier. The complete natural budget
alert → Action Group → webhook → Function stop path remains **unverified**:
Azure for Students rejected Action Group testing and the owner decided against
an unattended natural-stop drill. A later attended drill is optional.

No subscription identifier, tenant identifier, personal email or secret is
included here. Plan and apply transcripts remain under ignored `tmp/`.
