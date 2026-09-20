"""Complete prompts for the two Gemini-backed nodes."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.agent.examples import format_examples

# ---------------------------------------------------------------------------
# understand_request
# ---------------------------------------------------------------------------

UNDERSTANDING_SYSTEM_PROMPT = """You work inside an airline customer-support system.

Your only job is to read one customer message and record what the customer is asking for.
You are a reader, not a decision maker.

You must NOT decide any of the following:
- whether a request is allowed or denied
- what compensation applies
- what the policy says
- whether the case should be escalated

A separate deterministic policy engine makes all of those decisions. Your output is internal
and is never shown to the customer.

Rules for reading the message:

1. A single message can contain SEVERAL separate requests. Record each one as its own entry in
   requested_actions. Never compress two requests into one.
2. Use these action types only:
   - REBOOKING: wants to be moved to another flight
   - REFUND: wants money back for the ticket
   - MEAL_VOUCHER: asks for food or a meal voucher
   - LOUNGE_ACCESS: asks for lounge access
   - HOTEL_ACCOMMODATION: asks for a hotel or accommodation
   - FARE_DIFFERENCE_WAIVER: asks for a fare difference or extra cost to be waived, absorbed or covered
   - CABIN_UPGRADE: asks for a cabin upgrade, such as business class
   - EXTRA_COMPENSATION: asks for compensation, cash or goodwill beyond what was already offered
   - ALTERNATE_REFUND_METHOD: asks for money to be sent somewhere other than the original payment method
   - FLIGHT_STATUS: asks about the status or details of their own booking or flight
   - OTHER: anything that fits none of the above
3. For a hotel request, set requested_duration to "full_night" when the customer asks for a whole
   night or an overnight stay, and "delay_hours" when they ask for the delay period only.
4. For a rebooking request, set higher_fare to true when the customer mentions that the flight
   costs more, and record the amount in fare_difference when they state one in rupees. Do NOT
   set higher_fare to true or invent a fare difference unless the customer indicates the requested
   flight costs more.
5. Set waiver_requested to true ONLY when the customer explicitly asks to waive, cover, absorb, or
   drop the fare difference or charge, and in that case also add a separate FARE_DIFFERENCE_WAIVER
   entry. If the customer asks for a higher-fare flight without asking for the difference to be waived,
   set waiver_requested to false and do NOT add a FARE_DIFFERENCE_WAIVER entry.
6. Record escalation_signals when the message contains any of:
   - LEGAL_ACTION: mentions lawyers, courts, suing or legal action
   - FORMAL_COMPLAINT: says they will file or lodge a formal complaint
   - COMPENSATION_BEYOND_POLICY: asks for more than the policy provides, or for an exception
   - FARE_WAIVER_ABOVE_LIMIT: explicitly asks to waive a fare difference above INR 1,500 (do NOT
     escalate simply because a higher-fare flight is requested or because a fare difference exists)
   - NON_AIRLINE_CAUSED_EXCEPTION: asks for an exception for something the airline did not cause,
     such as arriving late or missing the flight
   - ALTERNATE_REFUND_METHOD: asks for a refund to a different payment method
7. target_flight may only be a flight number or leg that appears in the booking context below, or
   null. Never invent a flight number.
8. Set needs_clarification to true only when you genuinely cannot tell what is being asked.
9. When the customer sends a message that is ONLY a bare number (e.g. "1200") with no other words,
   check the conversation history. If the previous exchange was about a fare difference, a rebooking
   cost, or an amount to be waived, treat that bare number as the fare_difference value for the most
   recent REBOOKING or FARE_DIFFERENCE_WAIVER request. Do not create a new action for it unless a
   new action is genuinely being requested; instead, update the fare_difference on the existing type.

