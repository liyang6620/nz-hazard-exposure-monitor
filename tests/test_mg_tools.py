import json
from pathlib import Path

from scripts.build_local_map import mmi_band as map_mmi_band
from scripts.cross_validate_kaikoura import mmi_band
from scripts.export_file_geodatabase import FIELD_METADATA
from shapely.geometry import shape


def test_mmi_bands_match_reporting_contract() -> None:
    assert [mmi_band(value) for value in (None, 3.9, 4.0, 5.9, 7.99, 8.0)] == [
        "<4",
        "<4",
        "4",
        "5",
        "7",
        "8+",
    ]
    assert [map_mmi_band(value) for value in (3.9, 4.0, 7.99, 8.0)] == [
        "<4",
        "4",
        "7",
        "8+",
    ]


def test_file_geodatabase_metadata_covers_each_export_layer() -> None:
    layers = {row[0] for row in FIELD_METADATA}

    assert layers == {"nzhem_events", "event_exposure_r6"}


def test_local_map_does_not_embed_arcgis_credentials() -> None:
    map_root = Path("hosts/local/site/map")
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in (map_root / "index.html", map_root / "map.js")
    ).lower()

    assert "apikey" not in source
    assert "accesstoken" not in source
    assert "portalitem" not in source


def test_local_map_geojson_is_strict_wgs84_xy() -> None:
    data_root = Path("hosts/local/site/map/data")

    for path in sorted(data_root.glob("*.geojson")):
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
        for feature in payload["features"]:
            min_x, min_y, max_x, max_y = shape(feature["geometry"]).bounds
            assert 160 <= min_x <= 180 or -180 <= min_x <= -170
            assert 160 <= max_x <= 180 or -180 <= max_x <= -170
            assert -50 <= min_y <= -30
            assert -50 <= max_y <= -30


def test_arcgis_write_test_respects_static_map_and_secret_limits() -> None:
    path = Path("evidence/mg/arcgis-write-test.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    text = path.read_text(encoding="utf-8")

    assert payload["static_maps"]["calls"] <= 3
    assert payload["prohibited_services_called"] is False
    assert payload["secret_logged"] is False
    assert payload["account_or_permissions_changed"] is False
    assert "AAPT" not in text


def test_arcgis_formal_publish_evidence_is_within_project_limits() -> None:
    path = Path("evidence/mg/arcgis-publish.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    text = path.read_text(encoding="utf-8")

    assert payload["hosted_layer"]["feature_count"] == 4011
    assert payload["hosted_layer"]["definition_admin_operations_called"] is False
    assert payload["incremental_update"]["item_id_unchanged"] is True
    assert payload["limits"]["under_limits"] is True
    assert payload["static_maps"]["rest_validation_calls"] <= 2
    assert payload["static_maps"]["known_successful_calls_this_work"] <= 200
    assert payload["static_maps"]["prohibited_services_called"] is False
    assert payload["credential"]["browser_exposure"] is False
    assert payload["credential"]["secret_logged"] is False
    assert "AAPT" not in text
