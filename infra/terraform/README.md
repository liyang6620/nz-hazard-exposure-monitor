# Production infrastructure

This root owns the M1 production resources and never references the independent
fixed-amount budgets in `infra/guardrails`.

The remote backend coordinates and all identity values are provided at init or
plan time and are never committed. For a pre-bootstrap review, initialize with
`terraform init -backend=false`. After approval and bootstrap apply, initialize
the remote backend with its approved coordinates.

No `terraform apply` is permitted until the saved plan has been approved by the
project manager and repository owner. The Azure OpenAI model version and
regional availability must be rechecked immediately before apply.
