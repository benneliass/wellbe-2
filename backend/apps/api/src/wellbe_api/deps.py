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
from typing import Annotated, Any

import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_c1_consent import ConsentService, OnboardingService
from wellbe_contracts.c13_api import AuditRefV2, ProblemCode
from wellbe_db import AsyncSessionFactory, create_engine, create_session_factory
from wellbe_events import emit_event

from wellbe_api.auth import OidcVerifier, TokenInvalidError, bearer_token, http_jwks_fetcher
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
    if oidc_enabled():
        # Fail fast on a half-configured oidc deployment rather than 401-ing everyone.
        get_oidc_verifier()
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
    def __init__(
        self, correlation_id: str, *, code: str = "unauthenticated", bearer: bool = False
    ) -> None:
        self.correlation_id = correlation_id
        self.code = code
        self.bearer = bearer
        super().__init__(code)


class OnboardingRequiredError(Exception):
    """A verified identity with no finalized WellBe account: only onboarding routes
    are reachable until it completes."""

    def __init__(self, correlation_id: str) -> None:
        self.correlation_id = correlation_id
        super().__init__("onboarding_required")


_oidc_verifier: OidcVerifier | None = None


def get_oidc_verifier() -> OidcVerifier:
    global _oidc_verifier  # noqa: PLW0603
    if _oidc_verifier is None:
        _oidc_verifier = OidcVerifier(
            issuer=settings.oidc_issuer,
            audiences=settings.oidc_audiences,
            algorithms=settings.oidc_algorithm_list,
            leeway_seconds=settings.oidc_leeway_seconds,
            cache_ttl_seconds=settings.oidc_jwks_cache_ttl_seconds,
            fetch_jwks=http_jwks_fetcher(
                issuer=settings.oidc_issuer,
                jwks_url=settings.oidc_jwks_url,
                host_header=settings.oidc_jwks_host_header,
            ),
        )
    return _oidc_verifier


def oidc_enabled() -> bool:
    return settings.auth_mode == "oidc"


async def _verified_claims(request: Request, correlation_id: str) -> dict[str, Any]:
    try:
        token = bearer_token(request.headers.get("authorization"))
        return await get_oidc_verifier().verify(token)
    except TokenInvalidError as exc:
        raise UnauthenticatedError(correlation_id, code="invalid_token", bearer=True) from exc


def _correlation_id(x_correlation_id: str | None) -> str:
    return x_correlation_id or f"corr-{uuid.uuid4().hex[:12]}"


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
    request: Request,
    session: SessionDep,
    x_wellbe_actor_id: Annotated[str | None, Header()] = None,
    x_wellbe_patient_id: Annotated[str | None, Header()] = None,
    x_wellbe_actor_type: Annotated[str, Header()] = "controller",
    x_correlation_id: Annotated[str | None, Header()] = None,
    x_trace_id: Annotated[str | None, Header()] = None,
) -> Principal:
    correlation_id = _correlation_id(x_correlation_id)
    if oidc_enabled():
        return await _principal_from_token(
            request,
            session,
            x_wellbe_patient_id=x_wellbe_patient_id,
            correlation_id=correlation_id,
            trace_id=x_trace_id or correlation_id,
        )
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


async def _principal_from_token(
    request: Request,
    session: AsyncSession,
    *,
    x_wellbe_patient_id: str | None,
    correlation_id: str,
    trace_id: str,
) -> Principal:
    """OIDC principal: the actor is the account bound to the verified (iss, sub).

    X-Wellbe-Actor-Id / -Actor-Type are never read here. X-Wellbe-Patient-Id may
    name another patient, but that only yields a non-controller principal, which
    require_access then admits solely on a live C1 grant (fail-closed)."""
    claims = await _verified_claims(request, correlation_id)
    actor_id = await OnboardingService(session).active_controller_patient_id(
        issuer=claims["iss"], subject=claims["sub"]
    )
    if actor_id is None:
        raise OnboardingRequiredError(correlation_id)
    try:
        patient_id = uuid.UUID(x_wellbe_patient_id) if x_wellbe_patient_id else actor_id
    except ValueError as exc:
        raise UnauthenticatedError(correlation_id) from exc
    return Principal(
        actor_id=actor_id,
        patient_id=patient_id,
        actor_type="controller" if patient_id == actor_id else "user",
        correlation_id=correlation_id,
        trace_id=trace_id,
    )


PrincipalDep = Annotated[Principal, Depends(resolve_principal)]


@dataclass(frozen=True)
class Identity:
    """The authenticated federated identity, present *before* onboarding.

    This is the (issuer, subject) pair an OIDC id-token would carry. Onboarding
    resolves it to a WellBe controller account; it is deliberately distinct from
    Principal, which requires a resolved patient/controller. In dev-headers mode it
    comes from X-Wellbe-Issuer / X-Wellbe-Subject; in oidc mode from the verified
    access token's ``iss`` / ``sub`` (the headers are ignored).
    """

    issuer: str
    subject: str
    display_name: str | None
    contact_email: str | None
    correlation_id: str
    trace_id: str


async def resolve_identity(
    request: Request,
    x_wellbe_issuer: Annotated[str, Header()] = "dev-local",
    x_wellbe_subject: Annotated[str | None, Header()] = None,
    x_wellbe_display_name: Annotated[str | None, Header()] = None,
    x_wellbe_email: Annotated[str | None, Header()] = None,
    x_correlation_id: Annotated[str | None, Header()] = None,
    x_trace_id: Annotated[str | None, Header()] = None,
) -> Identity:
    correlation_id = _correlation_id(x_correlation_id)
    if oidc_enabled():
        claims = await _verified_claims(request, correlation_id)
        name = claims.get("name") or claims.get("preferred_username")
        email = claims.get("email") if claims.get("email_verified") else None
        return Identity(
            issuer=claims["iss"],
            subject=claims["sub"],
            display_name=name if isinstance(name, str) else None,
            contact_email=email if isinstance(email, str) else None,
            correlation_id=correlation_id,
            trace_id=x_trace_id or correlation_id,
        )
    if not x_wellbe_subject:
        raise UnauthenticatedError(correlation_id)
    return Identity(
        issuer=x_wellbe_issuer,
        subject=x_wellbe_subject,
        display_name=x_wellbe_display_name,
        contact_email=x_wellbe_email,
        correlation_id=correlation_id,
        trace_id=x_trace_id or correlation_id,
    )


IdentityDep = Annotated[Identity, Depends(resolve_identity)]


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
        patient_id=principal.patient_id,
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
    extra: dict[str, Any] | None = None,
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
