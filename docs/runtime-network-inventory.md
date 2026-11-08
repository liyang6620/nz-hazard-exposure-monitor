# Production runtime network inventory

Checked against the Azure host's container assembly, settings model, Python
HTTP clients and React fetch/tile calls on 9 Nov 2026. These are endpoint
classes, not public account or subscription identifiers. Actual Azure hosts
are injected through protected Function settings. User-clickable About,
Method and footer links to GitHub are navigation links, not processing
dependencies; the GeoNet User-Agent includes a repository URL but sends the
request to GeoNet.

| Caller | Destination class | Purpose / condition |
| --- | --- | --- |
| Function | `service.geonet.org.nz` | Hourly FDSN `updatedafter` event poll. |
| Function | `shakinglayers.geonet.org.nz` | Official Shaking Layers discovery and files; preferred over preliminary MMI. |
| Function | Azure Blob, Data Lake, Queue and Table endpoints for the configured data/host accounts | Reference/gold input, queue, run state and static-site publication through managed identity. |
| Function | Configured project Key Vault | Approval and ArcGIS server secrets through managed identity. |
| Function | Configured Azure OpenAI endpoint | Bounded briefing prose only after the populated-MMI trigger. |
| Function | Configured ACS Email endpoint | Human review messages and operational mail. |
| Function | `www.arcgis.com` and a validated `services*.arcgis.com` hosted-layer URL | Bounded incremental private-layer publication; item URL, schema and quota are checked before edits. |
| Function | `location-services-mcp.arcgis.com` | Optional server-side static-map tool, when explicitly enabled; failure does not stop the briefing. |
| Function | `management.azure.com` | Budget-stop Function action only after the authenticated switch path. |
| Browser | Same-origin Storage static website `/data/`, `/briefings/`, and report assets | Public runtime JSON, GeoJSON, approved HTML, PNG and PDF. |
| Browser | Configured Function review origin | Human GET preview and one POST decision; CORS permits only the public site. |
| Browser | LINZ LDS `tiles-*.data-cdn.linz.govt.nz` or fallback `tile.openstreetmap.org` | Public topographic/base tiles with attribution. No Esri browser key. |

The production event-processing path has no GitHub API, raw-content, Actions,
Packages or release endpoint. The repository's GitHub URLs are ordinary
optional user navigation. Local reference import has LINZ/Stats NZ WFS
fallbacks and local development has Mailpit/OpenAI paths; neither is an
Azure hourly runtime dependency. DuckDB extension downloads occur in the
build job; the Function package contains the checked extension files and
loads them locally. This is a source/configuration inventory, not a packet
capture of every third-party SDK or Azure platform service. A full runtime
egress trace remains unverified.
