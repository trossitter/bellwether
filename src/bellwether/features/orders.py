"""Subscription order-history features keyed by subscription_id."""

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
        subscription_orders AS (
            SELECT
                s.subscription_id,
                o.ORDER_ID_HASH AS order_id,
                o.ORDER_CREATED_AT_UTC AS order_created_at_utc,
                o.TOTAL_PRICE AS total_price,
                o.NET_REVENUE AS net_revenue,
                o.TOTAL_DISCOUNTS AS total_discounts,
                DATEDIFF(
                    'day',
                    LAG(o.ORDER_CREATED_AT_UTC) OVER (
                        PARTITION BY s.subscription_id
                        ORDER BY o.ORDER_CREATED_AT_UTC
                    ),
                    o.ORDER_CREATED_AT_UTC
                ) AS days_since_previous_order
            FROM base_subscriptions s
            JOIN GAUNTLET_SANDBOX.SOURCE.ORDERS o
                ON s.email_hash = o.EMAIL_HASH
            WHERE o.ORDER_CREATED_AT_UTC < '{guard.date_str}'::DATE
                AND o.IS_VALID_ORDER = TRUE
                AND o.IS_SUBSCRIPTION_ORDER = TRUE
        ),
        order_aggregates AS (
            SELECT
                subscription_id,
                COUNT(DISTINCT order_id) AS order_count,
                AVG(total_price) AS aov,
                SUM(COALESCE(net_revenue, 0)) AS total_revenue,
                SUM(COALESCE(total_discounts, 0)) AS total_discounts,
                DATEDIFF(
                    'day',
                    MAX(order_created_at_utc),
                    '{guard.date_str}'::DATE
                ) AS days_since_last_order,
                AVG(days_since_previous_order) AS order_cadence_days,
                IFF(SUM(COALESCE(total_discounts, 0)) > 0, 1, 0)
                    AS has_discount_history
            FROM subscription_orders
            GROUP BY subscription_id
        ),
        product_aggregates AS (
            SELECT
                so.subscription_id,
                COUNT(DISTINCT l.PRODUCT_TITLE) AS distinct_products
            FROM subscription_orders so
            JOIN GAUNTLET_SANDBOX.SOURCE.ORDER_LINES l
                ON so.order_id = l.ORDER_ID_HASH
            WHERE l.IS_VALID_LINE_ITEM = TRUE
                AND l.IS_SUBSCRIPTION = TRUE
            GROUP BY so.subscription_id
        )
        SELECT
            s.subscription_id,
            COALESCE(oa.order_count, 0) AS order_count,
            oa.aov AS aov,
            COALESCE(oa.total_revenue, 0) AS total_revenue,
            COALESCE(oa.total_discounts, 0) AS total_discounts,
            oa.days_since_last_order AS days_since_last_order,
            oa.order_cadence_days AS order_cadence_days,
            CASE
                WHEN COALESCE(oa.order_count, 0) = 0 THEN NULL
                ELSE COALESCE(pa.distinct_products, 0)
            END AS distinct_products,
            COALESCE(oa.has_discount_history, 0) AS has_discount_history
        FROM base_subscriptions s
        LEFT JOIN order_aggregates oa
            ON s.subscription_id = oa.subscription_id
        LEFT JOIN product_aggregates pa
            ON s.subscription_id = pa.subscription_id
    """)
