# Realtime event processing evidence

Date: 30 Oct 2026 (Pacific/Auckland)

## Root cause and correction

The hourly housekeeping job polled GeoNet, inserted event state and enqueued an
`events` message, but no local worker consumed that queue. The site publisher
then synthesised every unmatched realtime event as `processing` and incorrectly
labelled it as as-if-today. Nothing could move those records to a result.

The local host now consumes the queue before each site publication. It prefers
an official GeoNet Shaking Layer and otherwise uses the approved Dowrick-Rhoades
point-source estimate for events inside the paper's M4.9-M8.2 range. Realtime
building counts use the event timestamp and are published with
`as_if_today=false`. Events outside the calibrated magnitude range without an
official layer receive an explicit `outside_model_range` result.

The state machine permits three attempts. It records `failed` after the third
error and changes abandoned `processing` records to `timed_out` after 60
minutes. Revisions already in a terminal state are not recomputed. Events older
than the 30-day monitoring window become `expired` rather than consuming the
national exposure calculation again.

## Backlog result

The corrected container started at 22:57 NZDT. Its first housekeeping run
consumed all 65 queued messages and published generation
`20261029T100308424944Z` at 23:03 NZDT. The SQLite queue was empty afterwards.

The feed had advanced from the 33 events in the review report to 35 M4.0+ events
inside the latest 30-day window:

| Terminal result | Events |
|---|---:|
| Ready | 14 |
| Outside model range | 21 |
| Processing, queued or failed | 0 |

Of the 14 completed assessments, 13 used official GeoNet surfaces and one used
the preliminary point-source fallback. Event `2026p779975`, offshore south-west
of the Snares Islands, is the verified fallback case: M4.9, maximum populated
MMI 1.6, zero buildings and zero people at MMI 6+. All 35 records use the event
time basis. The published homepage contains no pending assessment.

Across retained state, older work ended as 30 `expired`, 22
`outside_model_range` and 21 `ready`; there were no queued, processing or failed
records after the run.

## Resource controls

- DuckDB memory limit: 512 MB and one execution thread.
- Highest observed application-container memory during the real backlog run:
  approximately 537 MiB, below the 768 MB process ceiling.
- Application-container memory after publication: approximately 214 MiB.
- C-drive free space after publication: 33.5 GiB, above the 20 GiB floor.
- Published generation size: approximately 2.4 MB.

## End-to-end latency observation

The monitor activation timestamp is `2026-10-29T09:57:24Z` (22:57:24 NZDT).
GeoNet's [FDSN event record](https://service.geonet.org.nz/fdsnws/event/1/query?eventid=2026p817279&format=text)
identifies the first later M4.0+ event as `2026p817279`, 565 km north-east of
Te Araroa. Its latest preferred magnitude is M4.1617 (`Mw(mB)`), displayed as
M4.2. The magnitude revision was at 22:32:38 NZDT on 30 Oct.

| Observed step | Pacific/Auckland time |
|---|---|
| Earthquake origin | 30 Oct 2026, 22:25:09 NZDT |
| Assessment completed | 30 Oct 2026, 22:51:18 NZDT |
| First site publication, generation `20261030T095119126499Z` | 30 Oct 2026, 22:51:19 NZDT |
| Earthquake to first publication | **26m 10s** (1,570 seconds) |

The observed elapsed time is below the one-hour target. This event is an
`outside_model_range` conclusion: M4.2 is below the published M4.9-M8.2 model
range and no official shaking layer was available. Maximum MMI and exposure
counts are unavailable, not zero. The local Docker stack was stopped at the
event time and its startup catch-up produced the assessment and first
publication. This observation verifies catch-up latency, **not continuously
online hourly operation**. The homepage timeline names the terminal conclusion.
The first-published timestamp was restored from the retained first-generation
manifest after the timeline logic was extended to include this terminal state;
the later regeneration was not used as the publication time.

## Data consistency

The current public generation is `20261030T101921807437Z`. Its Taumarunui
realtime detail and historical replay both use the latest GeoNet preferred
magnitude 5.65806, displayed as M5.7, with type `M` and magnitude revision at
15 Oct 2026, 18:53 NZDT. Exposure bases remain separate: event-time for the
realtime record and as-if-today for the replay. The approved briefing is an
immutable earlier snapshot and retains its original title.

All 8,164 non-null MMI values in 132 published JSON and GeoJSON files were
checked for one-decimal precision; there were no violations. The public bundle
contains only the current numbered generation and its matching manifest.

## Method decision

[ADR 0002](../../docs/adr/0002-d22-tvz-model-revision.md) records the accepted
D22 revision and its measured impact. Nine station-validation events use the
shallow main-region model and the 268.7 km Taumarunui event uses the deep model.
All ten fixed replays use official surfaces, so replay exposure totals are
unchanged; MAE remains 1.049. A TVZ delta is not reported because there is no
approved authoritative boundary with suitable reuse terms.

## Verification

- Python: 121 passed; total coverage 80.29%.
- Frontend unit tests: 20 passed.
- Playwright: 11 passed and one desktop-only mobile-navigation case skipped by
  design; desktop and mobile product routes, realtime result and approved
  briefing produced no console errors.
- Frontend lint, type check, production build, key-boundary scan and home asset
  budget passed. Initial assets totalled 94,063 gzip bytes against the 256,000
  byte limit.

## Screenshots

- `screenshots/home-desktop.png`
- `screenshots/home-mobile.png`
- `screenshots/realtime-detail-desktop.png`
- `screenshots/realtime-detail-mobile.png`
- `screenshots/approved-briefing-desktop.png`
- `screenshots/history-desktop.png`
