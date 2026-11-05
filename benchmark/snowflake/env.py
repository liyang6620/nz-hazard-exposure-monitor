"""Load ignored local settings for benchmark CLI processes."""

from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]


def load_local_env() -> None:
    load_dotenv(ROOT / ".env", override=False)
