# Evaluation

## M3 event replay

The ten locked events use the latest published GeoNet Shaking Layers MMI
polygons. Exposure is assigned by testing each populated H3-8 centre against
the official polygons. Observed `stationlist.json` intensity is used only to
evaluate the approved point-source attenuation formula; it never fills the
exposure grid.

The national replay is recorded in `evidence/m3/m3-replay.json`. The overall
formula MAE is **1.049 MMI** across **2,547** station/intensity rows. This exceeds
the D23 review threshold of 1.0 and is escalated at Checkpoint A. Event-level
MAE above 1.0 occurs for Darfield, East Cape, Kaikoura, Kermadec and the 2026
deep Taumarunui event. The larger errors are consistent with known limitations:
epicentral rather than rupture distance, no interface model, no TVZ branch, and
reported intensity uncertainty. No coefficient was tuned against these events.

Kermadec's highest MMI on a populated New Zealand H3 cell is 2.2 and its MMI 6
building and population exposure is zero, satisfying the near-zero check.

## Building-time coverage and as-if-today replay

The LINZ export contains lifecycle history only from 2018-10-16. Consequently,
the eight fixed 2010-2016 events have no supported event-time count; their
event-time fields are `NULL` with status `not_supported`, never zero. The main
M3 result is now an **as-if-today** replay: all ten official shaking surfaces
use the current 3,219,311 deduplicated buildings and fixed 2023 SA1 population.
Kermadec 2021 has 3,243,168 event-time valid deduplicated buildings, and the
2026 recent event has 3,219,311. Current or replacement outlines are never
substituted into the event-time field for unsupported historical events.

## MG Kaikoura spatial cross-validation

The MG validation compares two ways of assigning the official Kaikoura MMI
surface to the same 3,219,311 current, deduplicated building points:

1. an exact GeoPandas/Shapely point-in-polygon join against the published MMI
   contour polygons; and
2. the production H3-8 centre assignment from `int_event_shaking_h3`.

MMI bands agree for 3,201,877 buildings, or **99.458%**. The mean absolute
numeric MMI difference is **0.00365**. Most differences are buildings close to
an MMI contour where the building point and its H3 cell centre fall on opposite
sides. The CSV evidence reports the resulting movement by region and MMI band.

This is a spatial-method validation only. Kaikoura occurred before the LINZ
lifecycle coverage begins, so its event-time valid building count is `NULL` with
status `not_supported`; it is never represented as zero. The current building
points used here are not substituted into the M3 exposure result and are not
presented as a 2016 building inventory.

## M6 briefing agent evaluation

The M6 evaluation runs the ten fixed historical events against the local M3
gold Parquet and approved national reference generation. It uses the same four
read-only tools as the application and local MCP server.

Run it from the repository root:

```text
python scripts/run_m6_agent_evaluation.py
```

The script reads `OPENAI_API_KEY` from ignored `.env`, uses `gpt-5-mini` with
minimal reasoning, enforces a 1,200 output-token ceiling, and checks the US$1
cumulative budget before every call. Evidence contains token counts, cost,
status and payload hashes, never prompts, generated content or credentials.

The 2026-10-26 result is 10/10 payloads with 100% numeric fidelity. Measured
cost for the complete ten-event run was US$0.01052725; known cumulative M6
actual cost was US$0.01287375. Two setup calls whose usage was not persisted
are represented by a conservative US$0.0102 reserve, making the budget-accounted
total US$0.02307375.

The validator requires:

- the exact strict JSON field set and all three required limitations;
- every visible number to occur in the current tool results;
- every key figure's declared tool and field to contain its exact value;
- no more than two retries after an incomplete, invalid or unfaithful result.

Machine-readable results are in `evidence/m6/agent-evaluation.json`.
