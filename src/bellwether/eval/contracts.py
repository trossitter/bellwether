"""Deterministic behavior contracts for intervention proposals.

Every proposal must pass all contracts before reaching the judge or dispatch.
A contract failure is a hard stop — not a warning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Proposal shape — superseded by intervene/schema.py when that module exists.
# ---------------------------------------------------------------------------

@dataclass
class InterventionProposal:
    subscriber_id: str
    archetype: str
    action: str
    message: str
    urgency_level: str  # "low" | "medium" | "high"


# ---------------------------------------------------------------------------
# Contract primitives
# ---------------------------------------------------------------------------

@dataclass
class ContractResult:
    passed: bool
    violation: str | None = None


@runtime_checkable
class Contract(Protocol):
    name: str

    def check(self, proposal: InterventionProposal) -> ContractResult:
        ...


# ---------------------------------------------------------------------------
# Built-in contracts
# ---------------------------------------------------------------------------

class ActionConsistencyContract:
    """Action must be in the allowed set for the proposal's archetype."""

    name = "action_consistency"

    def __init__(self, archetype_actions: dict[str, set[str]]) -> None:
        self._map = archetype_actions

    def check(self, proposal: InterventionProposal) -> ContractResult:
        allowed = self._map.get(proposal.archetype)
        if allowed is None:
            return ContractResult(False, f"unknown archetype '{proposal.archetype}'")
        if proposal.action not in allowed:
            return ContractResult(
                False,
                f"action '{proposal.action}' not allowed for archetype '{proposal.archetype}'",
            )
        return ContractResult(True)


class MessageLengthContract:
    """Message must be within character bounds."""

    name = "message_length"

    def __init__(self, min_chars: int = 50, max_chars: int = 500) -> None:
        self._min = min_chars
        self._max = max_chars

    def check(self, proposal: InterventionProposal) -> ContractResult:
        n = len(proposal.message)
        if n < self._min or n > self._max:
            return ContractResult(
                False,
                f"message length {n} outside [{self._min}, {self._max}]",
            )
        return ContractResult(True)


class ProhibitedContentContract:
    """Message must not contain any prohibited terms (case-insensitive)."""

    name = "prohibited_content"

    def __init__(self, prohibited: frozenset[str]) -> None:
        self._prohibited = frozenset(t.lower() for t in prohibited)

    def check(self, proposal: InterventionProposal) -> ContractResult:
        msg_lower = proposal.message.lower()
        for term in self._prohibited:
            if term in msg_lower:
                return ContractResult(False, f"prohibited term '{term}' found in message")
        return ContractResult(True)


class UrgencyConsistencyContract:
    """Urgency level must be one of the three allowed values."""

    name = "urgency_consistency"
    _ALLOWED = frozenset({"low", "medium", "high"})

    def check(self, proposal: InterventionProposal) -> ContractResult:
        if proposal.urgency_level not in self._ALLOWED:
            return ContractResult(False, f"invalid urgency_level '{proposal.urgency_level}'")
        return ContractResult(True)


# ---------------------------------------------------------------------------
# Suite runner
# ---------------------------------------------------------------------------

class ContractSuite:
    """Runs all contracts against a proposal in order; short-circuits on first failure."""

    def __init__(self, contracts: list[Contract]) -> None:
        self._contracts = contracts

    def run(self, proposal: InterventionProposal) -> list[ContractResult]:
        return [c.check(proposal) for c in self._contracts]

    def all_pass(self, proposal: InterventionProposal) -> bool:
        return all(r.passed for r in self.run(proposal))

    def first_failure(self, proposal: InterventionProposal) -> ContractResult | None:
        for result in self.run(proposal):
            if not result.passed:
                return result
        return None
