# Cost guardrails

This is an independent Terraform root module for the three subscription-level
fixed-amount budgets. It must not be referenced by the main infrastructure
module.

The previous local state belonged to a different subscription and is archived
under ignored `tmp/guardrails-old-subscription-2026-10-26/`. It must never be
migrated or used for this subscription. This module starts from empty state.

After the new bootstrap plan is approved and applied, initialize this root with
the new backend coordinates:

```bash
terraform init -reconfigure \
  -backend-config="resource_group_name=<state-resource-group>" \
  -backend-config="storage_account_name=<state-storage-account>" \
  -backend-config="container_name=tfstate"
```

Backend initialization and every apply remain approval-gated.

Pass `subscription_id`, `contact_email`, and `budget_start_date` through environment variables or an
untracked `.tfvars` file. Never commit personal contact details or credentials.
Set `budget_start_date` to the first day of the current billing month; Azure
rejects a new monthly budget whose start date is in an earlier month.

The subscription billing currency is NZD. The approved fixed thresholds remain
NZD 2, NZD 5 and NZD 8, and all three resources have `prevent_destroy`.
