"""LangGraph nodes.

Two nodes call Gemini (understanding and response wording). The two nodes in
between are deterministic Python: policy evaluation and action/escalation.

When GEMINI_API_KEY is not set, the two language nodes fall back to a rule-based
implementation so the application, the demo and the test suite still run. The
fallback never changes a policy outcome: it only reads the message and words the
reply from the same deterministic decisions.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional

from app.agent.prompts import (
    RESPONSE_SYSTEM_PROMPT,
    UNDERSTANDING_SYSTEM_PROMPT,
    build_response_prompt,
    build_understanding_prompt,
)
from app.agent.schemas import RequestedAction, StructuredRequest
from app.agent.state import AgentState
from app.services import action_executor, data_service, escalation_service, policy_engine
from app.services.policy_engine import ActionType, EscalationSignal, PolicyDecision

logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


# ---------------------------------------------------------------------------
# Gemini access
# ---------------------------------------------------------------------------

def get_llm(temperature: float = 0.0):
    """Return a Gemini chat model, or None when no API key is configured."""
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        return None
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=DEFAULT_MODEL,
            google_api_key=api_key,
            temperature=temperature,
        )
    except Exception as exc:  # pragma: no cover - depends on environment
        logger.warning("Gemini unavailable (%s); using rule-based fallback.", exc)
        return None


# ---------------------------------------------------------------------------
# Rule-based fallback reader
# ---------------------------------------------------------------------------

_AMOUNT_RE = re.compile(r"(?:₹|rs\.?|inr)\s*([\d][\d,]*(?:\.\d+)?)", re.IGNORECASE)
_PLAIN_AMOUNT_RE = re.compile(r"([\d][\d,]*(?:\.\d+)?)\s*(?:rupees|rs\b|inr)", re.IGNORECASE)


def _extract_amount(text: str) -> Optional[float]:
    for pattern in (_AMOUNT_RE, _PLAIN_AMOUNT_RE):
        match = pattern.search(text)
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def _contains(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)


def fallback_understand(message: str, booking: Dict[str, Any]) -> StructuredRequest:
    """Keyword reader used when Gemini is not configured."""

    text = message.lower()
    amount = _extract_amount(text)
    actions: List[RequestedAction] = []
    signals: List[str] = []

    target_flight = None
    for flight in booking.get("flights", []):
        number = flight.get("flight_number")
        if number and number.lower().replace("-", "") in text.replace("-", ""):
            target_flight = number
    if target_flight is None and _contains(text, "return", "way back", "coming back", "inbound"):
        target_flight = "return"

    wants_hotel = _contains(text, "hotel", "accommodation", "place to stay", "room for the night")
    full_night = _contains(text, "full night", "whole night", "entire night", "overnight", "night's stay", "nights stay")
    wants_refund = _contains(text, "refund", "money back", "my money", "reimburse")
    wants_rebook = _contains(
        text, "rebook", "re-book", "another flight", "different flight", "next flight",
        "put me on", "other flight", "later flight", "alternative flight", "switch flight",
    )
    higher_fare = _contains(text, "costs more", "more expensive", "higher fare", "costing", "costs ₹", "more than my")
    wants_waiver = _contains(text, "waive", "waiver", "cover the difference", "absorb", "don't want to pay", "not paying", "free of charge", "at no cost")
    wants_upgrade = _contains(text, "upgrade", "business class", "first class")
    wants_meal = _contains(text, "meal", "food", "voucher", "eat", "hungry")
    wants_lounge = _contains(text, "lounge")
    wants_status = _contains(text, "status", "still fine", "still ok", "still okay", "is my return", "what about my", "confirm my", "when does", "what time")
    wants_extra = _contains(text, "compensation", "compensate", "goodwill", "beyond your policy", "more than your policy", "extra for the trouble")
    alternate_method = _contains(text, "different card", "another card", "different account", "another account", "different payment", "other payment", "upi instead", "new card")

    if _contains(text, "legal action", "lawyer", "sue you", "sue the", "court", "consumer court", "litigation"):
        signals.append(EscalationSignal.LEGAL_ACTION)
    if _contains(text, "formal complaint", "file a complaint", "lodge a complaint", "official complaint"):
        signals.append(EscalationSignal.FORMAL_COMPLAINT)
    if _contains(text, "missed my flight", "i was late", "i arrived late", "my fault", "missed the flight"):
        signals.append(EscalationSignal.NON_AIRLINE_CAUSED_EXCEPTION)

    if wants_refund:
        actions.append(
            RequestedAction(
                action_type=ActionType.REFUND,
                target_flight=target_flight,
                alternate_payment_method=alternate_method,
                notes="Customer asked for their money back.",
            )
        )
    if wants_hotel:
        actions.append(
            RequestedAction(
                action_type=ActionType.HOTEL_ACCOMMODATION,
                target_flight=target_flight,
                requested_duration="full_night" if full_night else "delay_hours",
                notes="Customer asked for hotel accommodation.",
            )
        )
    if wants_rebook or (higher_fare and not wants_upgrade):
        actions.append(
            RequestedAction(
                action_type=ActionType.REBOOKING,
                target_flight=target_flight,
                higher_fare=higher_fare,
                fare_difference=amount if higher_fare else None,
                waiver_requested=wants_waiver,
                notes="Customer asked to be moved to another flight.",
            )
        )
    if wants_waiver:
        actions.append(
            RequestedAction(
                action_type=ActionType.FARE_DIFFERENCE_WAIVER,
                fare_difference=amount,
                waiver_requested=True,
                notes="Customer asked for the fare difference to be waived.",
            )
        )
    if wants_upgrade:
        actions.append(
            RequestedAction(
                action_type=ActionType.CABIN_UPGRADE,
                target_flight=target_flight,
                notes="Customer asked for a cabin upgrade.",
            )
        )
    if wants_meal and not wants_extra:
        actions.append(RequestedAction(action_type=ActionType.MEAL_VOUCHER, notes="Customer asked about a meal voucher."))
    if wants_lounge:
        actions.append(RequestedAction(action_type=ActionType.LOUNGE_ACCESS, notes="Customer asked about lounge access."))
    if alternate_method:
        actions.append(
            RequestedAction(
                action_type=ActionType.ALTERNATE_REFUND_METHOD,
                alternate_payment_method=True,
                notes="Customer asked for the money to go to a different payment method.",
            )
        )
    if wants_extra and not any(a.action_type == ActionType.EXTRA_COMPENSATION for a in actions):
        actions.append(
            RequestedAction(
                action_type=ActionType.EXTRA_COMPENSATION,
                notes="Customer asked for compensation beyond what has been offered.",
            )
        )
    if wants_status:
        actions.append(
            RequestedAction(
                action_type=ActionType.FLIGHT_STATUS,
                target_flight=target_flight,
                notes="Customer asked about their booking or flight status.",
            )
        )

    if _contains(text, "furious", "outrageous", "unacceptable", "ruined", "disgusting", "angry", "!!"):
        sentiment = "angry"
    elif _contains(text, "frustrat", "annoyed", "upset", "stuck", "!"):
        sentiment = "frustrated"
    else:
        sentiment = "neutral"

    if not actions:
        actions.append(
            RequestedAction(
                action_type=ActionType.FLIGHT_STATUS,
                target_flight=target_flight,
                notes="No specific action identified; treating as a question about the booking.",
            )
        )

    return StructuredRequest(
        primary_purpose=message.strip()[:200] or "Customer message",
        target_flight=target_flight,
        requested_actions=actions,
        relevant_details=[f"Stated amount: {amount}"] if amount else [],
        customer_sentiment=sentiment,
        escalation_signals=signals,
        needs_clarification=False,
    )


# ---------------------------------------------------------------------------
# Node 1: understand_request
# ---------------------------------------------------------------------------

def understand_request(state: AgentState) -> AgentState:
    """Read the message into an internal structured request. No decisions here."""

    message = state.get("current_message", "")
    booking = state.get("booking", {})
    customer = state.get("customer", {})
    history = state.get("conversation_history", [])
    trace = list(state.get("trace", []))

    structured: Optional[StructuredRequest] = None
    llm = get_llm(temperature=0.0)
    if llm is not None:
        try:
            model = llm.with_structured_output(StructuredRequest)
            structured = model.invoke(
                [
                    ("system", UNDERSTANDING_SYSTEM_PROMPT),
                    ("human", build_understanding_prompt(customer, booking, message, history)),
                ]
            )
            trace.append("understand_request: gemini")
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("Gemini understanding failed (%s); using fallback reader.", exc)
            structured = None

    if structured is None:
        structured = fallback_understand(message, booking)
        trace.append("understand_request: fallback")

    # Which flight is this message about? A purely informational message may point at
    # any leg ("is my return still fine?"); a message that asks for action is handled
    # against the disrupted leg of the booking.
    action_types = {a.action_type for a in structured.requested_actions}
    informational_only = action_types <= {ActionType.FLIGHT_STATUS}
    hint = (structured.target_flight or message) if informational_only else structured.target_flight
    if not informational_only and hint in (None, "return"):
        hint = None
    target_flight = data_service.resolve_target_flight(state["pnr"], hint)

    state["structured_request"] = structured.model_dump()
    state["target_flight"] = target_flight
    state["llm_available"] = llm is not None
    state["trace"] = trace
    return state


# ---------------------------------------------------------------------------
# Node 2: policy_evaluation
# ---------------------------------------------------------------------------

def policy_evaluation(state: AgentState) -> AgentState:
    """Run the deterministic policy engine. The LLM has no say here."""

    structured = state.get("structured_request", {})
    decision = policy_engine.evaluate(
        customer=state.get("customer", {}),
        booking=state.get("booking", {}),
        target_flight=state.get("target_flight"),
        requested_actions=structured.get("requested_actions", []),
        escalation_signals=structured.get("escalation_signals", []),
    )
    state["policy_decision"] = decision.model_dump()
    state["trace"] = list(state.get("trace", [])) + ["policy_evaluation: deterministic"]
    return state


# ---------------------------------------------------------------------------
# Node 3: action_or_escalation
# ---------------------------------------------------------------------------

def action_or_escalation(state: AgentState) -> AgentState:
    """Execute approved actions and raise an escalation when policy demands it."""

    decision = PolicyDecision(**state.get("policy_decision", {}))

    results = action_executor.execute(
        pnr=state["pnr"],
        policy_decision=decision,
        target_flight=state.get("target_flight"),
    )
    escalation = escalation_service.handle(
        pnr=state["pnr"],
        policy_decision=decision,
        customer=state.get("customer"),
    )

    state["action_results"] = [r.model_dump() for r in results]
    state["escalation_result"] = escalation.model_dump()
    state["trace"] = list(state.get("trace", [])) + [
        f"action_or_escalation: {len(results)} action(s), escalation={escalation.required}"
    ]
    return state


# ---------------------------------------------------------------------------
# Node 4: generate_response
# ---------------------------------------------------------------------------

def _flight_phrase(flight: Optional[Dict[str, Any]]) -> str:
    if not flight:
        return "your booking"
    route = flight.get("route", {})
    number = flight.get("flight_number")
    leg = f"{route.get('from')} to {route.get('to')}"
    date = flight.get("date_label") or flight.get("date")
    if number:
        return f"flight {number} ({leg}) on {date}"
    return f"your {leg} flight on {date}"


def fallback_response(state: AgentState) -> str:
    """Compose the reply from the deterministic decisions, without a model."""

    customer = state.get("customer", {})
    decision = state.get("policy_decision", {})
    actions = state.get("action_results", [])
    escalation = state.get("escalation_result", {})
    structured = state.get("structured_request", {})
    flight = state.get("target_flight")

    sentiment = structured.get("customer_sentiment", "neutral")
    lines: List[str] = []

    if sentiment in ("angry", "frustrated", "distressed"):
        lines.append("I'm sorry, this is a frustrating way for a trip to start, and I want to sort out what I can right now.")

    status = (flight or {}).get("status")
    if status == "cancelled":
        lines.append(
            f"I can see {_flight_phrase(flight)} was cancelled due to "
            f"{(flight or {}).get('disruption_reason') or 'operational reasons'}."
        )
    elif status == "delayed":
        lines.append(
            f"I can see {_flight_phrase(flight)} is delayed by {(flight or {}).get('delay_hours')} hours, "
            f"now departing at {(flight or {}).get('new_departure')}."
        )
    elif status == "unaffected":
        phrase = _flight_phrase(flight)
        lines.append(
            f"{phrase[0].upper()}{phrase[1:]} is unaffected and still departing as scheduled at "
            f"{(flight or {}).get('scheduled_departure')}."
        )

    for action in actions:
        lines.append(action["detail"])

    for item in decision.get("decisions", []):
        if item["action"] == "CANCELLATION_OPTIONS" and item["status"] == "allowed":
            lines.append(
                "You can choose either free rebooking on the next available flight within 24 hours, "
                "or a full refund. Which would you prefer?"
            )
        if item["status"] == "denied":
            lines.append(item["reason"])

    if str(customer.get("loyalty_tier")) in ("Gold", "Platinum") and any(
        d["action"] in ("REBOOKING", "CANCELLATION_OPTIONS") for d in decision.get("decisions", [])
    ):
        lines.append(
            f"As a {customer.get('loyalty_tier')} member you get priority rebooking and first access to "
            "next-available seats."
        )

    if escalation.get("required"):
        lines.append(escalation.get("customer_message") or "")

    return " ".join(line.strip() for line in lines if line and line.strip())


def generate_response(state: AgentState) -> AgentState:
    """Write the customer-facing reply. Wording only: outcomes are already fixed."""

    llm = get_llm(temperature=0.3)
    text = ""
    trace = list(state.get("trace", []))

    if llm is not None:
        try:
            prompt = build_response_prompt(
                customer=state.get("customer", {}),
                booking=state.get("booking", {}),
                message=state.get("current_message", ""),
                history=state.get("conversation_history", []),
                structured_request=state.get("structured_request", {}),
                policy_decision=state.get("policy_decision", {}),
                action_results=state.get("action_results", []),
                escalation_result=state.get("escalation_result", {}),
            )
            result = llm.invoke([("system", RESPONSE_SYSTEM_PROMPT), ("human", prompt)])
            text = (getattr(result, "content", "") or "").strip()
            if text:
                trace.append("generate_response: gemini")
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("Gemini response generation failed (%s); using fallback writer.", exc)
            text = ""

    if not text:
        text = fallback_response(state)
        trace.append("generate_response: fallback")

    state["final_response"] = text
    state["trace"] = trace
    return state
