# Analyst Workbench review evidence

The new website page is captured from the local Vite build at `/workbench`:

- [Desktop](workbench-desktop.png)
- [Mobile](workbench-mobile.png)

The page embeds the five report images and PDF accepted in M5. Those images are
labelled as a reviewed 6 Nov 2026 fixed snapshot. The updated PBIP source adds
20 ready live events to ten replays, an event-group selector, a threshold-aware
status and title, a website footer/button and a `Canterbury Analyst` RLS role.
The read-only Azure snapshot contained 30 events; MMI 6+ facts reconciled to
the source summaries without orphan region keys. The source PBIP has no
machine-local path.

The revised PBIP has not yet been refreshed/exported in Desktop. Desktop opens
on this machine, but window activation fails when automated. The new RLS
`View as` screenshot and a refreshed five-page PDF remain a review gate. No
Microsoft sign-in or Power BI Service publication was attempted. The site page
has not been deployed to Azure; this PR must remain open for project-manager
review.

## Automated checks

- Python: 175 tests passed, 80.67% coverage; Ruff lint and formatting passed.
- Frontend: 24 unit tests and 15 Playwright tests passed (one desktop-only
  mobile-navigation test skipped by design); ESLint, TypeScript and build
  passed. Initial gzip assets are 95,056 bytes against the 256,000-byte cap.
- PBIP: 75 visuals across five pages passed local structure, online PBIR JSON
  schema and machine-path checks. The 30-event snapshot reconciled MMI 6+
  buildings and people to its source summaries.
- Browser key boundary scan passed. Desktop refresh, visual/RLS inspection and
  updated PDF export remain explicitly unverified.
