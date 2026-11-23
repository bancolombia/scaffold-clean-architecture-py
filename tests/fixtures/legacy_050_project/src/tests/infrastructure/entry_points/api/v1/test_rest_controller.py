"""Tests for legacy-fixture REST API health endpoint."""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from legacy_fixture.application.app import create_app


@pytest.fixture()
def client() -> TestClient:
    """TestClient fixture wired to the FastAPI application.

    Add DI overrides here before constructing TestClient, e.g.:
        app = create_app()
        app.state.container.my_service.override(MockService())
    """
    return TestClient(create_app())


def test_health_returns_200(client: TestClient) -> None:
    """GET /v1/health must return HTTP 200."""
    response = client.get("/v1/health")
    assert response.status_code == 200


def test_health_returns_online_status(client: TestClient) -> None:
    """GET /v1/health body must contain a status key."""
    response = client.get("/v1/health")
    assert response.json().get("status") is not None


# ---------------------------------------------------------------------------
# Add your custom endpoint tests below this line
# ---------------------------------------------------------------------------


def test_get_book_returns_book() -> None:
    """GET /v1/books/{id} resolves the use case through DI."""
    with TestClient(create_app()) as client:
        response = client.get("/v1/books/1")
    assert response.status_code == 200
    assert response.json()["title"] == "Clean Architecture"


def test_get_book_returns_404_for_unknown_id() -> None:
    with TestClient(create_app()) as client:
        assert client.get("/v1/books/missing").status_code == 404
