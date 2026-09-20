"""Liveness endpoint."""

from __future__ import annotations

import os

from fastapi import APIRouter

from app.models.schemas import HealthResponse
from app.services import data_service

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="aionos-resolution-agent",
        gemini_configured=bool((os.getenv("GEMINI_API_KEY") or "").strip()),
        details={
            "customers_loaded": len(data_service.load_customers()),
            "bookings_loaded": len(data_service.load_bookings()),
        },
    )
