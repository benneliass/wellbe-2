from __future__ import annotations

import hashlib
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from wellbe_c2_vault import S3BlobStore, VaultRepository
from wellbe_contracts.c2_vault import RawContextEvent, VaultWriteRequest, VaultWriteResponse
from wellbe_db import AsyncSessionFactory, create_engine, create_session_factory
from wellbe_events import emit_event

from wellbe_vault_writer.config import VaultWriterSettings

settings = VaultWriterSettings()

_session_factory: AsyncSessionFactory
_blob_store: S3BlobStore


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    global _session_factory, _blob_store  # noqa: PLW0603

    engine = create_engine(settings.database_url.get_secret_value())
    _session_factory = create_session_factory(engine)
    _blob_store = S3BlobStore(
        endpoint=settings.s3_endpoint,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        bucket=settings.s3_bucket_raw,
    )
    yield
    await engine.dispose()


app = FastAPI(
    title="WellBe Vault Writer",
    version="0.1.0",
    description="C2/C3 Vault Writer: the ONLY process with INSERT permission on raw_context_events.",
    lifespan=lifespan,
)


async def _get_session() -> AsyncGenerator[AsyncSession]:
    async with _session_factory() as session:
        yield session


@app.post("/vault/events", response_model=VaultWriteResponse, status_code=201)
async def write_event(
    req: VaultWriteRequest,
    session: AsyncSession = Depends(_get_session),
) -> VaultWriteResponse:
    content_hash = hashlib.sha256(req.normalized_payload).hexdigest()

    repo = VaultRepository(session)

    dup_id = await repo.find_duplicate(req.patient_id, content_hash)
    if dup_id is not None:
        existing = await repo.get_event(dup_id)
        if existing is None:
            raise HTTPException(status_code=500, detail="Duplicate record vanished")
        existing_ingested = existing.ingested_at
        if existing_ingested.tzinfo is None:
            existing_ingested = existing_ingested.replace(tzinfo=timezone.utc)
        return VaultWriteResponse(
            event_id=existing.id,
            content_hash=content_hash,
            duplicate_of_event_id=None,
            ingested_at=existing_ingested,
        )

    event_id = uuid.uuid4()
    blob_key = f"raw/patient/{req.patient_id}/event/{event_id}/blob"
    blob_version_id = await _blob_store.upload_blob(
        blob_key, req.normalized_payload, content_hash
    )

    now_aware = datetime.now(timezone.utc)
    now = now_aware.replace(tzinfo=None)  # naive UTC for TIMESTAMP WITHOUT TIME ZONE columns
    prov = req.adapter_provenance
    captured_at = prov.captured_at
    if hasattr(captured_at, "tzinfo") and captured_at.tzinfo is not None:
        captured_at = captured_at.replace(tzinfo=None)

    inserted_id = await repo.insert_event(
        id=event_id,
        patient_id=req.patient_id,
        actor_id=req.actor_id,
        source_type=prov.source_type,
        source_id=prov.source_id,
        external_source_id=prov.external_source_id,
        idempotency_key=req.idempotency_key,
        captured_at=captured_at,
        received_at=now,
        ingested_at=now,
        content_hash=content_hash,
        blob_ref=f"s3://{settings.s3_bucket_raw}/{blob_key}",
        blob_bucket=settings.s3_bucket_raw,
        blob_key=blob_key,
        blob_version_id=blob_version_id or None,
        byte_size=len(req.normalized_payload),
        mime_type=prov.mime_type,
        encoding=prov.encoding,
        language=prov.language,
        original_filename_hash=prov.original_filename_hash,
        source_metadata=prov.source_metadata,
        adapter_name=prov.adapter_name,
        adapter_version=prov.adapter_version,
        consent_snapshot_id=req.consent_snapshot_id,
        share_grant_id=req.share_grant_id,
        encryption_key_id="default",
        correlation_id=req.correlation_id,
        trace_id=req.trace_id,
        created_at=now,
    )  # now is naive UTC — TIMESTAMP WITHOUT TIME ZONE

    await emit_event(
        session,
        event_type="raw_context.received",
        payload={
            "event_id": str(inserted_id),
            "patient_id": str(req.patient_id),
            "source_type": prov.source_type,
            "content_hash": content_hash,
        },
        correlation_id=req.correlation_id,
        trace_id=req.trace_id,
    )

    await session.commit()

    return VaultWriteResponse(
        event_id=inserted_id,
        content_hash=content_hash,
        duplicate_of_event_id=None,
        ingested_at=now_aware,
    )


@app.get("/vault/events/{event_id}", response_model=RawContextEvent)
async def get_event(
    event_id: uuid.UUID,
    session: AsyncSession = Depends(_get_session),
) -> RawContextEvent:
    repo = VaultRepository(session)
    row = await repo.get_event(event_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return RawContextEvent.model_validate(row)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
