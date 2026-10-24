from pathlib import Path
from zipfile import ZipFile

import pytest

from nzhem.adapters.local.shaking_layers import ShakingLayersClient


class Guard:
    def check(self) -> None:
        return None


def test_polygon_archive_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.zip"
    with ZipFile(archive, "w") as output:
        output.writestr("../intensity_mmi.shp", b"unsafe")
    client = ShakingLayersClient(tmp_path / "raw", Guard())  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Unsafe"):
        client._extract_polygons(archive, tmp_path / "out")


def test_polygon_archive_requires_expected_shapefile(tmp_path: Path) -> None:
    archive = tmp_path / "missing.zip"
    with ZipFile(archive, "w") as output:
        output.writestr("readme.txt", b"metadata")
    client = ShakingLayersClient(tmp_path / "raw", Guard())  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="No intensity_mmi.shp"):
        client._extract_polygons(archive, tmp_path / "out")
