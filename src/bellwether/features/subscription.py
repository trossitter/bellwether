"""Base subscription features keyed by subscription_id.

This module builds one point-in-time row per subscription created before the
observation date, using only non-label subscription attributes. PRICE is stored
as VARCHAR in Snowflake, so TRY_CAST is used to produce price_float without
failing the feature query when malformed values are present.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from bellwether.features.guard import PointInTimeGuard


def build(observation_date: date) -> pd.DataFrame:
    guard = PointInTimeGuard(observation_date)
    return guard.read(f"""
        SELECT
            SUBSCRIPTION_ID_HASH AS subscription_id,
            RECHARGE_CUSTOMER_ID_HASH AS customer_id,
            BRAND AS brand,
            TRY_CAST(PRICE AS FLOAT) AS price_float,
            QUANTITY AS quantity,
            ORDER_INTERVAL_FREQUENCY AS order_interval_frequency,
            ORDER_INTERVAL_UNIT AS order_interval_unit,
            CHARGE_INTERVAL_FREQUENCY AS charge_interval_frequency,
            DATEDIFF('day', CREATED_AT, '{guard.date_str}'::DATE) AS tenure_days,
            CASE
                WHEN NEXT_CHARGE_DATE IS NULL
                    OR NEXT_CHARGE_DATE < '{guard.date_str}'::DATE
                THEN NULL
                ELSE NULLIF(
                    DATEDIFF('day', '{guard.date_str}'::DATE, NEXT_CHARGE_DATE),
                    -1
                )
            END AS next_charge_days
        FROM GAUNTLET_SANDBOX.SOURCE.SUBSCRIPTIONS
        WHERE CREATED_AT < '{guard.date_str}'::DATE
    """)
