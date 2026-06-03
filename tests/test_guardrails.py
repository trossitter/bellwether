import pytest

from bellwether.eval.contracts import InterventionProposal
from bellwether.intervene.guardrails import GuardrailError, run_guardrails


def test_valid_proposal_passes_without_error(good_proposal):
    run_guardrails(good_proposal)


def test_invalid_action_raises_guardrail_error(good_proposal):
    proposal = InterventionProposal(**{**good_proposal.__dict__, "action": "send_gift"})

    with pytest.raises(GuardrailError, match="not allowed"):
        run_guardrails(proposal)


def test_prohibited_term_raises_guardrail_error(good_proposal):
    proposal = InterventionProposal(
        **{
            **good_proposal.__dict__,
            "message": (
                "We can help you find a better subscription rhythm, but this "
                "message must never mention a competitor in dispatch copy."
            ),
        }
    )

    with pytest.raises(GuardrailError, match="prohibited term"):
        run_guardrails(proposal)


def test_too_short_message_raises_guardrail_error(good_proposal):
    proposal = InterventionProposal(**{**good_proposal.__dict__, "message": "Too short."})

    with pytest.raises(GuardrailError, match="message length"):
        run_guardrails(proposal)


def test_run_guardrails_returns_proposal_unchanged_on_success(good_proposal):
    assert run_guardrails(good_proposal) is good_proposal
