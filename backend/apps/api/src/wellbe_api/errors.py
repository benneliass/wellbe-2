"""RFC 9457 Problem Details for the C13 boundary.

All handler-level failures raise ``ProblemError`` so the boundary returns a single
canonical error shape with a stable WellBe ``code`` (see ProblemCode). This keeps
user-facing detail safe while richer reason detail stays in the audit trail.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from wellbe_contracts.c13_api import ProblemCode, ProblemDetailsV2

_PROBLEM_BASE = "https://api.wellbe.example/problems/"


class ProblemError(Exception):
    """Raised by handlers/dependencies to emit an RFC 9457 Problem Details."""

    def __init__(
        self,
        *,
        status: int,
        code: ProblemCode,
        title: str,
        detail: str,
        correlation_id: str,
        audit_event_id: str | None = None,
        remediation: str | None = None,
    ) -> None:
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail
        self.correlation_id = correlation_id
        self.audit_event_id = audit_event_id
        self.remediation = remediation
        super().__init__(detail)

    def to_response(self) -> JSONResponse:
        problem = ProblemDetailsV2(
            type=f"{_PROBLEM_BASE}{self.code.value.replace('_', '-')}",
            title=self.title,
            status=self.status,
            code=self.code,
            detail=self.detail,
            correlation_id=self.correlation_id,
            audit_event_id=self.audit_event_id,
            remediation=self.remediation,
        )
        return JSONResponse(status_code=self.status, content=problem.model_dump(mode="json"))


async def problem_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ProblemError)
    return exc.to_response()


def unauthenticated_response(
    correlation_id: str, *, code: str = "unauthenticated", bearer: bool = False
) -> JSONResponse:
    """401 in RFC 9457 shape. Auth is outside the stable ProblemCode registry, so
    this uses a free-form code rather than polluting the contract enum."""
    detail = (
        "A valid bearer access token is required to call this endpoint."
        if code == "invalid_token"
        else "A resolved principal is required to call this endpoint."
    )
    return JSONResponse(
        status_code=401,
        headers={"WWW-Authenticate": 'Bearer error="invalid_token"'} if bearer else None,
        content={
            "type": f"{_PROBLEM_BASE}{code.replace('_', '-')}",
            "title": "Authentication required",
            "status": 401,
            "code": code,
            "detail": detail,
            "correlation_id": correlation_id,
        },
    )


def onboarding_required_response(correlation_id: str) -> JSONResponse:
    """403 for an authenticated identity that has not finished onboarding."""
    return JSONResponse(
        status_code=403,
        content={
            "type": f"{_PROBLEM_BASE}onboarding-required",
            "title": "Onboarding required",
            "status": 403,
            "code": "onboarding_required",
            "detail": "This identity has no active WellBe account yet; finish onboarding first.",
            "correlation_id": correlation_id,
        },
    )
