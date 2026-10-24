# M3 historical event replay

## Input lineage

- Reference data: `.local/data/curated/reference-export/dee5b263952e`.
- The retained WFS generation at `.local/data/curated/reference` was not read and was not deleted.
- The 21,483 buildings attributed to water meshblocks remain excluded, as approved.
- Building validity is the exact half-open interval `begin_lifespan <= event_time < end_lifespan`.
- Simultaneously valid source versions are deterministically reduced to one row per `building_id`.

## Ten-event replay

| Event | ID | UTC | Valid buildings | Max MMI | Bldgs >= 6 | Pop >= 6 | Source | MAE |
|---|---|---|---:|---:|---:|---:|---|---:|
| darfield_2010 | `3366146` | 2010-09-03T16:35:41.836Z | 0 | 8.4 | 0 | 534,594 | official | 1.160 |
| christchurch_feb_2011 | `3468575` | 2011-02-21T23:51:42.32Z | 0 | 9.4 | 0 | 461,765 | official | 0.861 |
| christchurch_jun_2011 | `3528839` | 2011-06-13T02:20:49.26Z | 0 | 8.8 | 0 | 406,499 | official | 0.849 |
| cook_strait_2013 | `2013p543824` | 2013-07-21T05:09:30.528Z | 0 | 7.6 | 0 | 19,950 | official | 0.852 |
| lake_grassmere_2013 | `2013p613797` | 2013-08-16T02:31:05.926Z | 0 | 8.0 | 0 | 31,464 | official | 0.787 |
| eketahuna_2014 | `2014p051675` | 2014-01-20T02:52:45.984Z | 0 | 6.8 | 0 | 84,416 | official | 0.641 |
| east_cape_2016 | `2016p661332` | 2016-09-01T16:37:55.44Z | 0 | 5.2 | 0 | 0 | official | 1.136 |
| kaikoura_2016 | `2016p858000` | 2016-11-13T11:02:56.346Z | 0 | 8.4 | 0 | 83,276 | official | 1.373 |
| kermadec_2021 | `2021p169764` | 2021-03-04T19:28:32Z | 3,243,168 | 2.2 | 0 | 0 | official | 2.821 |
| taumarunui_deep_2026 | `2026p776286` | 2026-10-15T05:25:34Z | 3,219,311 | 2.8 | 0 | 0 | official | 2.309 |

## Nine fixed-event lifecycle counts

- `3366146` at `2010-09-03T16:35:41.836Z`: `0`
- `3468575` at `2011-02-21T23:51:42.32Z`: `0`
- `3528839` at `2011-06-13T02:20:49.26Z`: `0`
- `2013p543824` at `2013-07-21T05:09:30.528Z`: `0`
- `2013p613797` at `2013-08-16T02:31:05.926Z`: `0`
- `2014p051675` at `2014-01-20T02:52:45.984Z`: `0`
- `2016p661332` at `2016-09-01T16:37:55.44Z`: `0`
- `2016p858000` at `2016-11-13T11:02:56.346Z`: `0`
- `2021p169764` at `2021-03-04T19:28:32Z`: `3,243,168`

The source lifecycle begins on 2018-10-16. The eight fixed events before that
date therefore have zero source-supported historical buildings; the pipeline
does not substitute current buildings. Population remains the approved fixed
2023 allocation. This is a source-coverage limitation, not a processing error.

## Validation

- Station rows evaluated: `2,547`.
- Overall point-source attenuation MAE: `1.049` MMI.
- MAE above 1.0 is explicitly escalated for project-manager review and does not
  replace the official Shaking Layers surfaces used for exposure.

Kermadec is evaluated only where its official surface intersects populated New
Zealand H3 cells. Exposure remains close to zero by design.
