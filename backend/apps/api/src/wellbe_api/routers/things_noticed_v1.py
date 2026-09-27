"""C13 /v1 "Things noticed" routes — the pending thread-candidate surface.

A candidate is the calm, lossless destination for weak/ambiguous concern signals
that genesis is not confident enough to open as a Health Thread (genesis Stories
C0/B1). This surface lets the controller see what WellBe noticed and act on it,
mirroring the relevance-candidate card actions:

- accept        -> ``confirm``: opens a Health Thread (terminal, ``promoted``);
- reject        -> ``dismiss``: not related, never resurfaced (terminal, ``dismissed``);
- ignore for now -> ``ignore``: stays pending, hidden until it is seen again;
- remind later  -> ``snooze``: stays pending, hidden until a chosen moment.

Personal-first and never-alarm: every read/write is scoped to the calling
controller, a candidate that is not theirs is invisible (404, not 403, so the
existence of another user's candidate is never leaked), and confirmation creates a
user-initiated thread (never a system auto-create) so the user stays in control.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from pydantic import AwareDatetime, BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_c7_thread import ThreadService
from wellbe_c9_continuity.genesis import GenesisCandidateService
from wellbe_c9_continuity.genesis.candidate_repository import CandidateRepository
from wellbe_c9_continuity.genesis.models import GenesisCandidateRow
from wellbe_c9_continuity.genesis.thread_linkage import ThreadLinkageService
from wellbe_contracts.c7_thread import ThreadCreatedBy
from wellbe_contracts.c13_api import ProblemCode
from wellbe_contracts.genesis import CandidateStatus, ThreadCandidate

from wellbe_api.deps import Principal, PrincipalDep, SessionDep, audit_ref, require_access
from wellbe_api.errors import ProblemError

router = APIRouter(prefix="/v1", tags=["v1-things-noticed"])

_RESOURCE = "thread_candidate"


class ThingNoticedV1(BaseModel):
    schema_version: str = "c13.thing_noticed.v1"
    candidate_id: str
    title: str
    candidate_type: str
    status: str
    seen_count: int
    confidence: float | None = None
    reason_code: str | None = None
    first_seen_at: datetime
    last_seen_at: datetime
    promoted_thread_id: str | None = None
    source_capture_count: int = 0
    source_fact_count: int = 0
    snoozed_until: datetime | None = None
    ignored_at: datetime | None = None


_MAX_SNOOZE = timedelta(days=365)


class SnoozeThingNoticedV1(BaseModel):
    """Remind me later: hide the candidate until ``until`` (future, within a year)."""

    until: AwareDatetime

    @field_validator("until")
    @classmethod
    def _within_window(cls, value: datetime) -> datetime:
        now = datetime.now(UTC)
        if value <= now:
            raise ValueError("until must be in the future")
        if value - now > _MAX_SNOOZE:
            raise ValueError("until must be within a year")
        return value


class ConfirmResponseV1(BaseModel):
    schema_version: str = "c13.thing_noticed_confirm.v1"
    candidate_id: str
    thread_id: str
    status: str


def _to_v1(candidate: ThreadCandidate) -> ThingNoticedV1:
    return ThingNoticedV1(
        candidate_id=str(candidate.candidate_id),
        title=candidate.display_title,
        candidate_type=candidate.candidate_type.value,
        status=candidate.status.value,
        seen_count=candidate.seen_count,
        confidence=candidate.confidence,
        reason_code=candidate.reason_code,
        first_seen_at=candidate.first_seen_at,
        last_seen_at=candidate.last_seen_at,
        promoted_thread_id=(
            str(candidate.promoted_thread_id)
            if candidate.promoted_thread_id is not None
            else None
        ),
        source_capture_count=len(candidate.source_capture_ids),
        source_fact_count=len(candidate.source_fact_ids),
        snoozed_until=candidate.snoozed_until,
        ignored_at=candidate.ignored_at,
    )


async def _load_owned_candidate(
    session: AsyncSession, principal: Principal, candidate_id: uuid.UUID
) -> GenesisCandidateRow:
    """Fetch a candidate, returning 404 if it is missing or not the caller's.

    The candidate repository does not filter by user, so ownership is enforced
    here — mirrors ``threads_v1._load_owned``.
    """
    repo = CandidateRepository(session)
    row = await repo.get(candidate_id)
    if row is None or row.user_id != principal.patient_id:
        raise ProblemError(
            status=404,
            code=ProblemCode.GRANT_REQUIRED,
            title="Candidate not found",
            detail="No thing-noticed with that id is visible to the principal.",
            correlation_id=principal.correlation_id,
        )
    return row


def _require_pending(row: GenesisCandidateRow, principal: Principal) -> None:
    """Guard mutating actions so they only apply to a pending candidate.

    Prevents a second confirm from spawning a duplicate thread, or acting on an
    already-dismissed/merged candidate.
    """
    if row.status != CandidateStatus.PENDING.value:
        raise ProblemError(
            status=409,
            code=ProblemCode.SCOPE_DENIED,
            title="Candidate is not pending",
            detail=f"This thing-noticed is already '{row.status}' and cannot be changed.",
            correlation_id=principal.correlation_id,
        )


@router.get("/things-noticed", response_model=list[ThingNoticedV1])
async def list_things_noticed(
    principal: PrincipalDep, session: SessionDep
) -> list[ThingNoticedV1]:
    await require_access(principal, session, action="read", resource_type=_RESOURCE)
    svc = GenesisCandidateService(session)
    candidates = await svc.list_things_noticed(principal.patient_id)
    return [_to_v1(c) for c in candidates]


@router.post("/things-noticed/{candidate_id}/dismiss", response_model=ThingNoticedV1)
async def dismiss_thing_noticed(
    candidate_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> ThingNoticedV1:
    await require_access(
        principal, session, action="write", resource_type=_RESOURCE, resource_id=candidate_id
    )
    row = await _load_owned_candidate(session, principal, candidate_id)
    _require_pending(row, principal)
    svc = GenesisCandidateService(session)
    candidate = await svc.dismiss(candidate_id)
    await audit_ref(
        session,
        event_type="c13.things_noticed.dismissed",
        principal=principal,
        summary="Thing noticed dismissed",
        extra={"candidate_id": str(candidate_id)},
    )
    await session.commit()
    return _to_v1(candidate)


@router.post("/things-noticed/{candidate_id}/ignore", response_model=ThingNoticedV1)
async def ignore_thing_noticed(
    candidate_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> ThingNoticedV1:
    """Ignore for now: no decision; it comes back if it is noticed again."""
    await require_access(
        principal, session, action="write", resource_type=_RESOURCE, resource_id=candidate_id
    )
    row = await _load_owned_candidate(session, principal, candidate_id)
    _require_pending(row, principal)
    svc = GenesisCandidateService(session)
    candidate = await svc.ignore(candidate_id)
    await audit_ref(
        session,
        event_type="c13.things_noticed.ignored",
        principal=principal,
        summary="Thing noticed ignored for now",
        extra={"candidate_id": str(candidate_id)},
    )
    await session.commit()
    return _to_v1(candidate)


@router.post("/things-noticed/{candidate_id}/snooze", response_model=ThingNoticedV1)
async def snooze_thing_noticed(
    candidate_id: uuid.UUID,
    body: SnoozeThingNoticedV1,
    principal: PrincipalDep,
    session: SessionDep,
) -> ThingNoticedV1:
    """Remind me later: hidden until ``until``, then it reappears unchanged."""
    await require_access(
        principal, session, action="write", resource_type=_RESOURCE, resource_id=candidate_id
    )
    row = await _load_owned_candidate(session, principal, candidate_id)
    _require_pending(row, principal)
    svc = GenesisCandidateService(session)
    candidate = await svc.snooze(candidate_id, until=body.until)
    await audit_ref(
        session,
        event_type="c13.things_noticed.snoozed",
        principal=principal,
        summary="Thing noticed snoozed",
        extra={"candidate_id": str(candidate_id), "until": body.until.isoformat()},
    )
    await session.commit()
    return _to_v1(candidate)


@router.post("/things-noticed/{candidate_id}/confirm", response_model=ConfirmResponseV1)
async def confirm_thing_noticed(
    candidate_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> ConfirmResponseV1:
    await require_access(
        principal, session, action="write", resource_type=_RESOURCE, resource_id=candidate_id
    )
    row = await _load_owned_candidate(session, principal, candidate_id)
    _require_pending(row, principal)

    # User-initiated thread (created_by=user): the controller is choosing to track
    # this concern. The candidate's concern_key carries forward so the new thread
    # dedups against future genesis decisions. The candidate is then marked
    # promoted into this thread; both writes land in one transaction.
    threads = ThreadService(session)
    thread_id = await threads.create_thread(
        patient_id=principal.patient_id,
        title=row.display_title,
        created_by=ThreadCreatedBy.USER,
        created_via="things_noticed_confirm",
        concern_key=dict(row.concern_key or {}),
        correlation_id=principal.correlation_id,
        trace_id=principal.trace_id,
    )
    # Carry what was noticed into the thread: C5 evidence, C6 thread scope, and
    # C8 clinical memory — otherwise the confirmed thread is an empty shell.
    linkage = await ThreadLinkageService(session).link_facts(
        patient_id=principal.patient_id,
        thread_id=thread_id,
        fact_ids=list(row.source_fact_ids or []),
        correlation_id=principal.correlation_id,
        trace_id=principal.trace_id,
        linked_by="user",
    )
    svc = GenesisCandidateService(session)
    candidate = await svc.promote(candidate_id, thread_id=thread_id)
    await audit_ref(
        session,
        event_type="c13.things_noticed.confirmed",
        principal=principal,
        summary="Thing noticed confirmed into a health thread",
        extra={
            "candidate_id": str(candidate_id),
            "thread_id": str(thread_id),
            "evidence_links": len(linkage.evidence_links),
            "graph_nodes": linkage.nodes_tagged,
        },
    )
    await session.commit()
    return ConfirmResponseV1(
        candidate_id=str(candidate_id),
        thread_id=str(thread_id),
        status=candidate.status.value,
    )
