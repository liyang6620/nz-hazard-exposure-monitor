"""Check PBIP structure and reject accidental implicit aggregations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/powerbi/nzhem.Report/definition"
MODEL = ROOT / "reports/powerbi/nzhem.SemanticModel/definition"
PAGES = ["event-overview", "event-comparison", "regional-exposure", "event-history", "data-health"]
REQUIRED_MEASURES = (
    "Exposed Buildings",
    "Exposed Footprint m2",
    "Exposed Population",
    "% Region Buildings Exposed",
    "Max MMI",
    "Event Count",
    "Estimated MMI MAE",
    "Last Successful Run",
    "Hours Since Last Run",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--schema", action="store_true", help="also validate against online PBIR JSON schemas"
    )
    args = parser.parse_args()
    page_metadata = json.loads((REPORT / "pages/pages.json").read_text(encoding="utf-8"))
    assert page_metadata["pageOrder"] == PAGES
    measures = (MODEL / "tables/_Measures.tmdl").read_text(encoding="utf-8")
    model = (MODEL / "model.tmdl").read_text(encoding="utf-8")
    assert "discourageImplicitMeasures" in model
    date_table = (MODEL / "tables/dim_date.tmdl").read_text(encoding="utf-8")
    assert "dataCategory: Time" in date_table and "isKey" in date_table
    for measure in REQUIRED_MEASURES:
        assert f"measure '{measure}' =" in measures
    assert "SUM(fct_validation[Absolute Error])" in measures
    assert "COUNTROWS(fct_validation)" in measures
    assert "SELECTEDVALUE('MMI Threshold'[MMI Threshold], 6)" in measures
    visuals = list((REPORT / "pages").glob("*/visuals/*/visual.json"))
    assert len(visuals) >= 40, len(visuals)
    for page in PAGES:
        assert (REPORT / "pages" / page / "page.json").exists()
        assert len(list((REPORT / "pages" / page / "visuals").glob("*/visual.json"))) >= 7
    schemas: dict[str, dict] = {}
    if args.schema:
        import jsonschema
        import requests

    for path in visuals:
        item = json.loads(path.read_text(encoding="utf-8"))
        assert "Aggregation" not in json.dumps(item), path
        if args.schema:
            url = item["$schema"]
            if url not in schemas:
                response = requests.get(url, timeout=20)
                response.raise_for_status()
                schemas[url] = response.json()
            jsonschema.validate(item, schemas[url])
    print(f"Power BI project check passed: {len(PAGES)} pages, {len(visuals)} visuals")


if __name__ == "__main__":
    main()
