import json
from datetime import datetime
from pathlib import Path

import pytest
from scripts.build_powerbi_snapshot import public_housekeeping_completed_at, utc_naive
from scripts.check_pbip_portability import find_local_paths

ROOT = Path(__file__).resolve().parents[1]
PBIP_ROOT = ROOT / "reports" / "powerbi"


def test_pbip_project_has_five_pages_and_local_only_sources() -> None:
    project = json.loads((PBIP_ROOT / "nzhem.pbip").read_text(encoding="utf-8"))
    definition = PBIP_ROOT / "nzhem.Report" / "definition"
    page_metadata = json.loads((definition / "pages" / "pages.json").read_text(encoding="utf-8"))
    pages_root = definition / "pages"
    page_names = [
        "event-overview",
        "event-comparison",
        "regional-exposure",
        "event-history",
        "data-health",
    ]

    assert project["version"] == "1.0"
    assert page_metadata["pageOrder"] == page_names
    for page_name in page_names:
        page = json.loads((pages_root / page_name / "page.json").read_text(encoding="utf-8"))
        visuals = list((pages_root / page_name / "visuals").glob("*/visual.json"))
        assert page["name"] == page_name
        assert len(visuals) >= 8
        assert all("Aggregation" not in visual.read_text(encoding="utf-8") for visual in visuals)

    model_root = PBIP_ROOT / "nzhem.SemanticModel" / "definition"
    report_text = "\n".join(path.read_text(encoding="utf-8") for path in definition.rglob("*.json"))
    model_text = "\n".join(path.read_text(encoding="utf-8") for path in model_root.rglob("*.tmdl"))
    assert "File.Contents" in model_text
    assert "https://" not in model_text
    assert 'expression RepoRoot = "..\\\\.."' in model_text
    assert "discourageImplicitMeasures" in model_text
    assert "dataCategory: Time" in model_text
    assert "crossFilteringBehavior: oneDirection" in model_text
    assert "table _Measures" in model_text
    assert "measure 'Exposed Buildings'" in model_text
    assert "measure 'Estimated MMI MAE'" in model_text
    combined_text = report_text + model_text
    assert "OPENAI_API_KEY" not in combined_text
    assert "ARCGIS_API_KEY" not in combined_text
    assert "C:/Users/" not in combined_text
    assert "C:\\\\Users\\\\" not in combined_text
    assert find_local_paths(PBIP_ROOT) == []
    assert "READ-ONLY AZURE SNAPSHOT" in combined_text
    assert "not an actuarial loss estimate" in combined_text
    assert "Historical replays use current building outlines and 2023 population" in combined_text


def test_powerbi_health_timestamps_keep_utc_hour() -> None:
    assert utc_naive("2026-11-05T11:00:02Z") == datetime(2026, 11, 5, 11, 0, 2)
    assert utc_naive("2026-11-06T00:00:02+13:00") == datetime(2026, 11, 5, 11, 0, 2)
    with pytest.raises(ValueError, match="timezone"):
        utc_naive("2026-11-05T11:00:02")

    measures = (PBIP_ROOT / "nzhem.SemanticModel/definition/tables/_Measures.tmdl").read_text(
        encoding="utf-8"
    )
    assert "DATEDIFF(MAX(fct_health[Last Run]), MAX(fct_health[Snapshot At]), HOUR)" in measures


def test_powerbi_cloud_health_requires_completed_publication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "success", "completed_at": "2026-11-06T02:00:19Z"}

    monkeypatch.setattr(
        "scripts.build_powerbi_snapshot.requests.get", lambda *args, **kwargs: Response()
    )
    assert public_housekeeping_completed_at() == datetime(2026, 11, 6, 2, 0, 19)

    class Incomplete(Response):
        def json(self) -> dict[str, str]:
            return {"status": "failed", "completed_at": "2026-11-06T03:00:19Z"}

    monkeypatch.setattr(
        "scripts.build_powerbi_snapshot.requests.get", lambda *args, **kwargs: Incomplete()
    )
    with pytest.raises(RuntimeError, match="completion record"):
        public_housekeeping_completed_at()


def test_powerbi_event_identity_and_visual_filters() -> None:
    model = (PBIP_ROOT / "nzhem.SemanticModel/definition/tables/_Measures.tmdl").read_text(
        encoding="utf-8"
    )
    assert "DISTINCTCOUNT(dim_event[GeoNet Event ID])" in model
    assert "replay_exists" in model
    assert "NOT ISFILTERED(dim_event[Event Group])" in model

    pages = PBIP_ROOT / "nzhem.Report/definition/pages"
    expected = {
        ("event-overview", "regions"): "Visible Exposed Region",
        ("event-comparison", "event-buildings"): "Positive Buildings",
        ("event-comparison", "event-people"): "Positive People",
        ("regional-exposure", "region-table"): "Visible Regional Row",
        ("event-history", "history-table"): "Visible History Event",
    }
    for (page, visual_name), measure in expected.items():
        visual = json.loads(
            (pages / page / "visuals" / visual_name / "visual.json").read_text(encoding="utf-8")
        )
        filters = visual["filterConfig"]["filters"]
        assert any(item["field"].get("Measure", {}).get("Property") == measure for item in filters)
    assert "IF([Visible History Event] = 1, MAX(dim_event[Timeline Year]))" in model


def test_powerbi_controls_do_not_overlap() -> None:
    pages = PBIP_ROOT / "nzhem.Report/definition/pages"
    control_names = {
        "event-overview": [
            "event-group-slicer",
            "event-slicer",
            "event-source",
            "exposure-status",
            "threshold",
        ],
        "event-comparison": ["threshold"],
        "regional-exposure": ["event-slicer", "threshold"],
        "event-history": ["region-filter", "event-group-slicer", "threshold"],
    }
    for page, names in control_names.items():
        positions = {
            name: json.loads(
                (pages / page / "visuals" / name / "visual.json").read_text(encoding="utf-8")
            )["position"]
            for name in names
        }
        for index, name in enumerate(names):
            a = positions[name]
            for other in names[index + 1 :]:
                b = positions[other]
                assert not (
                    a["x"] < b["x"] + b["width"]
                    and b["x"] < a["x"] + a["width"]
                    and a["y"] < b["y"] + b["height"]
                    and b["y"] < a["y"] + a["height"]
                ), (page, name, other)


def test_regional_share_uses_full_stock_and_report_titles_preserve_acronyms() -> None:
    model = (PBIP_ROOT / "nzhem.SemanticModel/definition/tables/_Measures.tmdl").read_text(
        encoding="utf-8"
    )
    share = model.split("measure '% Region Buildings Exposed' = ", 1)[1].split("\n", 1)[0]
    assert "REMOVEFILTERS(dim_region)" in share
    assert "ISINSCOPE(dim_region[Territorial Authority])" in share
    assert "dim_region[Region] = selected_region" in share
    assert "dim_region[Territorial Authority] = selected_authority" in share
    assert "CALCULATE(SUM(dim_region[Region Buildings]), REMOVEFILTERS(dim_region))" in share

    pages = PBIP_ROOT / "nzhem.Report/definition/pages"
    region_table = json.loads(
        (pages / "regional-exposure/visuals/region-table/visual.json").read_text(encoding="utf-8")
    )
    assert "_Measures.Repeat Exposure" in json.dumps(region_table)
    assert "_Measures.Accumulated Building Exposures" not in json.dumps(region_table)
    mae_card = json.loads(
        (pages / "data-health/visuals/mae/visual.json").read_text(encoding="utf-8")
    )
    assert "Station-Weighted MAE" in json.dumps(mae_card)
