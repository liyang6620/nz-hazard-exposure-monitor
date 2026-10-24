# M2 national LINZ export import

- Acquisition: owner-supplied manual GeoPackage export (Method B)
- Expected layer version: `438679`
- Exported layer version: `None`
- Version comparison: numeric version not embedded; export publication date matches the 438679 metadata date
- Expected source features: `6,634,223`
- Exported source features: `6,634,223`
- Accepted land buildings: `6,612,732`
- Region 99: `0`
- Non-land meshblocks: `21,483`
- No containing meshblock: `0`
- Invalid or unindexed geometry: `8`
- Tiles: `3,794` at no more than
  `5,000` candidates each
- DuckDB: one thread, configured by the 512 MB local default
- Peak worker RSS: `164.8` MB
- Minimum observed free disk: `54.59` GB
- First-to-last tile checkpoint time: `1.18` hours
- Stats NZ SA1 rows: `33,164`
- Published population total: `4,994,034`
- Allocated population total: `4,994,034`
- Suppressed SA1 rows: `0`
- Population invariant failures: `0`
- Unlocated SA1 rows: `16` containing
  `24` people
- Nonzero unlocated SA1 rows: `2`

The numeric LINZ layer version is not embedded in this export when the exported
version above is `None`. In that case the evidence records the publication-date
comparison rather than claiming a numeric match. Full machine-readable counts and
the retained WFS comparison are in `national-import.json`.

## Retained WFS comparison

| Region | IDs | Source attrs | Meshblock | H3-8 | H3-6 | Mean area delta m2 | Max area delta m2 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 01 | 231,127 | 0 | 1 | 2 | 16,162 | 0.00003769 | 0.00131327 |
| 02 | 815,372 | 0 | 0 | 3 | 54,345 | 0.00003733 | 0.00376263 |
| 03 | 1,215,746 | 0 | 0 | 6 | 80,274 | 0.00003610 | 0.00204260 |

The retained WFS and export generations contain exactly the same IDs in regions
01, 02 and 03, and their source attributes are identical. The WFS GeoJSON
coordinates are rounded differently from the GeoPackage coordinates, so exact
coordinate comparison differs for every retained row. The resulting area deltas
are sub-centimetre-square numerical effects. H3-8 differences reflect a small
number of point-on-surface coordinates falling on adjacent H3 boundaries; one
point falls on an adjacent meshblock boundary. H3-6 is derived as the parent of
H3-8, so its larger differences against retained WFS reflect the old WFS
generation independently classifying H3-6 at H3 boundaries, not changed source
buildings. These are serialization-precision effects, not evidence of a
source-version change.

Sixteen official region-99 SA1 records have neither population-layer geometry
nor meshblock-boundary geometry; two have nonzero population. Their 24 residents
are preserved as `unlocated_no_geometry` rows with null H3 values instead of
assigning a false location. They remain in the per-SA1 and national population
invariants and are excluded from `dim_h3_cell`.

The second full deterministic building hash run remains deferred to Checkpoint A
under the project-manager decision. Tile checkpoints already verify source and
output hashes on every restart.

## Excluded source rows

All eight excluded IDs are present in the GeoPackage and its RTree but fail
`ST_IsValid`: `1880151`, `5733078`, `6402952`, `6403012`, `6451145`, `7112394`, `7127014`, `7877722`. They are counted in
`invalid_or_unindexed_geometry`; no source row is unexplained.
