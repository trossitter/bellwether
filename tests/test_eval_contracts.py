"""Tests for eval/contracts.py — all offline, no Snowflake."""

import pytest

from bellwether.eval.contracts import (
    ActionConsistencyContract,
    ContractSuite,
    InterventionProposal,
    MessageLengthContract,
    ProhibitedContentContract,
    UrgencyConsistencyContract,
)

ARCHETYPE_ACTIONS: dict[str, set[str]] = {
    "price":       {"offer_discount", "explain_value"},
    "efficacy":    {"share_testimonial", "offer_consult"},
    "fatigue":     {"adjust_cadence", "pause_subscription"},
    "life_change": {"pause_subscription", "reduce_quantity"},
    "stimulant":   {"recommend_alternative", "offer_consult"},
    "involuntary": {"retry_payment", "update_payment_method"},
}


def _suite() -> ContractSuite:
    return ContractSuite([
        ActionConsistencyContract(ARCHETYPE_ACTIONS),
        MessageLengthContract(min_chars=50, max_chars=500),
        ProhibitedContentContract(frozenset({"competitor", "cure", "guaranteed"})),
        UrgencyConsistencyContract(),
    ])


# ---------------------------------------------------------------------------
# ActionConsistencyContract
# ---------------------------------------------------------------------------

def test_valid_action_passes(good_proposal):
    c = ActionConsistencyContract(ARCHETYPE_ACTIONS)
    result = c.check(good_proposal)
    assert result.passed


def test_invalid_action_fails(good_proposal):
    bad = InterventionProposal(**{**good_proposal.__dict__, "action": "send_gift"})
    result = ActionConsistencyContract(ARCHETYPE_ACTIONS).check(bad)
    assert not result.passed
    assert "not allowed" in result.violation


def test_unknown_archetype_fails(good_proposal):
    bad = InterventionProposal(**{**good_proposal.__dict__, "archetype": "mystery"})
    result = ActionConsistencyContract(ARCHETYPE_ACTIONS).check(bad)
    assert not result.passed
    assert "unknown archetype" in result.violation


@pytest.mark.parametrize("archetype,action", [
    ("price", "offer_discount"),
    ("price", "explain_value"),
    ("efficacy", "share_testimonial"),
    ("efficacy", "offer_consult"),
    ("fatigue", "adjust_cadence"),
    ("fatigue", "pause_subscription"),
    ("life_change", "pause_subscription"),
    ("life_change", "reduce_quantity"),
    ("stimulant", "recommend_alternative"),
    ("stimulant", "offer_consult"),
    ("involuntary", "retry_payment"),
    ("involuntary", "update_payment_method"),
])
def test_all_valid_archetype_action_pairs(good_proposal, archetype, action):
    proposal = InterventionProposal(
        subscriber_id=good_proposal.subscriber_id,
        archetype=archetype,
        action=action,
        message=good_proposal.message,
        urgency_level="low",
    )
    result = ActionConsistencyContract(ARCHETYPE_ACTIONS).check(proposal)
    assert result.passed, f"Expected ({archetype}, {action}) to pass"


# ---------------------------------------------------------------------------
# MessageLengthContract
# ---------------------------------------------------------------------------

def test_message_too_short_fails(good_proposal):
    bad = InterventionProposal(**{**good_proposal.__dict__, "message": "Too short."})
    result = MessageLengthContract().check(bad)
    assert not result.passed
    assert "length" in result.violation


def test_message_too_long_fails(good_proposal):
    bad = InterventionProposal(**{**good_proposal.__dict__, "message": "x" * 501})
    result = MessageLengthContract().check(bad)
    assert not result.passed


def test_message_at_boundaries_passes(good_proposal):
    for length in (50, 500):
        msg = "a" * length
        proposal = InterventionProposal(**{**good_proposal.__dict__, "message": msg})
        result = MessageLengthContract().check(proposal)
        assert result.passed, f"Expected length {length} to pass"


# ---------------------------------------------------------------------------
# ProhibitedContentContract
# ---------------------------------------------------------------------------

def test_prohibited_term_fails(good_proposal):
    bad = InterventionProposal(
        **{**good_proposal.__dict__,
           "message": "This supplement is guaranteed to cure your fatigue." + " " * 30}
    )
    result = ProhibitedContentContract(frozenset({"cure", "guaranteed"})).check(bad)
    assert not result.passed


def test_prohibited_term_case_insensitive(good_proposal):
    bad = InterventionProposal(
        **{**good_proposal.__dict__,
           "message": "Better than COMPETITOR and totally safe! " + "x" * 30}
    )
    result = ProhibitedContentContract(frozenset({"competitor"})).check(bad)
    assert not result.passed


def test_clean_message_passes(good_proposal):
    result = ProhibitedContentContract(frozenset({"cure", "guaranteed", "competitor"})).check(good_proposal)
    assert result.passed


# ---------------------------------------------------------------------------
# UrgencyConsistencyContract
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("level", ["low", "medium", "high"])
def test_valid_urgency_passes(good_proposal, level):
    proposal = InterventionProposal(**{**good_proposal.__dict__, "urgency_level": level})
    assert UrgencyConsistencyContract().check(proposal).passed


def test_invalid_urgency_fails(good_proposal):
    bad = InterventionProposal(**{**good_proposal.__dict__, "urgency_level": "critical"})
    result = UrgencyConsistencyContract().check(bad)
    assert not result.passed


# ---------------------------------------------------------------------------
# ContractSuite
# ---------------------------------------------------------------------------

def test_suite_all_pass(good_proposal):
    suite = _suite()
    assert suite.all_pass(good_proposal)
    assert suite.first_failure(good_proposal) is None


def test_suite_catches_first_failure(good_proposal):
    bad = InterventionProposal(**{**good_proposal.__dict__, "action": "unknown_action"})
    suite = _suite()
    assert not suite.all_pass(bad)
    failure = suite.first_failure(bad)
    assert failure is not None
    assert not failure.passed


def test_suite_run_returns_all_results(good_proposal):
    suite = _suite()
    results = suite.run(good_proposal)
    assert len(results) == 4
    assert all(r.passed for r in results)
