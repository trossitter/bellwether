"""Tests for simulated dispatch receipts."""

from datetime import datetime
import uuid

import pytest

from bellwether.dispatch import DispatchReceipt, SimulatedAdapter
from bellwether.eval.contracts import InterventionProposal


PROPOSAL_CASES = [
    ("price", "offer_discount"),
    ("efficacy", "share_testimonial"),
    ("fatigue", "pause_subscription"),
]


def _proposal(archetype: str, action: str) -> InterventionProposal:
    return InterventionProposal(
        subscriber_id=f"sub_{archetype}",
        archetype=archetype,
        action=action,
        message=(
            "We noticed your subscription renews soon. As a loyal Thesis member, "
            "we want to make sure your next step matches what you need right now."
        ),
        urgency_level="medium",
    )


@pytest.mark.parametrize("archetype,action", PROPOSAL_CASES)
def test_simulated_receipt_has_required_fields(archetype: str, action: str) -> None:
    proposal = _proposal(archetype, action)
    receipt = SimulatedAdapter().send(proposal)

    assert isinstance(receipt, DispatchReceipt)
    assert receipt.subscriber_id == proposal.subscriber_id
    assert receipt.action == proposal.action
    assert receipt.channel == "simulated"
    assert uuid.UUID(receipt.idempotency_key).version == 4
    dispatched_at = datetime.fromisoformat(receipt.dispatched_at)
    assert dispatched_at.tzinfo is not None
    assert dispatched_at.utcoffset().total_seconds() == 0
    assert receipt.success is True
    assert receipt.error is None


def test_idempotency_key_is_unique_for_same_proposal() -> None:
    proposal = _proposal("price", "offer_discount")
    adapter = SimulatedAdapter()

    first = adapter.send(proposal)
    second = adapter.send(proposal)

    assert first.idempotency_key != second.idempotency_key


def test_simulated_receipt_channel_is_simulated() -> None:
    receipt = SimulatedAdapter().send(_proposal("efficacy", "share_testimonial"))

    assert receipt.channel == "simulated"


def test_simulated_receipt_success_is_true() -> None:
    receipt = SimulatedAdapter().send(_proposal("fatigue", "pause_subscription"))

    assert receipt.success is True
