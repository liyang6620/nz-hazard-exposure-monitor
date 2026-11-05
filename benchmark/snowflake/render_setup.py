"""Render account-specific SQL locally; the output stays under ignored .local/."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = Path(__file__).with_name("setup.sql")

try:
    from .env import load_local_env
except ImportError:
    from env import load_local_env


def render(quota: str, public_key: str) -> str:
    if not re.fullmatch(r"[1-9][0-9]*(?:\.[0-9]+)?", quota):
        raise ValueError("Trial credit quota must be a positive number of credits")
    if not re.fullmatch(r"[A-Za-z0-9+/=]+", public_key) or len(public_key) < 300:
        raise ValueError("Expected an unwrapped RSA public key in base64")
    return (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("{{TRIAL_CREDIT_QUOTA}}", quota)
        .replace("{{RSA_PUBLIC_KEY}}", public_key)
    )


def main() -> None:
    load_local_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / ".local/snowflake/setup.rendered.sql")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / ".local").resolve()):
        raise ValueError("Rendered setup SQL must stay under ignored .local/")
    quota = os.environ["SNOWFLAKE_TRIAL_CREDIT_QUOTA"]
    public_key = os.environ["SNOWFLAKE_RSA_PUBLIC_KEY"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(quota, public_key), encoding="utf-8")
    print(f"Rendered setup SQL to {output}; verify the quota before execution")


if __name__ == "__main__":
    main()
