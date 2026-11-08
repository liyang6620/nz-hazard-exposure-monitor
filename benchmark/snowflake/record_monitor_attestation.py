"""Record a short-lived local witness of an administrator's guard check."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime

try:
    from .auth import ATTESTATION
    from .env import load_local_env
except ImportError:
    from auth import ATTESTATION
    from env import load_local_env


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verified-in-snowsight", action="store_true", required=True)
    args = parser.parse_args()
    if not args.verified_in_snowsight:
        raise ValueError("Administrator verification is required")
    load_local_env()
    if os.environ["SNOWFLAKE_TRIAL_CREDIT_QUOTA"] != "40":
        raise ValueError("Approved project monitor cap differs")
    record = {
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "account_sha256": hashlib.sha256(os.environ["SNOWFLAKE_ACCOUNT"].encode()).hexdigest(),
        "warehouse": "NZHEM_XS",
        "resource_monitor": "NZHEM_TRIAL_GUARD",
        "credit_quota": 40,
        "suspend_immediately_at_percent": 50,
        "source": "ACCOUNTADMIN SHOW WAREHOUSES and SHOW RESOURCE MONITORS in Snowsight",
    }
    ATTESTATION.parent.mkdir(parents=True, exist_ok=True)
    ATTESTATION.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print("Recorded a four-hour local monitor attestation; no identifiers or keys printed")


if __name__ == "__main__":
    main()
