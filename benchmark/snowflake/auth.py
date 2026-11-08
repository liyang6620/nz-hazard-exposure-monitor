"""Key-pair authentication for the isolated benchmark service user."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography.hazmat.primitives import serialization

try:
    from .env import ROOT, load_local_env
except ImportError:
    from env import ROOT, load_local_env

ATTESTATION = ROOT / ".local/snowflake/monitor-attestation.json"


def admin_monitor_attested() -> bool:
    if not ATTESTATION.is_file():
        return False
    try:
        record = json.loads(ATTESTATION.read_text(encoding="utf-8"))
        checked = datetime.fromisoformat(record["checked_at_utc"])
        account_hash = hashlib.sha256(os.environ["SNOWFLAKE_ACCOUNT"].encode()).hexdigest()
        return (
            checked.tzinfo is not None
            and timedelta(0) <= datetime.now(UTC) - checked <= timedelta(hours=4)
            and record["account_sha256"] == account_hash
            and record["warehouse"] == "NZHEM_XS"
            and record["resource_monitor"] == "NZHEM_TRIAL_GUARD"
            and record["credit_quota"] == 40
            and record["suspend_immediately_at_percent"] == 50
        )
    except (KeyError, ValueError, TypeError, json.JSONDecodeError):
        return False


def connection_options() -> dict[str, object]:
    load_local_env()
    key_path = Path(os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]).expanduser()
    if not key_path.is_file():
        raise FileNotFoundError("Snowflake private key file is missing")
    passphrase = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")
    key = serialization.load_pem_private_key(
        key_path.read_bytes(), password=passphrase.encode() if passphrase else None
    )
    return {
        "account": os.environ["SNOWFLAKE_ACCOUNT"],
        "user": os.environ.get("SNOWFLAKE_USER", "NZHEM_BENCHMARK_USER"),
        "role": "NZHEM_BENCHMARK_ROLE",
        "warehouse": "NZHEM_XS",
        "database": "NZHEM_BENCHMARK",
        "schema": "CURATED",
        "private_key": key.private_bytes(
            serialization.Encoding.DER,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
        "client_session_keep_alive": False,
        "login_timeout": 30,
    }


def connect():
    import snowflake.connector

    try:
        return snowflake.connector.connect(**connection_options())
    except snowflake.connector.Error as error:
        message = str(error).lower()
        signals = [
            signal
            for signal in (
                "does not exist",
                "disabled",
                "dns",
                "ssl",
                "certificate",
                "timed out",
                "timeout",
                "jwt",
                "public key",
                "private key",
                "invalid",
                "unauthorized",
                "connection refused",
                "network",
                "not found",
                "proxy",
                "account",
                "fingerprint",
                "signature",
                "expired",
                "issued",
                "mismatch",
                "not registered",
                "user",
            )
            if signal in message
        ]
        raise RuntimeError(
            f"Snowflake connection failed (code {error.errno}, SQLSTATE {error.sqlstate}, "
            f"signals {signals})"
        ) from None


def assert_warehouse_guard() -> None:
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("SHOW WAREHOUSES LIKE 'NZHEM_XS'")
        columns = [column[0].lower() for column in cursor.description]
        rows = cursor.fetchall()
        if len(rows) != 1:
            raise RuntimeError("Benchmark warehouse is missing or not visible")
        warehouse = dict(zip(columns, rows[0], strict=True))
        monitor = str(warehouse.get("resource_monitor", "")).upper()
        if (
            str(warehouse.get("size", "")).lower() not in {"x-small", "xsmall"}
            or int(warehouse.get("auto_suspend") or 0) != 60
            or (
                monitor != "NZHEM_TRIAL_GUARD"
                and not (monitor == "NULL" and admin_monitor_attested())
            )
        ):
            raise RuntimeError("Benchmark warehouse guard differs from approved setup")


def suspend_warehouse() -> None:
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("SHOW WAREHOUSES LIKE 'NZHEM_XS'")
        columns = [column[0].lower() for column in cursor.description]
        rows = cursor.fetchall()
        if len(rows) != 1:
            raise RuntimeError("Benchmark warehouse missing during suspension")
        warehouse = dict(zip(columns, rows[0], strict=True))
        if str(warehouse.get("state", "")).upper() != "SUSPENDED":
            cursor.execute("ALTER WAREHOUSE NZHEM_XS SUSPEND")
