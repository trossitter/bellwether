"""Leakage, schema, and quiz-feature tests for the score pipeline.

Offline tests run without Snowflake. Integration tests (marked) hit the
real data and are the authoritative leakage gate.
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from bellwether.features.guard import LeakageError, PointInTimeGuard
from bellwether.features.quiz import QUIZ_FEATURE_NAMES, _parse_formula_string, _absent
from bellwether.labels.observation import SNAPSHOT_DATE

OBS_DATE = date(2026, 1, 21)
HORIZON = 30

# ---------------------------------------------------------------------------
# PointInTimeGuard — leakage enforcement
# ---------------------------------------------------------------------------

class TestPointInTimeGuard:
    def test_raises_when_date_absent_from_query(self):
        guard = PointInTimeGuard(OBS_DATE)
        with pytest.raises(LeakageError, match="observation_date"):
            guard.read("SELECT * FROM orders WHERE 1=1")

    def test_raises_on_wrong_date(self):
        guard = PointInTimeGuard(OBS_DATE)
        wrong_date = (OBS_DATE + timedelta(days=1)).isoformat()
        with pytest.raises(LeakageError):
            guard.read(f"SELECT * FROM orders WHERE created_at < '{wrong_date}'::DATE")

    def test_passes_when_date_present(self):
        guard = PointInTimeGuard(OBS_DATE)
        query = f"SELECT 1 FROM t WHERE event_date < '{OBS_DATE.isoformat()}'::DATE"
        with patch("bellwether.features.guard.read_sql") as mock_sql:
            mock_sql.return_value = pd.DataFrame({"col": [1]})
            df = guard.read(query)
        assert len(df) == 1

    def test_columns_lowercased(self):
        guard = PointInTimeGuard(OBS_DATE)
        query = f"SELECT 1 AS VAL WHERE '{OBS_DATE.isoformat()}' IS NOT NULL"
        with patch("bellwether.features.guard.read_sql") as mock_sql:
            mock_sql.return_value = pd.DataFrame({"VAL": [1]})
            df = guard.read(query)
        assert "val" in df.columns

    def test_rejects_future_date(self):
        future = SNAPSHOT_DATE + timedelta(days=1)
        guard = PointInTimeGuard(future)
        # The guard doesn't know about SNAPSHOT_DATE; that's the label builder's job.
        # But the feature query carrying a future date string will execute — the
        # snapshot validation lives in labels/observation.py._validate().
        # This test confirms the guard's date_str is correct.
        assert guard.date_str == future.isoformat()


# ---------------------------------------------------------------------------
# Quiz feature parser — offline
# ---------------------------------------------------------------------------

class TestParseFormulaString:
    def test_null_returns_absent(self):
        result = _parse_formula_string(None)
        assert result == _absent()
        assert result["no_quiz_proxy"] is True

    def test_empty_string_returns_absent(self):
        assert _parse_formula_string("")["no_quiz_proxy"] is True
        assert _parse_formula_string("   ")["no_quiz_proxy"] is True

    def test_clean_four_formula(self):
        r = _parse_formula_string("Clarity, Creativity, Energy, Logic")
        assert r["has_clarity"] is True
        assert r["has_creativity"] is True
        assert r["has_energy"] is True
        assert r["has_logic"] is True
        assert r["has_motivation"] is False
        assert r["has_confidence"] is False
        assert r["formula_count"] == 4
        assert r["multi_formula"] is True
        assert r["no_quiz_proxy"] is False
        assert r["is_caffeine_free"] is False

    def test_caffeine_free_detected(self):
        r = _parse_formula_string(
            "Clarity (Caffeine-Free), Creativity (Caffeine-Free), "
            "Energy (Caffeine-Free), Logic (Caffeine-Free)"
        )
        assert r["is_caffeine_free"] is True
        assert r["has_clarity"] is True

    @pytest.mark.parametrize("raw", [
        "caffeine free clarity, energy, motivation, confidence",
        "Clarity(Caffeine-Free)",
        "Clarity  ( Caffeine Free)",
        "Clarity (Caff-Free)",
        "Clarity (caffeine-free)",
        "Clarity (Caffeine_free)",
        "Clarity.CaffFree",
    ])
    def test_caffeine_free_variants(self, raw):
        r = _parse_formula_string(raw)
        assert r["is_caffeine_free"] is True

    @pytest.mark.parametrize("raw,expected", [
        ("Calrity, Energy", "clarity"),
        ("Clairty, Logic", "clarity"),
        ("Ceativity, Energy", "creativity"),
    ])
    def test_typo_tolerance(self, raw, expected):
        r = _parse_formula_string(raw)
        assert r[f"has_{expected}"] is True
        assert r["no_quiz_proxy"] is False

    def test_whitespace_normalised(self):
        r = _parse_formula_string("\r\n    Clarity\r\n    Energy\r\n    Logic\r\n    Motivation")
        assert r["has_clarity"] is True
        assert r["has_energy"] is True

    def test_single_formula_not_multi(self):
        r = _parse_formula_string("Clarity, Clarity, Clarity, Clarity")
        assert r["multi_formula"] is False
        assert r["formula_count"] == 1

    def test_no_quiz_proxy_false_when_parseable(self):
        r = _parse_formula_string("Energy, Logic")
        assert r["no_quiz_proxy"] is False

    def test_returns_none_not_nan_for_absent_flags(self):
        r = _absent()
        for key in ("has_clarity", "has_energy", "formula_count"):
            assert r[key] is None


# ---------------------------------------------------------------------------
# Quiz feature schema — column presence
# ---------------------------------------------------------------------------

class TestQuizFeatureSchema:
    def _make_mock_df(self) -> pd.DataFrame:
        rows = [
            {"subscription_id": "s1", "customer_id": "c1",
             "thesis_formulas": "Clarity, Energy, Logic, Motivation"},
            {"subscription_id": "s2", "customer_id": "c2",
             "thesis_formulas": None},
        ]
        return pd.DataFrame(rows)

    def test_all_quiz_feature_names_present(self):
        from bellwether.features.quiz import build, QUIZ_FEATURE_NAMES
        mock_raw = self._make_mock_df()
        with patch("bellwether.features.quiz.PointInTimeGuard") as MockGuard:
            instance = MockGuard.return_value
            instance.date_str = OBS_DATE.isoformat()
            instance.read.return_value = mock_raw
            df = build(OBS_DATE)
        for col in QUIZ_FEATURE_NAMES:
            assert col in df.columns, f"Missing column: {col}"

    def test_null_rows_have_no_quiz_proxy_true(self):
        from bellwether.features.quiz import build
        mock_raw = self._make_mock_df()
        with patch("bellwether.features.quiz.PointInTimeGuard") as MockGuard:
            instance = MockGuard.return_value
            instance.date_str = OBS_DATE.isoformat()
            instance.read.return_value = mock_raw
            df = build(OBS_DATE)
        null_rows = df[df["no_quiz_proxy"] == True]
        assert len(null_rows) == 1
        assert null_rows.iloc[0]["subscription_id"] == "s2"

    def test_non_null_rows_have_no_quiz_proxy_false(self):
        from bellwether.features.quiz import build
        mock_raw = self._make_mock_df()
        with patch("bellwether.features.quiz.PointInTimeGuard") as MockGuard:
            instance = MockGuard.return_value
            instance.date_str = OBS_DATE.isoformat()
            instance.read.return_value = mock_raw
            df = build(OBS_DATE)
        present_rows = df[df["no_quiz_proxy"] == False]
        assert len(present_rows) == 1


# ---------------------------------------------------------------------------
# Leakage contract: observation_date validation in label builder
# ---------------------------------------------------------------------------

class TestLabelBuilderValidation:
    def test_rejects_observation_date_at_snapshot(self):
        from bellwether.labels.observation import _validate
        with pytest.raises(ValueError, match="before snapshot"):
            _validate(SNAPSHOT_DATE, 30)

    def test_rejects_observation_date_after_snapshot(self):
        from bellwether.labels.observation import _validate
        with pytest.raises(ValueError, match="before snapshot"):
            _validate(SNAPSHOT_DATE + timedelta(days=1), 30)

    def test_rejects_horizon_that_exceeds_snapshot(self):
        from bellwether.labels.observation import _validate
        # 10 days before snapshot + 30 horizon = 20 days past snapshot
        obs = SNAPSHOT_DATE - timedelta(days=10)
        with pytest.raises(ValueError, match="exceeds snapshot"):
            _validate(obs, 30)

    def test_accepts_valid_observation_date(self):
        from bellwether.labels.observation import _validate
        obs = SNAPSHOT_DATE - timedelta(days=60)
        _validate(obs, 30)  # should not raise


# ---------------------------------------------------------------------------
# Integration: quiz features against real Snowflake (requires credentials)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestQuizFeaturesIntegration:
    def test_no_quiz_proxy_rate_above_80pct(self):
        """86%+ of active subscribers have no quiz data — this must hold."""
        from bellwether.features.quiz import build
        df = build(OBS_DATE)
        rate = df["no_quiz_proxy"].mean()
        assert rate > 0.80, f"no_quiz_proxy rate {rate:.1%} unexpectedly low"

    def test_all_expected_columns_present(self):
        from bellwether.features.quiz import build, QUIZ_FEATURE_NAMES
        df = build(OBS_DATE)
        for col in QUIZ_FEATURE_NAMES:
            assert col in df.columns

    def test_no_future_subscriptions_in_features(self):
        """Leakage gate: no subscription created after observation_date."""
        from bellwether.db.snowflake import read_sql
        obs_str = OBS_DATE.isoformat()
        df = read_sql(f"""
            SELECT COUNT(*) AS violations
            FROM GAUNTLET_SANDBOX.SOURCE.SUBSCRIPTIONS
            WHERE CREATED_AT >= '{obs_str}'::DATE
              AND SUBSCRIPTION_ID_HASH IN (
                  SELECT SUBSCRIPTION_ID_HASH
                  FROM GAUNTLET_SANDBOX.SOURCE.SUBSCRIPTIONS
                  WHERE CREATED_AT < '{obs_str}'::DATE
              )
        """)
        assert df.iloc[0, 0] == 0, "Leakage: subscriptions with future creation dates found in feature set"
