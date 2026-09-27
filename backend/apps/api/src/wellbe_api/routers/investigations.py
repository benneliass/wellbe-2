"""C13 /v2 Investigation, Theory, and External-context routes (real data).

Every handler resolves a principal, runs the C1/C17 access predicate before any
read or write, delegates lifecycle to C14/C15/C16 (which own the rules), and emits
a C12 audit event for state changes. Non-diagnosis is structural: TheoryV2 forbids
diagnosis-shaped fields, so they cannot be serialized.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field
from wellbe_c6_graph import GraphRepository
from wellbe_c7_thread import ThreadService
from wellbe_c14_investigation import (
    ClosureBlockedByThreadError,
    InvalidInvestigationTransitionError,
    InvestigationNotFoundError,
    InvestigationService,
    InvestigationVersionConflictError,
)
from wellbe_c14_investigation.repository import InvestigationRepository
from wellbe_c15_theory import (
    TheoryBlockedError,
    TheoryEvaluationError,
    TheoryNotFoundError,
    TheoryService,
    TheoryVersionConflictError,
    user_evaluation_from_row,
)
from wellbe_c15_theory.models import TheoryRow
from wellbe_c15_theory.repository import TheoryRepository
from wellbe_c16_external import ExternalEvidenceService
from wellbe_contracts.c13_api import (
    InvestigationV2,
    ProblemCode,
    RelevanceLinkV2,
    TheoryEvaluationResultV2,
    TheoryEvaluationV2,
    TheoryV2,
)
from wellbe_contracts.c14_investigation import (
    InvestigationOwnerType,
    InvestigationStatus,
    ThreadRelationship,
)
from wellbe_contracts.c15_theory import (
    ASSESSMENT_LABEL,
    MAX_EVIDENCE_REFS,
    RATIONALE_MAX_LENGTH,
    TheoryAssessment,
    TheoryEvidenceRef,
    TheoryEvidenceRefKind,
    TheoryType,
)

from wellbe_api import mappers
from wellbe_api.deps import Principal, PrincipalDep, SessionDep, audit_ref, require_access
from wellbe_api.errors import ProblemError

router = APIRouter(prefix="/v2", tags=["v2-investigations"])

_RESOURCE = "investigation"


def _svc(session: SessionDep) -> InvestigationService:
    return InvestigationService(session, ThreadService(session))


async def _load_owned(
    session: SessionDep, principal: Principal, investigation_id: uuid.UUID
) -> InvestigationRepository:
    """Load an investigation and assert it belongs to the principal's patient."""
    repo = InvestigationRepository(session)
    row = await repo.get(investigation_id)
    if row is None or row.patient_id != principal.patient_id:
        raise ProblemError(
            status=404,
            code=ProblemCode.GRANT_REQUIRED,
            title="Investigation not found",
            detail="No investigation with that id is visible to the principal.",
            correlation_id=principal.correlation_id,
        )
    return repo


class CreateInvestigationRequest(BaseModel):
    primary_question: str
    owner_type: InvestigationOwnerType = InvestigationOwnerType.USER
    thread_ids: list[uuid.UUID] = Field(default_factory=list)


class TransitionInvestigationRequest(BaseModel):
    target_status: InvestigationStatus
    reason_code: str
    expected_version: int | None = None


class CloseInvestigationRequest(BaseModel):
    reason_code: str = "user_closed"
    expected_version: int | None = None


class CreateTheoryRequest(BaseModel):
    theory_text: str
    theory_type: TheoryType = TheoryType.SYMPTOM_CAUSE


class EvidenceRefRequest(BaseModel):
    kind: TheoryEvidenceRefKind
    id: uuid.UUID


class EvaluateTheoryRequest(BaseModel):
    """The user's own evaluation. ``to_status`` is the user's mark, never a diagnosis."""

    to_status: TheoryAssessment
    rationale: str = Field(max_length=RATIONALE_MAX_LENGTH)
    # Validated by C15 (clear 422 codes) rather than a bare schema error.
    evidence_refs: list[EvidenceRefRequest] = Field(
        default_factory=list, max_length=MAX_EVIDENCE_REFS
    )
    expected_version: int = Field(ge=1)


