"""Simulated action executor.

These actions are prototype simulations for the assignment. No real airline,
payment or hotel system is contacted or modified. The executor will only run
actions the deterministic policy engine marked as allowed.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.policy_engine import (
    STATUS_ALLOWED,
    ActionType,
    PolicyDecision,
)

# Actions that produce a customer-visible action card.
EXECUTABLE_ACTIONS = {
    ActionType.REBOOKING,
    ActionType.REFUND,
    ActionType.MEAL_VOUCHER,
    ActionType.LOUNGE_ACCESS,
    ActionType.HOTEL_ACCOMMODATION,
    ActionType.FARE_DIFFERENCE_WAIVER,
}

ACTION_LABELS = {
    ActionType.REBOOKING: "Rebooking requested",
    ActionType.REFUND: "Refund initiated",
    ActionType.MEAL_VOUCHER: "Meal voucher issued",
    ActionType.LOUNGE_ACCESS: "Lounge access provided",
    ActionType.HOTEL_ACCOMMODATION: "Hotel accommodation arranged",
    ActionType.FARE_DIFFERENCE_WAIVER: "Fare difference waived",
}


class ActionResult(BaseModel):
    action: str
    label: str
    status: str
    detail: str
    simulated: bool = True
    details: Dict[str, Any] = Field(default_factory=dict)


def execute(
    pnr: str,
    policy_decision: PolicyDecision,
    target_flight: Optional[Dict[str, Any]] = None,
    executed_actions: Optional[List[str]] = None,
) -> List[ActionResult]:
    """Execute every allowed action once, in the order the policy returned.

    Actions listed in *executed_actions* have already been performed in a
    previous turn of this conversation and must not be repeated.  Only the
    newly-executed results are returned.
    """

    results: List[ActionResult] = []
    # Pre-populate `seen` with actions already executed in earlier turns so
    # they are not repeated in the current turn's response.
    seen: set[str] = set(executed_actions or [])
    flight_number = (target_flight or {}).get("flight_number")
    flight_label = flight_number or "your booked flight"

    for item in policy_decision.decisions:
        if item.status != STATUS_ALLOWED:
            continue
        action = item.action
        if action not in EXECUTABLE_ACTIONS or action in seen:
            continue
        seen.add(action)
        details = dict(item.details)

        if action == ActionType.REFUND:
            results.append(
                ActionResult(
                    action=action,
                    label=ACTION_LABELS[action],
                    status="initiated",
                    detail=(
                        "Full refund requested for the cancelled flight. Refunds are processed "
                        "within 7 business days to the original payment method."
                    ),
                    details=details,
                )
            )
        elif action == ActionType.REBOOKING:
            if details.get("charge") == 0:
                detail = (
                    f"Rebooking requested for {flight_label} on the next available flight "
                    "within 24 hours, at no extra cost."
                )
            else:
                fare = details.get("fare_difference_inr")
                fare_text = f" The fare difference of ₹{fare:,.0f} is payable by you." if fare else (
                    " The fare difference is payable by you."
                )
                detail = f"Rebooking requested on the higher-fare flight you asked for.{fare_text}"
            if details.get("priority_rebooking"):
                detail += " Priority rebooking has been applied to this request."
            results.append(
                ActionResult(
                    action=action,
                    label=ACTION_LABELS[action],
                    status="requested",
                    detail=detail,
                    details=details,
                )
            )
        elif action == ActionType.MEAL_VOUCHER:
            amount = details.get("amount_inr")
            results.append(
                ActionResult(
                    action=action,
                    label=ACTION_LABELS[action],
                    status="issued",
                    detail=(
                        f"₹{amount:,} meal voucher added to your booking."
                        if amount
                        else "Meal voucher added to your booking."
                    ),
                    details=details,
                )
            )
        elif action == ActionType.LOUNGE_ACCESS:
            results.append(
                ActionResult(
                    action=action,
                    label=ACTION_LABELS[action],
                    status="issued",
                    detail="Lounge access added to your booking for today's departure.",
                    details=details,
                )
            )
        elif action == ActionType.HOTEL_ACCOMMODATION:
            hours = details.get("delay_hours")
            results.append(
                ActionResult(
                    action=action,
                    label=ACTION_LABELS[action],
                    status="arranged",
                    detail=(
                        f"Hotel accommodation arranged to cover the {hours}-hour delay period."
                        if hours
                        else "Hotel accommodation arranged to cover the delay period."
                    ),
                    details=details,
                )
            )
        elif action == ActionType.FARE_DIFFERENCE_WAIVER:
            amount = details.get("fare_difference_inr")
            results.append(
                ActionResult(
                    action=action,
                    label=ACTION_LABELS[action],
                    status="applied",
                    detail=(
                        f"Fare difference of ₹{amount:,.0f} waived."
                        if amount is not None
                        else "Fare difference waived."
                    ),
                    details=details,
                )
            )

    return results
