"""CORS regression tests for the C13 boundary.

The browser web app is served from a different origin than the API and every
data request carries custom X-Wellbe-* headers, so requests are preflighted.
These tests lock in that allowed origins get the proper CORS response headers
(without which the browser blocks all data fetches).
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from wellbe_api.main import app

_ALLOWED_ORIGIN = "http://app.localhost"


def _client() -> TestClient:
    return TestClient(app)


def test_preflight_allows_known_web_origin() -> None:
    resp = _client().options(
        "/v1/threads",
        headers={
            "Origin": _ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-wellbe-actor-id,x-correlation-id",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == _ALLOWED_ORIGIN


def test_simple_request_echoes_allow_origin() -> None:
    resp = _client().get("/health", headers={"Origin": _ALLOWED_ORIGIN})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == _ALLOWED_ORIGIN


def test_unknown_origin_is_not_allowed() -> None:
    resp = _client().get("/health", headers={"Origin": "http://evil.example"})
    assert resp.status_code == 200
    assert "access-control-allow-origin" not in resp.headers
