# Production infrastructure

This root owns the M1 production resources inside the resource group pre-created
by `infra/bootstrap`. It never references the independent fixed-amount budgets
in `infra/guardrails`.

The remote backend coordinates and all identity values are provided at init or
plan time and are never committed. For a pre-bootstrap review, initialize with
`terraform init -backend=false`. After approval and bootstrap apply, initialize
the remote backend with its approved coordinates.

No `terraform apply` is permitted until the saved plan has been approved by the
project manager and repository owner. The Azure OpenAI model version and
regional availability must be rechecked immediately before apply.

The Function App is publicly reachable over HTTPS because application access
restrictions cannot distinguish browser approval routes from the budget route.
Every HTTP trigger therefore authenticates in application code. Terraform
generates the budget webhook token and approval HMAC key; both are held only in
protected state and Azure configuration. Never print them in plans, logs,
screenshots or evidence. Platform Function keys are not used as route
authentication.

The MG browser map uses the approved token-free static GeoJSON design. The
`map-token` route is disabled and returns 404. Its exact-origin and per-IP rate
guards are present, but an actual relay stays unavailable until a separate
read-only OAuth broker is approved; the owner-privileged ArcGIS publisher key
must never be returned to a browser.

After provider registration, the subscription did not expose the planned
`Azure Communication Services Email Sender` role. The Function therefore uses
the ACS connection string from protected Terraform state and its app settings.
This credential must not be logged or copied into evidence.

The product frontend replan adds a runtime table, an events poison queue,
three container-scoped GitHub upload roles and a separate Standard LRS Function
host storage account. `AzureWebJobsStorage` and deployment packages use that
account. The Function system identity has `Storage Blob Data Owner` only there;
its data-account roles remain at Contributor level. Fixed pages and every
published event route receive an HTML blob so direct links return HTTP 200;
`index.html` remains the 404 fallback for unknown routes. The conditional
review plan has 50 creates, up from the 47-create replan; see
[`evidence/m1-a/replan-2026-10-31.md`](../../evidence/m1-a/replan-2026-10-31.md).
The GitHub UAMI principal ID is supplied at plan time after bootstrap and is
never committed.
