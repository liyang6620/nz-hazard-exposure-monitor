# Analyst Workbench review evidence

The new website page is captured from the local Vite build at `/workbench`:

- [Desktop](workbench-desktop.png)
- [Mobile](workbench-mobile.png)

The page embeds the new [five-page Desktop PDF](nzhem-powerbi-report.pdf) and
the five report images exported from the 6 Nov 2026 snapshot:

- [Event Overview](event-overview.png)
- [Event Comparison](event-comparison.png)
- [Regional Exposure](regional-exposure.png)
- [Event History](event-history.png)
- [Data Health](data-health.png)
- [Event Overview at MMI 7+](threshold-7-event-overview.png)

The read-only Azure snapshot at 6 Nov 2026 11:25 UTC contained 20 ready live
events and ten historical replays, representing 29 distinct GeoNet events.
Taumarunui (2026p776286) is available in both groups; the All view prefers
the historical replay. MMI 6+ facts reconciled to the source
summaries without orphan region keys. Desktop refresh completed on the ignored
`.local/powerbi-desktop-workbench-review63/nzhem.pbip` copy. The event selector showed
both Live events and Historical replays; a live M4.1 event showed event-time
basis and "No damaging shaking" with zero MMI 6+ exposure. The five pages,
website button and product footer were checked in Desktop. At MMI 6+, Kaikōura
showed 78,564 buildings and 83,276 people. At MMI 7+, the same event showed
9,720 buildings and 5,895 people; the card and chart titles changed with the
threshold. Data Health showed the last successful run at 6 Nov 2026 11:00 UTC,
zero failed runs and 27 poison messages including acceptance drills. The
Regional Exposure matrix total share covers the visible mapped regions; the
separate card shows the national share.

Desktop `View as` Canterbury Analyst restricted Kaikōura's MMI 7+ building
count from 9,720 nationally to 5,963 in Canterbury; the region chart showed
only Canterbury. [RLS screenshot](rls-canterbury-analyst.png) includes the
Desktop role banner and the complete snapshot timestamp. After Stop viewing,
the unrestricted 9,720 returned. No Microsoft sign-in or Power BI Service
publication was attempted. The site page has not been deployed to Azure;
PR #63 remains open for project-manager review.

The public successful-run heartbeat is
`https://stnzhem8495b7ca.z8.web.core.windows.net/data/housekeeping.json`.
The website now shows its `completed_at` as "Last checked"; unchanged data
does not force a new manifest generation.

## Automated checks

- Python: 178 tests passed, 80.67% coverage; Ruff lint and formatting passed.
- Frontend: 27 unit tests and 15 Playwright tests passed (one mobile-only
  navigation test skipped on desktop by design); ESLint, TypeScript, build and
  the home-page asset budget passed. The changed frontend files passed Prettier.
- PBIP: 75 visuals across five pages passed local structure, online PBIR JSON
  schema and machine-path checks. The 30-assessment, 29-event snapshot
  reconciled MMI 6+ buildings and people to its source summaries.
- Browser key boundary scan passed. The new PDF has five pages. Its extracted
  text contains no machine path,
  email address, Azure GUID or key assignment.
