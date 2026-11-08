# ADR 0008: H3-8 computation and H3-6 presentation

Status: accepted method, confirmed at Checkpoint A.

## Context

Building polygons and administrative boundaries are handled in NZTM2000.
Each building is represented by a point on its surface, transformed to WGS84
with explicit axis order. An H3 grid makes event overlays bounded and
publishable as static event-specific GeoJSON.

## Decision

Assign buildings and 2023 population to H3 resolution 8 for computation.
Aggregate to H3 resolution 6 for maps and regional summaries. Keep the
approved 512 MB DuckDB and 768 MB process ceilings. Do not infer exact
building-level shaking from the displayed H3-6 polygon.

## Consequences

Kaikōura point-in-polygon cross-validation matched 3,201,877 of 3,219,311
current building MMI bands (99.458%). The 17,434 mismatches cluster near
official contour boundaries; mean numeric MMI difference was 0.00365.
The map and method page disclose the cell-centre approximation. A resolution
change would alter published numbers and needs a method review, resource
measurement and new cross-validation.

See [MG evidence](../../evidence/mg/README.md) and
[the methodology](../methodology.md).
