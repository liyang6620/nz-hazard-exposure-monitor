# Phase 0 findings

Assessment date: 2026-10-22. Status terms are **verified** (directly observed),
**documented** (supported by vendor documentation), and **unverified** (requires
a resource/account that M0 was not authorised to create).

## Preparation and guardrails

- **Verified:** the production identity is a personal Gmail-backed Microsoft
  account; no school identity is used. This differs from section 3.1's 163
  address and requires PM ratification.
- **Verified:** Azure Free Account registration date is 2026-10-22,
  subscription `5f4500df-375b-4a36-a973-c807e23e04b2`, billing currency NZD.
- **Verified:** the subscription is enabled and currently contains no ARM
  resources. ArcGIS registration remains correctly deferred to MG.
- **Verified:** subscription budgets `spend-alert-1`, `spend-alert-3`, and
  `spend-alert-5` exist with the required amounts and notifications. The saved
  creation plan contained exactly three
  `azurerm_consumption_budget_subscription` creates. The apply added three,
  changed zero and destroyed zero. A refresh plan now reports no changes.
- **Verified:** all three Terraform resources have `prevent_destroy`, the
  contact address is a sensitive variable, and the module has independent local
  state pending M1 state migration.
- **Known deviation:** the first provider initialisation registered
  `Microsoft.AVS` even though no AVS resource was created. Registration is not a
  billable resource, but it was an unintended subscription state change. It has
  not been unregistered because that is another state-changing operation.
- **Not a blocker (D19):** Cost anomaly alerts are reported as unsupported for
  the current free subscription. Recheck after PAYG upgrade and add one through
  the normal approval flow only if supported.

## Data and scientific method

Detailed source results are in [data-sources.md](data-sources.md) and the model
baseline is in [methodology.md](methodology.md).

- **Verified:** FDSN v1.2 supports `updatedafter`, has a 10,000-event response
  cap, and returns XML/text rather than GeoJSON. The complementary Quake API is
  GeoJSON and exposes current quality, including deleted state.
- **Verified:** the live Intensity API is a present-state endpoint. Historical
  Shaking Layers packages provide versioned MMI files and `stationlist.json`.
- **Verified:** the Shaking Layers API has published versions for all nine
  fixed historical events named in section 10.4. The tenth event is selected in
  M3 to satisfy the rolling recent-event requirement.
- **Verified:** LINZ layer 101292 contains 6,634,223 building polygons and the
  lifecycle/capture fields listed in the design. The authoritative licence is
  CC BY 4.0.
- **Blocked on PM decision, not technology:** no public 2023 meshblock total
  population layer was found. Stats NZ layer 120766 supplies 33,164 SA1 areas
  and `VAR_1_3` is the 2023 census usually resident population count. Layer
  111225 supplies meshblock and higher-geography boundaries.
- **Verified:** the Dowrick and Rhoades (2005) equations and coefficients were
  recovered from the paper. The paper does not provide a suitable worked
  numeric example, and the input data does not support all regional/mechanism
  variants. Model selection and test-oracle substitution require PM approval.

## Azure Functions and deployment

- **Verified in subscription:** Flex Consumption is offered in
  `australiaeast`. Python 3.10-3.14 are listed. The current memory choices are
  512, 2,048 (default) and 4,096 MB; maximum instances can be set as low as 1.
  M1 should use Python 3.12, 2,048 MB and maximum instances 1.
- **Documented:** Flex timeout defaults to 30 minutes and is unbounded when
  configured, with a 60-minute scale-in grace period and 10-minute platform
  update grace period. HTTP responses still have a 230-second load-balancer
  limit. See <https://learn.microsoft.com/azure/azure-functions/functions-scale>.
- **Documented:** the deployment ZIP limit is 1 GB. See
  <https://learn.microsoft.com/azure/azure-functions/deployment-zip-push>.
- **Verified locally:** pinned M0 packages (dbt-duckdb, DuckDB, Azure Functions,
  identity and Blob SDKs) plus `azure`, `httpfs`, and `spatial` DuckDB extensions
  occupied 598,821,960 bytes uncompressed and 181,746,036 bytes compressed.
  The sample is below the ZIP limit but close enough to Flex temporary-storage
  limits that M1 must prune tests/caches and report the Linux build size.
- **Verified locally:** with extension auto-install and auto-load disabled,
  DuckDB loaded all three extensions from local files and executed a spatial
  query. This satisfies C6's packaging premise.
- **Partly verified:** DuckDB accepts `CREATE SECRET` with Azure
  `CREDENTIAL_CHAIN` and `CHAIN 'managed_identity'`. Real ADLS read/write was
  not possible without creating storage. M1 must test it; the approved fallback
  is Azure SDK download to local temporary storage, local dbt execution, then
  SDK upload.
