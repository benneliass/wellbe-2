"""C13 API & Contract Layer — FastAPI entrypoint stub."""
from __future__ import annotations

import hashlib
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from wellbe_contracts.c13_api import (
    AuditRefV2,
    ProblemCode,
    ProblemDetailsV2,
    RenderValidateRequestV2,
    RenderValidateResponseV2,
    SupportedSchemaVersionsV2,
)

app = FastAPI(
    title="WellBe API",
    version="0.1.0",
    description=(
        "Single external boundary. All surfaces call through here. "
        "See docs/architecture/component-map.md C13."
    ),
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v2/schema", response_model=SupportedSchemaVersionsV2)
async def v2_schema() -> SupportedSchemaVersionsV2:
    return SupportedSchemaVersionsV2()


@app.post("/v2/render/validate", response_model=None)
async def v2_render_validate(
    request: RenderValidateRequestV2,
) -> RenderValidateResponseV2 | JSONResponse:
    if request.render_approval is None:
        return _problem(
            status=428,
            code=ProblemCode.C10_TOKEN_REQUIRED,
            title="C10 render authorization is required",
            detail="User-facing AI output requires valid C10 render authorization.",
            correlation_id=request.correlation_id,
        )

    rendered_hash = _text_sha256(request.text)
    if rendered_hash != request.render_approval.binds_text_sha256:
        return _problem(
            status=409,
            code=ProblemCode.C10_TOKEN_HASH_MISMATCH,
            title="C10 render authorization does not match the output text",
            detail="The submitted text differs from the exact text C10 evaluated.",
            correlation_id=request.correlation_id,
            audit_event_id=request.render_approval.audit_event_id,
        )

    missing_obligations = [
        obligation.obligation_code
        for obligation in request.render_approval.obligations
        if obligation.blocking_if_unfulfilled
        and obligation.obligation_code not in request.surface_capabilities
    ]
    if missing_obligations:
        return _problem(
            status=409,
            code=ProblemCode.C10_OBLIGATIONS_UNFULFILLED,
            title="C10 display obligations cannot be fulfilled",
            detail="The rendering surface cannot fulfill all blocking C10 obligations.",
            correlation_id=request.correlation_id,
            audit_event_id=request.render_approval.audit_event_id,
        )

    audit_ref = AuditRefV2(
        audit_event_id=f"aud_render_{uuid4().hex}",
        correlation_id=request.correlation_id,
        visibility=["controller_visible"],
        event_summary="C10-approved output rendered",
    )
    return RenderValidateResponseV2(render_approval=request.render_approval, audit_ref=audit_ref)


def _text_sha256(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode()).hexdigest()}"


def _problem(
    *,
    status: int,
    code: ProblemCode,
    title: str,
    detail: str,
    correlation_id: str,
    audit_event_id: str | None = None,
) -> JSONResponse:
    problem = ProblemDetailsV2(
        type=f"https://api.wellbe.example/problems/{code.value.replace('_', '-')}",
        title=title,
        status=status,
        code=code,
        detail=detail,
        correlation_id=correlation_id,
        audit_event_id=audit_event_id,
    )
    return JSONResponse(status_code=status, content=problem.model_dump(mode="json"))