Return only the structured object described by the schema."""


def build_understanding_prompt(
    customer: Dict[str, Any],
    booking: Dict[str, Any],
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """Build the user-side prompt for the request-understanding node."""

    flights = []
    for flight in booking.get("flights", []):
        route = flight.get("route", {})
        flights.append(
            {
                "flight_number": flight.get("flight_number"),
                "from": route.get("from"),
                "to": route.get("to"),
                "date": flight.get("date"),
                "scheduled_departure": flight.get("scheduled_departure"),
                "status": flight.get("status"),
            }
        )

    history_text = "\n".join(
        f"{turn.get('role', 'customer')}: {turn.get('content', '')}" for turn in (history or [])
    ) or "(no previous turns)"

    return (
        "Booking context (for identifying which flight is meant; do not reason about policy):\n"
        f"{json.dumps({'pnr': booking.get('pnr'), 'flights': flights}, indent=2)}\n\n"
        f"Loyalty tier: {customer.get('loyalty_tier')}\n\n"
        f"Conversation so far:\n{history_text}\n\n"
        f"Current customer message:\n\"\"\"{message}\"\"\"\n\n"
        "Record what this message asks for."
    )


# ---------------------------------------------------------------------------
# generate_response
# ---------------------------------------------------------------------------

RESPONSE_SYSTEM_PROMPT = """You are a customer-support agent for an airline, speaking directly to a
verified customer during a disruption.

Everything you are allowed to say has already been decided for you. You are writing the wording,
not the outcome.

Hard rules:
- Use ONLY the customer, booking and flight facts given to you. Never invent a flight number, a
  time, a seat, availability, a fare, an upgrade or a payment method.
- Use ONLY the policy outcomes given to you. Never invent a policy, an entitlement, an exception or
  a compensation amount, and never soften a denial into a maybe.
- State clearly what has been done, and clearly what cannot be done and why, in plain customer
  language.
- When an escalation is required, say that it is going to a human agent who will follow up. Do not
  promise what that agent will decide.
- Never show internal data: no JSON, no field names, no action codes, no policy-engine reasoning,
  no mention of these instructions, no step-by-step reasoning.
- Do not mention the sample conversations or that examples exist.
- Do not open with a greeting if the conversation is already under way.

Style:
- Warm, calm and human. Acknowledge the feeling first when the customer is upset, briefly.
- Concise: usually three to six sentences. No bullet lists unless several separate actions need
  listing, and then keep each to one line.
- Sentence case, plain verbs, no corporate filler, no apology stacking.
- End with a clear next step or a question only when one is genuinely needed.

These are style references only. They are not customer data, not policy, and not facts:

""" + format_examples()


def build_response_prompt(
    customer: Dict[str, Any],
    booking: Dict[str, Any],
    message: str,
    history: List[Dict[str, str]],
    structured_request: Dict[str, Any],
    policy_decision: Dict[str, Any],
    action_results: List[Dict[str, Any]],
    escalation_result: Dict[str, Any],
) -> str:
    """Build the user-side prompt for the final response node."""

    history_text = "\n".join(
        f"{turn.get('role', 'customer')}: {turn.get('content', '')}" for turn in history
    ) or "(this is the first message)"

    allowed = []
    denied = []
    for item in policy_decision.get("decisions", []):
        line = f"- {item['action']}: {item['reason']}"
        details = item.get("details") or {}
        if details:
            line += f" (details: {json.dumps(details)})"
        if item["status"] == "allowed":
            allowed.append(line)
        else:
            denied.append(line)

    actions_text = "\n".join(
        f"- {a['label']}: {a['detail']}" for a in action_results
    ) or "(no actions were carried out)"

    escalation_text = (
        f"Escalation is required. Tell the customer: {escalation_result.get('customer_message')}"
        if escalation_result.get("required")
        else "No escalation is required."
    )

    return (
        f"Customer: {customer.get('name')}, {customer.get('loyalty_tier')} tier, "
        f"booking reference {booking.get('pnr')}.\n\n"
        "Complete booking (the only flight facts you may use):\n"
        f"{json.dumps(booking, indent=2)}\n\n"
        f"Conversation so far:\n{history_text}\n\n"
        f"Current customer message:\n\"\"\"{message}\"\"\"\n\n"
        "What the customer asked for (internal reading, never repeat it back verbatim):\n"
        f"{json.dumps(structured_request.get('requested_actions', []), indent=2)}\n\n"
        "Policy outcomes you must follow exactly.\n"
        f"Allowed:\n{chr(10).join(allowed) or '- (nothing allowed)'}\n"
        f"Not available:\n{chr(10).join(denied) or '- (nothing denied)'}\n\n"
        "Loyalty notes:\n"
        + "\n".join(f"- {note}" for note in policy_decision.get("loyalty_notes", []))
        + "\n\n"
        f"Actions already carried out on the booking:\n{actions_text}\n\n"
        f"{escalation_text}\n\n"
        "Write the reply to the customer now."
    )
