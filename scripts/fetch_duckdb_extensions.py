from __future__ import annotations

import gzip
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "scripts" / "duckdb-extension-lock.json"
OUTPUT = ROOT / "hosts" / "azure_functions" / "vendor" / "duckdb_extensions"


def main() -> None:
    lock = json.loads(LOCK_PATH.read_text(encoding="ascii"))
    version = lock["duckdb_version"]
    platform = lock["platform"]
    OUTPUT.mkdir(parents=True, exist_ok=True)

    for name, metadata in lock["extensions"].items():
        host = (
            "community-extensions.duckdb.org"
            if metadata["repository"] == "community"
            else "extensions.duckdb.org"
        )
        url = f"https://{host}/v{version}/{platform}/{name}.duckdb_extension.gz"
        destination = OUTPUT / f"{name}.duckdb_extension"
        request = urllib.request.Request(  # noqa: S310
            url,
            headers={"User-Agent": "nz-hazard-exposure-monitor/0.1"},
        )
        with (
            urllib.request.urlopen(request, timeout=30) as response,  # noqa: S310
            gzip.GzipFile(fileobj=response) as compressed,
            destination.open("wb") as output,
        ):
            shutil.copyfileobj(compressed, output)

        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        if digest != metadata["sha256"]:
            destination.unlink(missing_ok=True)
            raise RuntimeError(f"SHA256 mismatch for {name}: {digest}")
        print(f"{name}: {destination.stat().st_size} bytes sha256={digest}")


if __name__ == "__main__":
    main()
