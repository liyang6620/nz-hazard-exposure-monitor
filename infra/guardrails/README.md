# Cost guardrails

This is an independent Terraform root module for the three subscription-level
fixed-amount budgets. It must not be referenced by the main infrastructure
module.

The module initially uses local Terraform state because the M1 remote-state
storage account does not exist yet. M1 must migrate this state to its own
Azure Storage backend key before changing the module.

Pass `subscription_id` and `contact_email` through environment variables or an
untracked `.tfvars` file. Never commit personal contact details or credentials.

All three resources have `prevent_destroy`. Any apply after the initial M0
creation requires the normal project-manager approval process.