@router.get("/investigations", response_model=list[InvestigationV2])
async def list_investigations(
    principal: PrincipalDep, session: SessionDep
) -> list[InvestigationV2]:
    await require_access(principal, session, action="read", resource_type=_RESOURCE)
    repo = InvestigationRepository(session)
    rows = await repo.list_for_patient(principal.patient_id)
    out: list[InvestigationV2] = []
    for row in rows:
        thread_ids = await repo.linked_thread_ids(row.id)
        out.append(mappers.investigation_to_v2(row, thread_ids=thread_ids))
    return out


@router.post("/investigations", response_model=InvestigationV2, status_code=201)
async def create_investigation(
    body: CreateInvestigationRequest, principal: PrincipalDep, session: SessionDep
) -> InvestigationV2:
    await require_access(principal, session, action="write", resource_type=_RESOURCE)
    svc = _svc(session)
    iid = await svc.create_investigation(
        patient_id=principal.patient_id,
        primary_question=body.primary_question,
        owner_type=body.owner_type,
        correlation_id=principal.correlation_id,
        trace_id=principal.trace_id,
        created_by_actor_id=principal.actor_id,
    )
    for tid in body.thread_ids:
        await svc.link_thread(
            investigation_id=iid,
            thread_id=tid,
            relationship=ThreadRelationship.PRIMARY,
            correlation_id=principal.correlation_id,
            trace_id=principal.trace_id,
        )
    audit = await audit_ref(
        session,
        event_type="c13.investigation.created",
        principal=principal,
        summary="Investigation created",
        extra={"investigation_id": str(iid)},
    )
    repo = InvestigationRepository(session)
    row = await repo.get(iid)
    assert row is not None
    thread_ids = await repo.linked_thread_ids(iid)
    await session.commit()
    return mappers.investigation_to_v2(row, thread_ids=thread_ids, audit_refs=[audit])


