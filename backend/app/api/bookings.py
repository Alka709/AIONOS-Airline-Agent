"""Booking retrieval for a verified booking reference."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.api.auth import has_verified_session, resolve_session
from app.models.schemas import BookingResponse
from app.services import data_service

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


@router.get("/{pnr}", response_model=BookingResponse)
def get_booking(pnr: str, session_token: str | None = Query(default=None)) -> BookingResponse:
    normalised = data_service.normalise_pnr(pnr)

    token_pnr = resolve_session(session_token)
    if session_token is not None:
        authorised = token_pnr == normalised
    else:
        authorised = has_verified_session(normalised)

    if not authorised:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please verify your booking reference and email first.",
        )

    booking = data_service.get_booking(normalised)
    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No booking found for that reference."
        )
    return BookingResponse(booking=booking)
