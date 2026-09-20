"""Pydantic request and response schemas for the HTTP API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# Shared
# --------------------------------------------------------------------------

class Route(BaseModel):
    from_: str = Field(alias="from")
    to: str

    model_config = {"populate_by_name": True}


class Flight(BaseModel):
    flight_number: Optional[str] = None
    route: Route
    date: str
    date_label: Optional[str] = None
    scheduled_departure: str
    status: str
    disruption_reason: Optional[str] = None
    airline_caused: bool = False
    delay_hours: Optional[float] = None
    new_departure: Optional[str] = None


class Booking(BaseModel):
    pnr: str
    flights: List[Flight]


class Contact(BaseModel):
    email: str
    phone: str


class PreviousComplaint(BaseModel):
    type: str
    resolution: str


class TravelHistory(BaseModel):
    flights_last_12_months: int
    prior_complaints: int
    previous_complaint: Optional[PreviousComplaint] = None


class Customer(BaseModel):
    name: str
    loyalty_tier: str
    booking_reference: str
    contact: Contact
    travel_history: TravelHistory


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------

class VerifyRequest(BaseModel):
    pnr: str = Field(min_length=1, description="Booking reference exactly as printed on the ticket")
    email: str = Field(min_length=1, description="Email address held against this booking")


class VerifyResponse(BaseModel):
    verified: bool
    session_token: str
    customer: Customer
    booking: Booking


# --------------------------------------------------------------------------
# Chat
# --------------------------------------------------------------------------

class ChatRequest(BaseModel):
    pnr: str = Field(min_length=1)
    message: str = Field(min_length=1)
    session_token: Optional[str] = None


class ActionCard(BaseModel):
    action: str
    label: str
    status: str
    detail: str
    simulated: bool = True


class EscalationInfo(BaseModel):
    required: bool = False
    reason: Optional[str] = None
    ticket_id: Optional[str] = None


class ChatResponse(BaseModel):
    message: str
    actions: List[ActionCard] = Field(default_factory=list)
    escalation: EscalationInfo = Field(default_factory=EscalationInfo)


# --------------------------------------------------------------------------
# Misc
# --------------------------------------------------------------------------

class BookingResponse(BaseModel):
    booking: Booking


class HealthResponse(BaseModel):
    status: str
    service: str
    gemini_configured: bool
    details: Dict[str, Any] = Field(default_factory=dict)
