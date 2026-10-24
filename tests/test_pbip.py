import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PBIP_ROOT = ROOT / "reports" / "powerbi"


def test_pbip_project_has_five_pages_and_local_only_sources() -> None:
    project = json.loads((PBIP_ROOT / "nzhem.pbip").read_text(encoding="utf-8"))
    report = json.loads(
        (PBIP_ROOT / "nzhem.Report" / "definition" / "report.json").read_text(encoding="utf-8")
    )
    pages = list((PBIP_ROOT / "nzhem.Report" / "definition" / "pages").glob("*/page.json"))

    assert project["Version"] == "1.0"
    assert len(report["sections"]) == 5
    assert len(pages) == 5
    assert all(
        json.loads(page.read_text(encoding="utf-8"))["visualContainers"] == [] for page in pages
    )

    model_text = (PBIP_ROOT / "nzhem.SemanticModel" / "definition" / "model.bim").read_text(
        encoding="utf-8"
    )
    assert "File.Contents" in model_text
    assert "https://" not in model_text
    assert "OPENAI_API_KEY" not in model_text
    assert "ARCGIS_API_KEY" not in model_text
