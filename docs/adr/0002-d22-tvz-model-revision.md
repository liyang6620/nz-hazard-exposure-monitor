# ADR 0002: D22 revision for TVZ classification

## Status

Accepted retrospectively by the project manager, 2026-10-29. Future material
method changes require review before implementation.

## Context

D22 originally selected attenuation models in this order: deep source, TVZ,
then shallow main seismic region, with the paper taking precedence. It also
required the TVZ boundary to come from an authoritative, licence-compatible
source and said not to use the TVZ branch if no such boundary could be found.

No authoritative boundary with suitable reuse terms and deterministic
point-in-polygon geometry was identified during M0-M3. Approximating the TVZ
with an undocumented rectangle would make classification irreproducible.
Subduction-interface classification also remains unsupported because the
project has neither slab geometry nor reliable focal-mechanism classification.

## Revised decision

- At source depth of 70 km or greater, use Dowrick and Rhoades deep-region
  Model 3 (Table 7, p. 198).
- For shallower events, use main seismic region Model 2 (Table 6, p. 198).
- Do not use the TVZ or subduction-interface branches until an authoritative,
  appropriately licensed classification dataset is approved.
- Continue to reject magnitudes outside the paper's M4.9-M8.2 calibration data
  when no official shaking layer is available.
- Prefer reviewed and then automatic official GeoNet Shaking Layers over every
  point-source estimate.

## Measured impact

All ten fixed M3 exposure replays use official Shaking Layers, so this revision
changes none of their published exposure totals. The independent station
validation applies the implemented point-source selection: nine shallow events
use Model 2 and the 268.7 km Taumarunui event uses the deep model. Its aggregate
MAE remains 1.049 MMI.

No defensible “with TVZ” MAE delta can be calculated without the missing TVZ
boundary; assigning events by an invented boundary would manufacture evidence.
The likely impact is therefore limited to future preliminary estimates for
shallow earthquakes that a later approved boundary classifies inside the TVZ.
Those events currently use Model 2 and are explicitly labelled preliminary.
