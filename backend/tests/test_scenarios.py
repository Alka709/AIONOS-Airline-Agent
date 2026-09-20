"""The three supplied demo scenarios, end to end through the API."""

from __future__ import annotations

from app.services.policy_engine import ActionType


def send(client, pnr, token, message):
    response = client.post(
        "/api/chat", json={"pnr": pnr, "message": message, "session_token": token}
    )
    assert response.status_code == 200
    return response.json()


# -- Priya: cancellation, refund, and an upgrade that does not exist --------

def test_priya_refund_and_upgrade_request(client, priya_session):
    body = send(
        client,
        "SK4821X",
        priya_session["session_token"],
        "This is outrageous. I want a full cash refund, and a free business class upgrade on my "
        "return flight for the trouble.",
    )

    actions = {a["action"] for a in body["actions"]}
    assert ActionType.REFUND in actions
    assert ActionType.CABIN_UPGRADE not in actions

    refund = next(a for a in body["actions"] if a["action"] == ActionType.REFUND)
    assert "7 business days" in refund["detail"]
    assert "original payment method" in refund["detail"]

    # A cabin upgrade is compensation beyond the supplied policy.
    assert body["escalation"]["required"] is True

    text = body["message"].lower()
    assert "business class" not in text or "cannot" in text or "beyond" in text or "human agent" in text


def test_priya_return_leg_status(client, priya_session):
    body = send(client, "SK4821X", priya_session["session_token"], "Is my return still fine?")
    text = body["message"]
    assert "Goa" in text and "Delhi" in text
    assert "16:20" in text
    assert body["escalation"]["required"] is False
    # No flight number exists for the return leg, so none may appear for it.
    assert "SK-2" not in text.split("Goa")[-1]


def test_priya_gold_tier_gets_priority_not_extra_compensation(client, priya_session):
    body = send(client, "SK4821X", priya_session["session_token"], "Put me on another flight please.")
    rebooking = next(a for a in body["actions"] if a["action"] == ActionType.REBOOKING)
    assert "no extra cost" in rebooking["detail"]
    assert "Priority rebooking" in rebooking["detail"]


# -- Arvind: four-hour delay, hotel requested ------------------------------

def test_arvind_four_hour_delay_hotel_request(client, arvind_session):
    body = send(
        client,
        "TR1190B",
        arvind_session["session_token"],
        "I have a connecting meeting and this delay is ruining it. Give me a hotel.",
    )

    actions = {a["action"] for a in body["actions"]}
    assert ActionType.MEAL_VOUCHER in actions
    assert ActionType.LOUNGE_ACCESS in actions
    assert ActionType.HOTEL_ACCOMMODATION not in actions
    assert body["escalation"]["required"] is False


# -- Meher: six-hour delay, full-night hotel, higher fare, waiver ----------

def test_meher_full_night_hotel_and_fare_waiver(client, meher_session):
    body = send(
        client,
        "WL7742",
        meher_session["session_token"],
        "I want a full night hotel, not just the delay hours. I also want another flight that "
        "costs ₹2,000 more and I want you to waive that difference.",
    )

    actions = {a["action"] for a in body["actions"]}
    assert ActionType.HOTEL_ACCOMMODATION in actions
    assert ActionType.REBOOKING in actions
    assert ActionType.FARE_DIFFERENCE_WAIVER not in actions

    hotel = next(a for a in body["actions"] if a["action"] == ActionType.HOTEL_ACCOMMODATION)
    assert "6" in hotel["detail"]

    assert body["escalation"]["required"] is True
    assert body["escalation"]["ticket_id"]


def test_meher_six_hour_delay_entitlements(client, meher_session):
    body = send(client, "WL7742", meher_session["session_token"], "What am I entitled to for this delay?")
    actions = {a["action"] for a in body["actions"]}
    assert actions >= {
        ActionType.MEAL_VOUCHER,
        ActionType.LOUNGE_ACCESS,
        ActionType.HOTEL_ACCOMMODATION,
    }


# -- Prohibited conversations ---------------------------------------------

def test_legal_action_escalates_through_the_api(client, arvind_session):
    body = send(
        client,
        "TR1190B",
        arvind_session["session_token"],
        "This is unacceptable, I am going to take legal action.",
    )
    assert body["escalation"]["required"] is True
    assert body["escalation"]["reason"]


def test_formal_complaint_escalates_through_the_api(client, meher_session):
    body = send(client, "WL7742", meher_session["session_token"], "I want to file a formal complaint.")
    assert body["escalation"]["required"] is True


def test_refund_to_a_different_card_escalates(client, priya_session):
    body = send(
        client,
        "SK4821X",
        priya_session["session_token"],
        "Refund me, but send it to a different card this time.",
    )
    assert body["escalation"]["required"] is True
