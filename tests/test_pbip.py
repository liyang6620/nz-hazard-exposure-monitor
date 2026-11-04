import json
from pathlib import Path

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
    assert 'Value = "..\\\\.."' in model_text
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
    assert "No policy or insured-value data" in combined_text
    assert "not an actuarial loss estimate" in combined_text
    assert "Building lifecycle dates are approximate" in combined_text