@router.get("/investigations/{investigation_id}", response_model=InvestigationV2)
async def get_investigation(
    investigation_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> InvestigationV2:
    await require_access(
        principal, session, action="read", resource_type=_RESOURCE, resource_id=investigation_id
    )
    repo = await _load_owned(session, principal, investigation_id)
    row = await repo.get(investigation_id)
    assert row is not None
    thread_ids = await repo.linked_thread_ids(investigation_id)
    return mappers.investigation_to_v2(row, thread_ids=thread_ids)


@router.patch("/investigations/{investigation_id}", response_model=InvestigationV2)
async def patch_investigation(
    investigation_id: uuid.UUID,
    body: TransitionInvestigationRequest,
    principal: PrincipalDep,
    session: SessionDep,
) -> InvestigationV2:
    await require_access(
        principal, session, action="write", resource_type=_RESOURCE, resource_id=investigation_id
    )
    await _load_owned(session, principal, investigation_id)
    await _transition(
        session,
        principal,
        investigation_id,
        body.target_status,
        body.reason_code,
        body.expected_version,
    )
    return await _reload(session, principal, investigation_id)


@router.post("/investigations/{investigation_id}/close", response_model=InvestigationV2)
async def close_investigation(
    investigation_id: uuid.UUID,
    body: CloseInvestigationRequest,
    principal: PrincipalDep,
    session: SessionDep,
) -> InvestigationV2:
    await require_access(
        principal, session, action="write", resource_type=_RESOURCE, resource_id=investigation_id
    )
    await _load_owned(session, principal, investigation_id)
    await _transition(
        session,
        principal,
        investigation_id,
        InvestigationStatus.CLOSED,
        body.reason_code,
        body.expected_version,
    )
    return await _reload(session, principal, investigation_id)


@router.post("/investigations/{investigation_id}/reopen", response_model=InvestigationV2)
async def reopen_investigation(
    investigation_id: uuid.UUID,
    body: CloseInvestigationRequest,
    principal: PrincipalDep,
    session: SessionDep,
) -> InvestigationV2:
    await require_access(
        principal, session, action="write", resource_type=_RESOURCE, resource_id=investigation_id
    )
    await _load_owned(session, principal, investigation_id)
    await _transition(
        session,
        principal,
        investigation_id,
        InvestigationStatus.OPEN,
        body.reason_code or "user_reopened",
        body.expected_version,
    )
    return await _reload(session, principal, investigation_id)


@router.get(
    "/investigations/{investigation_id}/theories", response_model=list[TheoryV2]
)
async def list_theories(
    investigation_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> list[TheoryV2]:
    await require_access(
        principal, session, action="read", resource_type=_RESOURCE, resource_id=investigation_id
    )
    await _load_owned(session, principal, investigation_id)
    trepo = TheoryRepository(session)
    rows = await trepo.list_for_investigation(investigation_id)
    latest = await trepo.latest_user_evaluations([r.id for r in rows])
    return [
        mappers.theory_to_v2(
            r,
            latest_evaluation=(
                user_evaluation_from_row(latest[r.id]) if r.id in latest else None
            ),
        )
        for r in rows
    ]


@router.post(
    "/investigations/{investigation_id}/theories", response_model=TheoryV2, status_code=201
)
async def create_theory(
    investigation_id: uuid.UUID,
    body: CreateTheoryRequest,
    principal: PrincipalDep,
    session: SessionDep,
) -> TheoryV2:
    await require_access(
        principal, session, action="write", resource_type=_RESOURCE, resource_id=investigation_id
    )
    inv_repo = await _load_owned(session, principal, investigation_id)
    tsvc = TheoryService(session)
    tid = await tsvc.create_theory(
        patient_id=principal.patient_id,
        theory_text=body.theory_text,
        theory_type=body.theory_type,
        correlation_id=principal.correlation_id,
        trace_id=principal.trace_id,
        linked_investigation_id=investigation_id,
        created_by_actor_id=principal.actor_id,
    )
    audit = await audit_ref(
        session,
        event_type="c13.theory.created",
        principal=principal,
        summary="Theory created",
        extra={"theory_id": str(tid), "investigation_id": str(investigation_id)},
    )
    trepo = TheoryRepository(session)
    row = await trepo.get(tid)
    assert row is not None
    # The theory lives in the investigation's threads, reached from the investigation.
    investigation = await inv_repo.get(investigation_id)
    if (
        investigation is not None
        and investigation.projection_node_id is not None
        and row.projection_node_id is not None
    ):
        graph = GraphRepository(session)
        await graph.upsert_observed_edge(
            patient_id=principal.patient_id,
            from_node_id=investigation.projection_node_id,
            to_node_id=row.projection_node_id,
            edge_type="investigates",
            confidence=1.0,
            observation_key=f"theory:{tid}",
        )
        for thread_id in await inv_repo.linked_thread_ids(investigation_id):
            await graph.tag_nodes_with_thread(
                patient_id=principal.patient_id,
                node_ids=[row.projection_node_id],
                thread_id=thread_id,
            )
            await graph.tag_edges_within_thread(
                patient_id=principal.patient_id, thread_id=thread_id
            )
    await session.commit()
    return mappers.theory_to_v2(row, audit_refs=[audit])


@router.get(
    "/investigations/{investigation_id}/external-context",
    response_model=list[RelevanceLinkV2],
)
async def investigation_external_context(
    investigation_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> list[RelevanceLinkV2]:
    await require_access(
        principal,
        session,
        action="view_external_context",
        resource_type=_RESOURCE,
        resource_id=investigation_id,
    )
    repo = await _load_owned(session, principal, investigation_id)
    row = await repo.get(investigation_id)
    assert row is not None
    if row.projection_node_id is None:
        return []
    ext = ExternalEvidenceService(session)
    results = await ext.list_context_for_node(
        patient_id=principal.patient_id, personal_node_id=row.projection_node_id
    )
    return [
        mappers.relevance_to_v2(
            r,
            investigation_id=investigation_id,
            why_relevant_summary="External context relevant to this investigation.",
        )
        for r in results
    ]


async def _load_theory(
    session: SessionDep, principal: Principal, theory_id: uuid.UUID
) -> TheoryRow:
    """Load a theory and assert it belongs to the principal's patient (404 otherwise)."""
    row = await TheoryRepository(session).get(theory_id)
    if row is None or row.patient_id != principal.patient_id:
        raise ProblemError(
            status=404,
            code=ProblemCode.GRANT_REQUIRED,
            title="Theory not found",
            detail="No theory with that id is visible to the principal.",
            correlation_id=principal.correlation_id,
        )
    return row


async def _theory_v2(session: SessionDep, row: TheoryRow) -> TheoryV2:
    latest = await TheoryRepository(session).latest_user_evaluations([row.id])
    ev = latest.get(row.id)
    return mappers.theory_to_v2(
        row, latest_evaluation=user_evaluation_from_row(ev) if ev is not None else None
    )


_EVALUATION_ERROR_CODES: dict[str, ProblemCode] = {
    "theory_evidence_required": ProblemCode.THEORY_EVIDENCE_REQUIRED,
    "theory_rationale_required": ProblemCode.THEORY_RATIONALE_REQUIRED,
    "theory_evidence_not_found": ProblemCode.THEORY_EVIDENCE_NOT_FOUND,
    "theory_evidence_unrelated": ProblemCode.THEORY_EVIDENCE_UNRELATED,
    "theory_not_linked_to_investigation": ProblemCode.THEORY_NOT_LINKED_TO_INVESTIGATION,
}


@router.get("/theories/{theory_id}", response_model=TheoryV2)
async def get_theory(
    theory_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> TheoryV2:
    row = await _load_theory(session, principal, theory_id)
    await require_access(
        principal,
        session,
        action="read",
        resource_type=_RESOURCE,
        resource_id=row.linked_investigation_id,
    )
    return await _theory_v2(session, row)


@router.get("/theories/{theory_id}/evaluations", response_model=list[TheoryEvaluationV2])
async def list_theory_evaluations(
    theory_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> list[TheoryEvaluationV2]:
    row = await _load_theory(session, principal, theory_id)
    await require_access(
        principal,
        session,
        action="read",
        resource_type=_RESOURCE,
        resource_id=row.linked_investigation_id,
    )
    evaluations = await TheoryRepository(session).list_user_evaluations(theory_id)
    return [
        mappers.theory_evaluation_to_v2(user_evaluation_from_row(e)) for e in evaluations
    ]


@router.post("/theories/{theory_id}/evaluate", response_model=TheoryEvaluationResultV2)
async def evaluate_theory(
    theory_id: uuid.UUID,
    body: EvaluateTheoryRequest,
    principal: PrincipalDep,
    session: SessionDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> TheoryEvaluationResultV2:
    """The USER marks a theory, citing their own evidence. The system never decides."""
    row = await _load_theory(session, principal, theory_id)
    await require_access(
        principal,
        session,
        action="write",
        resource_type=_RESOURCE,
        resource_id=row.linked_investigation_id,
    )
    if not principal.is_controller:
        raise ProblemError(
            status=403,
            code=ProblemCode.ACTIVE_ROLE_REQUIRED,
            title="Only the account owner can evaluate a theory",
            detail="Theory evaluations are the user's own judgement; delegates cannot record them.",
            correlation_id=principal.correlation_id,
        )
    thread_ids: list[uuid.UUID] = []
    if row.linked_investigation_id is not None:
        thread_ids = await InvestigationRepository(session).linked_thread_ids(
            row.linked_investigation_id
        )
    try:
        outcome = await TheoryService(session).evaluate_by_user(
            theory_id=theory_id,
            patient_id=principal.patient_id,
            actor_id=principal.actor_id,
            assessment=body.to_status,
            rationale=body.rationale,
            evidence_refs=[TheoryEvidenceRef(kind=r.kind, id=r.id) for r in body.evidence_refs],
            expected_version=body.expected_version,
            investigation_thread_ids=thread_ids,
            idempotency_key=idempotency_key or principal.correlation_id,
            correlation_id=principal.correlation_id,
            trace_id=principal.trace_id,
        )
    except TheoryNotFoundError as exc:
        raise ProblemError(
            status=404,
            code=ProblemCode.GRANT_REQUIRED,
            title="Theory not found",
            detail="No theory with that id is visible to the principal.",
            correlation_id=principal.correlation_id,
        ) from exc
    except TheoryBlockedError as exc:
        raise ProblemError(
            status=409,
            code=ProblemCode.THEORY_DIAGNOSIS_VIOLATION,
            title="Theory is withheld",
            detail="This theory was withheld because it was phrased as a diagnosis.",
            correlation_id=principal.correlation_id,
        ) from exc
    except TheoryVersionConflictError as exc:
        raise ProblemError(
            status=409,
            code=ProblemCode.VERSION_CONFLICT,
            title="Version conflict",
            detail=str(exc),
            correlation_id=principal.correlation_id,
            remediation="Reload the theory and try again.",
        ) from exc
    except TheoryEvaluationError as exc:
        raise ProblemError(
            status=422,
            code=_EVALUATION_ERROR_CODES.get(exc.code, ProblemCode.PROVENANCE_MISSING),
            title="Evaluation needs your evidence",
            detail=exc.message,
            correlation_id=principal.correlation_id,
        ) from exc

    audits = []
    if not outcome.replayed:
        audits.append(
            await audit_ref(
                session,
                event_type="c13.theory.evaluated",
                principal=principal,
                summary=ASSESSMENT_LABEL[body.to_status],
                extra={
                    "theory_id": str(theory_id),
                    "evaluation_id": str(outcome.evaluation.evaluation_id),
                    "assessment": outcome.evaluation.assessment.value,
                    "from_status": outcome.evaluation.from_status.value,
                    "to_status": outcome.evaluation.to_status.value,
                    "evidence_ref_count": len(outcome.evaluation.evidence_refs),
                },
            )
        )
    await session.refresh(row)
    theory = (
        await _theory_v2(session, row)
        if outcome.replayed
        else mappers.theory_to_v2(row, latest_evaluation=outcome.evaluation)
    )
    await session.commit()
    return TheoryEvaluationResultV2(
        theory=theory,
        evaluation=mappers.theory_evaluation_to_v2(outcome.evaluation, audit_refs=audits),
    )


async def _transition(
    session: SessionDep,
    principal: Principal,
    investigation_id: uuid.UUID,
    target: InvestigationStatus,
    reason_code: str,
    expected_version: int | None,
) -> None:
    svc = _svc(session)
    try:
        await svc.transition(
            investigation_id=investigation_id,
            target_status=target,
            reason_code=reason_code,
            idempotency_key=f"{principal.correlation_id}:{target.value}",
            correlation_id=principal.correlation_id,
            trace_id=principal.trace_id,
            actor_id=principal.actor_id,
            expected_version=expected_version,
        )
    except InvestigationNotFoundError as exc:
        raise ProblemError(
            status=404,
            code=ProblemCode.GRANT_REQUIRED,
            title="Investigation not found",
            detail="No investigation with that id is visible to the principal.",
            correlation_id=principal.correlation_id,
        ) from exc
    except InvalidInvestigationTransitionError as exc:
        raise ProblemError(
            status=409,
            code=ProblemCode.SCOPE_DENIED,
            title="Invalid investigation transition",
            detail=str(exc),
            correlation_id=principal.correlation_id,
        ) from exc
    except ClosureBlockedByThreadError as exc:
        raise ProblemError(
            status=409,
            code=ProblemCode.SCOPE_DENIED,
            title="Closure blocked by unresolved thread",
            detail="One or more linked health threads are not resolved; cannot close.",
            correlation_id=principal.correlation_id,
        ) from exc
    except InvestigationVersionConflictError as exc:
        raise ProblemError(
            status=409,
            code=ProblemCode.SCOPE_DENIED,
            title="Version conflict",
            detail=str(exc),
            correlation_id=principal.correlation_id,
        ) from exc
    await audit_ref(
        session,
        event_type="c13.investigation.state_changed",
        principal=principal,
        summary=f"Investigation transitioned to {target.value}",
        extra={"investigation_id": str(investigation_id), "to_status": target.value},
    )
    await session.commit()


async def _reload(
    session: SessionDep, principal: Principal, investigation_id: uuid.UUID
) -> InvestigationV2:
    repo = InvestigationRepository(session)
    row = await repo.get(investigation_id)
    assert row is not None
    thread_ids = await repo.linked_thread_ids(investigation_id)
    return mappers.investigation_to_v2(row, thread_ids=thread_ids)
