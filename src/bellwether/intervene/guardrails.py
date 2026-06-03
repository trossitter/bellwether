"""Hard deterministic gate for intervention proposals before dispatch."""

from __future__ import annotations

from bellwether.eval.contracts import (
    ActionConsistencyContract,
    ContractSuite,
    InterventionProposal,
    MessageLengthContract,
    ProhibitedContentContract,
    UrgencyConsistencyContract,
)

ARCHETYPE_ACTIONS: dict[str, set[str]] = {
    "price": {"offer_discount", "explain_value"},
    "efficacy": {"share_testimonial", "offer_consult"},
    "fatigue": {"adjust_cadence", "pause_subscription"},
    "life_change": {"pause_subscription", "reduce_quantity"},
    "stimulant": {"recommend_alternative", "offer_consult"},
    "involuntary": {"retry_payment", "update_payment_method"},
}

_CONTRACTS = ContractSuite([
    ActionConsistencyContract(ARCHETYPE_ACTIONS),
    MessageLengthContract(min_chars=50, max_chars=500),
    ProhibitedContentContract(frozenset({
        "cure",
        "guaranteed",
        "competitor",
        "clinically proven",
        "FDA",
    })),
    UrgencyConsistencyContract(),
])


class GuardrailError(RuntimeError):
    """Raised when a proposal fails a deterministic guardrail check."""


def run_guardrails(proposal: InterventionProposal) -> InterventionProposal:
    """Run all contracts against proposal. Return it unchanged if all pass.

    Raise GuardrailError with the violation message if any contract fails.
    This is a hard stop - no proposal reaches dispatch without passing here.
    """
    failure = _CONTRACTS.first_failure(proposal)
    if failure is not None:
        raise GuardrailError(failure.violation)
    return proposal
