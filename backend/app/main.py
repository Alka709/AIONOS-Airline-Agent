"""FastAPI application for the Customer-Facing Resolution Agent."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, bookings, chat, health

load_dotenv()

APP_TITLE = "AIONOS Customer-Facing Resolution Agent"
APP_DESCRIPTION = (
    "Airline disruption support agent. PNR and email verification, a deterministic "
    "policy engine, and a LangGraph workflow over Gemini."
)


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    return origins or ["*"]


def create_app() -> FastAPI:
    application = FastAPI(title=APP_TITLE, description=APP_DESCRIPTION, version="1.0.0")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health.router)
    application.include_router(auth.router)
    application.include_router(chat.router)
    application.include_router(bookings.router)
    return application


app = create_app()


@app.get("/")
def root() -> dict:
    return {"service": APP_TITLE, "docs": "/docs", "health": "/health"}
