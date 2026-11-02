from __future__ import annotations

import argparse
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient


def staged_files(root: Path) -> list[tuple[str, str, Path]]:
    reference_parent = root / "curated" / "reference-export"
    references = sorted(path for path in reference_parent.iterdir() if path.is_dir())
    if not references:
        raise FileNotFoundError("No approved reference export exists")
    reference = references[-1]
    gold = root / "curated" / "events" / "m3"
    if not (gold / "mart_event_summary.parquet").is_file():
        raise FileNotFoundError("M3 gold outputs are missing")
    files = [
        (
            "curated",
            f"reference-export/{reference.name}/{path.relative_to(reference).as_posix()}",
            path,
        )
        for path in sorted(reference.rglob("*.parquet"))
    ]
    files.extend(
        ("gold", f"events/m3/{path.relative_to(gold).as_posix()}", path)
        for path in sorted(gold.rglob("*.parquet"))
    )
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage approved local Parquet for Azure Functions")
    parser.add_argument("--data-root", type=Path, default=Path(".local/data"))
    parser.add_argument("--account-name", required=True)
    parser.add_argument("--execute", action="store_true", help="Upload after the approved apply")
    args = parser.parse_args()
    files = staged_files(args.data_root)
    total = sum(path.stat().st_size for _, _, path in files)
    print(f"Parquet files: {len(files)}; bytes: {total}; upload: {args.execute}")
    if not args.execute:
        return
    service = BlobServiceClient(
        f"https://{args.account_name}.blob.core.windows.net",
        credential=DefaultAzureCredential(exclude_interactive_browser_credential=True),
    )
    for container, name, path in files:
        with path.open("rb") as stream:
            service.get_blob_client(container, name).upload_blob(
                stream, overwrite=True, max_concurrency=1
            )
    print(f"Uploaded {len(files)} Parquet files")


if __name__ == "__main__":
    main()
