"""Tests for GET /healthz and the request-id middleware, exercised through
the real app (lifespan included) since neither depends on network access -
gateway construction only needs Settings, never an actual API call."""

from fastapi.testclient import TestClient

from investment_agent.main import app


def test_healthz_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthz_response_has_request_id_header() -> None:
    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.headers["X-Request-ID"]


def test_each_request_gets_a_distinct_request_id() -> None:
    with TestClient(app) as client:
        first = client.get("/healthz")
        second = client.get("/healthz")

    assert first.headers["X-Request-ID"] != second.headers["X-Request-ID"]
