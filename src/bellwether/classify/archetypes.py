"""Deterministic subscriber routing into one intervention archetype.

Priority order is stimulant, efficacy, involuntary, fatigue, price,
life_change, then the default price fallback. The first matching rule wins so
each scored subscriber receives exactly one archetype without Snowflake or LLM
calls.
"""

from __future__ import annotations

import enum
import math

import pandas as pd


class Archetype(str, enum.Enum):
    price = "price"
    efficacy = "efficacy"
    fatigue = "fatigue"
    life_change = "life_change"
    stimulant = "stimulant"
    involuntary = "involuntary"


_EFFICACY_SHAP_FEATURES = frozenset({
    "has_clarity",
    "has_creativity",
    "has_logic",
    "has_confidence",
    "no_quiz_proxy",
})
_FATIGUE_SHAP_FEATURES = frozenset({
    "order_count",
    "order_cadence_days",
    "days_since_last_order",
    "distinct_products",
})
_PRICE_SHAP_FEATURES = frozenset({"price_float", "has_discount_history"})
_LIFE_CHANGE_SHAP_FEATURES = frozenset({
    "tenure_days",
    "days_since_last_order",
    "next_charge_days",
})


def classify(row: dict | pd.Series) -> Archetype:
    """Apply priority rules, return exactly one Archetype."""
    if _is_stimulant(row):
        return Archetype.stimulant
    if _is_efficacy(row):
        return Archetype.efficacy
    if _is_involuntary(row):
        return Archetype.involuntary
    if _is_fatigue(row):
        return Archetype.fatigue
    if _is_price(row):
        return Archetype.price
    if _is_life_change(row):
        return Archetype.life_change
    return Archetype.price


def classify_batch(df: pd.DataFrame) -> pd.Series:
    """classify() applied to every row; returns Series of Archetype."""
    return df.apply(classify, axis=1).astype(object)


def _is_stimulant(row: dict | pd.Series) -> bool:
    return _flag(row, "has_adverse_event") and (
        _flag(row, "has_motivation")
        or _flag(row, "has_energy")
        or _flag(row, "no_quiz_proxy")
    )


def _is_efficacy(row: dict | pd.Series) -> bool:
    return (
        (_flag(row, "has_adverse_event") and not _is_stimulant(row))
        or _flag(row, "has_support_cancel_reason")
        or _has_positive_top1(row, _EFFICACY_SHAP_FEATURES)
    )


def _is_involuntary(row: dict | pd.Series) -> bool:
    order_count = _number(row, "order_count")
    return _is_missing(_value(row, "next_charge_days")) and (
        order_count is not None and order_count <= 1
    )


def _is_fatigue(row: dict | pd.Series) -> bool:
    cadence = _number(row, "order_cadence_days")
    return _has_positive_top1(row, _FATIGUE_SHAP_FEATURES) or (
        cadence is not None and cadence < 20
    )


def _is_price(row: dict | pd.Series) -> bool:
    # Require SHAP confirmation — has_discount_history=1 alone means the subscriber
    # received a discount at some point, not that price is driving their churn risk.
    price_float = _number(row, "price_float")
    return (
        _has_positive_top1(row, _PRICE_SHAP_FEATURES)
        or (price_float is not None and price_float >= 99.0)
    )


def _is_life_change(row: dict | pd.Series) -> bool:
    tenure_days = _number(row, "tenure_days")
    return (
        tenure_days is not None
        and tenure_days >= 365
        and _feature(row, "shap_top1_feature") in _LIFE_CHANGE_SHAP_FEATURES
    )


def _has_positive_top1(row: dict | pd.Series, features: frozenset[str]) -> bool:
    shap_value = _number(row, "shap_top1_value")
    return (
        _feature(row, "shap_top1_feature") in features
        and shap_value is not None
        and shap_value > 0
    )


def _feature(row: dict | pd.Series, name: str) -> str:
    value = _value(row, name)
    return "" if _is_missing(value) else str(value)


def _flag(row: dict | pd.Series, name: str) -> bool:
    value = _value(row, name)
    return False if _is_missing(value) else bool(value)


def _number(row: dict | pd.Series, name: str) -> float | None:
    value = _value(row, name)
    if _is_missing(value):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(numeric) else numeric


def _value(row: dict | pd.Series, name: str):
    return row.get(name)


def _is_missing(value) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False
