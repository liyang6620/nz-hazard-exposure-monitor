# Milestone M1-L Acceptance Package

## 1. Completed work

- Reorganized the application into `core`, `ports`, local and Azure adapters,
  and separate local and Azure Functions hosts. Both hosts call the shared
  `HousekeepingService`. An AST test rejects any `azure` import from `core`.
- Added the supported local deployment: a locally built FastAPI/APScheduler
  image, filesystem containers matching the ADLS layout, SQLite tables and
  queues, Mailpit, and Caddy. SQLite implements message receipts, visibility
  timeouts, dequeue counts, retries, and poison queues.
- Added startup catch-up. The shared housekeeping path reads the last successful
  run and queries both New Zealand longitude partitions through GeoNet FDSN
  `updatedafter` before normal polling resumes.
- Added local adapters for environment secrets, SMTP, the OpenAI Responses API,
  and static-site publishing. `ARCGIS_PUBLISHER_ENABLED` defaults to `false` and
  the single-writer rule is documented.
- Added the Azure Functions host skeleton. Core Tools indexes `housekeeping` and
  `budget_stop` locally with Azurite; no Azure deployment was performed.
- Added the normalized parity-hash framework and explicit M1-only synthetic
  fixtures for the Christchurch 2011 and Kaikoura contracts.
- Added locked DuckDB `azure`, `httpfs`, `spatial`, and community `h3`
  extensions. A clean Linux build verifies hashes, loads all extensions from
  local files, and runs `h3_latlng_to_cell` without online installation.
- Removed public subscription identifiers, added the local deployment guide,
  and documented one-command startup in the README. `.env`, local state,
  downloaded extensions, and deployment packages are ignored.
- Expanded CI for Python/dbt checks, Docker Compose smoke testing, Terraform
  static validation, Linux package construction, and public-identifier scans.
  `terraform-plan.yml` and `deploy.yml` remain hard-disabled.

## 2. Evidence

- PR: <https://github.com/liyang6620/nz-hazard-exposure-monitor/pull/1>
- Current PR checks: <https://github.com/liyang6620/nz-hazard-exposure-monitor/pull/1/checks>
- Unit and contract tests: 29 passed; branch coverage 93.02% (minimum 80%).
- Static/data checks: Ruff check and format passed; SQLFluff passed; dbt built
  one seed and one model with `PASS=2`; Terraform formatting passed and all five
  roots validated. `infra/bootstrap` has one provider deprecation warning.
- Local deployment: `docker compose up --build --detach --wait` started the app,
  Mailpit, and Caddy. `/health` returned `status=ok`, `environment=local`, and
  `arcgis_publisher_enabled=false`. The locally built application image is
  141,906,615 bytes.
- Housekeeping: the live startup catch-up completed successfully from a 48-hour
  lookback and enqueued four GeoNet events. The success row is stored in the
  local `runs` table.
- Mail and web: Mailpit received the subject `M1-L local mail check`; Caddy served
  the local NZ Hazard Exposure Monitor page.
- Azure host local check: Functions Core Tools 4.16.0 initialized the Python
  worker, indexed `budget_stop` and `housekeeping`, and acquired the timer host
  lock through Azurite. Calling `budget_stop` in local mode returned the designed
  Azure-only 501 response and completed without an exception.
- Linux/H3 evidence: [package-size.json](package-size.json). The ZIP is
  162,961,540 bytes with 837,038,460 bytes of headroom below the 1 GB limit. The
  offline H3 call returned cell `615782128600219647`.
- Replay evidence: [parity-hashes.json](parity-hashes.json). Both event contracts
  reproduced their locked normalized hashes at six-decimal float precision.
- The repository scan found no committed subscription ID, tenant ID, personal
  email address, `.env`, credential, or downloaded extension binary. Only
  `example.invalid` test addresses are present.

## 3. Deviations from the plan

- The M1-L replay inputs are deliberately small synthetic contract fixtures,
  not representations of the two historical earthquakes. This follows the M1-L
  requirement to create the framework; M3 replaces them with licensed,
  reproducible event snapshots and real gold tables.
- Azurite is an optional `azure-dev` Compose profile rather than part of the
  supported local deployment. It is used only to exercise the Azure host.
- The Compose file is at the repository root so the documented command remains
  exactly `docker compose up`; the local host implementation stays under
  `hosts/local`.

## 4. Risks and unresolved issues

- **Azure deployment acceptance:** managed-identity access, Flex deployment,
  ACS delivery, Azure alerts, budget stop, remote guardrails state, actual cloud
  package behavior, and local/Azure hash equality remain unverified until the
  Microsoft account is restored. No local evidence is presented as Azure proof.
- The Azure adapters are contract-level skeletons. They need integration tests
  against the approved subscription during M1-A.
- `infra/bootstrap` validates with a warning that
  `azurerm_storage_container.resource_manager_id` is deprecated for provider
  5.0. This is non-blocking for the locked 4.81.0 provider and should be removed
  during M1-A before a provider-major upgrade.
- The first live startup request encountered a transient HTTP failure; the next
  housekeeping run succeeded and persisted its checkpoint. Scheduled retry is
  the intended recovery path.

## 5. Decisions requested from the project manager

1. Accept M1-L and authorize work to begin on M2.
2. Confirm that the real licensed replay snapshots remain an M3 deliverable;
   M2 will continue to run the locked M1 contract fixtures in local CI.

No Terraform apply, provider registration, Azure resource creation, state
migration, Azure deployment, paid inference, or external account registration
is requested by this acceptance package.

## 6. Actual milestone cost

- Azure cost attributable to M1-L: **NZD 0**. No Azure mutation or paid Azure
  operation was performed.
- OpenAI API cost: **NZD 0**. The adapter was tested without making an inference.
- The account restriction prevents a current Azure Cost Management screenshot;
  this is retained as Azure deployment acceptance rather than fabricated.
