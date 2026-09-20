"""Chat endpoint: runs the LangGraph agent for a verified customer."""

from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, HTTPException, status

from app.agent.graph import run_agent
from app.api.auth import has_verified_session, resolve_session
from app.models.schemas import ActionCard, ChatRequest, ChatResponse, EscalationInfo
from app.services import data_service

router = APIRouter(prefix="/api", tags=["chat"])

MAX_HISTORY_TURNS = 20

# In-memory conversation history per booking reference.
_HISTORY: Dict[str, List[Dict[str, str]]] = {}


def get_history(pnr: str) -> List[Dict[str, str]]:
    return _HISTORY.get(data_service.normalise_pnr(pnr), [])


def clear_history(pnr: str | None = None) -> None:
    if pnr is None:
        _HISTORY.clear()
    else:
        _HISTORY.pop(data_service.normalise_pnr(pnr), None)


def _append(pnr: str, role: str, content: str) -> None:
    key = data_service.normalise_pnr(pnr)
    turns = _HISTORY.setdefault(key, [])
    turns.append({"role": role, "content": content})
    del turns[:-MAX_HISTORY_TURNS]


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    pnr = data_service.normalise_pnr(payload.pnr)

    # The agent is reachable only after PNR + email verification.
    token_pnr = resolve_session(payload.session_token)
    if payload.session_token is not None:
        if token_pnr is None or token_pnr != pnr:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session has expired. Please verify your booking again.",
            )
    elif not has_verified_session(pnr):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please verify your booking reference and email before starting a chat.",
        )

    context = data_service.build_customer_context(pnr)
    if context is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please verify your booking reference and email before starting a chat.",
        )

    history = list(get_history(pnr))
    final_state = run_agent(
        pnr=pnr,
        customer=context["customer"],
        booking=context["booking"],
        message=payload.message,
        history=history,
    )

    reply = final_state.get("final_response", "")
    _append(pnr, "customer", payload.message)
    _append(pnr, "agent", reply)

    escalation = final_state.get("escalation_result", {}) or {}

    # Only the customer-facing surface is returned: no structured request,
    # no policy reasoning, no prompts, no trace.
    return ChatResponse(
        message=reply,
        actions=[ActionCard(**a) for a in final_state.get("action_results", [])],
        escalation=EscalationInfo(
            required=bool(escalation.get("required")),
            reason=escalation.get("customer_message") if escalation.get("required") else None,
            ticket_id=escalation.get("ticket_id"),
        ),
    )
