# Azure for Students deployment progress, 1 Nov 2026 NZDT

For the subsequent partial production apply and recovery plan, see
[`production-recovery-2026-11-02.md`](production-recovery-2026-11-02.md).

## Completed

- The active Azure management token was checked immediately before planning:
  its authentication methods included `mfa`. No token or account identifier is
  recorded here.
- Bootstrap was planned against the approved 13-create resource set. The first
  apply created the resource groups, GitHub managed identity and federated
  credentials, role definition, and several role assignments. It stopped while
  the AzureRM provider tried shared-key Blob access on the state account, where
  shared keys are disabled.
- The state account was verified as Standard LRS in Australia East, with shared
  keys and anonymous Blob access disabled. Terraform had marked it tainted
  solely because the data-plane check failed. Entra data-plane access was
  confirmed, `storage_use_azuread` was enabled in the Bootstrap provider, and
  the erroneous taint was cleared. The remaining plan created the state
  container and two previously approved Blob roles and finished the account's
  approved versioning and 14-day retention settings. No resource was deleted.
- Guardrails remote state was initialized in the new state container. The first
  budget apply was rejected because the October start date was earlier than the
  current billing month; none of the budgets was created. A fresh plan with a
  1 November start date contained exactly three creates: `spend-alert-1` (NZD
  2), `spend-alert-3` (NZD 5), and `spend-alert-5` (NZD 8). Apply succeeded with
  three creates, zero changes, and zero destroys. The notification recipient
  was confirmed by the owner in masked form outside the repository; its value
  is absent from this evidence.
- Fresh state-aware read-only plans after both applies reported no changes for
  Bootstrap and Guardrails.

## Production review stop

The formal production plan uses remote state, the real GitHub managed-identity
principal, the confirmed notification recipient, and a 1 November budget start.
It contains **50 creates, zero changes, zero destroys**. Against the previous
50-create plan, the resource-value differences are limited to the three
container-scoped GitHub role assignments' principal IDs and the
`budget-killswitch` start date. Resource types, role names and scopes, and
network exposure are otherwise unchanged. The reviewed estimate remains NZD
0.50-1.60 for a normal demonstration month plus low-volume host storage; actual
production spend cannot yet be measured.

The saved formal plan is kept only at ignored
`tmp/m1-a-production-formal.tfplan`; its SHA-256 is
`E39F2B2DDE659BB8A87377D8D6BDEE87D55C6A89B5CE88511AC1ECF82246413D`.

The instruction for production apply permits replacing the placeholder
principal ID only. The budget start date must also move from October to
November or Azure will reject it, as the Guardrails attempt demonstrated. This
extra plan difference needs project-manager approval. **No production apply,
reference upload, Function deployment, or Azure acceptance has occurred.** The
public website URL, cloud event latency, ACS mail flow, budget-stop rehearsal,
Azure/local table-hash comparison, and actual production cost remain pending.

All saved plan binaries, raw output, state, and backend coordinates remain in
ignored local paths. No subscription ID, tenant ID, email address, or key is
committed here.
