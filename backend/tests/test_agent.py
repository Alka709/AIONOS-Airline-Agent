"""The LangGraph workflow end to end (deterministic path, no network)."""

from __future__ import annotations

from app.agent.graph import build_graph, run_agent
from app.agent.nodes import fallback_understand
from app.services import data_service
from app.services.policy_engine import ActionType, EscalationSignal


def run(pnr: str, message: str):
    context = data_service.build_customer_context(pnr)
    return run_agent(pnr, context["customer"], context["booking"], message)


def test_graph_compiles_with_the_four_nodes():
    compiled = build_graph()
    nodes = set(compiled.get_graph().nodes)
    for name in ("understand_request", "policy_evaluation", "action_or_escalation", "generate_response"):
        assert name in nodes


def test_state_carries_every_stage():
    state = run("TR1190B", "My flight is delayed and I am stuck here.")
    for key in (
        "structured_request",
        "policy_decision",
        "action_results",
        "escalation_result",
        "final_response",
    ):
        assert key in state
    assert state["final_response"].strip()


def test_reader_extracts_multiple_actions_from_one_message():
    booking = data_service.get_booking("WL7742")
    structured = fallback_understand(
        "I want a full night hotel and I also want another flight that costs ₹2,000 more.",
        booking,
    )
    types = [a.action_type for a in structured.requested_actions]
    assert ActionType.HOTEL_ACCOMMODATION in types
    assert ActionType.REBOOKING in types
    hotel = next(a for a in structured.requested_actions if a.action_type == ActionType.HOTEL_ACCOMMODATION)
    assert hotel.requested_duration == "full_night"
    rebooking = next(a for a in structured.requested_actions if a.action_type == ActionType.REBOOKING)
    assert rebooking.higher_fare is True
    assert rebooking.fare_difference == 2000


def test_reader_maps_simple_phrases():
    booking = data_service.get_booking("SK4821X")
    assert ActionType.REFUND in [a.action_type for a in fallback_understand("I want my money back.", booking).requested_actions]
    assert ActionType.HOTEL_ACCOMMODATION in [a.action_type for a in fallback_understand("Give me a hotel.", booking).requested_actions]
    assert ActionType.REBOOKING in [a.action_type for a in fallback_understand("Put me on another flight.", booking).requested_actions]
    assert ActionType.FLIGHT_STATUS in [a.action_type for a in fallback_understand("Is my return still okay?", booking).requested_actions]


def test_reader_detects_escalation_signals():
    booking = data_service.get_booking("SK4821X")
    assert EscalationSignal.LEGAL_ACTION in fallback_understand("I am going to take legal action.", booking).escalation_signals
    assert EscalationSignal.FORMAL_COMPLAINT in fallback_understand("I will file a formal complaint.", booking).escalation_signals


def test_executor_never_runs_a_denied_action():
    state = run("TR1190B", "Give me a hotel for tonight.")
    executed = {a["action"] for a in state["action_results"]}
    assert ActionType.HOTEL_ACCOMMODATION not in executed
    assert ActionType.MEAL_VOUCHER in executed
    assert ActionType.LOUNGE_ACCESS in executed


def test_response_never_leaks_internal_structures(client, priya_session):
    response = client.post(
        "/api/chat",
        json={
            "pnr": "SK4821X",
            "message": "I want a refund and a free business class upgrade.",
            "session_token": priya_session["session_token"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"message", "actions", "escalation"}
    lowered = body["message"].lower()
    for leak in ("action_type", "policy_decision", "structured_request", "escalation_signals", "json", "prompt"):
        assert leak not in lowered


def test_conversation_history_is_kept_per_booking(client, priya_session):
    token = priya_session["session_token"]
    client.post("/api/chat", json={"pnr": "SK4821X", "message": "Is my return still fine?", "session_token": token})
    client.post("/api/chat", json={"pnr": "SK4821X", "message": "And what about the refund?", "session_token": token})
    from app.api.chat import get_history

    history = get_history("SK4821X")
    assert len(history) == 4
    assert history[0]["role"] == "customer"


def test_bookings_endpoint_returns_the_complete_booking(client, priya_session):
    response = client.get(f"/api/bookings/SK4821X?session_token={priya_session['session_token']}")
    assert response.status_code == 200
    flights = response.json()["booking"]["flights"]
    assert len(flights) == 2
    assert flights[1]["flight_number"] is None


def test_health_endpoint(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["details"]["customers_loaded"] == 3
