"""C13 /v1 capture route — the user-facing "Log something" write path.

CaptureModal -> this endpoint -> C3 ingestion adapter -> C2 immutable Vault, per
the approved decision docs/decisions/capture-write-path-contract.md:

- A common envelope ``{ capture_type, payload, occurred_at?, source? }`` with a
  type-specific payload (symptom / lab / document / note).
- A client ``Idempotency-Key`` header; the durable Vault id is a deterministic
  uuid5 of the natural key and the append is idempotent (ON CONFLICT) — a retried
  capture can never create a duplicate permanent raw record.
- Validate synchronously, perform the durable C2 append, return ``201`` with the
  raw record id and ``processing: "pending"``; C4 extraction runs asynchronously.

v1 is personal-first: the capture write path is controller self-capture only.
"""

from __future__ import annotations

import base64
import hashlib
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Header
from pydantic import BaseModel, Field
from wellbe_contracts.c13_api import ProblemCode

from wellbe_api.config import ApiSettings
from wellbe_api.deps import PrincipalDep, SessionDep, audit_ref, require_access
from wellbe_api.errors import ProblemError

router = APIRouter(prefix="/v1", tags=["v1-capture"])

_RESOURCE = "raw_context"
_settings = ApiSettings()

# Deterministic controller self-consent snapshot. The controller is always the
# data subject acting on their own data (personal-first); v1 capture does not
# support grant-scoped third-party writes.
_CONSENT_NS = uuid.UUID("0d6f4b51-3c2a-5e7d-8b19-7a4c2f6e9d30")


def _self_consent_snapshot(patient_id: uuid.UUID) -> uuid.UUID:
    return uuid.uuid5(_CONSENT_NS, f"controller-self-consent:{patient_id}")


class CaptureType(StrEnum):
    SYMPTOM = "symptom"
    LAB = "lab"
    DOCUMENT = "document"
    NOTE = "note"


class CaptureRequestV1(BaseModel):
    schema_version: str = "c13.capture.request.v1"
    capture_type: CaptureType
    # Type-specific payload — validated per capture_type below.
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime | None = None
    source: str | None = None
    thread_id: str | None = None


class CaptureResponseV1(BaseModel):
    schema_version: str = "c13.capture.response.v1"
    capture_id: str
    status: str = "captured"
    # Derived memory (C4 facts, C6 graph) is produced asynchronously; the raw
    # record is durable immediately.
    processing: str = "pending"


def _bad_request(detail: str, correlation_id: str) -> ProblemError:
    return ProblemError(
        status=422,
        code=ProblemCode.PROVENANCE_MISSING,
        title="Invalid capture payload",
        detail=detail,
        correlation_id=correlation_id,
    )


