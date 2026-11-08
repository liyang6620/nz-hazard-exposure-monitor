# Section 16 final acceptance ledger

Source: the project manager's original 17-point section 16 and constraints
C1-C10, supplied by the owner on 9 Nov 2026. This ledger preserves the
mid-project decisions. **Completed** means the cited scope was observed;
**Cancelled** means the owner approved removal or an explicit exception;
**Unverified** means evidence is insufficient. A working component does not
turn a wider unverified requirement into a pass.

## Owner-supplied acceptance basis

The owner supplied the previously missing section 16 and C1-C10 text on
9 Nov 2026. The numbered requirements below retain the original scope;
the status tables after them apply the project's later decisions.

1. On a clean computer, `docker compose up` starts the complete local system
   following the README. Core code has no Azure dependency, and local/Azure
   consistency tests pass.
2. C1-C10 are all met; billing proves cloud cost is at most US$3/month; Esri
   pay-as-you-go has never been enabled.
3. ArcGIS has an automatically updated hosted layer, web map, File
   Geodatabase, cross-validation and technical explanation. Neither the web
   page nor repository contains a long-lived Esri key.
4. Production runtime does not depend on GitHub; inspect every address it
   accesses at runtime.
5. No keys in repository or CI; managed identity and OIDC are configured
   correctly.
6. Fixed-amount alerts live in `infra/guardrails/` with `prevent_destroy`;
   anomaly alert follows D19; `budget-killswitch` and automatic stop are
   exercised.
7. Evidence shows a new event reaches gold within one polling period, and
   the five-minute configuration was tested.
8. Evidence covers idempotence, fault injection and weekly full rebuilds.
9. All ten historical events replay and their figures are traceable.
10. Formula-estimate error is reported.
11. Power BI has a PBIP, screenshots, PDF and video, with visible limitations;
    Power BI files contain no keys.
12. Briefing has an end-to-end demo and approval-security tests; numeric
    fidelity is 100% or exceptions are explained.
13. MCP demo and Esri MCP briefing map, fallback, quota, whitelist and local
    combined demo are evidenced.
14. Snowflake reconciliation and comparison document exist.
15. Every README figure is backed by an observed result; limitations are
    complete.
16. Eleven ADRs, runbook, cost document, demo script and video exist.
17. Migration and backup procedures were rehearsed once.

| ID | Original constraint |
| --- | --- |
| C1 | Total cloud cost is at most US$3/month. |
| C2 | GitHub serves only code hosting and CI/CD; production runtime uses no GitHub service. |
| C3 | Two production targets, Terraform-managed Azure and local Docker Compose, share core code and produce identical results; guardrails are separate. |
| C4 | No long-lived keys in code, configuration or CI; CI uses OIDC, runtime uses managed identity, and third-party credentials are only in Key Vault. |
| C5 | Observe GeoNet, LINZ and Stats NZ licences, credit them in README and commit no raw data. |
| C6 | Production runtime downloads no code or extensions; DuckDB extensions are packaged. |
| C7 | Label estimates, reproduce figures and mark uncertain claims unverified. |
| C8 | Snowflake runs only during its 30-day trial and is absent from production. |
| C9 | No school-account dependency. |
| C10 | Esri free tier only, never pay-as-you-go; whitelist services, expose no long-lived browser Esri key, keep publication failure non-fatal and do not use ArcGIS Pro. |

Accepted changes to this basis: the owner cancelled the M5 and M8 videos,
retaining the PBIP, five screenshots, PDF and five-minute interview script;
the Azure for Students school-account deployment is an explicit C9 exception,
expected to expire around October 2027 and requiring migration to a new
subscription. The direct `budget-stop` drill passed, but the natural budget
alert to Action Group to stop chain did not; the owner removed the NZD 1 drill
budget and the student tier does not support the D19 anomaly alert. C4 has
accepted exceptions for the ACS connection string and some Function settings,
the public browser LINZ tile key and a server-side ArcGIS owner-scope key;
GitHub OIDC deployment remains inactive pending repository configuration and
deployments use a local MFA session. The web map uses token-free option B.
The web frontend, Analyst Workbench, Desktop RLS, realtime processing repair
and outage record were added and accepted after the original checklist.
Stable-period actual daily cost and Snowflake per-run metered credits remain
unverified.

## Original section 16

