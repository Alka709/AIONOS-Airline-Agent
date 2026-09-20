"""Loading and lookup of the supplied customer, booking and policy data.

This module is the only place that reads the JSON source files. Nothing in the
application invents customer, booking or flight data: every value returned here
comes from backend/app/data/*.json.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

CUSTOMERS_FILE = DATA_DIR / "customers.json"
BOOKINGS_FILE = DATA_DIR / "bookings.json"
POLICIES_FILE = DATA_DIR / "policies.json"


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_customers() -> List[Dict[str, Any]]:
    """Return the three supplied customers."""
    return _read_json(CUSTOMERS_FILE)


@lru_cache(maxsize=1)
def load_bookings() -> Dict[str, Any]:
    """Return every booking, keyed by PNR."""
    return _read_json(BOOKINGS_FILE)


@lru_cache(maxsize=1)
def load_policies() -> Dict[str, Any]:
    """Return the machine-readable form of the supplied service rules."""
    return _read_json(POLICIES_FILE)


def normalise_pnr(pnr: Optional[str]) -> str:
    return (pnr or "").strip().upper()


def normalise_email(email: Optional[str]) -> str:
    return (email or "").strip().lower()


def find_customer_by_pnr(pnr: str) -> Optional[Dict[str, Any]]:
    """Find the customer whose booking reference matches the PNR."""
    target = normalise_pnr(pnr)
    for customer in load_customers():
        if normalise_pnr(customer["booking_reference"]) == target:
            return customer
    return None


def get_booking(pnr: str) -> Optional[Dict[str, Any]]:
    """Return the complete booking (all legs) for a PNR."""
    return load_bookings().get(normalise_pnr(pnr))


def verify_credentials(pnr: str, email: str) -> Optional[Dict[str, Any]]:
    """Return the customer only when the PNR exists AND the email matches it.

    Returns ``None`` for every failure mode so the caller cannot tell whether
    the PNR or the email was the part that did not match.
    """
    customer = find_customer_by_pnr(pnr)
    if customer is None:
        return None
    if normalise_email(customer["contact"]["email"]) != normalise_email(email):
        return None
    if get_booking(pnr) is None:
        return None
    return customer


def get_flights(pnr: str) -> List[Dict[str, Any]]:
    booking = get_booking(pnr)
    return list(booking["flights"]) if booking else []


def find_flight_by_number(pnr: str, flight_number: Optional[str]) -> Optional[Dict[str, Any]]:
    if not flight_number:
        return None
    wanted = flight_number.strip().upper().replace(" ", "")
    for flight in get_flights(pnr):
        number = flight.get("flight_number")
        if number and number.upper().replace(" ", "") == wanted:
            return flight
    return None


def get_disrupted_flights(pnr: str) -> List[Dict[str, Any]]:
    return [f for f in get_flights(pnr) if f.get("status") in {"cancelled", "delayed"}]


def resolve_target_flight(pnr: str, hint: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Pick the flight a message is about, using only flights in this booking.

    Order of preference: an explicit flight number, then a route/leg hint
    ("return", a city name), then the disrupted flight, then the first leg.
    """
    flights = get_flights(pnr)
    if not flights:
        return None

    if hint:
        by_number = find_flight_by_number(pnr, hint)
        if by_number:
            return by_number

        text = hint.strip().lower()
        for flight in flights:
            number = (flight.get("flight_number") or "").lower()
            if number and number in text:
                return flight

        outbound = flights[0]
        if any(word in text for word in ("return", "inbound", "coming back", "way back")):
            for flight in flights[1:]:
                return flight
        if any(word in text for word in ("outbound", "first leg", "departure leg")):
            return outbound
        for flight in flights:
            route = flight.get("route", {})
            origin = str(route.get("from", "")).lower()
            destination = str(route.get("to", "")).lower()
            if origin and destination and origin in text and destination in text:
                return flight

    disrupted = get_disrupted_flights(pnr)
    if disrupted:
        return disrupted[0]
    return flights[0]


def build_customer_context(pnr: str) -> Optional[Dict[str, Any]]:
    """Return the full verified context: customer + complete booking."""
    customer = find_customer_by_pnr(pnr)
    booking = get_booking(pnr)
    if customer is None or booking is None:
        return None
    return {"customer": customer, "booking": booking}


def clear_caches() -> None:
    """Drop cached JSON (used by tests that patch the data files)."""
    load_customers.cache_clear()
    load_bookings.cache_clear()
    load_policies.cache_clear()
