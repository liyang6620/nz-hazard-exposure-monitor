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

Pass `subscription_id` and `contact_email` through environment variables or an
untracked `.tfvars` file. Never commit personal contact details or credentials.

The subscription billing currency is NZD. The approved fixed thresholds remain
NZD 2, NZD 5 and NZD 8, and all three resources have `prevent_destroy`.
