# Product frontend PR 1 evidence

Screenshots are captured from the local Vite build with the versioned site data
contract generated on 29 Oct 2026 NZDT after manual briefing approval.

- `home-desktop.png`: overview at 1440 x 1000.
- `event-desktop.png`: Kaikōura exposure detail at 1440 x 1200, including its
  approved briefing.
- `home-mobile.png`: overview first viewport at 390 x 844.
- `event-mobile.png`: Kaikōura exposure detail at 390 x 844.

The automated Playwright suite covers both desktop Chromium and a Pixel 7
viewport, checks the product overview and event detail, and fails on browser
console errors. The project manager, acting on the repository owner's explicit
instruction, manually reviewed and approved all ten revision 3 briefings using
the GET confirmation page followed by POST. Reused links were rejected. The
earlier twenty drafts are marked `superseded` and their links are invalid.

`briefing-summary-reconciliation.md` records the deterministic title and every
key figure alongside the source `summary.json` generation and digest.
