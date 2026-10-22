# NZ Hazard Exposure Monitor

An Azure-hosted demonstration system for estimating New Zealand earthquake
exposure using building count, building footprint and 2023 Census population.

## Status

M1 is in progress. M0 feasibility findings and evidence are available under
[`docs/`](docs/) and [`evidence/m0/`](evidence/m0/). Production infrastructure
is not created until its Terraform plan is approved.

## Important limitations

- The system has no insurance policy data. "Exposure" means building count,
  building footprint and population.
- Estimated Modified Mercalli Intensity is illustrative, not an actuarial,
  engineering or emergency-management conclusion.
- Building appearance and disappearance dates are approximate inferences from
  aerial imagery and source lifecycle metadata.
- Population is published 2023 SA1 population distributed within each SA1 by
  current building footprint. SA1 is coarser than meshblock and Stats NZ applies
  confidentiality treatment to small-area counts.

## Repository layout

```text
app/                  Azure Functions application
dbt/                  DuckDB/dbt transformation project
infra/bootstrap/      one-time remote-state storage
infra/providers/      explicitly approved Azure provider registrations
infra/identity/       Entra applications and GitHub OIDC bootstrap
infra/guardrails/     independent subscription budget root module
infra/terraform/      production Azure infrastructure
scripts/              build and verification tooling
docs/                 method, architecture and operating documentation
evidence/              sanitized milestone evidence
```

## Local checks

```bash
python -m pip install -r requirements-dev.txt
ruff check app scripts
pytest
sqlfluff lint dbt/models --dialect duckdb
dbt build --project-dir dbt --profiles-dir dbt/profiles --target duckdb_local
```

Terraform roots must be initialized and validated independently. They never
share state references. Runtime secrets are provided by managed identity and
Key Vault; no long-lived credentials belong in this repository or GitHub CI.

## Data attribution

- Earthquakes and intensity: GeoNet / Earth Sciences New Zealand, CC BY 3.0 NZ.
- Shaking Layers Dataset: Earth Sciences New Zealand, DOI 10.21420/J856-2J84.
- Building outlines: Land Information New Zealand, CC BY 4.0.
- Census and boundaries: Stats NZ, CC BY 4.0. Counts may be randomly rounded or
  suppressed for confidentiality.

## Licence

Project code is licensed under the [MIT License](LICENSE). Third-party data and
generated data products retain their source licences and attribution terms.
