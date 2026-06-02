"""Tests for eval/metrics.py — all offline, no Snowflake."""

import numpy as np
import pytest

from bellwether.eval.metrics import (
    brier_score,
    expected_calibration_error,
    pr_auc,
    pr_auc_subgroup_gap,
    shannon_entropy,
    shap_quiz_share,
)

QUIZ_FEATURES = {"primary_goal", "stress_flag", "stimulant_sensitivity",
                 "efficacy_concern", "overstock_flag", "price_sensitive",
                 "multi_formula", "no_quiz_proxy"}


# ---------------------------------------------------------------------------
# brier_score
# ---------------------------------------------------------------------------

def test_brier_perfect_predictions():
    y = np.array([1.0, 0.0, 1.0, 0.0])
    assert brier_score(y, y) == pytest.approx(0.0)


def test_brier_worst_predictions():
    y = np.array([1.0, 0.0])
    p = np.array([0.0, 1.0])
    assert brier_score(y, p) == pytest.approx(1.0)


def test_brier_calibrated_within_threshold(binary_labels, calibrated_probs):
    score = brier_score(binary_labels, calibrated_probs)
    assert score <= 0.12, f"Brier {score:.4f} exceeds threshold 0.12"


# ---------------------------------------------------------------------------
# expected_calibration_error
# ---------------------------------------------------------------------------

def test_ece_perfect_calibration():
    # Each bin: predicted == observed fraction
    y = np.array([0.0, 0.0, 1.0, 1.0])
    p = np.array([0.1, 0.2, 0.8, 0.9])
    ece = expected_calibration_error(y, p, n_bins=2)
    assert ece < 0.15


def test_ece_calibrated_within_threshold(binary_labels, calibrated_probs):
    ece = expected_calibration_error(binary_labels, calibrated_probs)
    assert ece <= 0.05, f"ECE {ece:.4f} exceeds threshold 0.05"


# ---------------------------------------------------------------------------
# pr_auc
# ---------------------------------------------------------------------------

def test_pr_auc_perfect():
    y = np.array([1, 1, 0, 0], dtype=float)
    p = np.array([0.9, 0.8, 0.2, 0.1])
    assert pr_auc(y, p) == pytest.approx(1.0)


def test_pr_auc_above_floor(binary_labels, calibrated_probs):
    auc = pr_auc(binary_labels, calibrated_probs)
    assert auc >= 0.40, f"PR-AUC {auc:.4f} below floor 0.40"


# ---------------------------------------------------------------------------
# shannon_entropy
# ---------------------------------------------------------------------------

def test_entropy_uniform():
    counts = {"a": 25, "b": 25, "c": 25, "d": 25}
    ent = shannon_entropy(counts)
    assert ent == pytest.approx(np.log(4), rel=1e-5)


def test_entropy_degenerate():
    assert shannon_entropy({"a": 100, "b": 0}) == pytest.approx(-np.log(1.0), abs=1e-9)


def test_entropy_meets_threshold():
    # Simulate a plausible archetype distribution
    counts = {"price": 300, "efficacy": 150, "fatigue": 200, "life_change": 100,
              "stimulant": 50, "involuntary": 80}
    ent = shannon_entropy(counts)
    assert ent >= 1.0, f"Entropy {ent:.4f} below floor 1.0 nats"


def test_entropy_empty():
    assert shannon_entropy({}) == 0.0


# ---------------------------------------------------------------------------
# pr_auc_subgroup_gap
# ---------------------------------------------------------------------------

def test_subgroup_gap_within_threshold(binary_labels, calibrated_probs, quiz_present_mask):
    auc_present, auc_absent, gap = pr_auc_subgroup_gap(
        binary_labels, calibrated_probs, quiz_present_mask
    )
    assert not np.isnan(gap), "Gap is NaN — subgroup too small or no positives"
    assert gap <= 0.08, (
        f"Quiz dependency gap {gap:.4f} exceeds threshold 0.08; "
        f"model degrades too much without quiz data (present={auc_present:.3f}, absent={auc_absent:.3f})"
    )


def test_subgroup_gap_all_present(binary_labels, calibrated_probs):
    mask = np.ones(len(binary_labels), dtype=bool)
    _, auc_absent, gap = pr_auc_subgroup_gap(binary_labels, calibrated_probs, mask)
    assert np.isnan(auc_absent)
    assert np.isnan(gap)


# ---------------------------------------------------------------------------
# shap_quiz_share
# ---------------------------------------------------------------------------

def _make_shap(n_rows: int, feature_names: list[str], quiz_weight: float) -> np.ndarray:
    """Synthetic SHAP matrix where quiz features contribute ``quiz_weight`` of total."""
    rng = np.random.default_rng(0)
    n_features = len(feature_names)
    quiz_idx = [i for i, n in enumerate(feature_names) if n in QUIZ_FEATURES]
    non_quiz_idx = [i for i in range(n_features) if i not in quiz_idx]

    values = np.abs(rng.normal(size=(n_rows, n_features)))
    total_per_col = values.mean(axis=0)

    # Scale so quiz columns contribute exactly quiz_weight of the total mean |SHAP|
    quiz_total = total_per_col[quiz_idx].sum()
    non_quiz_total = total_per_col[non_quiz_idx].sum()
    if quiz_total > 0 and non_quiz_total > 0:
        desired_non_quiz = quiz_total * (1 - quiz_weight) / quiz_weight
        values[:, non_quiz_idx] *= desired_non_quiz / non_quiz_total

    return values


def test_shap_quiz_share_within_threshold():
    feature_names = list(QUIZ_FEATURES) + ["tenure_days", "billing_cycle", "aov", "ticket_count"]
    shap_vals = _make_shap(200, feature_names, quiz_weight=0.25)
    share = shap_quiz_share(shap_vals, feature_names, QUIZ_FEATURES)
    assert share <= 0.30, f"Quiz SHAP share {share:.3f} exceeds threshold 0.30"


def test_shap_quiz_share_over_threshold_detected():
    feature_names = list(QUIZ_FEATURES) + ["tenure_days", "billing_cycle"]
    shap_vals = _make_shap(200, feature_names, quiz_weight=0.60)
    share = shap_quiz_share(shap_vals, feature_names, QUIZ_FEATURES)
    assert share > 0.30, "Expected over-reliance to be detected"


def test_shap_quiz_share_no_quiz_features():
    feature_names = ["tenure_days", "billing_cycle", "aov"]
    shap_vals = np.abs(np.random.default_rng(0).normal(size=(100, 3)))
    share = shap_quiz_share(shap_vals, feature_names, QUIZ_FEATURES)
    assert share == pytest.approx(0.0)
