"""PNR + email verification.

A customer cannot reach the chat agent without passing through this endpoint.
Verification failures are deliberately indistinguishable from one another so the
response never reveals whether a PNR or an email exists on its own.
"""

from __future__ import annotations

import secrets
import time
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import VerifyRequest, VerifyResponse
from app.services import data_service

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_TTL_SECONDS = 60 * 60 * 4

# In-memory session registry. A prototype store: no database in this assignment.
_SESSIONS: Dict[str, Dict[str, float | str]] = {}

VERIFICATION_ERROR = (
    "We couldn't match that booking reference and email address. "
    "Please check both and try again."
)


def create_session(pnr: str) -> str:
    token = secrets.token_urlsafe(24)
    _SESSIONS[token] = {"pnr": data_service.normalise_pnr(pnr), "created_at": time.time()}
    return token


def resolve_session(token: Optional[str]) -> Optional[str]:
    """Return the PNR for a live token, or None."""
    if not token:
        return None
    session = _SESSIONS.get(token)
    if not session:
        return None
    if time.time() - float(session["created_at"]) > SESSION_TTL_SECONDS:
        _SESSIONS.pop(token, None)
        return None
    return str(session["pnr"])


def has_verified_session(pnr: str) -> bool:
    """True when this PNR has at least one live verified session."""
    target = data_service.normalise_pnr(pnr)
    now = time.time()
    expired = [t for t, s in _SESSIONS.items() if now - float(s["created_at"]) > SESSION_TTL_SECONDS]
    for token in expired:
        _SESSIONS.pop(token, None)
    return any(s["pnr"] == target for s in _SESSIONS.values())


def clear_sessions() -> None:
    _SESSIONS.clear()


@router.post("/verify", response_model=VerifyResponse)
def verify(payload: VerifyRequest) -> VerifyResponse:
    customer = data_service.verify_credentials(payload.pnr, payload.email)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=VERIFICATION_ERROR)

    pnr = data_service.normalise_pnr(payload.pnr)
    booking = data_service.get_booking(pnr)
    if booking is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=VERIFICATION_ERROR)

    return VerifyResponse(
        verified=True,
        session_token=create_session(pnr),
        customer=customer,
        booking=booking,
    )
