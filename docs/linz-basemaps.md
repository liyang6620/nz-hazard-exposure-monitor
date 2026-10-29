# LINZ Basemaps browser key

The event map prefers the free LINZ Basemaps topographic vector tiles. The current
local build falls back to OpenStreetMap because `VITE_LINZ_BASEMAPS_API_KEY` has not
been configured.

To obtain the key:

1. Sign in to [LINZ Basemaps](https://basemaps.linz.govt.nz/) with a LINZ Data
   Service account.
2. Open **API keys**, create a key for this project, and restrict its allowed
   origins to the local and deployed website origins where possible.
3. Put the value in `frontend/.env.local` as `VITE_LINZ_BASEMAPS_API_KEY=...` for
   direct Vite development, or in the repository-root untracked `.env` for the
   Docker Compose build.
4. Rebuild the frontend or `web` image. The map attribution must continue to show
   Toitū Te Whenua LINZ and CC BY 4.0.

This is a public browser key intended to appear in browser requests. It is separate
from `LINZ_API_KEY`, which authorises LINZ Data Service downloads, and from the
server-only ArcGIS and OpenAI credentials. Do not reuse those private credentials in
the frontend.
