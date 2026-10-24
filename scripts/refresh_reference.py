from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from nzhem.adapters.local.resource_guard import ResourceLimitExceeded
from nzhem.config import Settings
from nzhem.container import build_container

LOGGER = logging.getLogger(__name__)


def run_once() -> None:
    settings = Settings.from_env()
    result = build_container(settings).refresh_reference()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    arguments = parser.parse_args()
    if arguments.worker:
        try:
            run_once()
        except ResourceLimitExceeded as exc:
            LOGGER.warning("Resource guard requested a clean worker restart: %s", exc)
            raise SystemExit(75) from exc
        return

    command = [sys.executable, str(Path(__file__).resolve()), "--worker"]
    while True:
        completed = subprocess.run(command, check=False)  # noqa: S603
        if completed.returncode == 0:
            return
        if completed.returncode != 75:
            raise SystemExit(completed.returncode)
        LOGGER.info("Restarting reference refresh from verified page checkpoints")


if __name__ == "__main__":
    main()
