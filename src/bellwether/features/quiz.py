"""Synthetic quiz features derived from THESIS_FORMULAS on SUBSCRIPTIONS.

THESIS_FORMULAS is a free-text comma-separated string (e.g. "Clarity, Energy,
Logic, Motivation") set when the subscriber completed the Thesis assessment.
43.9% of all subscriptions have NULL — that population is first-class via
no_quiz_proxy=True, not imputed away.

The raw strings are dirty: tabs, \\r\\n, typos (Calrity, Ceativity), and
~15 spellings of "Caffeine-Free". Parsing normalises aggressively in Python
after a single SQL fetch; no Snowflake UDFs.

Keyed on subscription_id (not customer_id) to match the label builder.
"""

from __future__ import annotations

import re
from datetime import date

import pandas as pd

from bellwether.features.guard import PointInTimeGuard

# ---------------------------------------------------------------------------
# Known formula canonical names and their typo/alias patterns.
# Order matters: longer/more-specific patterns first.
# ---------------------------------------------------------------------------

_FORMULA_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("confidence",  re.compile(r"confiden", re.I)),
    ("creativity",  re.compile(r"creativ|eativi", re.I)),   # "eativi" catches "Ceativity" typo
    ("clarity",     re.compile(r"clarit|calrit|clairt", re.I)),  # covers Calrity/Clairty typos
    ("motivation",  re.compile(r"motivat", re.I)),
    ("energy",      re.compile(r"energy", re.I)),
    ("logic",       re.compile(r"logic", re.I)),
]

QUIZ_FEATURE_NAMES: frozenset[str] = frozenset({
    "has_clarity", "has_creativity", "has_energy",
    "has_logic", "has_motivation", "has_confidence",
    "is_caffeine_free", "formula_count", "multi_formula", "no_quiz_proxy",
})

# "caff" is distinctive enough to catch all variants: Caffeine-Free, CaffFree,
# Caff-Free, Caffine-Free, caffeine free, etc.
_CAFFEINE_RE = re.compile(r"caff", re.I)


def build(observation_date: date) -> pd.DataFrame:
    """Return one row per subscription with quiz-derived feature columns.

    Columns: subscription_id, customer_id, has_clarity, has_creativity,
    has_energy, has_logic, has_motivation, has_confidence,
    is_caffeine_free, formula_count, multi_formula, no_quiz_proxy.

    Subscriptions without THESIS_FORMULAS get NaN for all has_* columns and
    no_quiz_proxy=True, so LightGBM can learn the absence pattern natively.
    """
    guard = PointInTimeGuard(observation_date)
    raw = guard.read(f"""
        SELECT
            SUBSCRIPTION_ID_HASH      AS subscription_id,
            RECHARGE_CUSTOMER_ID_HASH AS customer_id,
            THESIS_FORMULAS           AS thesis_formulas
        FROM GAUNTLET_SANDBOX.SOURCE.SUBSCRIPTIONS
        WHERE CREATED_AT < '{guard.date_str}'::DATE
    """)

    parsed = raw["thesis_formulas"].map(_parse_formula_string)
    flags = pd.DataFrame(parsed.tolist(), index=raw.index)
    return pd.concat([raw[["subscription_id", "customer_id"]], flags], axis=1)


def _parse_formula_string(raw: str | None) -> dict:
    """Parse one THESIS_FORMULAS value into a flat feature dict."""
    if not raw or not isinstance(raw, str) or not raw.strip():
        return _absent()

    # Normalise whitespace and control characters
    cleaned = re.sub(r"[\r\n\t]+", " ", raw)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

    is_caffeine_free = bool(_CAFFEINE_RE.search(cleaned))

    found: set[str] = set()
    for name, pattern in _FORMULA_PATTERNS:
        if pattern.search(cleaned):
            found.add(name)

    if not found:
        # Non-null but unparseable — treat as absent to avoid silent noise
        return _absent()

    return {
        "has_clarity":      "clarity"     in found,
        "has_creativity":   "creativity"  in found,
        "has_energy":       "energy"      in found,
        "has_logic":        "logic"       in found,
        "has_motivation":   "motivation"  in found,
        "has_confidence":   "confidence"  in found,
        "is_caffeine_free": is_caffeine_free,
        "formula_count":    len(found),
        "multi_formula":    len(found) > 1,
        "no_quiz_proxy":    False,
    }


def _absent() -> dict:
    return {
        "has_clarity":      None,
        "has_creativity":   None,
        "has_energy":       None,
        "has_logic":        None,
        "has_motivation":   None,
        "has_confidence":   None,
        "is_caffeine_free": None,
        "formula_count":    None,
        "multi_formula":    None,
        "no_quiz_proxy":    True,
    }
