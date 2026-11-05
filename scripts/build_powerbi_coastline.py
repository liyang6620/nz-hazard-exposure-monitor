"""Render a lightweight New Zealand land outline from the project's Stats NZ SA1 files."""

from __future__ import annotations

import gzip
import json
import shutil
from pathlib import Path

import shapely
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".local/data/raw/reference/stats_population/nationwide"
OUTPUT = ROOT / "reports/powerbi/nzhem.Report/StaticResources/RegisteredResources/nz-coastline.svg"
X_MIN, X_MAX = 160.0, 185.0
Y_MIN, Y_MAX = -48.5, -33.5
WIDTH, HEIGHT = 1200, 720


def path_for_ring(ring: object) -> str:
    coords = list(ring.coords)
    points = [
        f"{(lon - X_MIN) * WIDTH / (X_MAX - X_MIN):.1f},"
        f"{(Y_MAX - lat) * HEIGHT / (Y_MAX - Y_MIN):.1f}"
        for lon, lat in coords
    ]
    return "M" + " L".join(points) + " Z"


def main() -> None:
    if shutil.disk_usage(ROOT).free < 20 * 1024**3 + 256 * 1024**2:
        raise RuntimeError("C: free space is too close to the 20 GiB floor")
    pieces = []
    files = sorted(SOURCE.glob("*.geojson.gz"))
    if not files:
        raise FileNotFoundError("Stats NZ SA1 project source files are missing")
    for source in files:
        with gzip.open(source, "rt", encoding="utf-8") as stream:
            page = json.load(stream)
        land = [
            shape(feature["geometry"])
            for feature in page["features"]
            if feature["geometry"] is not None
            and feature["properties"].get("LANDWATER_NAME") in {"Mainland", "Island"}
        ]
        if land:
            pieces.append(shapely.union_all(land))
    geometry = shapely.union_all(pieces).simplify(0.05, preserve_topology=True)
    polygons = list(geometry.geoms) if hasattr(geometry, "geoms") else [geometry]
    paths = []
    for polygon in polygons:
        if polygon.area < 0.02:
            continue
        paths.append(path_for_ring(polygon.exterior))
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" '
        'viewBox="0 0 1200 720" role="img" aria-label="New Zealand coastline">'
        '<rect width="1200" height="720" fill="#F2EDDF"/>'
        '<path d="' + " ".join(paths) + '" fill="#E8E9E5" stroke="#A6A9A3" '
        'stroke-width="0.6"/></svg>\n'
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(svg, encoding="utf-8")
    print(
        f"Coastline SVG generated from {len(files)} Stats NZ SA1 source pages; "
        f"{len(polygons)} land polygons, {OUTPUT.stat().st_size} bytes"
    )


if __name__ == "__main__":
    main()
