"""LangGraph state for the resolution agent."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class AgentState(TypedDict, total=False):
    # Verified identity and context
    pnr: str
    customer: Dict[str, Any]
    booking: Dict[str, Any]

    # Conversation
    current_message: str
    conversation_history: List[Dict[str, str]]

    # Node outputs
    target_flight: Optional[Dict[str, Any]]
    structured_request: Dict[str, Any]
    policy_decision: Dict[str, Any]
    action_results: List[Dict[str, Any]]
    escalation_result: Dict[str, Any]
    final_response: str

    # Diagnostics (never returned to the customer)
    llm_available: bool
    trace: List[str]


def new_state(
    pnr: str,
    customer: Dict[str, Any],
    booking: Dict[str, Any],
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> AgentState:
    return AgentState(
        pnr=pnr,
        customer=customer,
        booking=booking,
        current_message=message,
        conversation_history=list(history or []),
        target_flight=None,
        structured_request={},
        policy_decision={},
        action_results=[],
        escalation_result={},
        final_response="",
        llm_available=False,
        trace=[],
    )