- **Verified locally:** DuckDB Spatial's bundled GDAL reports OpenFileGDB create
  support. A point File Geodatabase was written and read back successfully.
- **Documented:** GPv2 storage supports static website hosting. M1 can enable it
  with Terraform without a separate service.

## Azure AI and email

- **Verified in subscription:** one Azure OpenAI S0 account is allowed in
  Australia East. Contrary to an earlier coarse quota check, Global Standard
  chat quota is available for some models: `gpt-5-mini` currently has 500k TPM,
  `gpt-4.1-mini` 200k TPM and `o4-mini` 100k TPM. `gpt-5-mini` is listed as GA
  with chat and Responses capabilities. Creating and testing the resource is a
  paid/state-changing M1 operation and needs the normal approval.
- **Documented:** Azure Communication Services Email supports an Azure-managed
  domain and token credentials/`DefaultAzureCredential`; the Python SDK can use
  the Function managed identity. See the
  [send-email quickstart](https://learn.microsoft.com/azure/communication-services/quickstarts/email/send-email).
- **Unverified:** actual managed-domain provisioning, the minimum runtime RBAC
  role, delivery to the owner Gmail account/spam placement and actual per-email
  cost require the M1 resources. If managed identity fails, the design's
  connection-string-in-Key-Vault fallback remains permitted.

## Budget accounting and cost

- **Unverified without billable usage:** no ARM resources or usage records
  exist, and the Cost Management query API returns that the free subscription
  does not have a supported WebDirect/AIRS offer. Therefore M0 cannot empirically
  prove whether a budget evaluates usage before the USD 200 credit is applied.
  No paid usage was created merely to test an alert. Treat fixed budgets as
  notification defence only; the M1 durable switch plus ARM stop is the hard
  control.
- **Current M0 cost:** NZD 0.00. The only created objects are no-charge
  subscription budgets; the subscription resource list is empty.
- **Estimated steady state:** approximately USD 0.25-0.90/month (roughly NZD
  0.45-1.60 at an illustrative 0.56 USD/NZD), excluding unusual rebuilds. Flex
  executions are expected to remain inside its recurring free grants. Storage,
  transactions, Key Vault operations, sparse email and small LLM briefings are
  the variable components. This is an engineering range, not a quote; M1 must
  obtain current Australia East price exports before apply and every milestone
  reports actual Cost Management data.
- **Free-period sensitivity:** the Azure Free Account's 12-month offers may
  cover the first 5 GB of LRS storage and limited operations. Those benefits
  expire; the estimate above assumes storage is paid, so projected post-month-12
  cost remains below the USD 3 cap. Flex grants are part of Flex pricing rather
  than the 12-month account promotion. Azure OpenAI and ACS Email have no
  assumed promotional credit in the estimate.

The estimate uses deliberately small but explicit operating assumptions. It is
not an Azure quote and must be refreshed from the price sheet before M1 apply.

| Component | Monthly assumption | Expected USD | Free-period / post-12-month treatment |
|---|---:|---:|---|
| Functions Flex | 3,000 GB-s, about 1,500 executions | 0.00-0.08 | The 100,000 GB-s and 250,000 execution grants are documented as recurring Flex grants. Even with no grant, this workload is about USD 0.08 at representative rates. Live invoice applicability is unverified. |
| Storage/ADLS and Terraform state | 5-15 GB LRS plus low transaction volume | 0.10-0.35 | The Free Account may cover its first 5 GB and limited operations for 12 months. The upper estimate assumes paid storage after expiry. |
| Tables, queues and static website | Low thousands of operations, under 1 GB | 0.01-0.05 | No reliance on a promotional credit. |
| Key Vault | Under 10,000 operations | 0.00-0.03 | May be covered during the free period; the upper estimate assumes paid operations. |
| Application Insights / Log Analytics | Expected under 0.1 GB/month; hard cap 0.1 GB/day | 0.00 | Expected ingestion is inside the documented monthly free allowance. A cap is a ceiling, not an expected 3 GB usage budget. |
| Metric alert and budgets | One metric rule; four budgets after M1 | 0.00 | Expected inside free metric-alert allowance; budgets are no-charge management objects. |
| ACS Email | Up to 20 small operational emails | under 0.01 | Pay per use; no promotional allowance assumed. |
| Azure OpenAI | Up to 10 short briefings, tightly capped | 0.03-0.20 | Pay per token; no promotional allowance assumed. Exact model price is rechecked before deployment. |
| **Total** | Normal demonstration month | **0.25-0.90** | Includes headroom for transactions and price variation; remains below USD 3. |

## Automatic stop design for M1

Use a durable `budget_stop` row in Azure Table Storage as the first-line switch.
Every paid function checks it before work. The budget Action Group calls an
Entra-authenticated HTTP function; that function sets the row, attempts an ACS
email, and uses its managed identity to invoke ARM stop on the sole Function
App. Recovery is manual and documented. This avoids repository secrets and
continues to block work even if the app later restarts. M1 must prove the
Action Group authentication and narrow custom ARM permission during the
approved drill.

## Power BI Desktop

- **Verified locally:** Power BI Desktop 2.155.756.0 is installed. Its shipped
  components include Parquet, ADLS/File Data Lake, and Azure Maps visual assets.
- **Not end-to-end verified:** no ADLS resource exists, so personal-account
  authentication to an actual `gold` container cannot be tested in M0. Windows
  UI automation also failed to attach to the newly opened Power BI window; no
  claim is made from that attempt.
- **Recommended decision:** select option 2 for M5: use `az storage blob
  download-batch --auth-mode login` and import local Parquet. It has no account
  key, is scriptable, avoids connector token persistence, and remains valid if
  the personal-account ADLS connector path later fails. Azure Maps is bundled;
  its actual render remains an M5 acceptance test, with centroid bubbles as the
  documented fallback.

## ArcGIS and Esri MCP

No ArcGIS account was registered, as required before MG. These are documentation
findings, not live account tests.

- **Documented current free allowances:** 250 MB feature storage, 250 MB
  files/attachments, 125 MB feature queries, 125 MB feature edits, two million
  basemap tiles, 1,000 basemap sessions and 1,000 static maps per billing cycle.
  Project caps remain half of feature storage and 200 static maps. Services with
  no free allocation remain prohibited by C10.
- **Documented behaviour:** with pay-as-you-go disabled and no payment method,
  exhaustion suspends the affected service until reset; it does not authorise
  billing. MG must screenshot and verify this in the owner account before use.
- **Publisher authentication risk:** ArcGIS API keys/app credentials are
  suitable for location services and scoped item access, but M0 found no
  authoritative guarantee that an API key can create and update owner-hosted
  feature layers unattended. Plan for OAuth user authorisation with a refresh
  token in Key Vault; PM approval is required because this differs from the
  plan's `esri-publisher-key` wording.
- **Map token:** OAuth app credentials can issue short-lived app tokens, but
  access to same-account private hosted layers must be tested after MG account
  creation. If item sharing/scoping cannot meet least privilege, use plan B
  (static-site GeoJSON and no browser Esri token).
- **Verified toolchain:** DuckDB/GDAL OpenFileGDB write and read works locally.
- **Esri MCP:** the hosted beta endpoint is
  `https://location-services-mcp.arcgis.com/beta/mcp` and uses Streamable HTTP.
  Tools documented in M0 are `find_address_candidates`, `reverse_geocode`,
  `solve_route`, `elevation_at_locations`, `map_with_overlay`,
  `get_topic_fields`, `describe_location`, and `buffer`. Only
  `map_with_overlay` is allowed by this project. It accepts point, polyline and
  polygon overlays and returns a base64 PNG. Successful calls are charged to
  their backing service; geocoding is stored geocoding and has no free tier, so
  all non-static-map tools remain blocked. References:
  <https://developers.arcgis.com/ai/mcp-arcgis-location-services/> and the
  [ArcGIS Location Platform pricing page](https://location.arcgis.com/pricing/).

## Decisions required from the project manager

1. Ratify Gmail as the production identity in place of the plan's 163 address.
2. Choose SA1 population allocation or identify another authoritative public
   meshblock population source.
3. Select the supported Dowrick-Rhoades region/depth model and define `r`,
   `hc`, crustal classification and TVZ/interface/deep handling.
4. Approve an independently reproduced equation value as the unit-test oracle
   in place of a nonexistent published worked example.
5. Confirm Azure OpenAI `gpt-5-mini` as the preferred D2 path, subject to an
   approved M1 create/test plan.
6. Approve OAuth user authentication/refresh token in Key Vault for ArcGIS
   publishing if an API key cannot update hosted layers.
7. Accept the unintended `Microsoft.AVS` provider registration or direct a
   separately approved unregister operation.
8. Confirm the local-sync Power BI connection choice.

## M1 verification gates

The following are explicitly deferred because each needs approved resources:

- live DuckDB managed-identity ADLS read/write;
- Flex Linux deployment package size, cold start and temporary-space headroom;
- ACS managed domain, least-privilege role, Gmail delivery and price;
- static website enablement;
- Azure OpenAI resource/model deployment;
- budget evaluation with real usage;
- secure Action Group to `budget_stop` and the complete stop/recovery drill.
