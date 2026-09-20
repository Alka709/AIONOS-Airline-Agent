"""Verification: PNR plus email, and nothing leaks on failure."""

from __future__ import annotations


def test_priya_valid_credentials(client):
    response = client.post(
        "/api/auth/verify", json={"pnr": "SK4821X", "email": "priya.nair@example.com"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["verified"] is True
    assert body["customer"]["name"] == "Priya Nair"
    assert body["customer"]["loyalty_tier"] == "Gold"
    assert body["booking"]["pnr"] == "SK4821X"
    assert body["session_token"]


def test_arvind_valid_credentials(client):
    response = client.post(
        "/api/auth/verify", json={"pnr": "TR1190B", "email": "arvind.kulkarni@example.com"}
    )
    assert response.status_code == 200
    assert response.json()["customer"]["loyalty_tier"] == "Silver"


def test_meher_valid_credentials(client):
    response = client.post(
        "/api/auth/verify", json={"pnr": "WL7742", "email": "meher.kaur@example.com"}
    )
    assert response.status_code == 200
    assert response.json()["customer"]["loyalty_tier"] == "Platinum"


def test_mismatched_pnr_and_email_is_rejected(client):
    response = client.post(
        "/api/auth/verify", json={"pnr": "SK4821X", "email": "arvind.kulkarni@example.com"}
    )
    assert response.status_code == 401
    assert "Priya" not in response.text
    assert "Arvind" not in response.text


def test_unknown_pnr_and_unknown_email_give_the_same_error(client):
    unknown_pnr = client.post(
        "/api/auth/verify", json={"pnr": "ZZ0000Z", "email": "priya.nair@example.com"}
    )
    wrong_email = client.post(
        "/api/auth/verify", json={"pnr": "SK4821X", "email": "nobody@example.com"}
    )
    assert unknown_pnr.status_code == wrong_email.status_code == 401
    assert unknown_pnr.json()["detail"] == wrong_email.json()["detail"]


def test_verification_is_case_insensitive_on_pnr_and_email(client):
    response = client.post(
        "/api/auth/verify", json={"pnr": "sk4821x", "email": "Priya.Nair@Example.com"}
    )
    assert response.status_code == 200


def test_chat_is_unreachable_before_verification(client):
    response = client.post("/api/chat", json={"pnr": "SK4821X", "message": "Where is my flight?"})
    assert response.status_code == 401


def test_booking_endpoint_is_unreachable_before_verification(client):
    assert client.get("/api/bookings/SK4821X").status_code == 401


def test_chat_rejects_a_session_token_for_another_booking(client, priya_session):
    response = client.post(
        "/api/chat",
        json={
            "pnr": "TR1190B",
            "message": "Hello",
            "session_token": priya_session["session_token"],
        },
    )
    assert response.status_code == 401
