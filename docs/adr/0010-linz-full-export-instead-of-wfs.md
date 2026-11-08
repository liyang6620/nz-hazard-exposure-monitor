# ADR 0010: Use the complete LINZ export instead of WFS for the reference

Status: accepted M2 import decision.

## Context

The national building layer is too large for a fragile region-by-region WFS
run. WFS GeoJSON coordinate precision also changed a few boundary
assignments compared with the source GeoPackage. A manual complete LINZ
GeoPackage export was available under the existing data licence.

## Decision

Use the owner-supplied, unfiltered full export as the M3 reference generation.
Import it in bounded national tiles, verify source counts and checkpoints,
and keep the older WFS generation only as comparison evidence. The production
dbt graph must not silently fall back to that WFS generation. Do not commit
the raw ZIP or GeoPackage.

## Consequences

The import accounted for all 6,634,223 source outlines, accepted 6,612,732
land-building rows, and retained 21,483 water-meshblock exclusions. It used
3,794 tiles, one DuckDB thread and a 512 MB limit; peak worker RSS was
164.8 MB. The export did not embed a numeric layer version, so evidence
compares its publication date with LINZ metadata instead of claiming a
numeric match. The three retained WFS regions had identical source IDs and
attributes; small H3/boundary differences were documented.

See [M2 import evidence](../../evidence/m2/README.md) and
[Checkpoint A](../../evidence/checkpoint-a/README.md).
