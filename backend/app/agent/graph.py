"""LangGraph construction and the entry point used by the API."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional

from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    action_or_escalation,
    generate_response,
    policy_evaluation,
    understand_request,
)
from app.agent.state import AgentState, new_state


def build_graph():
    """START -> understand_request -> policy_evaluation -> action_or_escalation -> generate_response -> END"""

    graph = StateGraph(AgentState)

    graph.add_node("understand_request", understand_request)
    graph.add_node("policy_evaluation", policy_evaluation)
    graph.add_node("action_or_escalation", action_or_escalation)
    graph.add_node("generate_response", generate_response)

    graph.add_edge(START, "understand_request")
    graph.add_edge("understand_request", "policy_evaluation")
    graph.add_edge("policy_evaluation", "action_or_escalation")
    graph.add_edge("action_or_escalation", "generate_response")
    graph.add_edge("generate_response", END)

    return graph.compile()


@lru_cache(maxsize=1)
def get_compiled_graph():
    return build_graph()


def run_agent(
    pnr: str,
    customer: Dict[str, Any],
    booking: Dict[str, Any],
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Run the full graph for one customer message and return the final state."""

    state = new_state(pnr=pnr, customer=customer, booking=booking, message=message, history=history)
    return dict(get_compiled_graph().invoke(state))
