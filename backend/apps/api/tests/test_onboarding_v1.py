"""Unit tests for the C13 /v1/onboarding surface (authenticate-first first run).

Covers the identity guard (no resolved identity -> 401), the start draft (pending
state surfaces the four core-consent purposes), the consent gate (finalize without
explicit acceptance -> 422), and the finalize happy path (active state carries the
provisioned personal workspace). OnboardingService + audit are stubbed so these
stay infra-free unit tests; SQL-level idempotency is covered by the e2e suite.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from wellbe_api.deps import get_session
from wellbe_api.main import app
from wellbe_api.routers import onboarding_v1
from wellbe_c1_consent.onboarding import OnboardingState

_ISSUER = "dev-local"
_SUBJECT = "user-abc"
_AUTH = {"X-Wellbe-Issuer": _ISSUER, "X-Wellbe-Subject": _SUBJECT}
_ACCOUNT_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
_PATIENT_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
_WORKSPACE_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")


class _FakeSession:
    async def commit(self) -> None: ...


def _override_session() -> None:
    async def _fake_session() -> AsyncGenerator[_FakeSession]:
        yield _FakeSession()

    app.dependency_overrides[get_session] = _fake_session


def _state(status: str, *, workspace: bool) -> OnboardingState:
    return OnboardingState(
        account_id=_ACCOUNT_ID,
        controller_patient_id=_PATIENT_ID,
        status=status,
        consent_version="core.v1",
        choices={},
        baseline={},
        personal_workspace_id=_WORKSPACE_ID if workspace else None,
        display_name=None,
    )


class _FakeAccount:
    id = _ACCOUNT_ID
    controller_patient_id = _PATIENT_ID
    display_name = None


@pytest.fixture(autouse=True)
def _no_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_audit(*_: Any, **__: Any) -> None:
        return None

    monkeypatch.setattr(onboarding_v1, "audit_ref", _fake_audit)
    yield
    app.dependency_overrides.pop(get_session, None)


def _stub_service(monkeypatch: pytest.MonkeyPatch, *, finalize_status: str = "active") -> None:
    class _FakeService:
        def __init__(self, _session: Any) -> None: ...

        async def find_account(self, **_: Any) -> Any:
            return _FakeAccount()

        async def get_or_create_account(self, **_: Any) -> Any:
            return _FakeAccount()

        async def start(self, _account: Any) -> Any:
            return None

        async def save_draft(self, _account: Any, **_kw: Any) -> Any:
            return None

        async def get_state(self, _account: Any) -> OnboardingState:
            return _state("pending", workspace=False)

        async def finalize(self, _account: Any) -> OnboardingState:
            return _state(finalize_status, workspace=True)

    monkeypatch.setattr(onboarding_v1, "OnboardingService", _FakeService)
    _override_session()


def test_onboarding_requires_identity() -> None:
    resp = _client_get("/v1/onboarding")
    assert resp.status_code == 401


def test_start_returns_pending_with_core_consent(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_service(monkeypatch)
    resp = TestClient(app).post("/v1/onboarding/start", headers=_AUTH, json={})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert len(body["core_consent"]) == 4
    assert {c["purpose"] for c in body["core_consent"]} == {
        "core.workspace",
        "core.memory",
        "core.threads",
        "core.audit",
    }


def test_finalize_requires_explicit_consent(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_service(monkeypatch)
    resp = TestClient(app).post(
        "/v1/onboarding/finalize", headers=_AUTH, json={"accept_core_consent": False}
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "scope_denied"


def test_finalize_happy_path_activates_and_returns_workspace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_service(monkeypatch)
    resp = TestClient(app).post(
        "/v1/onboarding/finalize", headers=_AUTH, json={"accept_core_consent": True}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "active"
    assert body["personal_workspace_id"] == str(_WORKSPACE_ID)
    assert body["controller_patient_id"] == str(_PATIENT_ID)


def _client_get(path: str) -> Any:
    return TestClient(app).get(path)
