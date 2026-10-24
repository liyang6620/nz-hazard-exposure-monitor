# Checkpoint A: M2-M3 technical validation

## Reference data

- LINZ source rows: 6,634,223.
- Accepted land-building rows: 6,612,732.
- Current deduplicated buildings: 3,219,311.
- Water-meshblock exclusions retained: 21,483.
- 2023 SA1 population: 4,994,034, with zero allocation invariant failures.
- Approved reference generation: `reference-export/dee5b263952e`.
- Retained WFS generation was neither read by M3 nor deleted.

The nationwide building logical hash was independently read twice with a
512 MB DuckDB limit and fixed `region_code, building_outline_id` ordering. Both
runs produced:

```text
b0c43ce34f4bbbb9b23acc673d81b64ad1d667b927822d9baa65975611c54b99
```

## Historical-event method

- Building validity uses the exact half-open interval
  `begin_lifespan <= event_time < end_lifespan`.
- Overlapping old/new versions are reduced to one row per `building_id`.
- All ten events use official GeoNet Shaking Layers surfaces.
- Population is the approved fixed 2023 SA1 allocation.
- Kermadec maximum populated-cell MMI is 2.2; MMI 6 exposure is zero.

The export lifecycle starts on 2018-10-16, so all eight fixed events from
2010-2016 have zero source-supported historical buildings. Kermadec 2021 has
3,243,168 valid buildings. Full event results are in `evidence/m3/README.md`.

## Validation and escalation

- Locked independent attenuation vectors: 12.
- Station/intensity rows: 2,547.
- Overall point-source MAE: 1.049 MMI.
- D23 escalation required: MAE is above 1.0. Official surfaces remain the
  exposure source; no coefficient was tuned to the validation events.
- dbt reads the export generation and M3 event Parquet directly; it does not
  fall back to the old WFS generation.
- Synthetic M1 replay fixtures were replaced by locked real GeoNet summaries
  for Christchurch 2011 and Kaikoura 2016.

## Resource and consistency checks

- DuckDB memory limit: 512 MB; process RSS guard: 768 MB.
- C-drive floor: 20 GB; minimum during M2 import: 54.59 GiB.
- National population invariants: pass.
- Two-pass national building hash: pass.
- Unit tests, dbt tests, lint and replay hash are required in CI.

## Deferred decisions

- The project manager should review MAE 1.049 under D23.
- The repository owner should decide whether to delete the retained WFS data.
- Azure-only validation remains deferred until account recovery.
