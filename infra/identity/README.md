# Microsoft Entra identities

This owner-run root bootstraps two secretless identities:

- the GitHub Actions workload identity, restricted to this repository's pull
  requests and protected `main` branch;
- the audience application used by Azure Monitor's secure webhook and Function
  App Easy Auth.

The GitHub identity receives its remote-state container role here and its
production RBAC assignments in `infra/terraform`. It is not granted Microsoft
Graph application permissions, so future identity-root plans remain an
owner-run operation. Apply only an approved saved plan.