| No. | Requirement | Status | Evidence and remaining boundary |
| --- | --- | --- | --- |
| 1 | Clean-computer local Compose deployment, Azure-independent core and local/Azure parity | **Unverified** | [CI local deployment](../.github/workflows/ci.yml) starts Compose on a clean runner and [Azure replay](../evidence/m1-a/azure-acceptance-2026-11-02.md) matched 56 Parquet objects. A separate clean physical-computer install has not been observed. |
| 2 | C1-C10 and a bill proving no more than US$3/month; Esri pay-as-you-go always off | **Unverified** | [Actual cost](cost.md) covers only an early, deployment-heavy part of November; no complete stable month or account-level Esri billing attestation. C4 and C9 have approved exceptions or pending work below. |
| 3 | ArcGIS automatic hosted layer, web map, File Geodatabase, cross-validation, technical explanation and no long-lived Esri browser/repository key | **Completed** | [Azure incremental handover](../evidence/m1-a/owner-assisted-acceptance-2026-11-04.md), [MG geodatabase/cross-validation](../evidence/mg/README.md), [map/credential contract](arcgis-operations.md) and [public map check](../evidence/m1-a/azure-acceptance-2026-11-02.md). The ArcGIS owner-scope key is server-side in Key Vault. |
| 4 | Production runtime must not depend on GitHub; inspect runtime destinations | **Completed** | [Source/configuration endpoint inventory](runtime-network-inventory.md) lists each application destination class and finds no GitHub processing call. GitHub links are optional user navigation. A packet-level egress capture was not performed. |
| 5 | No keys in repository/CI; managed identity and OIDC correct | **Unverified** | [CI identifier and frontend-key gates](../.github/workflows/ci.yml) and [managed-identity host check](../evidence/m1-a/analyst-workbench-azure-2026-11-08.md) pass, but [OIDC workflow enablement and matching trust subjects](github-oidc-completion.md) are pending project-manager review. Accepted runtime-setting and browser tile-key compromises are recorded in [ADR 0001](adr/0001-m1-security-and-cost-boundaries.md). |
| 6 | Protected fixed budgets, D19 anomaly alert, budget stop and automatic stop drill | **Unverified**; D19 alert **Cancelled** | [Guardrails Terraform](../infra/guardrails/main.tf) has `prevent_destroy`; [direct stop/recovery](../evidence/m1-a/azure-acceptance-2026-11-02.md) passed. D19 anomaly alert is unsupported on the student tier. The natural budget alert -> Action Group -> stop path was not tested; the [NZD 1 drill budget was removed](../evidence/m1-a/budget-drill-removal-2026-11-06.md). |
| 7 | New event reaches gold within one poll period; five-minute configuration test | **Completed** | [Genuine GeoNet event](../evidence/m1-a/azure-acceptance-2026-11-02.md) reached the public site in 32 minutes 9 seconds; the five-minute timer was exercised then restored to hourly. |
| 8 | Idempotence, fault injection and weekly full-rebuild evidence | **Unverified** | [Azure acceptance](../evidence/m1-a/azure-acceptance-2026-11-02.md) records duplicate-free catch-up and one 37-file exact-hash rebuild rehearsal; [poison exercise](../evidence/m1-a/owner-assisted-acceptance-2026-11-04.md) left gold hashes unchanged. A continuing weekly rebuild has not been observed. |
| 9 | Ten reproducible historical replays and traceable figures | **Completed** | [M3 event results](../evidence/m3/README.md), [Checkpoint A](../evidence/checkpoint-a/README.md) and [briefing/summary reconciliation](../evidence/frontend-pr1/briefing-summary-reconciliation.md). |
| 10 | Formula-estimate error reported | **Completed** | [Station validation](../evidence/checkpoint-a/README.md) reports 2,547 observations and MAE 1.049 MMI; [ADR 0002](adr/0002-d22-tvz-model-revision.md) records the model-branch limitation. |
| 11 | Power BI PBIP, images, PDF, video and visible limitations | **Completed**, video **Cancelled** | [M5 deliverables](../evidence/m5/README.md) and [Workbench RLS evidence](../evidence/analyst-workbench/README.md) are reviewed. The owner cancelled both M5 and M8 video requirements in [ADR 0006](adr/0006-m5-deliverables.md). PBIP sources contain no machine path or key under CI portability checks. |
| 12 | Briefing end-to-end approval/security and 100% numeric fidelity, or explanation | **Completed** | [M6 ten-event evaluation](../evidence/m6/README.md) passed 10/10 strict fidelity checks; [manual revision-3 approval](../evidence/frontend-pr1/README.md) and [Azure GET/POST, expiry, tamper and replay checks](../evidence/m1-a/azure-acceptance-2026-11-02.md) were recorded. The 100% figure describes that evaluated set, not an unconditional future guarantee. |
| 13 | MCP demo and Esri MCP static map, fallback, quota, whitelist and local combined demo | **Completed** | [M6 local MCP/briefing workflow](../evidence/m6/README.md), [MG Esri MCP PNG and free-quota record](../evidence/mg/README.md), and [server-only whitelist/limits](arcgis-operations.md). Static-map failure is non-fatal. |
| 14 | Snowflake reconciliation and platform comparison | **Completed** | [M7 trial](../evidence/m7/trial-benchmark-2026-11-08.md) passed dbt/parity and timed both workloads; [comparison](platform-comparison.md) is published. Actual per-run credits still await delayed administrator Account Usage, so the cost comparison is provisional. |
| 15 | Every README number sourced and limitations complete | **Completed** | [README](../README.md) links publication, replay, M7 and [dated cost evidence](../evidence/m8/cost-2026-11-09.md); limits and unsupported claims are explicit. |
| 16 | Eleven ADRs, runbook, cost document, demo script and video | **Unverified**, video **Cancelled** | [ADR 0001-0011](adr/), [runbook](runbook.md), [cost](cost.md) and [five-minute script](interview-demo.md) exist. The owner cancelled video in [ADR 0006](adr/0006-m5-deliverables.md); a stable-period actual daily cost is still unavailable. |
| 17 | Migration and backup rehearsal | **Unverified** | [Read-only state backup and 56-file migration preflight](../evidence/m1-a/azure-acceptance-2026-11-02.md) were exercised without a new subscription or mutation. A full restore/cutover to another subscription was not exercised; [runbook](runbook.md#move-to-another-subscription) documents it. |

## Constraints C1-C10

| ID | Constraint | Status | Evidence and accepted deviation |
| --- | --- | --- | --- |
| C1 | All cloud cost <= US$3/month | **Unverified** | [Cost Management daily rows](../evidence/m8/cost-2026-11-09.md) are actual NZD charges but not a complete steady month. The 5-7 Nov observed average includes deployments. No US$ monthly pass is inferred. |
| C2 | GitHub only for code/CI/CD, never a production runtime service | **Completed** | [Runtime endpoint inventory](runtime-network-inventory.md); user-clickable repository links and a GeoNet User-Agent URL do not make processing depend on GitHub. |
| C3 | Azure Terraform and local Compose share the core and produce consistent results | **Completed** | [Azure/local 56-file parity](../evidence/m1-a/azure-acceptance-2026-11-02.md), [local CI host](../.github/workflows/ci.yml), and [two-host architecture](../README.md#architecture). The separate clean physical-computer installation in item 1 remains unverified. |
| C4 | No long-lived keys in code/config/CI; OIDC for CI; managed identity; third-party keys only in Key Vault | **Unverified** | Repository/CI key gates and runtime managed identity are in place, but GitHub OIDC deploy is inactive. [ADR 0001](adr/0001-m1-security-and-cost-boundaries.md) records the approved ACS/Function-setting sensitive values, public browser LINZ key and server-side ArcGIS Key Vault key. The original absolute wording has these accepted compromises. |
| C5 | Source licences and README attribution; no raw data committed | **Completed** | [Source/licence assessment](data-sources.md), [README attribution](../README.md#data-attribution) and ignored raw-source workflow in [ADR 0010](adr/0010-linz-full-export-instead-of-wfs.md). |
| C6 | No runtime code/extension download | **Completed** | [M0 local extension verification](phase0-findings.md) and [Function package build](../scripts/build_function_package.sh) embed tested DuckDB extensions; the Azure setting points at packaged files. Package construction downloads dependencies before deployment. |
| C7 | Estimates labelled, figures reproducible, uncertainty marked unverified | **Completed** | [Method](methodology.md), [M7 comparison](platform-comparison.md), [cost record](cost.md) and this ledger distinguish estimates, actuals and gaps. |
| C8 | Snowflake only in 30-day trial, outside production | **Completed** | [M7 trial evidence](../evidence/m7/trial-benchmark-2026-11-08.md) verifies the guarded trial and suspended warehouse; [ADR 0007](adr/0007-duckdb-production-after-snowflake-trial.md) retains DuckDB production. |
| C9 | No school-account dependency | **Cancelled: approved exception** | Personal Microsoft account recovery was blocked; production uses Azure for Students under a school account expected to expire around Oct 2027. [ADR 0003](adr/0003-student-subscription-acceptance-boundaries.md) and [migration runbook](runbook.md#move-to-another-subscription) disclose this. Migration is not yet proved. |
| C10 | Esri free tier only, no pay-as-you-go, whitelisted services, no browser Esri key, publication failure non-fatal, no ArcGIS Pro | **Unverified** | [MG usage](../evidence/mg/README.md) and [Azure publisher](../evidence/m1-a/owner-assisted-acceptance-2026-11-04.md) are under the project limits; [operations](arcgis-operations.md) constrain services and keep keys server-side. No account-level billing-state attestation proves pay-as-you-go was never enabled. |

## Added, accepted product scope

The [public React site and deep links](../evidence/m1-a/analyst-workbench-azure-2026-11-08.md),
[Analyst Workbench and Desktop RLS](../evidence/analyst-workbench/README.md),
and [real-time processing repair and 11-hour outage record](../evidence/m1-a/hourly-publication-incident-2026-11-03.md)
were added after the original checklist and have their own acceptance
evidence. They do not erase the unverified items above.
