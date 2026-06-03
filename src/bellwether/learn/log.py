"""Log dispatched actions without retaining private intervention message text.

Bellwether stores only message_length, never the message body, to preserve
subscriber privacy. The resulting action log enables future A/B outcome
measurement by joining dispatched interventions to outcomes on subscriber_id.
"""

from __future__ import annotations

import textwrap

from bellwether.db.snowflake import execute_sql, output_table
from bellwether.dispatch.adapter import DispatchReceipt
from bellwether.eval.contracts import InterventionProposal

_TABLE = "ACTIONS"

DDL = textwrap.dedent(f"""\
    CREATE TABLE IF NOT EXISTS {output_table(_TABLE)} (
        run_id            VARCHAR(64)    NOT NULL,
        subscriber_id     VARCHAR(256)   NOT NULL,
        archetype         VARCHAR(32)    NOT NULL,
        action_type       VARCHAR(64)    NOT NULL,
        urgency_level     VARCHAR(16)    NOT NULL,
        channel           VARCHAR(32)    NOT NULL,
        idempotency_key   VARCHAR(64)    NOT NULL,
        dispatched_at     TIMESTAMP_TZ   NOT NULL,
        message_length    INTEGER        NOT NULL,
        success           BOOLEAN        NOT NULL,
        error             VARCHAR(500),
        logged_at         TIMESTAMP_TZ   NOT NULL
    )
""")


def ensure_table() -> None:
    """Create BELLWETHER_ACTIONS if it does not exist."""
    execute_sql(DDL)


def log_action(
    run_id: str,
    proposal: InterventionProposal,
    receipt: DispatchReceipt,
) -> None:
    """Insert one dispatched action row into BELLWETHER_ACTIONS.

    logged_at is set to UTC now at insert time.
    message_length is len(proposal.message) - do not store the message text.
    """
    ensure_table()
    error = None if receipt.error is None else receipt.error[:500]
    sql = (
        f"INSERT INTO {output_table(_TABLE)} "
        "(run_id, subscriber_id, archetype, action_type, urgency_level, channel, "
        "idempotency_key, dispatched_at, message_length, success, error, logged_at) "
        "VALUES ("
        f"{_q(run_id)}, {_q(receipt.subscriber_id)}, {_q(proposal.archetype)}, "
        f"{_q(proposal.action)}, {_q(proposal.urgency_level)}, {_q(receipt.channel)}, "
        f"{_q(receipt.idempotency_key)}, TO_TIMESTAMP_TZ({_q(receipt.dispatched_at)}), "
        f"{_q(len(proposal.message))}, {_q(receipt.success)}, {_q(error)}, "
        "CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP()))"
    )
    execute_sql(sql)


def _q(v: object) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    escaped = str(v).replace("'", "''")
    return f"'{escaped}'"
