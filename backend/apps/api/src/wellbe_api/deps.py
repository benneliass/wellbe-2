"""C13 boundary dependencies: DB session, principal, C1/C17 access, C12 audit.

The boundary enforces, in order: principal resolution, then a C1/C17 access
predicate before any data is read or mutated (fail-closed), then handler logic,
then a C12 audit emit on critical paths. Audit is written through the shared
transactional outbox so it is durable and consistent with every other component.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, Header
from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_c1_consent import ConsentService
from wellbe_contracts.c13_api import AuditRefV2, ProblemCode
from wellbe_db import AsyncSessionFactory, create_engine, create_session_factory
from wellbe_events import emit_event

from wellbe_api.config import ApiSettings
from wellbe_api.errors import ProblemError

settings = ApiSettings()

_engine = None
_session_factory: AsyncSessionFactory | None = None
_redis: aioredis.Redis | None = None


def _ensure_factory() -> AsyncSessionFactory:
    """Build the engine/session factory on first use.

    Both the engine and the redis client connect lazily, so importing the app or
    resolving a dependency that does not query never opens a socket (keeps offline
    contract tests fast and infra-free)."""
    global _engine, _session_factory  # noqa: PLW0603
    if _session_factory is None:
        _engine = create_engine(settings.database_url.get_secret_value())
        _session_factory = create_session_factory(_engine)
    return _session_factory


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    _ensure_factory()
    yield
    if _engine is not None:
        await _engine.dispose()
    if _redis is not None:
        await _redis.aclose()


async def get_session() -> AsyncGenerator[AsyncSession]:
    factory = _ensure_factory()
    async with factory() as session:
        yield session


def get_redis() -> aioredis.Redis:
    global _redis  # noqa: PLW0603
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url)
    return _redis


SessionDep = Annotated[AsyncSession, Depends(get_session)]


class UnauthenticatedError(Exception):
    def __init__(self, correlation_id: str) -> None:
        self.correlation_id = correlation_id
        super().__init__("unauthenticated")


@dataclass(frozen=True)
class Principal:
    actor_id: uuid.UUID
    patient_id: uuid.UUID
    actor_type: str
    correlation_id: str
    trace_id: str

    @property
    def is_controller(self) -> bool:
        """The data subject acting on their own data — personal-first self-access."""
        return self.actor_id == self.patient_id and self.actor_type == "controller"


async def resolve_principal(
    x_wellbe_actor_id: Annotated[str | None, Header()] = None,
    x_wellbe_patient_id: Annotated[str | None, Header()] = None,
    x_wellbe_actor_type: Annotated[str, Header()] = "controller",
    x_correlation_id: Annotated[str | None, Header()] = None,
    x_trace_id: Annotated[str | None, Header()] = None,
) -> Principal:
    correlation_id = x_correlation_id or f"corr-{uuid.uuid4().hex[:12]}"
    if not x_wellbe_actor_id:
        raise UnauthenticatedError(correlation_id)
    try:
        actor_id = uuid.UUID(x_wellbe_actor_id)
        patient_id = uuid.UUID(x_wellbe_patient_id) if x_wellbe_patient_id else actor_id
    except ValueError as exc:
        raise UnauthenticatedError(correlation_id) from exc
    return Principal(
        actor_id=actor_id,
        patient_id=patient_id,
        actor_type=x_wellbe_actor_type,
        correlation_id=correlation_id,
        trace_id=x_trace_id or correlation_id,
    )


PrincipalDep = Annotated[Principal, Depends(resolve_principal)]


async def require_access(
    principal: Principal,
    session: AsyncSession,
    *,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID | None = None,
) -> None:
    """Fail-closed C1/C17 access predicate evaluated before any data access.

    Personal-first: the controller always has access to their own data. Any other
    principal must hold a live, in-scope C1 grant (capabilities default-deny).
    """
    if principal.is_controller:
        return
    consent = ConsentService(session, get_redis())
    allowed = await consent.check_scope(
        actor_id=principal.actor_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
    )
    if not allowed:
        raise ProblemError(
            status=403,
            code=ProblemCode.GRANT_REQUIRED,
            title="A live grant is required",
            detail=(
                "The principal is not the controller and holds no live grant with "
                f"'{action}' on '{resource_type}'."
            ),
            correlation_id=principal.correlation_id,
        )


async def audit_ref(
    session: AsyncSession,
    *,
    event_type: str,
    principal: Principal,
    summary: str,
    visibility: list[str] | None = None,
    extra: dict | None = None,
) -> AuditRefV2:
    """Emit a durable C13 audit event through the outbox and return its ref.

    Treated as part of the request's transaction boundary for critical paths.
    """
    payload = {
        "actor_id": str(principal.actor_id),
        "patient_id": str(principal.patient_id),
        "actor_type": principal.actor_type,
        "summary": summary,
        "occurred_at": datetime.now(UTC).isoformat(),
    }
    if extra:
        payload.update(extra)
    try:
        event_id = await emit_event(
            session=session,
            event_type=event_type,
            payload=payload,
            correlation_id=principal.correlation_id,
            trace_id=principal.trace_id,
        )
    except Exception as exc:  # noqa: BLE001 - audit write must fail closed
        raise ProblemError(
            status=500,
            code=ProblemCode.AUDIT_WRITE_FAILED,
            title="Audit write failed",
            detail="A required audit event could not be recorded; request aborted.",
            correlation_id=principal.correlation_id,
        ) from exc
    return AuditRefV2(
        audit_event_id=str(event_id),
        correlation_id=principal.correlation_id,
        trace_id=principal.trace_id,
        visibility=visibility or ["controller_visible"],
        event_summary=summary,
    )
