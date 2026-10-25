# M6 briefing agent, approval and MCP evidence

## Ten-event evaluation

`agent-evaluation.json` records the complete evaluation of the ten fixed M3
events with `gpt-5-mini`, minimal reasoning and a 1,200-output-token ceiling.
All ten final payloads passed strict-schema, required-limitations, key-figure
provenance and visible-number fidelity checks: **10/10, 100%**.

The successful evaluation made 14 measured API calls because three events
needed fidelity retries. It cost **US$0.01052725**. Together with the earlier
measured M6 calls, known actual spend is **US$0.01287375**. Two failed setup
calls did not persist usage before their processes exited; evidence reserves
their full pre-call upper bound of **US$0.0102** instead of inventing token
counts. Budget-accounted M6 spend is therefore **US$0.02307375**, below the
US$1 hard cap.

Pricing was checked against the official OpenAI `gpt-5-mini` model page on
2026-10-26: US$0.25/M input, US$0.025/M cached input and US$2/M output. Every
call was checked against the cumulative cap before dispatch. The API key was
read only from ignored `.env` and is absent from evidence, logs and images.

## Local approval workflow

`workflow-demo.json` records a real Kaikoura path through the M3 DuckDB tools,
the shared draft renderer, numeric validation, draft storage, loopback Mailpit,
HMAC review and local static-site publisher:

- GET preview left the briefing `pending`; POST changed it to `approved`;
- the approved page and one-entry publication index were written;
- token replay and a 73-hour-expired token were rejected;
- the reject path wrote `rejected` and did not publish;
- three messages were added through loopback-only SMTP.

`approved-briefing.png` shows the published page.
`mailpit-delivery-sanitized.png` shows sender, recipient and subjects only;
message bodies and review tokens are deliberately omitted. Compose binds the
app, Mailpit SMTP/UI and Caddy ports to `127.0.0.1`.

## Local MCP server

`mcp-demo.json` records a real stdio client/server handshake. Exactly four
read-only tools were registered, and `get_event` plus
`get_exposure_summary` returned successful content without network access.
The tool adapter reads M3 gold and reference generation
`reference-export/dee5b263952e`, with DuckDB capped at 512 MB and one thread.

## Esri and Azure status

The owner-approved ArcGIS test is recorded under `evidence/mg/`. The key could
create an empty service item but layer-definition update, deletion and all
three allowed Static Maps calls returned `403 GWM_0003`. Formal
`event_exposure_r6` publishing and Esri MCP imagery were therefore not
attempted further. The M6 static-map guard still enforces a hard
`static_map`-only whitelist, at most two reservations per briefing and 200 per
month, with failed attempts recorded without blocking the briefing.

Azure deployment evidence remains deferred until the Microsoft account is
restored. The shared core, Azure adapters and Key Vault secret-name mapping are
implemented, but no Azure resource was created and no Azure claim is made.

`openai-evaluation.json` is retained as the earlier six-call M6 smoke test.

## ArcGIS completion addendum

The follow-up MG block published the formal hosted layer and connected briefings
to Esri MCP `map_with_overlay`. The server-side adapter uses the existing
pre-request guard, so every attempted image counts toward the two-per-briefing
and 200-per-month limits. Successful PNGs remain draft artifacts until POST
approval, then publish with the briefing. Static-map failure remains non-fatal.
See `evidence/mg/arcgis-publish.json` and `docs/arcgis-operations.md`.
