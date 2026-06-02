"""The single place that talks to Snowflake.

Reads come only from the read-only ``SOURCE`` schema; writes go only to
namespaced tables in ``OUTPUTS`` (the role has ``CREATE TABLE`` on ``OUTPUTS``
but not on ``SOURCE``). Credentials come from the environment, never argv or disk.
"""

from __future__ import annotations

import os
from contextlib import contextmanager

import pandas as pd
import snowflake.connector

ACCOUNT = "CSB35864"
USER = "GAUNTLET_USER"
WAREHOUSE = "GAUNTLET_WH"
DATABASE = "GAUNTLET_SANDBOX"
SOURCE_SCHEMA = "SOURCE"
OUTPUT_SCHEMA = "OUTPUTS"
OUTPUT_PREFIX = "BELLWETHER_"

_PASSWORD_ENV = "SNOWFLAKE_PASSWORD"


class MissingCredentialError(RuntimeError):
    """Raised when the Snowflake password is absent from the environment."""


def _password() -> str:
    password = os.environ.get(_PASSWORD_ENV)
    if not password:
        raise MissingCredentialError(
            f"{_PASSWORD_ENV} is not set; export it before connecting."
        )
    return password


@contextmanager
def _connection():
    conn = snowflake.connector.connect(
        account=ACCOUNT,
        user=USER,
        password=_password(),
        warehouse=WAREHOUSE,
        database=DATABASE,
        schema=SOURCE_SCHEMA,
    )
    try:
        yield conn
    finally:
        conn.close()


def read_sql(query: str) -> pd.DataFrame:
    """Run a read query against ``SOURCE`` and return the rows as a DataFrame."""
    with _connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            return cursor.fetch_pandas_all()
        finally:
            cursor.close()


def output_table(name: str) -> str:
    """Return the fully-qualified, namespaced ``OUTPUTS`` table name for ``name``."""
    bare = name if name.startswith(OUTPUT_PREFIX) else f"{OUTPUT_PREFIX}{name}"
    return f"{DATABASE}.{OUTPUT_SCHEMA}.{bare}"
