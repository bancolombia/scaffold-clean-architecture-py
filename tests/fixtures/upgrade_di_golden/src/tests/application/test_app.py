"""Tests for application factory — legacy-fixture."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from legacy_fixture.application.app import create_app


def test_create_app_returns_fastapi_instance() -> None:
    app = create_app()
    assert isinstance(app, FastAPI)


def test_create_app_has_router_included() -> None:
    client = TestClient(create_app())
    assert client.get("/v1/health").status_code == 200


def test_create_app_registers_exception_handlers() -> None:
    app = create_app()
    assert app.exception_handlers
