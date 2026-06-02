"""Load a trained model and score the active Thesis subscriber cohort.

Returns calibrated P(churn in H days) and SHAP top-3 factors per subscriber.
SHAP explanations feed directly into the archetype classifier downstream.
"""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import shap

from bellwether.labels.observation import SNAPSHOT_DATE, scoring_cohort
from bellwether.score._features import assemble
from bellwether.score.train import BRAND_FILTER, FEATURE_COLS, MODEL_DIR, QUIZ_FEATURE_COLS
from bellwether.eval.metrics import (
    brier_score, expected_calibration_error, pr_auc,
    pr_auc_subgroup_gap, shap_quiz_share,
)


def predict(
    artifact: Path | None = None,
    horizon_days: int = 30,
) -> pd.DataFrame:
    """Score the active Thesis scoring cohort with the trained model.

    Returns one row per subscriber with columns:
        subscription_id, customer_id, brand, churn_prob_30d,
        shap_top1_feature, shap_top1_value,
        shap_top2_feature, shap_top2_value,
        shap_top3_feature, shap_top3_value,
        no_quiz_proxy
    """
    artifact = artifact or MODEL_DIR / f"bellwether_h{horizon_days}.pkl"
    with open(artifact, "rb") as f:
        bundle = pickle.load(f)

    lgbm = bundle["lgbm"]
    isotonic = bundle["isotonic"]
    feature_cols = bundle["feature_cols"]

    cohort = scoring_cohort()
    cohort = cohort[cohort["brand"] == BRAND_FILTER].copy()
    features = assemble(SNAPSHOT_DATE)
    df = cohort[["subscription_id"]].merge(
        features, on="subscription_id", how="left"
    )

    X = df[feature_cols].apply(pd.to_numeric, errors="coerce")

    raw_probs = lgbm.predict_proba(X)[:, 1]
    df["churn_prob_30d"] = isotonic.predict(raw_probs)

    explainer = shap.TreeExplainer(lgbm)
    shap_values = explainer.shap_values(X)
    # For binary classification lgbm returns list [neg, pos]; take pos class
    if isinstance(shap_values, list):
        shap_matrix = shap_values[1]
    else:
        shap_matrix = shap_values

    _attach_shap_top3(df, shap_matrix, feature_cols)
    _log_eval_metrics(df, shap_matrix, feature_cols)

    return df[[
        "subscription_id", "customer_id", "brand", "churn_prob_30d",
        "no_quiz_proxy",
        "shap_top1_feature", "shap_top1_value",
        "shap_top2_feature", "shap_top2_value",
        "shap_top3_feature", "shap_top3_value",
    ]]


def _attach_shap_top3(df: pd.DataFrame, shap_matrix: np.ndarray,
                      feature_cols: list[str]) -> None:
    abs_shap = np.abs(shap_matrix)
    top3_idx = np.argsort(abs_shap, axis=1)[:, -3:][:, ::-1]
    for rank in range(3):
        col = rank + 1
        df[f"shap_top{col}_feature"] = [feature_cols[i] for i in top3_idx[:, rank]]
        df[f"shap_top{col}_value"] = shap_matrix[
            np.arange(len(df)), top3_idx[:, rank]
        ]


def _log_eval_metrics(df: pd.DataFrame, shap_matrix: np.ndarray,
                      feature_cols: list[str]) -> None:
    """Log scoring-time diagnostics. Subgroup gap requires labels; deferred to train eval."""
    quiz_mask = ~df["no_quiz_proxy"].infer_objects().fillna(True).astype(bool)
    quiz_share = shap_quiz_share(shap_matrix, feature_cols, set(QUIZ_FEATURE_COLS))

    print(f"SHAP quiz share:      {quiz_share:.1%}  (threshold ≤ 30%)")
    print(f"Active cohort:        {len(df):,} Thesis subscribers")
    print(f"  quiz_present:       {quiz_mask.sum():,} ({quiz_mask.mean():.1%})")
    print(f"  quiz_absent:        {(~quiz_mask).sum():,} ({(~quiz_mask).mean():.1%})")
    print(f"Median churn prob:    {df.churn_prob_30d.median():.3f}")
    print(f"P90 churn prob:       {df.churn_prob_30d.quantile(0.9):.3f}")
