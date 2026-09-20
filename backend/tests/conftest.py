"""Shared pytest fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# The suite exercises the deterministic path: no API key, no network calls.
os.environ.pop("GEMINI_API_KEY", None)

from app.api import auth as auth_api  # noqa: E402
from app.api import chat as chat_api  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture()
def client() -> TestClient:
    auth_api.clear_sessions()
    chat_api.clear_history()
    with TestClient(create_app()) as test_client:
        yield test_client
    auth_api.clear_sessions()
    chat_api.clear_history()


@pytest.fixture()
def priya_session(client: TestClient) -> dict:
    response = client.post(
        "/api/auth/verify", json={"pnr": "SK4821X", "email": "priya.nair@example.com"}
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture()
def arvind_session(client: TestClient) -> dict:
    response = client.post(
        "/api/auth/verify", json={"pnr": "TR1190B", "email": "arvind.kulkarni@example.com"}
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture()
def meher_session(client: TestClient) -> dict:
    response = client.post(
        "/api/auth/verify", json={"pnr": "WL7742", "email": "meher.kaur@example.com"}
    )
    assert response.status_code == 200
    return response.json()
