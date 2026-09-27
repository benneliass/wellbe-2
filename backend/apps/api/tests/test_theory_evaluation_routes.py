"""C13 routes for user-authored theory evaluation (POST /v2/theories/{id}/evaluate).

DB, C15 service, and audit are stubbed; these tests pin the HTTP contract:
status codes + problem codes, controller-only writes, audit, and the response
shape (theory with current status/version/latest evaluation + the evaluation).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from wellbe_api.deps import get_session
from wellbe_api.main import app
from wellbe_api.routers import investigations
from wellbe_c15_theory import (
    TheoryEvidenceNotFoundError,
    TheoryEvidenceRequiredError,
    TheoryEvidenceUnrelatedError,
    TheoryVersionConflictError,
    UserEvaluationOutcome,
)
from wellbe_contracts.c13_api import AuditRefV2
from wellbe_contracts.c15_theory import (
    TheoryAssessment,
    TheoryEvidenceRef,
    TheoryEvidenceRefKind,
    TheoryStatus,
    TheoryUserEvaluation,
)

PATIENT = uuid.UUID("11111111-1111-1111-1111-111111111111")
AUTH = {"X-Wellbe-Actor-Id": str(PATIENT)}
THREAD = uuid.uuid4()
NOW = datetime(2026, 9, 27, 12, tzinfo=UTC)


def _theory_row(**over: Any) -> SimpleNamespace:
    base: dict[str, Any] = dict(
        id=uuid.uuid4(), patient_id=PATIENT, linked_investigation_id=uuid.uuid4(),
        created_by_actor_id=PATIENT, theory_text="Could screen time relate to my headaches?",
        status="unreviewed", safety_level="low", version=1,
        created_at=NOW, updated_at=NOW,
    )
    base.update(over)
    return SimpleNamespace(**base)


def _evaluation(theory_id: uuid.UUID, fact_id: uuid.UUID) -> TheoryUserEvaluation:
    return TheoryUserEvaluation(
        evaluation_id=uuid.uuid4(), theory_id=theory_id, patient_id=PATIENT, actor_id=PATIENT,
        evaluation_version=1, assessment=TheoryAssessment.WEAKENED,
        from_status=TheoryStatus.UNREVIEWED,
        to_status=TheoryStatus.NOT_SUPPORTED_BY_CURRENT_DATA,
        rationale="Headaches continued on screen-free days.",
        evidence_refs=[TheoryEvidenceRef(kind=TheoryEvidenceRefKind.FACT, id=fact_id)],
        evidence_node_ids=[uuid.uuid4()], created_at=NOW,
    )


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, row: Any) -> None:
        row.status = "not_supported_by_current_data"
        row.version = 2


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch):
    theory = _theory_row()
    fact_id = uuid.uuid4()
    state = SimpleNamespace(
        theory=theory, fact_id=fact_id, error=None, calls=[], audits=[],
        evaluation=_evaluation(theory.id, fact_id), session=_FakeSession(),
    )

    class FakeTheoryRepo:
        def __init__(self, _s: Any) -> None: ...

        async def get(self, tid: uuid.UUID):
            return state.theory if tid == state.theory.id else None

        async def latest_user_evaluations(self, ids):
            return {}

        async def list_user_evaluations(self, tid):
            return []

    class FakeInvestigationRepo:
        def __init__(self, _s: Any) -> None: ...

        async def linked_thread_ids(self, _iid):
            return [THREAD]

    class FakeService:
        def __init__(self, _s: Any) -> None: ...

        async def evaluate_by_user(self, **kw: Any) -> UserEvaluationOutcome:
            state.calls.append(kw)
            if state.error is not None:
                raise state.error
            return UserEvaluationOutcome(evaluation=state.evaluation, theory_version=2)

    async def fake_audit(_s: Any, **kw: Any) -> AuditRefV2:
        state.audits.append(kw)
        return AuditRefV2(
            audit_event_id=str(uuid.uuid4()), correlation_id="corr",
            visibility=["controller"], event_summary=kw["summary"],
        )

    async def allow(*_a: Any, **_k: Any) -> None:
        return None

    monkeypatch.setattr(investigations, "TheoryRepository", FakeTheoryRepo)
    monkeypatch.setattr(investigations, "InvestigationRepository", FakeInvestigationRepo)
    monkeypatch.setattr(investigations, "TheoryService", FakeService)
    monkeypatch.setattr(investigations, "audit_ref", fake_audit)
    monkeypatch.setattr(investigations, "require_access", allow)
    monkeypatch.setattr(
        investigations, "user_evaluation_from_row", lambda row: row
    )

    async def fake_session() -> AsyncGenerator[_FakeSession]:
        yield state.session

    app.dependency_overrides[get_session] = fake_session
    yield state
    app.dependency_overrides.pop(get_session, None)


def _body(state: Any, **over: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "to_status": "weakened",
        "rationale": "Headaches continued on screen-free days.",
        "evidence_refs": [{"kind": "fact", "id": str(state.fact_id)}],
        "expected_version": 1,
    }
    body.update(over)
    return body


def _post(state: Any, headers: dict[str, str] | None = None, **over: Any):
    return TestClient(app).post(
        f"/v2/theories/{state.theory.id}/evaluate",
        headers=headers or AUTH,
        json=_body(state, **over),
    )


def test_requires_authentication(env) -> None:
    resp = TestClient(app).post(f"/v2/theories/{env.theory.id}/evaluate", json=_body(env))
    assert resp.status_code == 401


def test_evaluate_returns_updated_theory_and_evaluation(env) -> None:
    resp = _post(env, headers={**AUTH, "Idempotency-Key": "idem-7"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    theory, evaluation = body["theory"], body["evaluation"]
    assert theory["status"] == "not_supported_by_current_data"
    assert theory["version"] == 2
    assert theory["assessment"] == "weakened"
    assert theory["assessment_label"] == "You marked this theory as weakened"
    assert theory["not_diagnosis"] is True
    assert theory["evidence_against"] == [
        {"kind": "fact", "id": str(env.fact_id), "cited_by": "user"}
    ]
    assert theory["latest_evaluation"]["evaluation_id"] == evaluation["evaluation_id"]
    assert evaluation["from_status"] == "unreviewed"
    assert evaluation["to_status"] == "not_supported_by_current_data"
    assert evaluation["rationale"].startswith("Headaches continued")
    assert evaluation["evaluated_by"]["role"] == "user"
    assert len(evaluation["audit_refs"]) == 1

    call = env.calls[0]
    assert call["assessment"] is TheoryAssessment.WEAKENED
    assert call["expected_version"] == 1
    assert call["investigation_thread_ids"] == [THREAD]
    assert call["idempotency_key"] == "idem-7"
    assert env.audits[0]["event_type"] == "c13.theory.evaluated"
    assert env.session.committed


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (TheoryEvidenceRequiredError("cite something"), 422, "theory_evidence_required"),
        (TheoryEvidenceNotFoundError("fact", "x"), 422, "theory_evidence_not_found"),
        (TheoryEvidenceUnrelatedError("fact", "x"), 422, "theory_evidence_unrelated"),
        (TheoryVersionConflictError("t", 1, 2), 409, "version_conflict"),
    ],
)
def test_service_rejections_map_to_problem_codes(env, error, status, code) -> None:
    env.error = error
    resp = _post(env)
    assert resp.status_code == status, resp.text
    assert resp.json()["code"] == code
    assert not env.audits
    assert not env.session.committed


def test_unknown_mark_is_rejected_by_schema(env) -> None:
    resp = _post(env, to_status="confirmed")
    assert resp.status_code == 422
    assert not env.calls


def test_non_controller_cannot_evaluate(env) -> None:
    delegate = {"X-Wellbe-Actor-Id": str(uuid.uuid4()), "X-Wellbe-Patient-Id": str(PATIENT)}
    resp = _post(env, headers=delegate)
    assert resp.status_code == 403
    assert resp.json()["code"] == "active_role_required"
    assert not env.calls


def test_other_patients_theory_is_not_found(env) -> None:
    env.theory.patient_id = uuid.uuid4()
    resp = _post(env)
    assert resp.status_code == 404
    assert not env.calls


def test_list_evaluations_and_get_theory(env) -> None:
    client = TestClient(app)
    listed = client.get(f"/v2/theories/{env.theory.id}/evaluations", headers=AUTH)
    assert listed.status_code == 200 and listed.json() == []
    got = client.get(f"/v2/theories/{env.theory.id}", headers=AUTH)
    assert got.status_code == 200
    assert got.json()["version"] == 1
    assert got.json()["latest_evaluation"] is None
