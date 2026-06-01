"""C13 API & Contract Layer — FastAPI entrypoint.

Single external boundary. All surfaces call through here. The boundary enforces
principal resolution, the C1/C17 access predicate, C5 provenance, C6 non-diagnosis,
C10 render authorization, and C12 audit. See docs/architecture/component-map.md C13
and docs/decisions/c13-versioned-api-contract-boundary.md.
"""

from __future__ import annotations

from fastapi import FastAPI

from wellbe_api.deps import UnauthenticatedError, lifespan
from wellbe_api.errors import ProblemError, problem_error_handler, unauthenticated_response
from wellbe_api.routers import access, investigations, render, threads_v1

app = FastAPI(
    title="WellBe API",
    version="0.1.0",
    description=(
        "Single external boundary. All surfaces call through here. "
        "See docs/architecture/component-map.md C13."
    ),
    lifespan=lifespan,
)

app.add_exception_handler(ProblemError, problem_error_handler)


@app.exception_handler(UnauthenticatedError)
async def _unauth_handler(_request: object, exc: UnauthenticatedError):  # noqa: ANN202
    return unauthenticated_response(exc.correlation_id)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(render.router)
app.include_router(threads_v1.router)
app.include_router(investigations.router)
app.include_router(access.router)
