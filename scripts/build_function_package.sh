#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
stage="$repo_root/dist/function"
archive="$repo_root/dist/function.zip"

rm -rf "$stage" "$archive"
mkdir -p "$stage/.python_packages/lib/site-packages" "$stage/vendor/duckdb_extensions"

python -m pip install \
  --requirement "$repo_root/app/requirements.txt" \
  --target "$stage/.python_packages/lib/site-packages" \
  --no-compile 1>&2
python "$repo_root/scripts/fetch_duckdb_extensions.py" 1>&2
python "$repo_root/scripts/verify_duckdb_extensions.py" 1>&2

cp "$repo_root/app/function_app.py" "$repo_root/app/host.json" "$stage/"
cp -R "$repo_root/app/src/nzhem" "$stage/.python_packages/lib/site-packages/"
cp "$repo_root/app/vendor/duckdb_extensions/"*.duckdb_extension \
  "$stage/vendor/duckdb_extensions/"
cp -R "$repo_root/dbt" "$stage/dbt"
find "$stage" -type d -name '__pycache__' -prune -exec rm -rf {} +
find "$stage" -type d -name 'tests' -prune -exec rm -rf {} +
rm -rf "$stage/dbt/target" "$stage/dbt/logs"

(
  cd "$stage"
  zip -q -r "$archive" .
)

uncompressed_bytes="$(du -sb "$stage" | cut -f1)"
zip_bytes="$(stat -c %s "$archive")"
python - <<PY
import json
print(json.dumps({
    "uncompressed_bytes": int("$uncompressed_bytes"),
    "zip_bytes": int("$zip_bytes"),
    "zip_limit_bytes": 1_000_000_000,
    "below_zip_limit": int("$zip_bytes") < 1_000_000_000,
}))
PY
