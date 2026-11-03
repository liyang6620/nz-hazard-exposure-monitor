# Function-failure Action Group second recipient, 4 Nov 2026 NZDT

The owner checked the 163 inbox and spam after the 22:41:47 UTC real
`nzhem-function-execution-failure` alert and reported no email. Azure Monitor's
built-in test notification returned HTTP 409 on Azure for Students. The owner
then supplied a Gmail address privately and requested another delivery test.
The address is held only in ignored `.env` and a sensitive Terraform input.

The proposed production Terraform plan was generated against remote state.
It contains **one update** to `azurerm_monitor_action_group.failure_email`,
zero creations and zero deletions. The receiver count changes from one to
two; the original 163 receiver remains and the added Gmail receiver uses the
common alert schema. The Action Group's name, short name, enabled state,
tags and webhook count are unchanged. No budget-stop Action Group, alert rule,
role assignment or network setting changes. A line-ending-only drift in the
housekeeping KQL was eliminated in source with explicit LF escapes before the
plan was saved; its query text and rule remain unchanged.

PR [#55](https://github.com/liyang6620/nz-hazard-exposure-monitor/pull/55)
passed CI and was merged. The saved plan SHA-256 was
`40652F0B93567F63832DC199E18BAEF31EC3629F8D0856D6E9BB42778AF3AA11`.
An MFA-bearing management token was verified without printing it, then that
exact plan applied: 0 added, 1 changed, 0 destroyed. Read-back showed both
email receivers enabled with the common alert schema and no webhook on the
failure Action Group. The original budget-stop group remained enabled with
one email receiver and one webhook. The failure metric alert remained enabled
and attached to one Action Group.

The previous failure alert had resolved before the repeat exercise. A
separately approved temporary queue-scoped Message Sender grant was created
from a one-create plan, one malformed message was sent to `events`, and the
grant was immediately removed by a one-delete plan. Azure reported zero
remaining owner assignments at that queue scope. `events-poison` increased
from 26 to 27. The 42 gold objects retained the same sorted name, size and
ETag metadata hash
`5DBB550974E97ACE6836269DED2C18323EAF9E8888536F1B121A0F09CA926737`.
Application Insights recorded six exceptions from the drill. Azure Monitor
created a new `nzhem-function-execution-failure` alert at 23:21:46 UTC,
`Fired` with no suppression. This proves the new receiver configuration and
alert transition, but not inbox delivery. The owner has been asked to check
the Gmail inbox; receipt remains pending their confirmation.
