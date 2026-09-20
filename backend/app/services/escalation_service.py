"""Escalation handling for the explicitly prohibited cases."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.policy_engine import EscalationSignal, PolicyDecision

# Customer-facing wording. Internal reasoning is never sent to the customer.
CUSTOMER_MESSAGES = {
    EscalationSignal.LEGAL_ACTION: "Your request has been passed to our specialist support team, who will contact you directly.",
    EscalationSignal.FORMAL_COMPLAINT: "Your complaint has been passed to our specialist support team, who will contact you directly.",
    EscalationSignal.COMPENSATION_BEYOND_POLICY: "This request goes beyond what I can approve, so a human agent will review it and get back to you.",
    EscalationSignal.FARE_WAIVER_ABOVE_LIMIT: "Waiving this fare difference needs supervisor approval, so a human agent will review it and get back to you.",
    EscalationSignal.NON_AIRLINE_CAUSED_EXCEPTION: "This request needs a human agent to review, and they will get back to you.",
    EscalationSignal.ALTERNATE_REFUND_METHOD: "Changing where a refund is sent needs a human agent, and they will get back to you.",
}

DEFAULT_CUSTOMER_MESSAGE = "Your request requires support from a human agent, who will follow up with you directly."

PRIORITY_ORDER = [
    EscalationSignal.LEGAL_ACTION,
    EscalationSignal.FORMAL_COMPLAINT,
    EscalationSignal.ALTERNATE_REFUND_METHOD,
    EscalationSignal.FARE_WAIVER_ABOVE_LIMIT,
    EscalationSignal.COMPENSATION_BEYOND_POLICY,
    EscalationSignal.NON_AIRLINE_CAUSED_EXCEPTION,
]


class EscalationResult(BaseModel):
    required: bool = False
    ticket_id: Optional[str] = None
    signals: List[str] = Field(default_factory=list)
    internal_reasons: List[str] = Field(default_factory=list)
    reason: Optional[str] = None
    customer_message: Optional[str] = None
    simulated: bool = True


def _primary(signals: List[str]) -> Optional[str]:
    for candidate in PRIORITY_ORDER:
        if candidate in signals:
            return candidate
    return signals[0] if signals else None


def handle(
    pnr: str,
    policy_decision: PolicyDecision,
    customer: Optional[Dict[str, Any]] = None,
) -> EscalationResult:
    """Create an escalation record when the policy engine demands one."""

    if not policy_decision.escalation_required:
        return EscalationResult(required=False)

    signals = list(policy_decision.escalation_signals)
    primary = _primary(signals)

    return EscalationResult(
        required=True,
        ticket_id=f"ESC-{pnr}-{uuid.uuid4().hex[:6].upper()}",
        signals=signals,
        internal_reasons=list(policy_decision.escalation_reasons),
        reason=policy_decision.escalation_reason,
        customer_message=CUSTOMER_MESSAGES.get(primary, DEFAULT_CUSTOMER_MESSAGE),
    )
