"""Dispatch adapters for delivering approved intervention proposals.

This module owns the seam between intervention output and real-world systems.
Sandbox runs use SimulatedAdapter; production can swap in a concrete Klaviyo or
Zendesk adapter without changing the rest of the Bellwether pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Protocol
import uuid

from bellwether.eval.contracts import InterventionProposal

logger = logging.getLogger(__name__)


@dataclass
class DispatchReceipt:
    subscriber_id: str
    action: str
    channel: str
    idempotency_key: str
    dispatched_at: str
    success: bool
    error: str | None


class DispatchAdapter(Protocol):
    def send(self, proposal: InterventionProposal) -> DispatchReceipt:
        ...


class SimulatedAdapter:
    """No-op adapter for sandbox use. Logs the proposal; does not send."""

    def send(self, proposal: InterventionProposal) -> DispatchReceipt:
        idempotency_key = str(uuid.uuid4())
        dispatched_at = datetime.now(timezone.utc).isoformat()

        logger.info(
            "Simulated dispatch for proposal %r",
            proposal,
            extra={
                "subscriber_id": proposal.subscriber_id,
                "archetype": proposal.archetype,
                "action": proposal.action,
                "urgency_level": proposal.urgency_level,
                "idempotency_key": idempotency_key,
            },
        )

        return DispatchReceipt(
            subscriber_id=proposal.subscriber_id,
            action=proposal.action,
            channel="simulated",
            idempotency_key=idempotency_key,
            dispatched_at=dispatched_at,
            success=True,
            error=None,
        )
