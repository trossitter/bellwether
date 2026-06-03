"""Train a calibrated LightGBM churn model over multiple Thesis observation windows.

Training strategy
-----------------
We stack labeled cohorts from four historical observation dates (see
``labels.observation.training_observation_dates``), each with a 30-day
horizon. All features are computed at the observation date so no future
data leaks into training. The temporal ordering is preserved: later
observation windows are held out as the validation fold rather than using
random k-fold, which would introduce leakage.

Calibration
-----------
LightGBM outputs are calibrated via IsotonicRegression so that a predicted
probability of 0.7 reflects ~70% observed churn. Calibrated probabilities
are required for the archetype routing stage, which uses probability
thresholds — not rankings — to determine intervention urgency.
"""

from __future__ import annotations

import pickle
import uuid
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import shap
from lightgbm import LGBMClassifier
from sklearn.isotonic import IsotonicRegression

from bellwether.eval.metrics import (
    brier_score, expected_calibration_error, pr_auc,
    pr_auc_subgroup_gap, shap_quiz_share,
)
from bellwether.eval.persist import ensure_table, record_metric
from bellwether.labels.observation import build_labels, training_observation_dates
from bellwether.score._features import assemble

HORIZON_DAYS = 30
BRAND_FILTER = "thesis"
MODEL_DIR = Path(__file__).parents[4] / "models"

# Feature columns passed to the model (quiz features are nullable — LightGBM
# handles NaN natively; no imputation).
FEATURE_COLS: list[str] = [
    # subscription
    "price_float", "quantity", "order_interval_frequency",
    "charge_interval_frequency", "tenure_days", "next_charge_days",
    # orders
    "order_count", "aov", "total_revenue", "total_discounts",
    "days_since_last_order", "order_cadence_days", "distinct_products",
    "has_discount_history",
    # support
    "ticket_count", "days_since_last_ticket", "has_adverse_event",
    "has_escalation", "avg_resolution_hours",
    "has_support_cancel_reason", "support_cancel_reason_count",
    # klaviyo
    "email_received_count", "email_open_count", "email_click_count",
    "sms_received_count", "email_open_rate", "email_click_rate",
    "days_since_last_email_open", "is_suppressed",
    # quiz (nullable — NaN = no assessment data)
    "has_clarity", "has_creativity", "has_energy", "has_logic",
    "has_motivation", "has_confidence", "is_caffeine_free",
    "formula_count", "multi_formula", "no_quiz_proxy",
]

QUIZ_FEATURE_COLS: list[str] = [
    "has_clarity", "has_creativity", "has_energy", "has_logic",
    "has_motivation", "has_confidence", "is_caffeine_free",
    "formula_count", "multi_formula", "no_quiz_proxy",
]


def train(horizon_days: int = HORIZON_DAYS) -> Path:
    """Assemble training data, fit a calibrated model, persist to disk.

    Returns the path to the saved model artifact.
    """
    MODEL_DIR.mkdir(exist_ok=True)

    obs_dates = training_observation_dates(horizon_days)
    train_dates, val_date = obs_dates[:-1], obs_dates[-1]

    print(f"Training windows: {[str(d) for d in train_dates]}")
    print(f"Validation window: {val_date}")

    train_frames = [_load_window(d, horizon_days) for d in train_dates]
    train_df = pd.concat(train_frames, ignore_index=True)
    val_df = _load_window(val_date, horizon_days)

    X_train, y_train = _split(train_df)
    X_val, y_val = _split(val_df)

    print(f"Train: {len(X_train):,} rows | churn rate {y_train.mean()*100:.1f}%")
    print(f"Val:   {len(X_val):,} rows | churn rate {y_val.mean()*100:.1f}%")

    lgbm = LGBMClassifier(
        n_estimators=500,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=50,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    lgbm.fit(X_train, y_train)

    # Isotonic calibration on the held-out validation fold so probabilities
    # reflect observed rates rather than raw model scores.
    val_raw = lgbm.predict_proba(X_val)[:, 1]
    isotonic = IsotonicRegression(out_of_bounds="clip")
    isotonic.fit(val_raw, y_val)

    # ── Evaluation metrics written to BELLWETHER_EVAL_RUNS ──────────────────
    run_id = str(uuid.uuid4())
    val_cal = isotonic.predict(val_raw)
    quiz_mask = val_df["no_quiz_proxy"].fillna(True).astype(bool)

    explainer   = shap.TreeExplainer(lgbm)
    shap_values = explainer.shap_values(X_val)
    shap_matrix = shap_values[1] if isinstance(shap_values, list) else shap_values

    ensure_table()

    metrics = [
        ("pr_auc",             pr_auc(y_val.values, val_cal),                             0.40),
        ("brier_score",        brier_score(y_val.values, val_cal),                        0.12),
        ("ece",                expected_calibration_error(y_val.values, val_cal),         0.05),
        ("shap_quiz_share",    shap_quiz_share(shap_matrix, FEATURE_COLS, set(QUIZ_FEATURE_COLS)), 0.30),
    ]
    _, _, gap = pr_auc_subgroup_gap(y_val.values, val_cal, (~quiz_mask).values)
    metrics.append(("pr_auc_subgroup_gap", gap if not np.isnan(gap) else 0.0, 0.08))

    git_sha = _git_sha()
    for name, value, threshold in metrics:
        record_metric(run_id, "score", "offline", name, value,
                      threshold=threshold, n_subscribers=len(X_val),
                      model_version=run_id[:8],
                      notes=f"git={git_sha}" if git_sha else None)
        status = "PASS" if (value <= threshold if name in {"brier_score","ece","shap_quiz_share","pr_auc_subgroup_gap"} else value >= threshold) else "FAIL"
        print(f"  {name:<28} {value:.4f}  [{status}]")

    artifact = MODEL_DIR / f"bellwether_h{horizon_days}.pkl"
    with open(artifact, "wb") as f:
        pickle.dump({"lgbm": lgbm, "isotonic": isotonic,
                     "feature_cols": FEATURE_COLS,
                     "quiz_feature_cols": QUIZ_FEATURE_COLS,
                     "horizon_days": horizon_days, "val_date": str(val_date),
                     "run_id": run_id}, f)

    print(f"Model saved: {artifact}  (run_id={run_id[:8]})")
    return artifact


def _git_sha() -> str | None:
    import subprocess
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=5).stdout.strip() or None
    except Exception:
        return None


def _load_window(obs_date: date, horizon_days: int) -> pd.DataFrame:
    labels = build_labels(obs_date, horizon_days)
    labels = labels[labels["brand"] == BRAND_FILTER].copy()
    features = assemble(obs_date)
    merged = labels[["subscription_id", "label"]].merge(
        features, on="subscription_id", how="left"
    )
    return merged


def _split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    X = df[FEATURE_COLS].copy()
    # Coerce all columns to float — quiz None values become NaN (LightGBM handles
    # NaN natively), object-typed numerics are cast, bools become 1.0/0.0.
    X = X.apply(pd.to_numeric, errors="coerce")
    y = df["label"].astype(int)
    return X, y
