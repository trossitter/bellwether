"""Point-in-time label builder for subscription churn.

A subscription is "in the cohort" at observation_date T if:
  - CREATED_AT <= T  (it existed)
  - CANCELLED_AT IS NULL OR CANCELLED_AT > T  (it had not yet been cancelled)

Label = 1 if the subscription was cancelled within horizon_days after T.
Label = 0 if it was still active at T + horizon_days.

The snapshot date (2026-04-21) is the last date any event is recorded.
No feature or label query may reference data beyond this date.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from bellwether.db.snowflake import read_sql

SNAPSHOT_DATE: date = date(2026, 4, 21)

# Training windows: observation points at which we create labeled examples.
# Each is at least horizon_days before the snapshot so labels are fully observable.
_TRAINING_OFFSETS_DAYS = [365, 270, 180, 90]


def build_labels(
    observation_date: date,
    horizon_days: int,
) -> pd.DataFrame:
    """Return one row per subscription active at ``observation_date``.

    Columns returned:
        subscription_id, customer_id, brand, observation_date, horizon_days,
        tenure_at_obs_days, label (0/1), cancelled_at, cancellation_reason,
        thesis_formulas, no_quiz_proxy

    ``observation_date`` must be before SNAPSHOT_DATE.
    ``horizon_days`` must be positive and observation_date + horizon_days <= SNAPSHOT_DATE.
    """
    _validate(observation_date, horizon_days)

    label_cutoff = observation_date + timedelta(days=horizon_days)
    obs_str = observation_date.isoformat()
    cutoff_str = label_cutoff.isoformat()

    query = f"""
        SELECT
            SUBSCRIPTION_ID_HASH                                   AS subscription_id,
            RECHARGE_CUSTOMER_ID_HASH                              AS customer_id,
            BRAND                                                  AS brand,
            THESIS_FORMULAS                                        AS thesis_formulas,
            (THESIS_FORMULAS IS NULL)                              AS no_quiz_proxy,
            CREATED_AT                                             AS created_at,
            CANCELLED_AT                                           AS cancelled_at,
            CANCELLATION_REASON                                    AS cancellation_reason,
            DATEDIFF('day', CREATED_AT, '{obs_str}'::DATE)         AS tenure_at_obs_days,
            CASE
                WHEN CANCELLED_AT >= '{obs_str}'::DATE
                 AND CANCELLED_AT <  '{cutoff_str}'::DATE
                THEN 1
                ELSE 0
            END                                                    AS label,
            '{obs_str}'::DATE                                      AS observation_date,
            {horizon_days}                                         AS horizon_days
        FROM GAUNTLET_SANDBOX.SOURCE.SUBSCRIPTIONS
        WHERE
            CREATED_AT < '{obs_str}'::DATE
            AND (CANCELLED_AT IS NULL OR CANCELLED_AT >= '{obs_str}'::DATE)
        ORDER BY subscription_id
    """
    df = read_sql(query)
    df.columns = df.columns.str.lower()
    df["observation_date"] = pd.to_datetime(df["observation_date"]).dt.date
    return df


def scoring_cohort(as_of: date = SNAPSHOT_DATE) -> pd.DataFrame:
    """Return subscriptions currently active at ``as_of`` — the population to score.

    No label column: these are the subscribers we want to predict for, not train on.
    """
    obs_str = as_of.isoformat()
    query = f"""
        SELECT
            SUBSCRIPTION_ID_HASH        AS subscription_id,
            RECHARGE_CUSTOMER_ID_HASH   AS customer_id,
            BRAND                       AS brand,
            THESIS_FORMULAS             AS thesis_formulas,
            (THESIS_FORMULAS IS NULL)   AS no_quiz_proxy,
            CREATED_AT                  AS created_at,
            PRICE                       AS price,
            ORDER_INTERVAL_FREQUENCY    AS order_interval_frequency,
            ORDER_INTERVAL_UNIT         AS order_interval_unit,
            CHARGE_INTERVAL_FREQUENCY   AS charge_interval_frequency,
            DATEDIFF('day', CREATED_AT, '{obs_str}'::DATE) AS tenure_at_obs_days
        FROM GAUNTLET_SANDBOX.SOURCE.SUBSCRIPTIONS
        WHERE STATUS = 'active'
        ORDER BY subscription_id
    """
    df = read_sql(query)
    df.columns = df.columns.str.lower()
    return df


def training_observation_dates(horizon_days: int) -> list[date]:
    """Return observation dates usable for training labels at ``horizon_days``.

    Each date is at least ``horizon_days`` before SNAPSHOT_DATE so labels
    are fully observable in the data.
    """
    return [
        SNAPSHOT_DATE - timedelta(days=offset)
        for offset in _TRAINING_OFFSETS_DAYS
        if offset > horizon_days
    ]


def _validate(observation_date: date, horizon_days: int) -> None:
    if horizon_days <= 0:
        raise ValueError(f"horizon_days must be positive, got {horizon_days}")
    if observation_date >= SNAPSHOT_DATE:
        raise ValueError(
            f"observation_date {observation_date} must be before snapshot {SNAPSHOT_DATE}"
        )
    label_cutoff = observation_date + timedelta(days=horizon_days)
    if label_cutoff > SNAPSHOT_DATE:
        raise ValueError(
            f"observation_date {observation_date} + {horizon_days}d = {label_cutoff} "
            f"exceeds snapshot {SNAPSHOT_DATE}; labels would be unobservable"
        )
