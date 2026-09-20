"""The deterministic policy engine, rule by rule."""

from __future__ import annotations

import pytest

from app.services import data_service
from app.services.policy_engine import (
    STATUS_ALLOWED,
    STATUS_DENIED,
    STATUS_ESCALATE,
    ActionType,
    EscalationSignal,
    delay_entitlements,
    evaluate,
)


def context(pnr: str, hint: str | None = None):
    customer = data_service.find_customer_by_pnr(pnr)
    booking = data_service.get_booking(pnr)
    flight = data_service.resolve_target_flight(pnr, hint)
    return customer, booking, flight


def status_of(decision, action: str):
    for item in decision.decisions:
        if item.action == action:
            return item.status
    return None


# -- Delay tiers ------------------------------------------------------------

@pytest.mark.parametrize(
    "hours,expected",
    [
        (1, [ActionType.MEAL_VOUCHER]),
        (2.5, [ActionType.MEAL_VOUCHER]),
        (3, [ActionType.MEAL_VOUCHER, ActionType.LOUNGE_ACCESS]),
        (4, [ActionType.MEAL_VOUCHER, ActionType.LOUNGE_ACCESS]),
        (5, [ActionType.MEAL_VOUCHER, ActionType.LOUNGE_ACCESS, ActionType.HOTEL_ACCOMMODATION]),
        (6, [ActionType.MEAL_VOUCHER, ActionType.LOUNGE_ACCESS, ActionType.HOTEL_ACCOMMODATION]),
    ],
)
def test_delay_entitlement_thresholds(hours, expected):
    assert delay_entitlements(hours) == expected


def test_delay_under_three_hours_gives_only_a_meal_voucher():
    assert delay_entitlements(2) == [ActionType.MEAL_VOUCHER]


def test_delay_over_three_hours_gives_meal_and_lounge():
    customer, booking, flight = context("TR1190B")
    decision = evaluate(customer, booking, flight, [])
    assert ActionType.MEAL_VOUCHER in decision.allowed_actions
    assert ActionType.LOUNGE_ACCESS in decision.allowed_actions
    assert ActionType.HOTEL_ACCOMMODATION not in decision.allowed_actions


def test_delay_over_five_hours_adds_hotel_for_delayed_hours_only():
    customer, booking, flight = context("WL7742")
    decision = evaluate(customer, booking, flight, [])
    assert ActionType.HOTEL_ACCOMMODATION in decision.allowed_actions
    hotel = next(d for d in decision.decisions if d.action == ActionType.HOTEL_ACCOMMODATION)
    assert hotel.details["covers"] == "delayed hours only"
    assert hotel.details["covers_full_night"] is False


# -- Cancellation and refund ------------------------------------------------

def test_cancellation_offers_rebooking_or_refund():
    customer, booking, flight = context("SK4821X")
    decision = evaluate(customer, booking, flight, [])
    options = next(d for d in decision.decisions if d.action == "CANCELLATION_OPTIONS")
    assert options.status == STATUS_ALLOWED
    assert options.details["options"] == ["REBOOKING", "REFUND"]


def test_refund_allowed_for_airline_caused_cancellation():
    customer, booking, flight = context("SK4821X")
    decision = evaluate(customer, booking, flight, [{"action_type": ActionType.REFUND}])
    refund = next(d for d in decision.decisions if d.action == ActionType.REFUND)
    assert refund.status == STATUS_ALLOWED
    assert refund.details["processing_time"] == "within 7 business days"
    assert refund.details["destination"] == "original payment method"
    assert decision.escalation_required is False


def test_refund_denied_for_a_delayed_flight():
    customer, booking, flight = context("TR1190B")
    decision = evaluate(customer, booking, flight, [{"action_type": ActionType.REFUND}])
    assert status_of(decision, ActionType.REFUND) == STATUS_DENIED


def test_refund_to_a_different_payment_method_escalates():
    customer, booking, flight = context("SK4821X")
    decision = evaluate(
        customer, booking, flight,
        [{"action_type": ActionType.REFUND, "alternate_payment_method": True}],
    )
    assert decision.escalation_required is True
    assert EscalationSignal.ALTERNATE_REFUND_METHOD in decision.escalation_signals


# -- Rebooking and fare difference -----------------------------------------

def test_free_rebooking_for_airline_caused_disruption():
    customer, booking, flight = context("SK4821X")
    decision = evaluate(customer, booking, flight, [{"action_type": ActionType.REBOOKING}])
    rebooking = next(d for d in decision.decisions if d.action == ActionType.REBOOKING)
    assert rebooking.status == STATUS_ALLOWED
    assert rebooking.details["charge"] == 0
    assert rebooking.details["window_hours"] == 24


def test_gold_customer_gets_priority_rebooking():
    customer, booking, flight = context("SK4821X")
    decision = evaluate(customer, booking, flight, [{"action_type": ActionType.REBOOKING}])
    rebooking = next(d for d in decision.decisions if d.action == ActionType.REBOOKING)
    assert rebooking.details["priority_rebooking"] is True
    assert any("no additional compensation" in note for note in decision.loyalty_notes)


