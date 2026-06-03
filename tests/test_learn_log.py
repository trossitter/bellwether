"""Tests for dispatched action logging."""

from datetime import datetime, timezone
import os
import re
import sys
import types
import uuid
from unittest.mock import Mock

import pytest

from bellwether.dispatch.adapter import DispatchReceipt
from bellwether.eval.contracts import InterventionProposal


def _proposal(message: str) -> InterventionProposal:
    return InterventionProposal(
        subscriber_id="sub_learn_001",
        archetype="price",
        action="offer_discount",
        message=message,
        urgency_level="medium",
    )


def _receipt(
    subscriber_id: str = "sub_learn_001",
    action: str = "offer_discount",
    error: str | None = "couldn't deliver",
) -> DispatchReceipt:
    return DispatchReceipt(
        subscriber_id=subscriber_id,
        action=action,
        channel="email",
        idempotency_key="idem_learn_001",
        dispatched_at="2026-06-02T12:34:56+00:00",
        success=True,
        error=error,
    )


def _purge_imports() -> None:
    for name in (
        "bellwether.learn.log",
        "bellwether.learn",
        "bellwether.db",
        "bellwether.db.snowflake",
    ):
        sys.modules.pop(name, None)
    bellwether = sys.modules.get("bellwether")
    if bellwether is not None:
        for attr in ("learn", "db"):
            if hasattr(bellwether, attr):
                delattr(bellwether, attr)


def test_log_action_inserts_well_formed_sql_without_message_text(monkeypatch: pytest.MonkeyPatch) -> None:
    private_message = "Private copy must not be stored anywhere in the action log."
    proposal = _proposal(private_message)
    receipt = _receipt()
    mock_read_sql = Mock()
    snowflake = types.ModuleType("bellwether.db.snowflake")
    snowflake.MissingCredentialError = RuntimeError
    snowflake.output_table = lambda name: f"GAUNTLET_SANDBOX.OUTPUTS.BELLWETHER_{name}"
    snowflake.read_sql = mock_read_sql

    _purge_imports()
    monkeypatch.setitem(sys.modules, "bellwether.db.snowflake", snowflake)
    try:
        from bellwether.learn.log import log_action

        log_action("run_learn_001", proposal, receipt)
    finally:
        _purge_imports()

    ddl_sql = mock_read_sql.call_args_list[0].args[0]
    insert_sql = mock_read_sql.call_args_list[1].args[0]

    assert len(mock_read_sql.call_args_list) == 2
    assert "CREATE TABLE IF NOT EXISTS GAUNTLET_SANDBOX.OUTPUTS.BELLWETHER_ACTIONS" in ddl_sql
    assert "INSERT INTO GAUNTLET_SANDBOX.OUTPUTS.BELLWETHER_ACTIONS" in insert_sql
    assert private_message not in insert_sql
    assert str(len(private_message)) in insert_sql
    assert "TO_TIMESTAMP_TZ('2026-06-02T12:34:56+00:00')" in insert_sql
    assert "CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP())" in insert_sql
    assert "'couldn''t deliver'" in insert_sql
    assert re.search(
        r"\(run_id, subscriber_id, archetype, action_type, urgency_level, channel, "
        r"idempotency_key, dispatched_at, message_length, success, error, logged_at\)",
        insert_sql,
    )
    assert re.search(
        r"VALUES \('run_learn_001', 'sub_learn_001', 'price', 'offer_discount', "
        r"'medium', 'email', 'idem_learn_001', TO_TIMESTAMP_TZ\('[^']+'\), "
        rf"{len(private_message)}, TRUE, 'couldn''t deliver', ",
        insert_sql,
    )


@pytest.mark.integration
def test_action_log_table_exists_and_row_round_trips() -> None:
    if not os.environ.get("SNOWFLAKE_PASSWORD"):
        pytest.skip("SNOWFLAKE_PASSWORD is required for Snowflake integration tests.")

    from bellwether.db.snowflake import output_table, read_sql
    from bellwether.learn.log import ensure_table, log_action

    run_id = f"run_{uuid.uuid4().hex}"
    subscriber_id = f"sub_{uuid.uuid4().hex}"
    idempotency_key = uuid.uuid4().hex
    message = "A concise integration message whose content should not be persisted."
    proposal = InterventionProposal(
        subscriber_id=subscriber_id,
        archetype="price",
        action="offer_discount",
        message=message,
        urgency_level="medium",
    )
    receipt = DispatchReceipt(
        subscriber_id=subscriber_id,
        action=proposal.action,
        channel="simulated",
        idempotency_key=idempotency_key,
        dispatched_at=datetime.now(timezone.utc).isoformat(),
        success=False,
        error="integration test error",
    )

    ensure_table()
    table_exists = read_sql("""
        SELECT COUNT(*) AS n
        FROM GAUNTLET_SANDBOX.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'OUTPUTS'
          AND TABLE_NAME = 'BELLWETHER_ACTIONS'
    """)

    try:
        log_action(run_id, proposal, receipt)
        rows = read_sql(f"""
            SELECT
                run_id,
                subscriber_id,
                archetype,
                action_type,
                urgency_level,
                channel,
                idempotency_key,
                message_length,
                success,
                error
            FROM {output_table("ACTIONS")}
            WHERE run_id = '{run_id}'
              AND idempotency_key = '{idempotency_key}'
        """)
    finally:
        read_sql(f"""
            DELETE FROM {output_table("ACTIONS")}
            WHERE run_id = '{run_id}'
              AND idempotency_key = '{idempotency_key}'
        """)

    assert int(table_exists.iloc[0, 0]) == 1
    assert len(rows) == 1
    row = rows.rename(columns=str.lower).iloc[0]
    assert row["run_id"] == run_id
    assert row["subscriber_id"] == subscriber_id
    assert row["archetype"] == proposal.archetype
    assert row["action_type"] == proposal.action
    assert row["urgency_level"] == proposal.urgency_level
    assert row["channel"] == receipt.channel
    assert row["idempotency_key"] == idempotency_key
    assert int(row["message_length"]) == len(message)
    assert bool(row["success"]) is False
    assert row["error"] == receipt.error
