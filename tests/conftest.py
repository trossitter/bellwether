"""Shared pytest fixtures."""

import numpy as np
import pytest

from bellwether.eval.contracts import InterventionProposal


@pytest.fixture()
def binary_labels() -> np.ndarray:
    rng = np.random.default_rng(42)
    return rng.integers(0, 2, size=500).astype(float)


@pytest.fixture()
def calibrated_probs(binary_labels: np.ndarray) -> np.ndarray:
    """Probabilities close to labels — should pass calibration thresholds."""
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 0.1, size=len(binary_labels))
    return np.clip(binary_labels + noise, 0.01, 0.99)


@pytest.fixture()
def quiz_present_mask(binary_labels: np.ndarray) -> np.ndarray:
    """~70% of subscribers have quiz data."""
    rng = np.random.default_rng(42)
    return rng.random(size=len(binary_labels)) < 0.70


@pytest.fixture()
def good_proposal() -> InterventionProposal:
    return InterventionProposal(
        subscriber_id="sub_001",
        archetype="price",
        action="offer_discount",
        message=(
            "We noticed your subscription renews soon. As a loyal Thesis member, "
            "we'd like to offer you 15% off your next cycle — no action needed, "
            "it'll apply automatically."
        ),
        urgency_level="medium",
    )
