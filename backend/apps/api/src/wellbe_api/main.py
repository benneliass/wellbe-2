"""C13 API & Contract Layer — FastAPI entrypoint.

Single external boundary. All surfaces call through here. The boundary enforces
principal resolution, the C1/C17 access predicate, C5 provenance, C6 non-diagnosis,
C10 render authorization, and C12 audit. See docs/architecture/component-map.md C13
and docs/decisions/c13-versioned-api-contract-boundary.md.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from wellbe_api.config import ApiSettings
from wellbe_api.deps import UnauthenticatedError, lifespan
from wellbe_api.errors import ProblemError, problem_error_handler, unauthenticated_response
from wellbe_api.routers import (
    access,
    ask_v2,
    capture_v1,
    delta_v2,
    graph_v2,
    investigations,
    onboarding_v1,
    patterns_v2,
    phase5,
    render,
    signals_v2,
    things_noticed_v1,
    threads_v1,
    visit_packets_v2,
)

app = FastAPI(
    title="WellBe API",
    version="0.1.0",
    description=(
        "Single external boundary. All surfaces call through here. "
        "See docs/architecture/component-map.md C13."
    ),
    lifespan=lifespan,
)

# CORS for the browser web app. Data requests send custom X-Wellbe-* headers
# (and Idempotency-Key / correlation ids), so they are always preflighted; an
# explicit allow-list is required for the cross-origin app.localhost -> api.localhost
# calls to succeed. Auth is header-based (no cookies), so credentials stay off.
_settings = ApiSettings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(ProblemError, problem_error_handler)


@app.exception_handler(UnauthenticatedError)
async def _unauth_handler(_request: object, exc: UnauthenticatedError) -> JSONResponse:
    return unauthenticated_response(exc.correlation_id)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(render.router)
app.include_router(threads_v1.router)
app.include_router(things_noticed_v1.router)
app.include_router(onboarding_v1.router)
app.include_router(capture_v1.router)
app.include_router(investigations.router)
app.include_router(access.router)
app.include_router(phase5.router)
app.include_router(visit_packets_v2.router)
app.include_router(ask_v2.router)
app.include_router(graph_v2.router)
app.include_router(patterns_v2.router)
app.include_router(delta_v2.router)
app.include_router(signals_v2.router)
