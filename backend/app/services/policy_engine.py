"""Deterministic policy engine.

Every policy decision in this application is made here, in plain Python, from
the supplied service rules. No language model participates in these decisions
and no rule exists here that is not in the source policy.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.data_service import load_policies


# --------------------------------------------------------------------------
# Vocabulary
# --------------------------------------------------------------------------

class ActionType:
    REBOOKING = "REBOOKING"
    REFUND = "REFUND"
    MEAL_VOUCHER = "MEAL_VOUCHER"
    LOUNGE_ACCESS = "LOUNGE_ACCESS"
    HOTEL_ACCOMMODATION = "HOTEL_ACCOMMODATION"
    HOTEL_ACCOMMODATION_FULL_NIGHT = "HOTEL_ACCOMMODATION_FULL_NIGHT"
    FARE_DIFFERENCE_WAIVER = "FARE_DIFFERENCE_WAIVER"
    CABIN_UPGRADE = "CABIN_UPGRADE"
    EXTRA_COMPENSATION = "EXTRA_COMPENSATION"
    ALTERNATE_REFUND_METHOD = "ALTERNATE_REFUND_METHOD"
    FLIGHT_STATUS = "FLIGHT_STATUS"
    OTHER = "OTHER"

    ALL = (
        REBOOKING,
        REFUND,
        MEAL_VOUCHER,
        LOUNGE_ACCESS,
        HOTEL_ACCOMMODATION,
        HOTEL_ACCOMMODATION_FULL_NIGHT,
        FARE_DIFFERENCE_WAIVER,
        CABIN_UPGRADE,
        EXTRA_COMPENSATION,
        ALTERNATE_REFUND_METHOD,
        FLIGHT_STATUS,
        OTHER,
    )


class EscalationSignal:
    LEGAL_ACTION = "LEGAL_ACTION"
    FORMAL_COMPLAINT = "FORMAL_COMPLAINT"
    COMPENSATION_BEYOND_POLICY = "COMPENSATION_BEYOND_POLICY"
    FARE_WAIVER_ABOVE_LIMIT = "FARE_WAIVER_ABOVE_LIMIT"
    NON_AIRLINE_CAUSED_EXCEPTION = "NON_AIRLINE_CAUSED_EXCEPTION"
    ALTERNATE_REFUND_METHOD = "ALTERNATE_REFUND_METHOD"

    ALL = (
        LEGAL_ACTION,
        FORMAL_COMPLAINT,
        COMPENSATION_BEYOND_POLICY,
        FARE_WAIVER_ABOVE_LIMIT,
        NON_AIRLINE_CAUSED_EXCEPTION,
        ALTERNATE_REFUND_METHOD,
    )


ESCALATION_REASONS = {
    EscalationSignal.LEGAL_ACTION: "Threat of legal action",
    EscalationSignal.FORMAL_COMPLAINT: "Formal complaint",
    EscalationSignal.COMPENSATION_BEYOND_POLICY: "Compensation requested beyond the stated policy",
    EscalationSignal.FARE_WAIVER_ABOVE_LIMIT: "Fare difference waiver above the agent limit",
    EscalationSignal.NON_AIRLINE_CAUSED_EXCEPTION: "Exception requested for a disruption that is not airline-caused",
    EscalationSignal.ALTERNATE_REFUND_METHOD: "Refund requested to a payment method other than the original",
}

STATUS_ALLOWED = "allowed"
STATUS_DENIED = "denied"
STATUS_ESCALATE = "escalate"


# --------------------------------------------------------------------------
# Structures
# --------------------------------------------------------------------------

class PolicyDecisionItem(BaseModel):
    action: str
    status: str
    reason: str
    details: Dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(BaseModel):
    decisions: List[PolicyDecisionItem] = Field(default_factory=list)
    allowed_actions: List[str] = Field(default_factory=list)
    denied_actions: List[str] = Field(default_factory=list)
    escalation_required: bool = False
    escalation_reason: Optional[str] = None
    escalation_reasons: List[str] = Field(default_factory=list)
    escalation_signals: List[str] = Field(default_factory=list)
    entitlements: List[str] = Field(default_factory=list)
    loyalty_notes: List[str] = Field(default_factory=list)
    target_flight_summary: Optional[Dict[str, Any]] = None


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def delay_entitlements(delay_hours: Optional[float]) -> List[str]:
    """Return the entitlements the supplied delay rule grants for a delay."""
    if delay_hours is None or delay_hours <= 0:
        return []
    if delay_hours < 3:
        return [ActionType.MEAL_VOUCHER]
    if delay_hours < 5:
        return [ActionType.MEAL_VOUCHER, ActionType.LOUNGE_ACCESS]
    return [ActionType.MEAL_VOUCHER, ActionType.LOUNGE_ACCESS, ActionType.HOTEL_ACCOMMODATION]


def meal_voucher_amount() -> int:
    tiers = load_policies()["delay_compensation"]["tiers"]
    for tier in tiers:
        if tier.get("meal_voucher_amount_inr"):
            return int(tier["meal_voucher_amount_inr"])
    return 0


def agent_waiver_limit() -> float:
    return float(load_policies()["fare_difference"]["agent_waiver_limit_inr"])


def flight_summary(flight: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not flight:
        return None
    route = flight.get("route", {})
    return {
        "flight_number": flight.get("flight_number"),
        "from": route.get("from"),
        "to": route.get("to"),
        "date": flight.get("date"),
        "date_label": flight.get("date_label"),
        "scheduled_departure": flight.get("scheduled_departure"),
        "status": flight.get("status"),
        "delay_hours": flight.get("delay_hours"),
        "new_departure": flight.get("new_departure"),
        "disruption_reason": flight.get("disruption_reason"),
    }


def _as_dict(action: Any) -> Dict[str, Any]:
    if hasattr(action, "model_dump"):
        return action.model_dump()
    if isinstance(action, dict):
        return dict(action)
    return {"action_type": str(action)}


# --------------------------------------------------------------------------
# Engine
# --------------------------------------------------------------------------

def evaluate(
    customer: Dict[str, Any],
    booking: Dict[str, Any],
    target_flight: Optional[Dict[str, Any]],
    requested_actions: Optional[List[Any]] = None,
    escalation_signals: Optional[List[str]] = None,
) -> PolicyDecision:
    """Evaluate every requested action against the supplied policy."""

    requested = [_as_dict(a) for a in (requested_actions or [])]
    signals = [s for s in (escalation_signals or []) if s in EscalationSignal.ALL]

    decision = PolicyDecision(target_flight_summary=flight_summary(target_flight))

    tier = str(customer.get("loyalty_tier", ""))
    loyalty = load_policies()["loyalty"].get(tier, {})
    priority = bool(loyalty.get("priority_rebooking"))

    status = (target_flight or {}).get("status")
    airline_caused = bool((target_flight or {}).get("airline_caused"))
    delay_hours = (target_flight or {}).get("delay_hours")
    is_cancelled = status == "cancelled"
    is_delayed = status == "delayed"

    entitlements = delay_entitlements(delay_hours) if is_delayed else []
    decision.entitlements = list(entitlements)

    if priority:
        decision.loyalty_notes.append(
            f"{tier} customer: priority rebooking and first access to next-available seats."
        )
    decision.loyalty_notes.append(
        f"{tier} customers receive no additional compensation beyond the standard policy."
    )

    def add(action: str, state: str, reason: str, details: Optional[Dict[str, Any]] = None) -> None:
        decision.decisions.append(
            PolicyDecisionItem(action=action, status=state, reason=reason, details=details or {})
        )
        if state == STATUS_ALLOWED and action not in decision.allowed_actions:
            decision.allowed_actions.append(action)
        if state in (STATUS_DENIED, STATUS_ESCALATE) and action not in decision.denied_actions:
            decision.denied_actions.append(action)

    def escalate(signal: str) -> None:
        if signal not in decision.escalation_signals:
            decision.escalation_signals.append(signal)
            decision.escalation_reasons.append(ESCALATION_REASONS[signal])
        decision.escalation_required = True
        decision.escalation_reason = decision.escalation_reasons[0]

    # -- Standing entitlements for a qualifying delay -----------------------
    for entitlement in entitlements:
        if entitlement == ActionType.MEAL_VOUCHER:
            add(
                ActionType.MEAL_VOUCHER,
                STATUS_ALLOWED,
                f"Delay of {delay_hours} hours qualifies for a meal voucher.",
                {"amount_inr": meal_voucher_amount(), "delay_hours": delay_hours},
            )
        elif entitlement == ActionType.LOUNGE_ACCESS:
            add(
                ActionType.LOUNGE_ACCESS,
                STATUS_ALLOWED,
                f"Delay of {delay_hours} hours (3 hours or more) qualifies for lounge access.",
                {"delay_hours": delay_hours},
            )
        elif entitlement == ActionType.HOTEL_ACCOMMODATION:
            add(
                ActionType.HOTEL_ACCOMMODATION,
                STATUS_ALLOWED,
                f"Delay of {delay_hours} hours (5 hours or more) qualifies for hotel accommodation.",
                {
                    "delay_hours": delay_hours,
                    "covers": "delayed hours only",
                    "covers_full_night": False,
                },
            )

    requested_types = {r.get("action_type") for r in requested}

    # -- Requested actions --------------------------------------------------
    for item in requested:
        action_type = item.get("action_type") or ActionType.OTHER

        if action_type == ActionType.FLIGHT_STATUS:
            add(
                ActionType.FLIGHT_STATUS,
                STATUS_ALLOWED,
                "Customers may be given their own booking and flight status information.",
                {},
            )

        elif action_type == ActionType.REFUND:
            if item.get("alternate_payment_method"):
                escalate(EscalationSignal.ALTERNATE_REFUND_METHOD)
                add(
                    ActionType.ALTERNATE_REFUND_METHOD,
                    STATUS_ESCALATE,
                    "Refunds may only be made to the original payment method.",
                    {},
                )
            if is_cancelled and airline_caused:
                add(
                    ActionType.REFUND,
                    STATUS_ALLOWED,
                    "Flight cancelled by the airline: the customer may choose a full refund.",
                    {
                        "amount": "full",
                        "processing_time": "within 7 business days",
                        "destination": "original payment method",
                    },
                )
            else:
                add(
                    ActionType.REFUND,
                    STATUS_DENIED,
                    "The refund rule applies to airline-caused cancellations, and this flight is not cancelled.",
                    {"flight_status": status},
                )

        elif action_type == ActionType.REBOOKING:
            higher_fare = bool(item.get("higher_fare"))
            fare_difference = item.get("fare_difference")
            if higher_fare:
                add(
                    ActionType.REBOOKING,
                    STATUS_ALLOWED,
                    "Rebooking on a higher-fare flight is a voluntary choice: the customer pays the fare difference.",
                    {
                        "charge": "fare difference payable by the customer",
                        "fare_difference_inr": fare_difference,
                        "priority_rebooking": priority,
                    },
                )
            elif (is_cancelled or is_delayed) and airline_caused:
                add(
                    ActionType.REBOOKING,
                    STATUS_ALLOWED,
                    "Airline-caused disruption: free rebooking on the next available flight within 24 hours.",
                    {
                        "charge": 0,
                        "window_hours": 24,
                        "priority_rebooking": priority,
                    },
                )
            else:
                add(
                    ActionType.REBOOKING,
                    STATUS_DENIED,
                    "Free rebooking applies to airline-caused disruption, which does not apply to this flight.",
                    {"flight_status": status},
                )

        elif action_type == ActionType.HOTEL_ACCOMMODATION:
            full_night = str(item.get("requested_duration") or "").lower() == "full_night"
            qualifies = ActionType.HOTEL_ACCOMMODATION in entitlements
            if full_night:
                add(
                    ActionType.HOTEL_ACCOMMODATION_FULL_NIGHT,
                    STATUS_DENIED,
                    "Hotel accommodation covers only the delayed hours, not a full night's stay.",
                    {"delay_hours": delay_hours},
                )
            if not qualifies and ActionType.HOTEL_ACCOMMODATION not in decision.allowed_actions:
                add(
                    ActionType.HOTEL_ACCOMMODATION,
                    STATUS_DENIED,
                    "Hotel accommodation applies to delays of 5 hours or more; this delay does not reach that threshold.",
                    {"delay_hours": delay_hours},
                )

        elif action_type == ActionType.MEAL_VOUCHER:
            if ActionType.MEAL_VOUCHER not in decision.allowed_actions:
                add(
                    ActionType.MEAL_VOUCHER,
                    STATUS_DENIED,
                    "Meal vouchers are provided for a delayed flight; this flight is not delayed.",
                    {"flight_status": status},
                )

        elif action_type == ActionType.LOUNGE_ACCESS:
            if ActionType.LOUNGE_ACCESS not in decision.allowed_actions:
                add(
                    ActionType.LOUNGE_ACCESS,
                    STATUS_DENIED,
                    "Lounge access applies to delays of 3 hours or more.",
                    {"delay_hours": delay_hours, "flight_status": status},
                )

        elif action_type == ActionType.FARE_DIFFERENCE_WAIVER:
            amount = item.get("fare_difference")
            limit = agent_waiver_limit()
            if amount is None:
                add(
                    ActionType.FARE_DIFFERENCE_WAIVER,
                    STATUS_DENIED,
                    "The fare difference amount has not been confirmed, so no waiver can be applied.",
                    {"agent_waiver_limit_inr": limit},
                )
            elif float(amount) > limit:
                escalate(EscalationSignal.FARE_WAIVER_ABOVE_LIMIT)
                add(
                    ActionType.FARE_DIFFERENCE_WAIVER,
                    STATUS_ESCALATE,
                    "Agents cannot waive fare differences above the limit without supervisor approval.",
                    {"fare_difference_inr": float(amount), "agent_waiver_limit_inr": limit},
                )
            else:
                add(
                    ActionType.FARE_DIFFERENCE_WAIVER,
                    STATUS_ALLOWED,
                    "The fare difference is within the amount an agent may waive.",
                    {"fare_difference_inr": float(amount), "agent_waiver_limit_inr": limit},
                )

        elif action_type == ActionType.CABIN_UPGRADE:
            escalate(EscalationSignal.COMPENSATION_BEYOND_POLICY)
            add(
                ActionType.CABIN_UPGRADE,
                STATUS_ESCALATE,
                "The supplied policy contains no cabin upgrade entitlement; this is compensation beyond policy.",
                {},
            )

        elif action_type == ActionType.EXTRA_COMPENSATION:
            escalate(EscalationSignal.COMPENSATION_BEYOND_POLICY)
            add(
                ActionType.EXTRA_COMPENSATION,
                STATUS_ESCALATE,
                "Compensation beyond the stated policy amounts requires a human agent.",
                {},
            )

        elif action_type == ActionType.ALTERNATE_REFUND_METHOD:
            escalate(EscalationSignal.ALTERNATE_REFUND_METHOD)
            add(
                ActionType.ALTERNATE_REFUND_METHOD,
                STATUS_ESCALATE,
                "Refunds may only be made to the original payment method.",
                {},
            )

        else:
            add(
                ActionType.OTHER,
                STATUS_DENIED,
                "The supplied policy does not cover this request.",
                {},
            )

    # -- Cancellation choice is informational until the customer chooses ----
    if is_cancelled and airline_caused:
        if not requested_types & {ActionType.REFUND, ActionType.REBOOKING}:
            add(
                "CANCELLATION_OPTIONS",
                STATUS_ALLOWED,
                "Cancelled by the airline: the customer chooses free rebooking within 24 hours or a full refund.",
                {"options": ["REBOOKING", "REFUND"], "priority_rebooking": priority},
            )

    # -- Standalone escalation signals --------------------------------------
    for signal in signals:
        escalate(signal)

    return decision
