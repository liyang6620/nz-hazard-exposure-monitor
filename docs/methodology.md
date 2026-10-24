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
`end_lifespan IS NULL`. Historical presence uses the exact UTC event timestamp
and a half-open validity interval:

```text
begin_lifespan <= event_time
AND (end_lifespan IS NULL OR end_lifespan > event_time)
```

After filtering, overlapping source versions are reduced to one deterministic
row per `building_id`, ordered by latest `begin_lifespan` and then highest
`building_outline_id`. This prevents old and replacement outlines from both
counting at one timestamp. Rows with missing or contradictory dates are
excluded from historical claims.

The approved M3 reference input is the manual-export generation
`reference-export/dee5b263952e`; the retained WFS generation is not a fallback.
The export's earliest `begin_lifespan` is 2018-10-16. Events before that date
therefore have no source-supported historical building count. The pipeline does
not substitute current buildings. The 21,483 outlines attributed to water
meshblocks remain excluded pending a later owner decision.

## Population allocation

The approved source is the 2023 Census usually resident population at SA1 level
(`VAR_1_3`). Each SA1 total is allocated among **currently present** buildings
(`valid_to_year IS NULL`) in proportion to footprint area, then aggregated to
H3. An SA1 with no current buildings assigns its total to the polygon's point on
surface. The allocation invariant is evaluated independently for every SA1:

```text
abs(sum(allocated_population) - source_population) < 1e-6
```

SA1 is coarser than meshblock, so within-SA1 distribution is an approximation.
Stats NZ applies fixed random rounding and suppression to small-area Census
counts; the pipeline preserves the published values and flags suppression
codes rather than attempting to reverse them. Population remains fixed at
Census 2023; then-versus-now comparisons apply only to buildings.

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

The paper's Main Seismic Region Model 2 (Table 6, p. 198) is:

```text
I = A1 + A2*Mw + A3*log10((r^3 + d^3)^(1/3)) + A4*hc + A5*deltaC

A1 =  4.40
A2 =  1.26
A3 = -3.67
A4 =  0.012
A5 =  0.409
d  = 11.78 km
```

`Mw` is moment magnitude. Under D22, `hc` is approximated by GeoNet source depth
and `r` by the great-circle distance from the epicentre to the H3 cell centre.
This is a point-source approximation rather than the rupture-distance treatment
used for larger earthquakes. Events of M6.5 or above without an official layer
are marked `point_source_approx`.

The paper also gives a deep-region Model 3 (Table 7, p. 198):

```text
I = 3.76 + 1.48*Mw - 3.50*log10(r) + 0.0031*hc
```

The implementation selects the deep-source model first at `hc >= 70 km`, the
paper's deep-event definition (data classification on pp. 190-192 and Model 3
on p. 198). Shallower events use Main Seismic Region Model 2. The TVZ branch is
disabled because M0/M3 did not identify an authoritative, licence-compatible
boundary suitable for deterministic point-in-polygon classification; it is not
approximated with an undocumented box. The paper's TVZ coefficients are
therefore not implemented. Remaining events use the main-region shallow model.
The interface model is excluded because the project has neither slab geometry
nor reliable focal-mechanism classification. The paper's 89-event calibration
dataset spans Mw 4.9-8.2 (dataset description, pp. 187-193). Magnitudes outside
that envelope are not extrapolated. Deep-event depth is clamped to the paper's
observed 70-300 km range and flagged. Zero epicentral distance is evaluated at
1 km to avoid `log10(0)` and is flagged. Paper rules, table numbers and page
citations take precedence if they conflict with these implementation rules.

For arithmetic regression only, the Table 6 equation produces
`7.476132218744497` for `Mw=7.8`, `r=100 km`, `hc=15 km`, and `deltaC=1`.
This value was calculated by the project and is **not** an example published in
the paper. D23 approves an independent, step-by-step calculation of at least 12
locked vectors covering every implemented model and boundary case, plus
monotonicity properties. The independent calculations and locked vectors are
in `docs/methodology-test-vectors.md`. `stationlist.json` supplies external MAE
validation. The ten-event M3 run evaluated 2,547 intensity rows and produced
MAE 1.049 MMI, so it is explicitly escalated at Checkpoint A. Official Shaking
Layers surfaces remain the exposure source for all ten events.

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
