"""Assemble all feature modules into a single wide DataFrame for a given observation date."""

from __future__ import annotations

from datetime import date
from functools import reduce

import pandas as pd

from bellwether.features import subscription, orders, support, klaviyo, quiz


def assemble(observation_date: date) -> pd.DataFrame:
    """Return one row per Thesis subscription_id with all feature columns merged.

    Subscriptions missing from any feature module receive NaN for that module's
    columns. The quiz module already returns None (→ NaN) for no-quiz subscribers;
    other modules use LEFT JOINs internally so coverage is always 100%.
    """
    frames = [
        subscription.build(observation_date),
        orders.build(observation_date).drop(columns=["customer_id"], errors="ignore"),
        support.build(observation_date),
        klaviyo.build(observation_date),
        quiz.build(observation_date).drop(columns=["customer_id"], errors="ignore"),
    ]

    # quiz has a 'no_quiz_proxy' column; subscription frame doesn't — keep quiz's version
    base = frames[0]
    for frame in frames[1:]:
        overlap = [c for c in frame.columns if c in base.columns and c != "subscription_id"]
        frame = frame.drop(columns=overlap, errors="ignore")
        base = base.merge(frame, on="subscription_id", how="left")

    return base
