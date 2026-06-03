"""Export real at-risk subscriber profiles for the Bellwether presentation page.

Runs the full pipeline, takes the top N subscribers by churn probability,
drafts a real intervention for each, and saves everything to docs/bellwether_data.json.

Usage:
    python3 docs/export_sample_subscribers.py

The JSON output is designed to be loaded directly by bellwether.html in Claude Design.
"""

import json
import re
import uuid
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from bellwether.classify.archetypes import Archetype, classify_batch
from bellwether.intervene.agent import intervene
from bellwether.labels.observation import SNAPSHOT_DATE, scoring_cohort
from bellwether.score._features import assemble
from bellwether.score.predict import predict

TOP_PER_ARCH = 2    # top N per archetype — ensures variety across card types
HORIZON = 30
SNAPSHOT = SNAPSHOT_DATE   # 2026-04-21
SUB_VALUE = 79.0

ARCHETYPE_DISPLAY = {
    "price":       "Price Sensitivity",
    "efficacy":    "Expectation Gap",
    "fatigue":     "Product Overstock",
    "life_change": "Life Change",
    "involuntary": "Payment Declined",
    "stimulant":   "Stimulant Sensitivity",
}

ARCHETYPE_COLOR = {
    "price":       "blue",
    "efficacy":    "amber",
    "fatigue":     "green",
    "life_change": "violet",
    "involuntary": "rose",
    "stimulant":   "amber",
}


