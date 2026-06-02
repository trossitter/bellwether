"""Klaviyo engagement features for the mandatory 180-day lookback window.

KLAVIYO_EVENTS has 102 million rows, so every query in this module must keep
both EVENT_AT bounds: EVENT_AT >= DATEADD('day', -180, observation_date) and
EVENT_AT < observation_date. The lower bound keeps Snowflake scans bounded;
the upper bound preserves point-in-time safety.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from bellwether.features.guard import PointInTimeGuard


def build(observation_date: date) -> pd.DataFrame:
    guard = PointInTimeGuard(observation_date)
    raw = guard.read(f"""
        WITH base_subscriptions AS (
            SELECT
                SUBSCRIPTION_ID_HASH AS subscription_id,
                EMAIL_HASH AS email_hash
            FROM GAUNTLET_SANDBOX.SOURCE.SUBSCRIPTIONS
            WHERE CREATED_AT < '{guard.date_str}'::DATE
        ),
        profiles_before_observation AS (
            SELECT
                PROFILE_ID_HASH,
                EMAIL_HASH,
                ACCEPTS_MARKETING
            FROM GAUNTLET_SANDBOX.SOURCE.KLAVIYO_PROFILES
            WHERE CREATED_AT < '{guard.date_str}'::DATE
        ),
        events_180_day AS (
            SELECT
                PROFILE_ID_HASH,
                METRIC_NAME,
                EVENT_AT
            FROM GAUNTLET_SANDBOX.SOURCE.KLAVIYO_EVENTS
            WHERE EVENT_AT >= DATEADD('day', -180, '{guard.date_str}'::DATE)
                AND EVENT_AT < '{guard.date_str}'::DATE
        )
        SELECT
            s.subscription_id,
            COALESCE(
                COUNT_IF(e.METRIC_NAME = 'Received Email'),
                0
            ) AS email_received_count,
            COALESCE(
                COUNT_IF(e.METRIC_NAME = 'Opened Email'),
                0
            ) AS email_open_count,
            COALESCE(
                COUNT_IF(e.METRIC_NAME = 'Clicked Email'),
                0
            ) AS email_click_count,
            COALESCE(
                COUNT_IF(e.METRIC_NAME = 'Received SMS'),
                0
            ) AS sms_received_count,
            DATEDIFF(
                'day',
                MAX(IFF(e.METRIC_NAME = 'Opened Email', e.EVENT_AT, NULL)),
                '{guard.date_str}'::DATE
            ) AS days_since_last_email_open,
            MAX(IFF(
                e.METRIC_NAME = 'Manually Suppressed from Email Marketing',
                1,
                0
            )) AS is_suppressed,
            MAX(CASE
                WHEN p.ACCEPTS_MARKETING THEN 1
                WHEN p.ACCEPTS_MARKETING = FALSE THEN 0
                ELSE NULL
            END) AS accepts_marketing
        FROM base_subscriptions s
        LEFT JOIN profiles_before_observation p
            ON s.email_hash = p.EMAIL_HASH
        LEFT JOIN events_180_day e
            ON p.PROFILE_ID_HASH = e.PROFILE_ID_HASH
        GROUP BY s.subscription_id
    """)

    denominator = raw["email_received_count"].where(raw["email_received_count"] != 0)
    raw["email_open_rate"] = raw["email_open_count"] / denominator
    raw["email_click_rate"] = raw["email_click_count"] / denominator
    raw["accepts_marketing"] = raw["accepts_marketing"].apply(
        lambda value: None if pd.isna(value) else bool(value)
    )
    return raw[[
        "subscription_id",
        "email_received_count",
        "email_open_count",
        "email_click_count",
        "sms_received_count",
        "email_open_rate",
        "email_click_rate",
        "days_since_last_email_open",
        "is_suppressed",
        "accepts_marketing",
    ]]
