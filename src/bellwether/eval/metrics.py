"""Shared metric implementations for all pipeline stages."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import average_precision_score


def brier_score(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Mean squared error between predicted probabilities and binary outcomes."""
    return float(np.mean((y_prob - y_true) ** 2))


def expected_calibration_error(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> float:
    """Weighted mean absolute deviation between predicted and observed fractions (ECE)."""
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    for lo, hi in zip(bin_edges[:-1], bin_edges[1:]):
        mask = (y_prob >= lo) & (y_prob < hi)
        count = mask.sum()
        if count == 0:
            continue
        accuracy = y_true[mask].mean()
        confidence = y_prob[mask].mean()
        ece += (count / n) * abs(accuracy - confidence)
    return float(ece)


def pr_auc(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Area under the precision-recall curve."""
    return float(average_precision_score(y_true, y_prob))


def shannon_entropy(counts: dict[str, int]) -> float:
    """Shannon entropy (nats) of a label-count distribution."""
    total = sum(counts.values())
    if total == 0:
        return 0.0
    probs = np.array([c / total for c in counts.values() if c > 0])
    return float(-np.sum(probs * np.log(probs)))


def pr_auc_subgroup_gap(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    quiz_present_mask: np.ndarray,
) -> tuple[float, float, float]:
    """PR-AUC on quiz-present and quiz-absent subgroups.

    Returns (auc_present, auc_absent, gap). Gap is the absolute difference;
    a gap > 0.08 means the model degrades unacceptably without quiz data.
    """
    present = quiz_present_mask.astype(bool)
    absent = ~present

    def _safe_auc(mask: np.ndarray) -> float:
        if mask.sum() < 2 or y_true[mask].sum() == 0:
            return float("nan")
        return pr_auc(y_true[mask], y_prob[mask])

    auc_present = _safe_auc(present)
    auc_absent = _safe_auc(absent)

    if np.isnan(auc_present) or np.isnan(auc_absent):
        gap = float("nan")
    else:
        gap = abs(auc_present - auc_absent)

    return auc_present, auc_absent, gap


def shap_quiz_share(
    shap_values: np.ndarray,
    feature_names: list[str],
    quiz_feature_names: set[str],
) -> float:
    """Fraction of mean |SHAP| attributable to quiz features collectively.

    A value > 0.30 signals the model is over-reliant on quiz data and would
    degrade badly for subscribers without THESIS_FORMULAS history.
    """
    mean_abs = np.abs(shap_values).mean(axis=0)
    total = mean_abs.sum()
    if total == 0.0:
        return 0.0
    quiz_indices = [i for i, name in enumerate(feature_names) if name in quiz_feature_names]
    quiz_total = mean_abs[quiz_indices].sum() if quiz_indices else 0.0
    return float(quiz_total / total)
