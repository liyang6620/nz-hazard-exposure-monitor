from __future__ import annotations

import argparse
import mimetypes
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish the built React site to $web")
    parser.add_argument("--dist", type=Path, default=Path("frontend/dist"))
    parser.add_argument("--account-name", required=True)
    args = parser.parse_args()
    root = args.dist.resolve()
    if not (root / "index.html").is_file():
        raise FileNotFoundError("Vite build output is missing index.html")
    service = BlobServiceClient(
        f"https://{args.account_name}.blob.core.windows.net",
        credential=DefaultAzureCredential(exclude_interactive_browser_credential=True),
    )
    web = service.get_container_client("$web")
    count = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative.startswith(("data/", "briefings/")):
            continue
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        cache_control = "no-cache" if relative == "index.html" else "public, max-age=31536000"
        with path.open("rb") as stream:
            web.upload_blob(
                relative,
                stream,
                overwrite=True,
                max_concurrency=1,
                content_settings=ContentSettings(
                    content_type=content_type, cache_control=cache_control
                ),
            )
        count += 1
    print(f"Published {count} static application files; runtime data was preserved")


if __name__ == "__main__":
    main()
