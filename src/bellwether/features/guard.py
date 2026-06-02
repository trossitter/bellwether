"""PointInTimeGuard — prevents feature leakage past observation_date.

Every feature query that touches a time-series table must include
observation_date as a date bound. The guard enforces this at runtime by
checking that the ISO date string appears in the query before executing it.

This is a hard gate: a query that slips past without the date bound would
silently introduce future data into training features.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from bellwether.db.snowflake import read_sql


class LeakageError(RuntimeError):
    """Raised when a feature query lacks an observation_date bound."""


class PointInTimeGuard:
    """Wraps read_sql and asserts temporal safety before execution.

    Usage in feature modules::

        guard = PointInTimeGuard(observation_date)
        df = guard.read(f\"\"\"
            SELECT ...
            FROM orders
            WHERE created_at < '{guard.date_str}'::DATE
        \"\"\")
    """

    def __init__(self, observation_date: date) -> None:
        self.observation_date = observation_date
        self.date_str = observation_date.isoformat()

    def read(self, query: str) -> pd.DataFrame:
        """Execute ``query`` after asserting it references ``observation_date``."""
        if self.date_str not in query:
            raise LeakageError(
                f"Feature query does not contain observation_date {self.date_str!r}. "
                "All time-series feature queries must be date-bounded to prevent leakage."
            )
        df = read_sql(query)
        df.columns = df.columns.str.lower()
        return df
