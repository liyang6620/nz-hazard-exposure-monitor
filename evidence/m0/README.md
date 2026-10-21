# M0 evidence index

All evidence is text-only and contains no contact email, credential, access
token, Terraform state or source data.

- `guardrails-plan.txt`: the saved, pre-approved creation plan summary.
- `guardrails-apply.txt`: recorded apply result and post-apply drift check.
- `guardrails-verification.json`: sanitized Azure REST verification.
- `local-feasibility.txt`: package, DuckDB extension and FileGDB checks.
- `azure-readonly.txt`: read-only subscription capability checks.

The local Terraform state and binary plan are intentionally ignored. The plan
file can expose subscription structure and the state contains the notification
email.
