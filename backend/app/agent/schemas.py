"""Pydantic schemas for structured LLM output.

These structures stay internal. They are never shown to the customer.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

ActionTypeLiteral = Literal[
    "REBOOKING",
    "REFUND",
    "MEAL_VOUCHER",
    "LOUNGE_ACCESS",
    "HOTEL_ACCOMMODATION",
    "FARE_DIFFERENCE_WAIVER",
    "CABIN_UPGRADE",
    "EXTRA_COMPENSATION",
    "ALTERNATE_REFUND_METHOD",
    "FLIGHT_STATUS",
    "OTHER",
]

EscalationSignalLiteral = Literal[
    "LEGAL_ACTION",
    "FORMAL_COMPLAINT",
    "COMPENSATION_BEYOND_POLICY",
    "FARE_WAIVER_ABOVE_LIMIT",
    "NON_AIRLINE_CAUSED_EXCEPTION",
    "ALTERNATE_REFUND_METHOD",
]

SentimentLiteral = Literal["calm", "neutral", "frustrated", "angry", "distressed"]


class RequestedAction(BaseModel):
    """One thing the customer is asking for. A message may contain several."""

    action_type: ActionTypeLiteral = Field(
        description="The kind of request the customer is making."
    )
    target_flight: Optional[str] = Field(
        default=None,
        description="Flight number or leg the request refers to, if the customer named one.",
    )
    requested_duration: Optional[str] = Field(
        default=None,
        description="For hotel requests: 'full_night' if the customer asked for a whole night, 'delay_hours' if they asked for the delay period, otherwise null.",
    )
    higher_fare: bool = Field(
        default=False,
        description="True if the customer is asking to move to a flight that costs more.",
    )
    fare_difference: Optional[float] = Field(
        default=None,
        description="Fare difference in INR if the customer stated an amount.",
    )
    waiver_requested: bool = Field(
        default=False,
        description="True if the customer asked for a charge or fare difference to be waived.",
    )
    alternate_payment_method: bool = Field(
        default=False,
        description="True if the customer asked for money to go somewhere other than the original payment method.",
    )
    notes: Optional[str] = Field(
        default=None, description="Short paraphrase of this part of the request."
    )


class StructuredRequest(BaseModel):
    """Internal interpretation of the customer's message.

    This schema records only what the customer asked for. It carries no
    judgement about whether any of it is permitted: that belongs to the
    deterministic policy engine.
    """

    primary_purpose: str = Field(
        description="One short sentence describing what the customer wants overall."
    )
    target_flight: Optional[str] = Field(
        default=None,
        description="Flight number or leg the message is about, if identifiable.",
    )
    requested_actions: List[RequestedAction] = Field(
        default_factory=list,
        description="Every distinct request in the message, one entry each.",
    )
    relevant_details: List[str] = Field(
        default_factory=list,
        description="Facts the customer supplied that matter for handling the request.",
    )
    customer_sentiment: SentimentLiteral = Field(
        default="neutral", description="How the customer sounds."
    )
    escalation_signals: List[EscalationSignalLiteral] = Field(
        default_factory=list,
        description="Signals present in the message, such as a threat of legal action or a formal complaint.",
    )
    needs_clarification: bool = Field(
        default=False,
        description="True if the message is too ambiguous to act on without asking a question.",
    )
    clarifying_question: Optional[str] = Field(
        default=None, description="The question to ask when clarification is needed."
    )
