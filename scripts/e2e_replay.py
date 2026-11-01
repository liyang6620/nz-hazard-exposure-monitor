from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _normalise(value: str, float_precision: int) -> str:
    stripped = value.strip()
    if stripped == "":
        return ""
    try:
        number = Decimal(stripped)
    except InvalidOperation:
        return stripped
    quantizer = Decimal(1).scaleb(-float_precision)
    return format(number.quantize(quantizer), "f")


def canonical_csv_hash(
    path: Path,
    *,
    primary_key: list[str],
    event_id: str,
    float_precision: int,
) -> str:
    with path.open(newline="", encoding="utf-8") as source:
        rows = [row for row in csv.DictReader(source) if row.get("event_id") == event_id]
    rows.sort(key=lambda row: tuple(row[column] for column in primary_key))
    normalised = [
        {key: _normalise(value, float_precision) for key, value in sorted(row.items())}
        for row in rows
    ]
    encoded = json.dumps(normalised, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def replay_and_hash(gold_root: Path, manifest_path: Path) -> dict[str, Any]:
    """Hash licensed real-event gold snapshots in deterministic primary-key order."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output: dict[str, Any] = {
        "fixture_kind": manifest["fixture_kind"],
        "float_precision": manifest["float_precision"],
        "events": {},
    }
    for event_name, event_id in manifest["events"].items():
        table_hashes = {}
        for table_name, table in manifest["tables"].items():
            table_hashes[table_name] = canonical_csv_hash(
                gold_root / table["path"],
                primary_key=table["primary_key"],
                event_id=event_id,
                float_precision=manifest["float_precision"],
            )
        output["events"][event_name] = {"event_id": event_id, "tables": table_hashes}
    return output


def verify_azure_parquet(data_root: Path, account_name: str) -> dict[str, Any]:
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient
    from scripts.stage_azure_data import staged_files

    service = BlobServiceClient(
        f"https://{account_name}.blob.core.windows.net",
        credential=DefaultAzureCredential(exclude_interactive_browser_credential=True),
    )
    files = staged_files(data_root)
    aggregate = hashlib.sha256()
    total_bytes = 0
    for container, blob_name, path in files:
        local_hash = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                local_hash.update(chunk)

        remote_hash = hashlib.sha256()
        remote_bytes = 0
        stream = service.get_blob_client(container, blob_name).download_blob(max_concurrency=1)
        for chunk in stream.chunks():
            remote_hash.update(chunk)
            remote_bytes += len(chunk)
        if remote_bytes != path.stat().st_size or remote_hash.digest() != local_hash.digest():
            raise ValueError(f"Azure Parquet differs from local: {container}/{blob_name}")
        total_bytes += remote_bytes
        aggregate.update(f"{container}/{blob_name}:".encode())
        aggregate.update(local_hash.hexdigest().encode())
    return {"files": len(files), "bytes": total_bytes, "sha256": aggregate.hexdigest()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay parity hashing framework")
    parser.add_argument("--gold-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--azure-account-name")
    parser.add_argument("--data-root", type=Path, default=Path(".local/data"))
    arguments = parser.parse_args()
    result = replay_and_hash(arguments.gold_root, arguments.manifest)
    if arguments.azure_account_name:
        result["azure_parquet_parity"] = verify_azure_parquet(
            arguments.data_root, arguments.azure_account_name
        )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
