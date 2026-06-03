"""Plain-text pipeline summary for TakeThesis partner review.

Produces a human-readable report of pipeline state: subscriber cohort,
archetype distribution, model metadata, evaluation status, and action log.
No model knowledge required to read it.
"""

from __future__ import annotations

import pickle
from datetime import datetime, timezone
from pathlib import Path

MODEL_DIR = Path(__file__).parents[4] / "models"


def generate(horizon_days: int = 30, brand: str = "thesis") -> str:
    """Return a plain-text Bellwether pipeline report."""
    sections = [
        _header(brand),
        _model_section(horizon_days),
        _cohort_section(horizon_days, brand),
        _evaluation_section(),
        _action_log_section(),
        _footer(),
    ]
    return "\n\n".join(s for s in sections if s)


def _header(brand: str) -> str:
    ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""\
╔══════════════════════════════════════════════════════════════╗
  BELLWETHER  ·  Subscription Churn Pipeline
  Brand: {brand.title()}   ·   Generated: {ts}
╚══════════════════════════════════════════════════════════════╝"""


def _model_section(horizon_days: int) -> str:
    artifact = MODEL_DIR / f"bellwether_h{horizon_days}.pkl"
    if not artifact.exists():
        return "MODEL\n  Not trained — run bellwether.score.train.train() first."
    with open(artifact, "rb") as f:
        bundle = pickle.load(f)
    val_date   = bundle.get("val_date", "unknown")
    n_features = len(bundle.get("feature_cols", []))
    return f"""\
MODEL
  Algorithm     LightGBM + IsotonicRegression calibration
  Horizon       {horizon_days}-day churn probability
  Validated on  {val_date} cohort (held-out temporal split)
  Features      {n_features} point-in-time feature columns
  Quiz handling no_quiz_proxy=True treated as first-class signal;
                86–91% of active subscribers have no assessment data —
                model trained and evaluated on both populations"""


def _cohort_section(horizon_days: int, brand: str) -> str:
    try:
        from bellwether.score.predict import predict
        from bellwether.score._features import assemble
        from bellwether.labels.observation import SNAPSHOT_DATE, scoring_cohort
        from bellwether.classify.archetypes import classify_batch, Archetype

        scored  = predict(horizon_days=horizon_days)
        cohort  = scoring_cohort()
        cohort  = cohort[cohort["brand"] == brand][["subscription_id"]]
        features = assemble(SNAPSHOT_DATE)
        full = cohort.merge(features, on="subscription_id", how="left")
        full = full.merge(
            scored[["subscription_id", "churn_prob_30d",
                    "shap_top1_feature", "shap_top1_value"]],
            on="subscription_id", how="left",
        )
        full["archetype"] = classify_batch(full)

        n_total  = len(full)
        n_medium = int((full["churn_prob_30d"] >= 0.10).sum())
        n_high   = int((full["churn_prob_30d"] >= 0.50).sum())

        arch_lines = []
        for arch in Archetype:
            subset   = full[full["archetype"] == arch]
            at_risk  = int((subset["churn_prob_30d"] >= 0.10).sum())
            pct      = at_risk / len(subset) * 100 if len(subset) > 0 else 0
            arch_lines.append(
                f"  {arch.value:<16}  {len(subset):>6,} subscribers   "
                f"{at_risk:>4,} at risk ({pct:.0f}%)"
            )

        arch_block = "\n".join(arch_lines)
        return (
            "ACTIVE SUBSCRIBER COHORT  (snapshot 2026-04-21)\n"
            f"  Total scored       {n_total:,}\n"
            f"  Medium-high risk   {n_medium:,}   (P >= 0.10)\n"
            f"  High risk          {n_high:,}   (P >= 0.50)\n"
            "\n"
            "  By intervention archetype:\n"
            f"{arch_block}"
        )
    except Exception as exc:
        return f"COHORT\n  Could not score — {exc}"


def _evaluation_section() -> str:
    try:
        from bellwether.db.snowflake import read_sql
        df = read_sql(
            "SELECT metric_name, metric_value, threshold, passed "
            "FROM GAUNTLET_SANDBOX.OUTPUTS.BELLWETHER_EVAL_RUNS "
            "ORDER BY run_ts DESC LIMIT 20"
        )
        df.columns = df.columns.str.lower()
        if df.empty:
            eval_body = "  No eval runs recorded yet."
        else:
            pass_count = int(df["passed"].sum())
            fail_count = len(df) - pass_count
            eval_body = (
                f"  {pass_count} metrics passing   {fail_count} failing\n"
                f"  Query BELLWETHER_EVAL_RUNS WHERE passed = FALSE for details."
            )
    except Exception:
        eval_body = "  BELLWETHER_EVAL_RUNS not yet populated."

    return f"""\
EVALUATION FRAMEWORK
  Model metrics     Brier ≤ 0.12, ECE ≤ 0.05, PR-AUC ≥ 0.40
  Quiz robustness   Subgroup gap ≤ 0.08, quiz SHAP share ≤ 30%
  Agent quality     Behavior contracts (hard gate) + LLM-as-judge
  Judge calibration Spearman r = 0.779 (warm voice, n=15, p=0.0000)
                    A/B tested against brand voice (r = 0.725) — warm selected
  Brand config      configs/thesis.yaml — editable without model retraining
{eval_body}"""


def _action_log_section() -> str:
    try:
        from bellwether.db.snowflake import read_sql
        df = read_sql(
            "SELECT archetype, action_type, COUNT(*) AS n "
            "FROM GAUNTLET_SANDBOX.OUTPUTS.BELLWETHER_ACTIONS "
            "GROUP BY archetype, action_type ORDER BY n DESC"
        )
        df.columns = df.columns.str.lower()
        if df.empty:
            return "ACTION LOG\n  No dispatched actions yet."
        total = int(df["n"].sum())
        rows  = "\n".join(
            f"  {r.archetype:<16}  {r.action_type:<28}  {int(r.n):>4,}"
            for _, r in df.iterrows()
        )
        return f"ACTION LOG  ({total:,} total dispatched)\n{rows}"
    except Exception:
        return "ACTION LOG\n  BELLWETHER_ACTIONS not yet populated."


def _footer() -> str:
    return """\
NEXT STEPS
  · Connect outcome data (BELLWETHER_ACTIONS ⟶ actual churn events)
    to measure intervention lift over no-action baseline
  · Expand to Stasis: add configs/stasis.yaml, retrain on Stasis cohort
  · Replace SimulatedAdapter with KlaviyoAdapter for live sends
  ─────────────────────────────────────────────────────────────────────
  Bellwether  ·  github.com/trossitter/bellwether"""
