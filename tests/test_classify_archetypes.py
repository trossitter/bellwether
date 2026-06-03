from __future__ import annotations

import pandas as pd
import pytest

from bellwether.classify.archetypes import (
    Archetype,
    _is_efficacy,
    _is_fatigue,
    _is_involuntary,
    _is_life_change,
    _is_price,
    _is_stimulant,
    classify,
    classify_batch,
)


def _row(**overrides):
    base = {
        "subscription_id": "sub_001",
        "churn_prob_30d": 0.72,
        "no_quiz_proxy": False,
        "shap_top1_feature": "neutral",
        "shap_top1_value": 0.0,
        "shap_top2_feature": "neutral",
        "shap_top2_value": 0.0,
        "shap_top3_feature": "neutral",
        "shap_top3_value": 0.0,
        "price_float": 49.0,
        "tenure_days": 90,
        "next_charge_days": 14.0,
        "order_count": 3,
        "order_cadence_days": 30.0,
        "days_since_last_order": 10.0,
        "has_discount_history": 0,
        "has_adverse_event": 0,
        "has_support_cancel_reason": 0,
        "has_clarity": None,
        "has_energy": 0.0,
        "has_motivation": 0.0,
        "has_confidence": None,
    }
    return {**base, **overrides}


@pytest.mark.parametrize("formula_flag", [
    {"has_motivation": 1.0},
    {"has_energy": 1.0},
    {"no_quiz_proxy": True},
])
def test_stimulant_fires(formula_flag):
    row = _row(has_adverse_event=1, **formula_flag)
    assert _is_stimulant(row)
    assert classify(row) == Archetype.stimulant


def test_efficacy_via_adverse_event():
    row = _row(has_adverse_event=1)
    assert _is_efficacy(row)
    assert classify(row) == Archetype.efficacy


def test_efficacy_via_support_reason():
    row = _row(has_support_cancel_reason=1)
    assert _is_efficacy(row)
    assert classify(row) == Archetype.efficacy


@pytest.mark.parametrize("feature", [
    "has_clarity",
    "has_creativity",
    "has_logic",
    "has_confidence",
    "no_quiz_proxy",
])
def test_efficacy_via_shap(feature):
    row = _row(shap_top1_feature=feature, shap_top1_value=0.2)
    assert _is_efficacy(row)
    assert classify(row) == Archetype.efficacy


def test_involuntary():
    row = _row(next_charge_days=None, order_count=1)
    assert _is_involuntary(row)
    assert classify(row) == Archetype.involuntary


@pytest.mark.parametrize("feature", [
    "order_count",
    "order_cadence_days",
    "days_since_last_order",
    "distinct_products",
])
def test_fatigue_via_shap(feature):
    row = _row(shap_top1_feature=feature, shap_top1_value=0.2)
    assert _is_fatigue(row)
    assert classify(row) == Archetype.fatigue


def test_fatigue_via_cadence():
    row = _row(order_cadence_days=14.0)
    assert _is_fatigue(row)
    assert classify(row) == Archetype.fatigue


@pytest.mark.parametrize("feature", ["price_float", "has_discount_history"])
def test_price_via_shap(feature):
    row = _row(shap_top1_feature=feature, shap_top1_value=0.2)
    assert _is_price(row)
    assert classify(row) == Archetype.price


def test_price_via_price_float():
    row = _row(price_float=99.0)
    assert _is_price(row)
    assert classify(row) == Archetype.price


def test_price_discount_history_alone_does_not_route():
    # has_discount_history alone no longer triggers price — it caught 51% of
    # all subscribers when used as a standalone signal. SHAP confirmation required.
    row = _row(has_discount_history=1)
    assert not _is_price(row)


def test_life_change():
    row = _row(tenure_days=365, shap_top1_feature="tenure_days")
    assert _is_life_change(row)
    assert classify(row) == Archetype.life_change


def test_default():
    assert classify(_row()) == Archetype.price


def test_mutual_exclusivity_across_synthetic_rows():
    rows = []
    archetype_rows = [
        _row(has_adverse_event=1, has_energy=1.0),
        _row(has_support_cancel_reason=1),
        _row(next_charge_days=None, order_count=1),
        _row(order_cadence_days=12.0),
        _row(price_float=120.0),
        _row(tenure_days=500, shap_top1_feature="next_charge_days"),
    ]
    for i in range(100):
        rows.append({**archetype_rows[i % len(archetype_rows)], "subscription_id": f"sub_{i:03d}"})

    result = classify_batch(pd.DataFrame(rows))

    assert set(result) == set(Archetype)
    assert len(result) == 100
    assert all(isinstance(value, Archetype) for value in result)


def test_classify_batch_dtype_and_length():
    df = pd.DataFrame([
        _row(subscription_id="sub_001"),
        _row(subscription_id="sub_002", price_float=105.0),
        _row(subscription_id="sub_003", has_support_cancel_reason=1),
    ], index=["a", "b", "c"])

    result = classify_batch(df)

    assert result.dtype == object
    assert list(result.index) == ["a", "b", "c"]
    assert len(result) == len(df)
