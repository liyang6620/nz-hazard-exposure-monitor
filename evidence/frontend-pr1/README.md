# Product frontend PR 1 evidence

Screenshots are captured from the local Vite build with the versioned M3 data
contract generated on 26 Oct 2026 NZDT.

- `home-desktop.png`: overview at 1440 x 1000.
- `event-desktop.png`: Kaikōura exposure detail at 1440 x 1000.
- `home-mobile.png`: overview first viewport at 390 x 844.
- `event-mobile.png`: Kaikōura exposure detail first viewport at 390 x 844.

The automated Playwright suite covers both desktop Chromium and a Pixel 7
viewport, checks the product overview and event detail, and fails on browser
console errors.
