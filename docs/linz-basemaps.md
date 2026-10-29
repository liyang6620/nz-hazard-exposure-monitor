# LINZ Basemaps browser key

The event map prefers the free LINZ Basemaps topographic vector tiles and falls
back to OpenStreetMap when no browser key is present. The website shows only the
active provider's normal attribution; missing configuration is not a
user-facing error.

To obtain the key:

1. Register or sign in to the
   [LINZ Data Service](https://data.linz.govt.nz/) account that will own the key.
2. Select the account name in the top menu, open **API Keys**, then select
   **Create API Key**.
3. Give it a project-specific label such as `nzhem-browser-basemap`, select
   **Data access only**, accept the applicable terms, and select **Add**. Do not
   use a key with upload or account-management permissions.
4. Put the value in `frontend/.env.local` as
   `VITE_LINZ_BASEMAPS_API_KEY=...` for direct Vite development, or in the
   repository-root untracked `.env` for the Docker Compose build.
5. Rebuild the `app` image because Vite embeds this public value at build time:
   `docker compose up -d --build app web`.
6. Open one event map and confirm that it says **LINZ basemap** and retains
   Toitū Te Whenua LINZ and CC BY 4.0 attribution.

This is a public browser key intended to appear in browser requests. It is separate
from `LINZ_API_KEY`, which authorises LINZ Data Service downloads, and from the
server-only ArcGIS and OpenAI credentials. Do not reuse those private credentials in
the frontend.

The LINZ creation screen and published instructions do not specify a fixed
expiry date for a data-access API key. Treat it as valid until it is deleted or
revoked by the account owner, or LINZ changes the account or service policy.
Record the creation date in the owner's password manager, review the key every
three months, and replace it immediately if the account or deployment origin
changes. This validity statement was checked against the LINZ “Creating an API
key” guidance on 29 Oct 2026; it is not a promise that LINZ will never rotate a
key.

Official instructions:
[Creating an API key](https://www.linz.govt.nz/guidance/data-service/linz-data-service-guide/web-services/creating-api-key).
