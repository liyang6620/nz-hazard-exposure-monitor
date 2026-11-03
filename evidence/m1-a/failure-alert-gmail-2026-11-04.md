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

Apply and mail delivery checks are pending CI. Do not treat a Fired alert
instance as evidence that Gmail received the message.
