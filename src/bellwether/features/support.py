"""Support-ticket history features keyed by subscription_id.

IS_CANCEL is FALSE for every row in this dataset (never populated).
Cancel intent is instead captured in CANCEL_REASON (non-null on ~15K tickets)
with structured values (cancel_reason__too_expensive, cancel_reason__no_effect,
etc.) that map directly to churn archetypes. has_support_cancel_reason reflects
this real signal.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from bellwether.features.guard import PointInTimeGuard


def build(observation_date: date) -> pd.DataFrame:
    guard = PointInTimeGuard(observation_date)
    return guard.read(f"""
        WITH base_subscriptions AS (
            SELECT
                SUBSCRIPTION_ID_HASH AS subscription_id,
                EMAIL_HASH AS email_hash
            FROM GAUNTLET_SANDBOX.SOURCE.SUBSCRIPTIONS
            WHERE CREATED_AT < '{guard.date_str}'::DATE
        ),
        tickets_before_observation AS (
            SELECT
                TICKET_ID_HASH,
                REQUESTER_EMAIL_HASH,
                CREATED_AT,
                RESOLUTION_HOURS,
                IS_ESCALATION,
                ADVERSE_EVENT,
                CANCEL_REASON
            FROM GAUNTLET_SANDBOX.SOURCE.SUPPORT_TICKETS
            WHERE CREATED_AT < '{guard.date_str}'::DATE
        )
        SELECT
            s.subscription_id,
            COUNT(t.TICKET_ID_HASH) AS ticket_count,
            CASE
                WHEN COUNT(t.TICKET_ID_HASH) = 0 THEN NULL
                ELSE DATEDIFF(
                    'day',
                    MAX(t.CREATED_AT),
                    '{guard.date_str}'::DATE
                )
            END AS days_since_last_ticket,
            MAX(IFF(COALESCE(t.ADVERSE_EVENT, FALSE), 1, 0)) AS has_adverse_event,
            MAX(IFF(COALESCE(t.IS_ESCALATION, FALSE), 1, 0)) AS has_escalation,
            AVG(t.RESOLUTION_HOURS) AS avg_resolution_hours,
            MAX(IFF(t.CANCEL_REASON IS NOT NULL, 1, 0)) AS has_support_cancel_reason,
            SUM(IFF(t.CANCEL_REASON IS NOT NULL, 1, 0)) AS support_cancel_reason_count
        FROM base_subscriptions s
        LEFT JOIN tickets_before_observation t
            ON s.email_hash = t.REQUESTER_EMAIL_HASH
        GROUP BY s.subscription_id
    """)