def test_platinum_customer_gets_priority_rebooking():
    customer, booking, flight = context("WL7742")
    decision = evaluate(customer, booking, flight, [{"action_type": ActionType.REBOOKING}])
    rebooking = next(d for d in decision.decisions if d.action == ActionType.REBOOKING)
    assert rebooking.details["priority_rebooking"] is True


def test_higher_fare_rebooking_charges_the_fare_difference():
    customer, booking, flight = context("WL7742")
    decision = evaluate(
        customer, booking, flight,
        [{"action_type": ActionType.REBOOKING, "higher_fare": True, "fare_difference": 2000}],
    )
    rebooking = next(d for d in decision.decisions if d.action == ActionType.REBOOKING)
    assert rebooking.status == STATUS_ALLOWED
    assert rebooking.details["fare_difference_inr"] == 2000
    assert rebooking.details["charge"] == "fare difference payable by the customer"


def test_fare_waiver_of_two_thousand_escalates():
    customer, booking, flight = context("WL7742")
    decision = evaluate(
        customer, booking, flight,
        [{"action_type": ActionType.FARE_DIFFERENCE_WAIVER, "fare_difference": 2000}],
    )
    assert status_of(decision, ActionType.FARE_DIFFERENCE_WAIVER) == STATUS_ESCALATE
    assert EscalationSignal.FARE_WAIVER_ABOVE_LIMIT in decision.escalation_signals
    assert decision.escalation_required is True


def test_fare_waiver_within_the_limit_is_allowed():
    customer, booking, flight = context("WL7742")
    decision = evaluate(
        customer, booking, flight,
        [{"action_type": ActionType.FARE_DIFFERENCE_WAIVER, "fare_difference": 1500}],
    )
    assert status_of(decision, ActionType.FARE_DIFFERENCE_WAIVER) == STATUS_ALLOWED
    assert decision.escalation_required is False


# -- Hotel ------------------------------------------------------------------

def test_hotel_denied_for_a_four_hour_delay():
    customer, booking, flight = context("TR1190B")
    decision = evaluate(customer, booking, flight, [{"action_type": ActionType.HOTEL_ACCOMMODATION}])
    assert status_of(decision, ActionType.HOTEL_ACCOMMODATION) == STATUS_DENIED
    assert decision.escalation_required is False


def test_full_night_hotel_is_denied_even_when_the_delay_qualifies():
    customer, booking, flight = context("WL7742")
    decision = evaluate(
        customer, booking, flight,
        [{"action_type": ActionType.HOTEL_ACCOMMODATION, "requested_duration": "full_night"}],
    )
    assert status_of(decision, ActionType.HOTEL_ACCOMMODATION_FULL_NIGHT) == STATUS_DENIED
    assert status_of(decision, ActionType.HOTEL_ACCOMMODATION) == STATUS_ALLOWED


# -- Escalation conditions --------------------------------------------------

def test_cabin_upgrade_is_never_granted():
    customer, booking, flight = context("SK4821X")
    decision = evaluate(customer, booking, flight, [{"action_type": ActionType.CABIN_UPGRADE}])
    assert status_of(decision, ActionType.CABIN_UPGRADE) == STATUS_ESCALATE
    assert ActionType.CABIN_UPGRADE not in decision.allowed_actions


def test_legal_action_escalates():
    customer, booking, flight = context("SK4821X")
    decision = evaluate(customer, booking, flight, [], [EscalationSignal.LEGAL_ACTION])
    assert decision.escalation_required is True
    assert decision.escalation_reason == "Threat of legal action"


def test_formal_complaint_escalates():
    customer, booking, flight = context("TR1190B")
    decision = evaluate(customer, booking, flight, [], [EscalationSignal.FORMAL_COMPLAINT])
    assert decision.escalation_required is True


def test_non_airline_caused_exception_escalates():
    customer, booking, flight = context("TR1190B")
    decision = evaluate(customer, booking, flight, [], [EscalationSignal.NON_AIRLINE_CAUSED_EXCEPTION])
    assert decision.escalation_required is True


def test_multiple_actions_in_one_message_are_all_evaluated():
    customer, booking, flight = context("WL7742")
    decision = evaluate(
        customer, booking, flight,
        [
            {"action_type": ActionType.HOTEL_ACCOMMODATION, "requested_duration": "full_night"},
            {"action_type": ActionType.REBOOKING, "higher_fare": True, "fare_difference": 2000},
            {"action_type": ActionType.FARE_DIFFERENCE_WAIVER, "fare_difference": 2000},
        ],
    )
    assert status_of(decision, ActionType.HOTEL_ACCOMMODATION) == STATUS_ALLOWED
    assert status_of(decision, ActionType.HOTEL_ACCOMMODATION_FULL_NIGHT) == STATUS_DENIED
    assert status_of(decision, ActionType.REBOOKING) == STATUS_ALLOWED
    assert status_of(decision, ActionType.FARE_DIFFERENCE_WAIVER) == STATUS_ESCALATE


def test_unaffected_return_leg_grants_nothing():
    customer, booking, flight = context("SK4821X", "is my return still fine?")
    decision = evaluate(customer, booking, flight, [{"action_type": ActionType.FLIGHT_STATUS}])
    assert decision.allowed_actions == [ActionType.FLIGHT_STATUS]
    assert decision.entitlements == []
