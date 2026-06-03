"""Write eval metric records to BELLWETHER_EVAL_RUNS in Snowflake OUTPUTS.

All writes route through ``output_table()`` from the existing Snowflake boundary
so the credential and schema discipline is never bypassed.
"""

from __future__ import annotations

import subprocess
import textwrap
from datetime import datetime, timezone

from bellwether.db.snowflake import execute_sql, output_table, read_sql

_TABLE = "EVAL_RUNS"

DDL = textwrap.dedent(f"""\
    CREATE TABLE IF NOT EXISTS {output_table(_TABLE)} (
        run_id          VARCHAR(64)   NOT NULL,
        run_ts          TIMESTAMP_TZ  NOT NULL,
        pipeline_stage  VARCHAR(32)   NOT NULL,
        eval_type       VARCHAR(32)   NOT NULL,
        metric_name     VARCHAR(64)   NOT NULL,
        metric_value    FLOAT         NOT NULL,
        threshold       FLOAT,
        passed          BOOLEAN       NOT NULL,
        n_subscribers   INTEGER,
        model_version   VARCHAR(64),
        git_sha         VARCHAR(40),
        notes           VARCHAR(1000)
    )
""")


def ensure_table() -> None:
    """Create BELLWETHER_EVAL_RUNS if it does not already exist."""
    execute_sql(DDL)


def _git_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() or None
    except Exception:
        return None


def record_metric(
    run_id: str,
    stage: str,
    eval_type: str,
    metric_name: str,
    metric_value: float,
    threshold: float | None = None,
    n_subscribers: int | None = None,
    model_version: str | None = None,
    notes: str | None = None,
) -> None:
    """Insert one metric row into BELLWETHER_EVAL_RUNS.

    ``passed`` is computed here: True when threshold is None (no gate) or
    metric_value meets the threshold direction encoded in metric_name convention
    (see plan). Callers that need custom pass logic should compute ``passed``
    and pass it via ``notes``; the default assumes lower-is-better for error
    metrics and higher-is-better for score metrics.
    """
    passed = _compute_passed(metric_name, metric_value, threshold)
    run_ts = datetime.now(tz=timezone.utc).isoformat()
    git = _git_sha()

    def _q(v: object) -> str:
        if v is None:
            return "NULL"
        if isinstance(v, bool):
            return "TRUE" if v else "FALSE"
        if isinstance(v, (int, float)):
            return str(v)
        escaped = str(v).replace("'", "''")
        return f"'{escaped}'"

    sql = (
        f"INSERT INTO {output_table(_TABLE)} "
        "(run_id, run_ts, pipeline_stage, eval_type, metric_name, metric_value, "
        "threshold, passed, n_subscribers, model_version, git_sha, notes) VALUES ("
        f"{_q(run_id)}, {_q(run_ts)}, {_q(stage)}, {_q(eval_type)}, "
        f"{_q(metric_name)}, {_q(metric_value)}, {_q(threshold)}, {_q(passed)}, "
        f"{_q(n_subscribers)}, {_q(model_version)}, {_q(git)}, {_q(notes)})"
    )
    execute_sql(sql)


# Metrics where lower values are better (threshold is an upper bound).
_LOWER_IS_BETTER = {
    "brier_score",
    "expected_calibration_error",
    "ece",
    "pr_auc_subgroup_gap",
    "shap_quiz_share",
    "null_rate",
    "duplicate_count",
    "contract_failures",
    "leakage_violations",
    "archetype_overlap_count",
    "row_drop_count",
}


def _compute_passed(metric_name: str, value: float, threshold: float | None) -> bool:
    if threshold is None:
        return True
    import math
    if math.isnan(value):
        return False
    if metric_name in _LOWER_IS_BETTER:
        return value <= threshold
    return value >= threshold
