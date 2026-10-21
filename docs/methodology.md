# Methodology

This is the M0 methodology baseline. It records what is supported by source
material and separates it from choices that still require project-manager
approval. The system is demonstrative: exposure is represented by buildings,
building footprint and population, not insurance policies; estimated MMI is not
an engineering or actuarial conclusion; and building appearance/disappearance
dates are approximate inferences from aerial capture and lifecycle metadata.

## Spatial framework

Building area and point-in-polygon work use NZTM2000 (EPSG:2193). Geometry is
transformed to WGS84 (EPSG:4326) with forced XY axis order before H3 indexing.
Computation uses H3 resolution 8 and presentation aggregates to resolution 6.
M2 will measure memory and runtime before any resolution change is proposed.

Each building uses a point on surface, not a centroid. Footprint area is
computed from the original EPSG:2193 polygon. Current building presence is
`end_lifespan IS NULL`; event-year presence is:

```text
year(begin_lifespan) <= event_year
AND (end_lifespan IS NULL OR year(end_lifespan) > event_year)
```

Rows with missing or contradictory dates remain in the current snapshot but
are excluded from historical claims and counted in data-quality output until
M2 establishes a defensible fallback.

## Population allocation

The approved plan allocates each meshblock population total among buildings in
that meshblock in proportion to footprint area, then aggregates to H3. A
population area with no buildings assigns its total to the polygon's point on
surface. The allocation invariant is:

```text
abs(sum(allocated_population) - source_population) < 1e-6
```

M0 found no public 2023 Census meshblock population layer. Stats NZ layer
120766 supplies SA1 totals (`VAR_1_3`). Applying the same invariant at SA1 is a
technically valid fallback but reduces spatial precision. Implementation is
paused pending a PM choice between SA1 allocation and another authoritative
population source. Population remains fixed at Census 2023; then-versus-now
comparisons apply only to buildings.

## MMI source priority

For each event, exactly one source class is used for the exposure grid:

1. `official`: the latest published Shaking Layers MMI polygon version, with
   reviewed preferred over automatic when both exist.
2. `estimated`: a project-approved Dowrick and Rhoades model when no official
   surface exists.

Observed/reported intensity points are validation evidence and are not used to
fill the grid. MMI is stored without early integer rounding; reporting bands are
`<4`, `4`, `5`, `6`, `7`, and `8+` from a dbt seed.

## Dowrick and Rhoades attenuation model

Source: Dowrick, D. J. and Rhoades, D. A. (2005), "Revised models for
attenuation of Modified Mercalli intensity in New Zealand earthquakes",
*Bulletin of the New Zealand Society for Earthquake Engineering* 38(4),
185-214, <https://doi.org/10.5459/bnzsee.38.4.185-214>.

The paper's Main Seismic Region Model 2 (Table 6) is:

```text
I = A1 + A2*Mw + A3*log10((r^3 + d^3)^(1/3)) + A4*hc + A5*deltaC

A1 =  4.40
A2 =  1.26
A3 = -3.67
A4 =  0.012
A5 =  0.409
d  = 11.78 km
```

`Mw` is moment magnitude, `hc` is centroid depth in kilometres and `deltaC` is
1 for crustal events and 0 otherwise. The meaning of distance `r` and the event
classification must match the paper; it must not be silently replaced with a
convenient epicentral distance.

The paper also gives a deep-region model (Table 7):

```text
I = 3.76 + 1.48*Mw - 3.50*log10(r) + 0.0031*hc
```

It contains regional, focal-mechanism and anisotropic alternatives. The planned
catalogue does not contain enough rupture geometry or mechanism information to
apply every alternative faithfully. The PM must choose the supported
classification and distance approximation before implementation.

For arithmetic regression only, the Table 6 equation produces
`7.476132218744497` for `Mw=7.8`, `r=100 km`, `hc=15 km`, and `deltaC=1`.
This value was calculated by the project and is **not** an example published in
the paper. M0 found no published worked numeric example that can serve as the
plan's requested independent unit-test oracle. The PM must approve a replacement
oracle, such as a locked calculation independently reproduced in two tools.

Only populated H3 cells inside the distance at which the selected model falls
below MMI 3 are evaluated. The cutoff is solved from the chosen equation and
event classification; it is not a fixed radius.

## Exposure metrics

For each event and H3 cell the system records MMI, source/version, buildings and
footprint at event date, current buildings and footprint, and 2023 population.
"Exposed" always means MMI greater than or equal to the selected threshold,
default 6. Regional summaries preserve MMI bands and source provenance.

The accumulation score is:

```text
count(events with cell MMI >= 6) * current_building_count
```

It is a ranking indicator, not an annual probability or loss estimate.

## Validation

Where `stationlist.json` is available, compare estimated MMI with observed
station/macroseismic intensity and report mean absolute error. For Kaikoura,
compare H3 assignment with an exact point-in-polygon overlay against the latest
reviewed Shaking Layers surface. Report boundary and grid approximation effects
instead of tuning the model to force agreement.
