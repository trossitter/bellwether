"""Evaluation infrastructure — metrics, contracts, judge, persistence, reporting."""

from bellwether.eval.contracts import (
    ContractResult,
    ContractSuite,
    InterventionProposal,
)
from bellwether.eval.metrics import (
    brier_score,
    expected_calibration_error,
    pr_auc,
    pr_auc_subgroup_gap,
    shannon_entropy,
    shap_quiz_share,
)

__all__ = [
    "brier_score",
    "expected_calibration_error",
    "pr_auc",
    "pr_auc_subgroup_gap",
    "shannon_entropy",
    "shap_quiz_share",
    "ContractResult",
    "ContractSuite",
    "InterventionProposal",
]
