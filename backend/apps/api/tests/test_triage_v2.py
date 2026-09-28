"""Route tests for C13 POST /v2/triage/evaluate.

Covers the auth guard, request validation, the urgent / routine contract, and
that every evaluation is audited with the route and rule ids but never the
answer text. The DB session and audit writer are stubbed (infra-free).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from wellbe_api.deps import get_session
from wellbe_api.main import app
from wellbe_api.routers import triage_v2

_ACTOR = "11111111-1111-1111-1111-111111111111"
_AUTH = {"X-Wellbe-Actor-Id": _ACTOR}


class _FakeSession:
    commits = 0

    async def commit(self) -> None:
        _FakeSession.commits += 1


@pytest.fixture(autouse=True)
def _audits(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[dict[str, Any]]]:
    audits: list[dict[str, Any]] = []

    async def _fake_audit(*_: Any, **kwargs: Any) -> None:
        audits.append(kwargs)

    async def _fake_session() -> AsyncGenerator[_FakeSession]:
        yield _FakeSession()

    monkeypatch.setattr(triage_v2, "audit_ref", _fake_audit)
    app.dependency_overrides[get_session] = _fake_session
    yield audits
    app.dependency_overrides.pop(get_session, None)


def _post(body: dict[str, Any], headers: dict[str, str] | None = None) -> Any:
    return TestClient(app).post(
        "/v2/triage/evaluate", json=body, headers=_AUTH if headers is None else headers
    )


def test_requires_authentication() -> None:
    assert _post({"answers": {"what": "chest pain"}}, headers={}).status_code == 401


def test_rejects_empty_answers() -> None:
    assert _post({"answers": {"what": ""}}).status_code == 422
    assert _post({"answers": {}}).status_code == 422


def test_urgent_route_returns_approved_guidance_and_is_audited(
    _audits: list[dict[str, Any]],
) -> None:
    resp = _post(
        {
            "answers": {
                "what": "Crushing chest pain and I'm short of breath",
                "onset": "Today",
            }
        }
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["schema_version"] == "c13.triage.evaluate.v2"
    assert body["route"] == "route_urgent"
    assert body["safety_gate_decision"] == "route_urgent"
    assert body["guidance"]["template_id"] == "emergency_now.v1"
    assert "your local emergency number" in body["guidance"]["action"]
    assert body["jurisdiction"] == "generic"
    assert body["clinical_review_status"] == "pending_clinical_review"
    assert body["not_diagnosis"] is True
    rule_ids = {r["rule_id"] for r in body["matched_rules"]}
    assert "U-CHEST-01" in rule_ids
    assert all(s["url"].startswith("https://") for s in body["sources"])

    (audit,) = _audits
    assert audit["event_type"] == "c13.triage.evaluated"
    extra = audit["extra"]
    assert extra["route"] == "route_urgent"
    assert extra["c10_event"] == "ai_output.routed_urgent"
    assert set(extra["rule_ids"]) == rule_ids
    assert extra["evaluation_id"] == body["evaluation_id"]
    assert len(extra["answers_sha256"]) == 64
    assert "crushing" not in repr(audit).lower()


def test_routine_route_carries_backstop(_audits: list[dict[str, Any]]) -> None:
    resp = _post({"answers": {"what": "No chest pain, just tired lately"}})
    assert resp.status_code == 200
    body = resp.json()
    assert body["route"] == "route_routine"
    assert body["safety_gate_decision"] == "allow_with_obligations"
    assert body["matched_rules"] == []
    assert "isn't complete" in body["guidance"]["backstop"]
    assert _audits[0]["extra"]["c10_event"] == "ai_output.allowed_with_obligations"


def test_region_in_context_substitutes_the_number() -> None:
    body = _post({"answers": {"what": "chest pain"}, "context": {"region": "GB"}}).json()
    assert body["guidance"]["emergency_number"] == "999"
    assert body["jurisdiction"] == "GB"


def test_route_is_in_the_v2_openapi() -> None:
    paths = TestClient(app).get("/openapi.json").json()["paths"]
    assert "post" in paths["/v2/triage/evaluate"]
