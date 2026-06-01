"""C13 /v1 Health Thread routes — stable MVP surface.

v1 stays backward compatible: it exposes only v1-safe Health Thread fields and
never returns Investigation/Theory/external-evidence/deep-grant internals.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel
from wellbe_c7_thread import (
    InvalidTransitionError,
    ThreadNotFoundError,
    ThreadService,
    VersionConflictError,
)
from wellbe_c7_thread.repository import ThreadRepository
from wellbe_contracts.c7_thread import (
    HealthThreadStatus,
    ThreadActor,
    ThreadActorType,
)
from wellbe_contracts.c13_api import ProblemCode

from wellbe_api.deps import Principal, PrincipalDep, SessionDep, audit_ref, require_access
from wellbe_api.errors import ProblemError

router = APIRouter(prefix="/v1", tags=["v1-threads"])

_RESOURCE = "health_thread"


class ThreadV1(BaseModel):
    schema_version: str = "c13.health_thread.v1"
    thread_id: str
    patient_id: str
    title: str
    status: str
    status_version: int
    created_at: datetime
    updated_at: datetime


class CreateThreadRequest(BaseModel):
    title: str


class TransitionThreadRequest(BaseModel):
    target_status: HealthThreadStatus
    reason_code: str
    expected_version: int | None = None


def _to_v1(row: object) -> ThreadV1:
    return ThreadV1(
        thread_id=str(row.id),  # type: ignore[attr-defined]
        patient_id=str(row.patient_id),  # type: ignore[attr-defined]
        title=row.title,  # type: ignore[attr-defined]
        status=row.status,  # type: ignore[attr-defined]
        status_version=row.status_version,  # type: ignore[attr-defined]
        created_at=row.created_at,  # type: ignore[attr-defined]
        updated_at=row.status_changed_at,  # type: ignore[attr-defined]
    )


async def _load_owned(session: SessionDep, principal: Principal, thread_id: uuid.UUID) -> object:
    repo = ThreadRepository(session)
    row = await repo.get(thread_id)
    if row is None or row.patient_id != principal.patient_id:
        raise ProblemError(
            status=404,
            code=ProblemCode.GRANT_REQUIRED,
            title="Thread not found",
            detail="No health thread with that id is visible to the principal.",
            correlation_id=principal.correlation_id,
        )
    return row


@router.get("/threads", response_model=list[ThreadV1])
async def list_threads(principal: PrincipalDep, session: SessionDep) -> list[ThreadV1]:
    await require_access(principal, session, action="read", resource_type=_RESOURCE)
    repo = ThreadRepository(session)
    rows = await repo.list_for_patient(principal.patient_id)
    return [_to_v1(r) for r in rows]


@router.post("/threads", response_model=ThreadV1, status_code=201)
async def create_thread(
    body: CreateThreadRequest, principal: PrincipalDep, session: SessionDep
) -> ThreadV1:
    await require_access(principal, session, action="write", resource_type=_RESOURCE)
    svc = ThreadService(session)
    tid = await svc.create_thread(patient_id=principal.patient_id, title=body.title)
    await audit_ref(
        session,
        event_type="c13.thread.created",
        principal=principal,
        summary="Health thread created",
        extra={"thread_id": str(tid)},
    )
    await session.commit()
    row = await _load_owned(session, principal, tid)
    return _to_v1(row)


@router.get("/threads/{thread_id}", response_model=ThreadV1)
async def get_thread(
    thread_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> ThreadV1:
    await require_access(
        principal, session, action="read", resource_type=_RESOURCE, resource_id=thread_id
    )
    row = await _load_owned(session, principal, thread_id)
    return _to_v1(row)


@router.post("/threads/{thread_id}/transition", response_model=ThreadV1)
async def transition_thread(
    thread_id: uuid.UUID,
    body: TransitionThreadRequest,
    principal: PrincipalDep,
    session: SessionDep,
) -> ThreadV1:
    await require_access(
        principal, session, action="write", resource_type=_RESOURCE, resource_id=thread_id
    )
    await _load_owned(session, principal, thread_id)
    svc = ThreadService(session)
    try:
        await svc.transition_thread(
            thread_id=thread_id,
            target_status=body.target_status,
            actor=ThreadActor(type=ThreadActorType.USER, id=principal.actor_id),
            reason_code=body.reason_code,
            idempotency_key=f"{principal.correlation_id}:{body.target_status.value}",
            correlation_id=principal.correlation_id,
            trace_id=principal.trace_id,
            expected_version=body.expected_version,
        )
    except ThreadNotFoundError as exc:
        raise ProblemError(
            status=404,
            code=ProblemCode.GRANT_REQUIRED,
            title="Thread not found",
            detail="No health thread with that id is visible to the principal.",
            correlation_id=principal.correlation_id,
        ) from exc
    except (InvalidTransitionError, VersionConflictError) as exc:
        raise ProblemError(
            status=409,
            code=ProblemCode.SCOPE_DENIED,
            title="Invalid thread transition",
            detail=str(exc),
            correlation_id=principal.correlation_id,
        ) from exc
    await audit_ref(
        session,
        event_type="c13.thread.state_changed",
        principal=principal,
        summary=f"Health thread transitioned to {body.target_status.value}",
        extra={"thread_id": str(thread_id), "to_status": body.target_status.value},
    )
    await session.commit()
    row = await _load_owned(session, principal, thread_id)
    return _to_v1(row)
