# Locked attenuation test vectors

These values independently check the M3 implementation of Dowrick and Rhoades
(2005). They are arithmetic regression values, not examples published by the
paper. Coefficients come from Main Seismic Region Model 2 (Table 6, p. 198) and
Deep Region Model 3 (Table 7, p. 198).

## Independent calculation

For a shallow event, the calculation is written as four steps:

```text
R = (r^3 + 11.78^3)^(1/3)
distance_term = -3.67 * log10(R)
source_term = 4.40 + 1.26 * Mw + 0.012 * hc + 0.409 * deltaC
MMI = source_term + distance_term
```

For a deep event:

```text
r_used = max(r, 1 km)
hc_used = min(max(hc, 70 km), 300 km)
distance_term = -3.50 * log10(r_used)
source_term = 3.76 + 1.48 * Mw + 0.0031 * hc_used
MMI = source_term + distance_term
```

The locked values were calculated separately with PowerShell `[math]::Log10`
and full double precision, not by importing the production Python function.

| # | Model | Mw | r km | hc km | deltaC | Expected MMI | Boundary covered |
|---:|---|---:|---:|---:|---:|---:|---|
| 1 | Main 2 | 4.9 | 0 | 0 | 1 | 7.0515718760 | lower Mw, zero distance |
| 2 | Main 2 | 5.5 | 10 | 5 | 1 | 7.6143071968 | near field |
| 3 | Main 2 | 6.0 | 50 | 10 | 1 | 6.2468772000 | ordinary shallow |
| 4 | Main 2 | 6.5 | 100 | 15 | 1 | 5.8381322187 | point-source flag boundary |
| 5 | Main 2 | 7.8 | 100 | 15 | 1 | 7.4761322187 | Kaikoura arithmetic check |
| 6 | Main 2 | 8.2 | 500 | 50 | 1 | 5.8357731362 | upper Mw, far field |
| 7 | Deep 3 | 5.0 | 1 | 70 | n/a | 11.3770000000 | deep boundary |
| 8 | Deep 3 | 5.5 | 50 | 100 | n/a | 6.2636049848 | ordinary deep |
| 9 | Deep 3 | 6.0 | 100 | 200 | n/a | 6.2600000000 | ordinary deep |
| 10 | Deep 3 | 7.0 | 300 | 300 | n/a | 6.3800756085 | maximum depth |
| 11 | Deep 3 | 8.2 | 1000 | 350 | n/a | 6.3260000000 | depth clamp, upper Mw |
| 12 | Main 2 | 6.0 | 100 | 69.999 | 0 | 5.4591202187 | below deep boundary |

Inputs below Mw 4.9 or above Mw 8.2 return no estimate. Automated property
tests also prove that predicted MMI does not increase with distance and does
not decrease with magnitude for both implemented models.
