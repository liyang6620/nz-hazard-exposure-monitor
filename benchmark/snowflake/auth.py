"""Key-pair authentication for the isolated benchmark service user."""

from __future__ import annotations

import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization

try:
    from .env import load_local_env
except ImportError:
    from env import load_local_env


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

    return snowflake.connector.connect(**connection_options())
