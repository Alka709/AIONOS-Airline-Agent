"""The supplied data is loaded exactly as given, with nothing added."""

from __future__ import annotations

from app.services import data_service


def test_exactly_three_customers():
    assert len(data_service.load_customers()) == 3


def test_no_customer_id_field_anywhere():
    for customer in data_service.load_customers():
        assert "customer_id" not in customer
        assert "id" not in customer


def test_priya_booking_contains_both_legs():
    booking = data_service.get_booking("SK4821X")
    assert booking is not None
    assert len(booking["flights"]) == 2

    outbound, inbound = booking["flights"]
    assert outbound["flight_number"] == "SK-204"
    assert outbound["route"] == {"from": "Delhi", "to": "Goa"}
    assert outbound["date"] == "2026-09-23"
    assert outbound["scheduled_departure"] == "18:40"
    assert outbound["status"] == "cancelled"
    assert outbound["disruption_reason"] == "operational reasons"

    assert inbound["route"] == {"from": "Goa", "to": "Delhi"}
    assert inbound["date"] == "2026-09-25"
    assert inbound["scheduled_departure"] == "16:20"
    assert inbound["status"] == "unaffected"


def test_priya_return_flight_number_is_not_fabricated():
    booking = data_service.get_booking("SK4821X")
    assert booking["flights"][1]["flight_number"] is None


def test_arvind_flight_matches_the_source():
    flight = data_service.get_booking("TR1190B")["flights"][0]
    assert flight["flight_number"] == "SK-118"
    assert flight["route"] == {"from": "Mumbai", "to": "Bengaluru"}
    assert flight["scheduled_departure"] == "07:10"
    assert flight["status"] == "delayed"
    assert flight["delay_hours"] == 4
    assert flight["new_departure"] == "11:10"


def test_meher_flight_matches_the_source():
    flight = data_service.get_booking("WL7742")["flights"][0]
    assert flight["flight_number"] == "SK-305"
    assert flight["route"] == {"from": "Delhi", "to": "Hyderabad"}
    assert flight["scheduled_departure"] == "14:00"
    assert flight["delay_hours"] == 6
    assert flight["new_departure"] == "20:00"


def test_verify_credentials_requires_both_parts():
    assert data_service.verify_credentials("SK4821X", "priya.nair@example.com") is not None
    assert data_service.verify_credentials("SK4821X", "meher.kaur@example.com") is None
    assert data_service.verify_credentials("NOPE123", "priya.nair@example.com") is None


def test_resolve_target_flight_prefers_the_disrupted_leg():
    flight = data_service.resolve_target_flight("SK4821X", "my flight")
    assert flight["flight_number"] == "SK-204"


def test_resolve_target_flight_finds_the_return_leg():
    flight = data_service.resolve_target_flight("SK4821X", "is my return still fine?")
    assert flight["route"]["from"] == "Goa"
    assert flight["flight_number"] is None
