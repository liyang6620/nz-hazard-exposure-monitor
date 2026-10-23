# Cost guardrails

This is an independent Terraform root module for the three subscription-level
fixed-amount budgets. It must not be referenced by the main infrastructure
module.

The module initially used local Terraform state because the M1 remote-state
storage account did not exist. After the bootstrap plan is approved and applied,
the owner migrates it with the approved backend coordinates:

```bash
terraform init -migrate-state \
  -backend-config="resource_group_name=<state-resource-group>" \
  -backend-config="storage_account_name=<state-storage-account>" \
  -backend-config="container_name=tfstate"
```

The migration is a state-changing operation and must not run before approval.

Pass `subscription_id` and `contact_email` through environment variables or an
untracked `.tfvars` file. Never commit personal contact details or credentials.

All three resources have `prevent_destroy`. Any apply after the initial M0
creation requires the normal project-manager approval process.