def run() -> None:
    print("Scoring active Thesis subscribers...")
    scored = predict(horizon_days=HORIZON)

    print("Assembling full feature frame...")
    cohort   = scoring_cohort()
    cohort   = cohort[cohort["brand"] == "thesis"][["subscription_id"]]
    features = assemble(SNAPSHOT)
    full = cohort.merge(features, on="subscription_id", how="left")
    full = full.merge(
        scored[["subscription_id", "churn_prob_30d",
                "shap_top1_feature", "shap_top1_value",
                "shap_top2_feature", "shap_top2_value",
                "shap_top3_feature", "shap_top3_value"]],
        on="subscription_id", how="left",
    )
    full["archetype"] = classify_batch(full)

    # Take top N per archetype so the presentation has variety, not just 10 × price
    frames = []
    for arch in Archetype:
        subset = full[full["archetype"] == arch]
        if not subset.empty:
            frames.append(subset.nlargest(TOP_PER_ARCH, "churn_prob_30d"))
    top = pd.concat(frames).sort_values("churn_prob_30d", ascending=False).copy()
    print(f"Top {TOP_PER_ARCH} per archetype selected ({len(top)} total).")

    records = []
    for _, row in top.iterrows():
        arch_raw = str(row.get("archetype", "")).rsplit(".", 1)[-1]
        rec = _build_record(row, arch_raw)
        if rec:
            records.append(rec)

    total_at_risk = int((full["churn_prob_30d"] >= 0.10).sum())
    output = {
        "generated_at": SNAPSHOT.isoformat(),
        "total_scored": len(full),
        "total_at_risk": total_at_risk,
        "showing": len(records),
        "subscribers": records,
    }

    out = Path(__file__).parent / "bellwether_data.json"
    with open(out, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved {len(records)} profiles → {out}")
    print(f"Total at-risk: {total_at_risk:,} of {len(full):,} active subscribers")


def _build_record(row: pd.Series, arch_raw: str) -> dict | None:
    try:
        print(f"  Drafting intervention for {arch_raw}...")
        proposal = intervene(dict(row), brand="thesis")
    except Exception as e:
        print(f"  Skipped — {e}")
        return None

    churn_prob = float(row.get("churn_prob_30d", 0))
    tenure_days = row.get("tenure_days")
    next_charge = row.get("next_charge_days")
    ltv = row.get("total_revenue")
    cadence_freq = row.get("order_interval_frequency")
    cadence_unit = row.get("order_interval_unit", "day")
    formulas_raw = row.get("thesis_formulas")

    return {
        "id":             _short_id(str(row.get("subscription_id", ""))),
        "archetype":      arch_raw,
        "archetype_label": ARCHETYPE_DISPLAY.get(arch_raw, arch_raw.replace("_", " ").title()),
        "archetype_color": ARCHETYPE_COLOR.get(arch_raw, "blue"),
        "churn_prob":     round(churn_prob * 100),
        "urgency":        proposal.urgency_level,
        "product":        _format_formulas(formulas_raw),
        "cadence":        _format_cadence(cadence_freq, cadence_unit),
        "tenure":         _format_tenure(tenure_days),
        "ltv":            _format_ltv(ltv),
        "next_renewal":   _format_renewal(next_charge),
        "action":         proposal.action.replace("_", " ").title(),
        "message":        proposal.message,
        "top_signal":     _format_signal(
            str(row.get("shap_top1_feature", "")),
            float(row.get("shap_top1_value", 0)),
        ),
    }


def _short_id(raw: str) -> str:
    return f"MBR-{raw[:6].upper()}" if len(raw) >= 6 else f"MBR-{uuid.uuid4().hex[:6].upper()}"


def _format_formulas(raw) -> str:
    if not raw or str(raw).strip() in ("", "nan", "None"):
        return "Assessment not completed"
    known = ["Clarity", "Motivation", "Energy", "Logic", "Creativity", "Confidence"]
    found = []
    for name in known:
        if re.search(name, str(raw), re.I) and name not in found:
            found.append(name)
    caff_free = bool(re.search(r"caffeine.?free|caff.?free", str(raw), re.I))
    if not found:
        return "Custom formula"
    label = " + ".join(found[:2])
    return f"{label} (Caffeine-Free)" if caff_free else label


def _format_cadence(freq, unit) -> str:
    if freq is None or (isinstance(freq, float) and freq != freq):
        return "—"
    freq = int(freq)
    unit = str(unit).lower().rstrip("s")
    if unit == "day":
        weeks = freq // 7
        return f"Every {weeks} weeks" if weeks and freq % 7 == 0 else f"Every {freq} days"
    return f"Every {freq} {unit}s"


def _format_tenure(days) -> str:
    if days is None or (isinstance(days, float) and days != days):
        return "—"
    days = int(days)
    if days < 30:
        return f"{days} days"
    months = days // 30
    years, rem = divmod(months, 12)
    if years >= 2:
        return f"{years} years" if rem == 0 else f"{years}y {rem}mo"
    if years == 1:
        return "1 year" if rem == 0 else f"1 year {rem}mo"
    return f"{months} months"


def _format_ltv(revenue) -> str:
    if revenue is None or (isinstance(revenue, float) and revenue != revenue):
        return "—"
    return f"${revenue:,.0f}"


def _format_renewal(next_charge_days) -> str:
    if next_charge_days is None or (isinstance(next_charge_days, float) and next_charge_days != next_charge_days):
        return "Overdue"
    days = int(next_charge_days)
    if days <= 0:
        return "Overdue"
    renewal_date = SNAPSHOT + timedelta(days=days)
    return renewal_date.strftime("%B %-d, %Y")


def _format_signal(feature: str, value: float) -> str:
    labels = {
        "tenure_days":            "Long subscriber, engagement shifting",
        "next_charge_days":       "Charge date is imminent",
        "price_float":            "Price is the primary churn driver",
        "order_cadence_days":     "Order cadence has slowed",
        "days_since_last_order":  "Extended gap since last order",
        "has_adverse_event":      "Reported a side effect",
        "has_support_cancel_reason": "Reached out to cancel via support",
        "has_clarity":            "Formula type is the key signal",
        "has_confidence":         "Formula type is the key signal",
        "has_motivation":         "Formula type is the key signal",
        "has_energy":             "Formula type is the key signal",
        "no_quiz_proxy":          "Assessment not on file",
    }
    return labels.get(feature, feature.replace("_", " ").capitalize())


if __name__ == "__main__":
    run()
