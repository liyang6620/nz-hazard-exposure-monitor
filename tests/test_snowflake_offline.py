from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from benchmark.snowflake import auth
from benchmark.snowflake.load_curated import (
    files_for,
    load,
    put_sql,
    snowflake_type,
    table_ddl,
    validate_schemas,
)
from benchmark.snowflake.reconcile import (
    require_equal_count,
    require_equal_mmi,
    require_equal_sum,
    stable_sum,
)
from benchmark.snowflake.record_credits import nonnegative_credits
from benchmark.snowflake.render_setup import render


def test_setup_requires_credit_quota_and_public_key() -> None:
    public = "A" * 400
    sql = render("200", public)
    assert "CREDIT_QUOTA = 200" in sql
    assert "ON 50 PERCENT DO SUSPEND_IMMEDIATE" in sql
    assert "START_TIMESTAMP = IMMEDIATELY" in sql
    assert "BINARY_AS_TEXT = FALSE" in sql
    assert "AUTO_SUSPEND = 60" in sql
    assert "GRANT OPERATE ON WAREHOUSE NZHEM_XS" in sql
    assert "USE ROLE SYSADMIN" not in sql
    assert "USE ROLE SECURITYADMIN" not in sql
    assert "ALTER USER NZHEM_BENCHMARK_USER SET RSA_PUBLIC_KEY" in sql
    assert "GRANT READ, WRITE ON STAGE" in sql
    assert "GRANT USAGE, READ, WRITE ON STAGE" not in sql
    assert public in sql
    with pytest.raises(ValueError):
        render("0; DROP DATABASE", public)
    with pytest.raises(ValueError):
        render("200", "not a key")


def test_parquet_ddl_and_put_are_local_stage_only(tmp_path: Path) -> None:
    file = tmp_path / "int_population_h3.parquet"
    import duckdb

    with duckdb.connect(":memory:") as connection:
        connection.execute(
            f"COPY (SELECT 617700169958293503::UBIGINT AS h3_res8, "
            f"1.5::DOUBLE AS population) TO '{file.as_posix()}' (FORMAT PARQUET)"
        )
    ddl = table_ddl("int_population_h3", file)
    assert "H3_RES8 NUMBER(20,0)" in ddl
    assert "POPULATION FLOAT" in ddl
    assert "STAGE" not in ddl
    assert "PUT 'file://" in put_sql("int_population_h3", file, tmp_path)
    assert snowflake_type("BLOB") == "BINARY"
    validate_schemas({"int_population_h3": [file]})
    with pytest.raises(FileNotFoundError):
        files_for(tmp_path, "dim_event")
    with pytest.raises(ValueError, match="Unknown curated table"):
        load(tmp_path, execute=False, start_at="wrong")


def test_reconciliation_rejects_count_sum_and_grid_mismatch() -> None:
    require_equal_count("dim_event", 10, 10)
    require_equal_sum("summary", "population", 8.1, 8.1000005)
    require_equal_mmi([("event", 1, 6.2)], [("event", 1, 6.2)])
    with pytest.raises(AssertionError):
        require_equal_count("dim_event", 10, 9)
    with pytest.raises(AssertionError):
        require_equal_sum("summary", "population", 8.1, 8.100001)
    with pytest.raises(AssertionError):
        require_equal_mmi([("event", 1, 6.2)], [("event", 1, 6.3)])

    class Batches:
        def __init__(self):
            self.rows = [[(1e16,), (1.0,), (-1e16,)], []]

        def fetchmany(self, _size: int):
            return self.rows.pop(0)

    assert stable_sum(Batches()) == 1.0
    assert nonnegative_credits("0.025") == "0.025"
    with pytest.raises(ValueError):
        nonnegative_credits("NaN")


def test_warehouse_guard_requires_fresh_admin_attestation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class Cursor:
        description = [(name,) for name in ("size", "auto_suspend", "resource_monitor")]

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def execute(self, sql: str) -> None:
            assert sql == "SHOW WAREHOUSES LIKE 'NZHEM_XS'"

        def fetchall(self):
            return [("X-Small", 60, "null")]

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def cursor(self):
            return Cursor()

    monkeypatch.setattr(auth, "connect", Connection)
    monkeypatch.setattr(auth, "ATTESTATION", tmp_path / "monitor-attestation.json")
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "test-account")
    with pytest.raises(RuntimeError, match="guard differs"):
        auth.assert_warehouse_guard()

    record = {
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "account_sha256": hashlib.sha256(b"test-account").hexdigest(),
        "warehouse": "NZHEM_XS",
        "resource_monitor": "NZHEM_TRIAL_GUARD",
        "credit_quota": 40,
        "suspend_immediately_at_percent": 50,
    }
    auth.ATTESTATION.write_text(json.dumps(record), encoding="utf-8")
    auth.assert_warehouse_guard()

    record["checked_at_utc"] = (datetime.now(UTC) - timedelta(hours=5)).isoformat()
    auth.ATTESTATION.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(RuntimeError, match="guard differs"):
        auth.assert_warehouse_guard()
