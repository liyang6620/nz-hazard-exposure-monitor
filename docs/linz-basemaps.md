# LINZ Data Service topographic tiles

The event map uses the LINZ Data Service (LDS) raster tile endpoint when a
tiles-only browser key is configured. It shows **NZ Topo250 Maps** (layer
`50798`) for national and broad regional views and switches to **NZ Topo50
Maps** (layer `50767`) at zoom 10. Without the key it uses OpenStreetMap tiles.
Attribution is shown on the map as "© Toitū Te Whenua LINZ, CC BY 4.0" or
"© OpenStreetMap contributors", according to the active provider.

The owner has created the tiles-only LDS key `nzhem-basemaps-browser`. It is a
public browser key: the browser must send it in LDS tile URLs, so it must have
only tile-read permission. Keep the value in ignored `frontend/.env.local` as
`VITE_LINZ_LDS_TILES_API_KEY=...` for local Vite builds. For Docker Compose,
also set the same variable in the ignored repository-root `.env` because Compose
passes build arguments from that file. Rebuild the app image after changing it:

```bash
docker compose up -d --build app web
```

For GitHub Actions Azure deployment, set encrypted repository secret
`LINZ_LDS_TILES_API_KEY`. The deploy workflow supplies it to Vite only during
the frontend build. The value is not committed. Never reuse the server-only
`LINZ_API_KEY`, ArcGIS publisher key or OpenAI key in browser configuration.

The LDS tile URL follows the documented XYZ service shape:
`https://tiles-{a-d}.data-cdn.linz.govt.nz/services;key=<browser-key>/tiles/v4/layer=<id>/EPSG:3857/{z}/{x}/{y}.png`.
Both selected layers returned PNG tiles in a read-only test on 31 Oct 2026.
The separately operated `basemaps.linz.govt.nz` API rejects this LDS key as
malformed. The earlier instructions in this document incorrectly treated an
LDS key as a LINZ Basemaps key; that is now corrected.

The LDS key creation screen does not specify a fixed expiry. Treat the key as
valid until revoked or changed by LINZ or the owner; review it periodically.
LDS key guidance: [Creating an API key](https://www.linz.govt.nz/guidance/data-service/linz-data-service-guide/web-services/creating-api-key).
