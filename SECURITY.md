# Security policy

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability or exposed credential.
Use GitHub's private vulnerability reporting for this repository. Include the
affected component, reproduction steps and potential impact without including
live credentials or personal information.

## Supported version

Only the current `main` branch is supported during development.

## Security boundaries

- Production uses managed identity; GitHub uses OIDC federation.
- Third-party credentials are stored only in Azure Key Vault.
- Terraform state is remote, private, versioned and protected by soft delete.
- GitHub is never part of the production runtime.
- Esri pay-as-you-go must remain disabled.
