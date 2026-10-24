# NZTM2000 to WGS84 axis order

## Problem

New Zealand source layers commonly use NZGD2000 / New Zealand Transverse
Mercator 2000 (EPSG:2193), while GeoJSON, web maps and H3 use longitude and
latitude in WGS84 (EPSG:4326 / OGC:CRS84). A formally correct CRS transform can
still produce unusable coordinates when software follows EPSG axis metadata
instead of the XY order expected by the calling API.

## Symptom

The failure is visually dramatic but can pass type checks: points expected near
`174 E, 41 S` appear near `41 E, 174 S`, outside valid latitude bounds, or on the
wrong side of the world. H3 accepts two numbers without knowing whether the
caller swapped them, so the error can propagate into plausible-looking cell IDs.

## Cause

EPSG:4326 is defined with latitude as its first axis in the EPSG registry.
GeoJSON and most web APIs use traditional XY order: longitude, latitude.
PROJ-based libraries expose an `always_xy` or equivalent option precisely
because both conventions exist. EPSG:2193 itself uses easting, northing, so the
ambiguity appears when transforming to geographic coordinates.

## Resolution

The pipeline performs area and point-on-surface work in EPSG:2193, then forces
traditional XY order for the transform to WGS84. In PyProj the safe pattern is:

```python
Transformer.from_crs(2193, 4326, always_xy=True).transform(easting, northing)
```

The returned values are named `longitude, latitude` and passed to H3 as
`h3_latlng_to_cell(latitude, longitude, resolution)`, because H3 deliberately
uses latitude first. GeoJSON writes them back as `[longitude, latitude]`.

## Verification

Tests and data checks should assert all three layers of the contract:

1. transformed longitude is approximately 166-179 and latitude -48 to -34 for
   mainland New Zealand data;
2. a known Wellington coordinate lands near 174.776 E, 41.287 S;
3. the H3 cell centre transformed back to WGS84 is close to the source point.

The MG File Geodatabase is written in EPSG:2193 and read back through GDAL to
verify its CRS. The browser GeoJSON remains WGS84 XY, and the token-free map's
event points provide a second visual check.
