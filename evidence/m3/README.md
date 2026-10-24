# M3 historical event replay

## Input lineage

- Reference data: `.local/data/curated/reference-export/dee5b263952e`.
- The retained WFS generation at `.local/data/curated/reference` was not read and was not deleted.
- The 21,483 buildings attributed to water meshblocks remain excluded, as approved.
- Building validity is the exact half-open interval `begin_lifespan <= event_time < end_lifespan`.
- Simultaneously valid source versions are deterministically reduced to one row per `building_id`.

## Ten-event replay (as-if-today)

The shaking surface is replayed for each event, but exposure uses the current
deduplicated building inventory (`3,219,311`) and fixed
2023 SA1 population. This is explicitly an **as-if-today** scenario, not a claim
that today's outlines existed at the historical event time.

| Event | ID | UTC | Today | Event | Status | Max MMI | Bldgs6+ | Pop6+ | Source | MAE |
|---|---|---|---:|---:|---|---:|---:|---:|---|---:|
| darfield_2010 | `3366146` | 2010-09-03T16:35:41.836Z | 3,219,311 | NULL | not_supported | 8.4 | 337,971 | 534,594 | official | 1.160 |
| christchurch_feb_2011 | `3468575` | 2011-02-21T23:51:42.32Z | 3,219,311 | NULL | not_supported | 9.4 | 270,518 | 461,765 | official | 0.861 |
| christchurch_jun_2011 | `3528839` | 2011-06-13T02:20:49.26Z | 3,219,311 | NULL | not_supported | 8.8 | 236,306 | 406,499 | official | 0.849 |
| cook_strait_2013 | `2013p543824` | 2013-07-21T05:09:30.528Z | 3,219,311 | NULL | not_supported | 7.6 | 16,059 | 19,950 | official | 0.852 |
| lake_grassmere_2013 | `2013p613797` | 2013-08-16T02:31:05.926Z | 3,219,311 | NULL | not_supported | 8.0 | 26,492 | 31,464 | official | 0.787 |
| eketahuna_2014 | `2014p051675` | 2014-01-20T02:52:45.984Z | 3,219,311 | NULL | not_supported | 6.8 | 65,461 | 84,416 | official | 0.641 |
| east_cape_2016 | `2016p661332` | 2016-09-01T16:37:55.44Z | 3,219,311 | NULL | not_supported | 5.2 | 0 | 0 | official | 1.136 |
| kaikoura_2016 | `2016p858000` | 2016-11-13T11:02:56.346Z | 3,219,311 | NULL | not_supported | 8.4 | 78,564 | 83,276 | official | 1.373 |
| kermadec_2021 | `2021p169764` | 2021-03-04T19:28:32Z | 3,219,311 | 3,243,168 | supported | 2.2 | 0 | 0 | official | 2.821 |
| taumarunui_deep_2026 | `2026p776286` | 2026-10-15T05:25:34Z | 3,219,311 | 3,219,311 | supported | 2.8 | 0 | 0 | official | 2.309 |

## Event-time lifecycle counts

- `3366146` at `2010-09-03T16:35:41.836Z`: `NULL` (`not_supported`)
- `3468575` at `2011-02-21T23:51:42.32Z`: `NULL` (`not_supported`)
- `3528839` at `2011-06-13T02:20:49.26Z`: `NULL` (`not_supported`)
- `2013p543824` at `2013-07-21T05:09:30.528Z`: `NULL` (`not_supported`)
- `2013p613797` at `2013-08-16T02:31:05.926Z`: `NULL` (`not_supported`)
- `2014p051675` at `2014-01-20T02:52:45.984Z`: `NULL` (`not_supported`)
- `2016p661332` at `2016-09-01T16:37:55.44Z`: `NULL` (`not_supported`)
- `2016p858000` at `2016-11-13T11:02:56.346Z`: `NULL` (`not_supported`)
- `2021p169764` at `2021-03-04T19:28:32Z`: `3,243,168` (`supported`)

The source lifecycle begins on 2018-10-16. Events before that date are marked
`not_supported` and their event-time count is blank (`NULL`), never zero. The
2021 and 2026 events are marked `supported` and retain their exact lifecycle
filtering. Population remains the approved fixed 2023 allocation.

## Validation

- Station rows evaluated: `2,547`.
- Overall point-source attenuation MAE: `1.049` MMI.
- MAE above 1.0 is explicitly escalated for project-manager review and does not
  replace the official Shaking Layers surfaces used for exposure.

Kermadec is evaluated only where its official surface intersects populated New
Zealand H3 cells. Exposure remains close to zero by design.
