# ArcGIS publishing and static maps

## Credential boundary

The publisher credential is an ArcGIS Location Platform **Private application
with all owner privileges**. It is intentionally a server-side credential. The
secret is read from `ARCGIS_API_KEY` through the secret-store port and must
never be embedded in HTML, JavaScript, map JSON, screenshots, logs, evidence or
test snapshots. Browser maps remain token-free or must use a separately
approved server-side token relay.

Despite its broad account privilege, the application is allowed to operate
only on NZHEM-owned project items. It must not change account, organization,
sharing or credential settings. Its Location Services access is limited to
Basemaps and Static Maps. Geocoding, routing, Places, Elevation and every other
location service are prohibited.

`ARCGIS_STATIC_MAPS_ENABLED=false` is the safe default. When enabled, the local
host constructs the Esri MCP adapter on the server. The adapter discovers the
available tools but calls only `map_with_overlay`. The guard reserves every
attempt before the request, allows at most two attempts for one briefing and
200 attempts per UTC month, and records success or failure in the table store.
A map failure does not block the briefing workflow.

The returned PNG is stored with the draft and added to the approved static page
only after the normal one-time POST approval. No credential is sent to the
browser or written into the image URL.

## Hosted feature layer

`event_exposure_r6` was published directly from a zipped File Geodatabase. Its
publication parameters set `Create,Delete,Query,Update,Editing`; no
`addToDefinition` or other layer-definition administration operation was used.
Incremental publication uses `applyEdits` and must preserve the service item
ID. Storage and feature-edit bandwidth are checked against the project limits
after publication.

The uploaded File Geodatabase source item is retained. It is only about 423
KiB, provides the traceable input needed to reproduce or overwrite the hosted
service, and leaves total storage far below the 125 MB project cap. Deletion is
not justified until an equally reproducible publishing artifact is stored
elsewhere.
