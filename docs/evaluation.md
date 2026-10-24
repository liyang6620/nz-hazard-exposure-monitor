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

## Building-time coverage

The LINZ export contains lifecycle history only from 2018-10-16. Consequently,
the eight fixed 2010-2016 events have zero source-supported buildings at their
event timestamps. Kermadec 2021 has 3,243,168 valid deduplicated buildings; the
2026 recent event has 3,219,311. Current or replacement outlines are never
substituted into earlier events.