def _build_ingest(
    body: CaptureRequestV1, correlation_id: str
) -> tuple[str, bytes, dict[str, Any]]:
    """Map a capture envelope to (source_type, raw_data, source_metadata).

    Symptom / lab / note are user-entered text captures (manual_text adapter);
    document is a binary upload (document adapter). The product-level capture_type
    and structured fields are preserved in source_metadata; raw bytes stay raw.
    """
    payload = body.payload or {}
    metadata: dict[str, Any] = {"capture_type": body.capture_type.value}
    if body.thread_id:
        metadata["thread_id"] = body.thread_id
    if body.source:
        metadata["source"] = body.source

    if body.capture_type is CaptureType.SYMPTOM:
        description = (payload.get("description") or "").strip()
        if not description:
            raise _bad_request("symptom.payload.description is required", correlation_id)
        if payload.get("severity"):
            metadata["severity"] = payload["severity"]
        return "manual_text", description.encode("utf-8"), metadata

    if body.capture_type is CaptureType.NOTE:
        text = (payload.get("text") or payload.get("body") or "").strip()
        if not text:
            raise _bad_request("note.payload.text is required", correlation_id)
        return "manual_text", text.encode("utf-8"), metadata

    if body.capture_type is CaptureType.LAB:
        test_name = (payload.get("test_name") or "").strip()
        value = str(payload.get("value") or "").strip()
        if not test_name or not value:
            raise _bad_request(
                "lab.payload.test_name and value are required", correlation_id
            )
        unit = (payload.get("unit") or "").strip()
        reference_range = (payload.get("reference_range") or "").strip()
        metadata.update(
            {
                "test_name": test_name,
                "value": value,
                "unit": unit or None,
                "reference_range": reference_range or None,
            }
        )
        summary = f"{test_name}: {value} {unit}".strip()
        if reference_range:
            summary += f" (ref {reference_range})"
        return "manual_text", summary.encode("utf-8"), metadata

    # DOCUMENT
    content_b64 = payload.get("content_base64")
    if not content_b64:
        raise _bad_request("document.payload.content_base64 is required", correlation_id)
    try:
        raw = base64.b64decode(content_b64, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise _bad_request(
            "document.payload.content_base64 is not valid base64", correlation_id
        ) from exc
    if not raw:
        raise _bad_request("document payload is empty", correlation_id)
    mime_type = payload.get("mime_type") or "application/pdf"
    metadata["mime_type"] = mime_type
    filename = payload.get("filename")
    if filename:
        metadata["original_filename_hash"] = hashlib.sha256(
            filename.encode("utf-8")
        ).hexdigest()
    return "pdf", raw, metadata


@router.post("/capture", response_model=CaptureResponseV1, status_code=201)
async def create_capture(
    body: CaptureRequestV1,
    principal: PrincipalDep,
    session: SessionDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> CaptureResponseV1:
    await require_access(principal, session, action="write", resource_type=_RESOURCE)

    if not idempotency_key:
        raise ProblemError(
            status=400,
            code=ProblemCode.PROVENANCE_MISSING,
            title="Idempotency-Key required",
            detail="Capture is a non-idempotent write; supply an 'Idempotency-Key' header.",
            correlation_id=principal.correlation_id,
        )

    source_type, raw_data, metadata = _build_ingest(body, principal.correlation_id)
    occurred_at = body.occurred_at or datetime.now(UTC)
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=UTC)

    ingest_payload = {
        "source_type": source_type,
        "raw_data": base64.b64encode(raw_data).decode("ascii"),
        "patient_id": str(principal.patient_id),
        "actor_id": str(principal.actor_id),
        "consent_snapshot_id": str(_self_consent_snapshot(principal.patient_id)),
        "captured_at": occurred_at.isoformat(),
        "metadata": metadata,
        "correlation_id": principal.correlation_id,
        "trace_id": principal.trace_id,
        "idempotency_key": idempotency_key,
    }

    try:
        async with httpx.AsyncClient(
            base_url=_settings.ingestion_worker_url, timeout=30.0
        ) as client:
            resp = await client.post("/ingest", json=ingest_payload)
    except httpx.HTTPError as exc:
        raise ProblemError(
            status=503,
            code=ProblemCode.POLICY_UNAVAILABLE,
            title="Capture pipeline unavailable",
            detail="The ingestion pipeline could not be reached; the capture was not stored.",
            correlation_id=principal.correlation_id,
        ) from exc

    if resp.status_code == 422:
        raise _bad_request(
            f"Capture rejected by ingestion adapter: {resp.text}", principal.correlation_id
        )
    if resp.status_code >= 400:
        raise ProblemError(
            status=502,
            code=ProblemCode.POLICY_UNAVAILABLE,
            title="Capture pipeline error",
            detail=f"Ingestion returned {resp.status_code}.",
            correlation_id=principal.correlation_id,
        )

    event_id = resp.json()["event_id"]

    await audit_ref(
        session,
        event_type="c13.capture.created",
        principal=principal,
        summary=f"Capture stored ({body.capture_type.value})",
        extra={"capture_id": str(event_id), "capture_type": body.capture_type.value},
    )
    await session.commit()

    return CaptureResponseV1(capture_id=str(event_id))
