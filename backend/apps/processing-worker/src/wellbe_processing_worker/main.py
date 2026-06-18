"""C4 Processing Worker: Dramatiq lightweight extraction jobs."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from wellbe_processing_worker.config import ProcessingWorkerSettings

logger = logging.getLogger(__name__)


async def _dispatch_outbox_loop(settings: ProcessingWorkerSettings) -> None:
    """Background task: poll outbox for raw_context.received and dispatch to extractor."""
    from wellbe_processing_worker.tasks import _extract_facts
    from wellbe_events.models import OutboxEventRow
    from wellbe_db import create_engine, create_session_factory

    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    vault_client = httpx.AsyncClient(base_url=settings.vault_writer_url, timeout=30.0)

    try:
        while True:
            try:
                async with session_factory() as session:
                    stmt = (
                        select(OutboxEventRow)
                        .where(OutboxEventRow.delivered_at.is_(None))
                        .where(OutboxEventRow.event_type == "raw_context.received")
                        .order_by(OutboxEventRow.created_at)
                        .limit(20)
                        # Claim rows so a second poller instance cannot pick up the
                        # same undelivered events concurrently. Combined with the
                        # idempotent C4/C5 writes, this prevents duplicate processing.
                        .with_for_update(skip_locked=True)
                    )
                    result = await session.execute(stmt)
                    rows = result.scalars().all()

                    if rows:
                        # Only events that reach a terminal state (processed, or
                        # permanently unprocessable) are marked delivered. Transient
                        # failures (e.g. vault unreachable) are intentionally left
                        # undelivered so the next poll retries them — marking them
                        # delivered on error silently drops data and breaks the
                        # at-least-once guarantee.
                        ids = []
                        for row in rows:
                            try:
                                event_id = (
                                    row.payload.get("event_id")
                                    if isinstance(row.payload, dict)
                                    else None
                                )
                                if event_id is None:
                                    # Malformed event with no vault ref — can never be
                                    # processed; mark delivered to avoid a poison-pill loop.
                                    ids.append(row.id)
                                    continue

                                vault_resp = await vault_client.get(f"/vault/events/{event_id}")
                                if vault_resp.status_code == 404:
                                    logger.warning(
                                        "vault event %s not found (404); skipping", event_id
                                    )
                                    ids.append(row.id)
                                    continue
                                if vault_resp.status_code != 200:
                                    # Transient upstream error — retry on the next poll.
                                    logger.warning(
                                        "vault fetch for %s returned %s; will retry",
                                        event_id,
                                        vault_resp.status_code,
                                    )
                                    continue

                                vault_event = vault_resp.json()
                                source_metadata = vault_event.get("source_metadata") or {}
                                text_content = source_metadata.get("text", "")
                                # The captured text lives in the raw blob, not in
                                # source_metadata (raw stays raw). Fetch it so the
                                # extractor has real input; without this the C4
                                # pipeline runs on empty text and produces no facts.
                                source_type = vault_event.get("source_type")
                                if not text_content and source_type == "manual_text":
                                    content_resp = await vault_client.get(
                                        f"/vault/events/{event_id}/content"
                                    )
                                    if content_resp.status_code == 200:
                                        text_content = content_resp.content.decode(
                                            "utf-8", errors="replace"
                                        )
                                    else:
                                        # Couldn't retrieve the raw content — retry
                                        # later rather than extract from nothing.
                                        logger.warning(
                                            "content fetch for %s returned %s; will retry",
                                            event_id,
                                            content_resp.status_code,
                                        )
                                        continue
                                vault_event["_raw_text"] = text_content

                                await _extract_facts(json.dumps(vault_event))
                                ids.append(row.id)
                            except Exception:
                                # Do NOT mark delivered — leave undelivered for retry.
                                logger.exception("error dispatching event %s; will retry", row.id)

                        if ids:
                            await session.execute(
                                update(OutboxEventRow)
                                .where(OutboxEventRow.id.in_(ids))
                                .values(delivered_at=datetime.utcnow())
                            )
                            await session.commit()
                            logger.info("dispatched %d outbox events", len(ids))

            except Exception:
                logger.exception("outbox dispatch loop error")

            await asyncio.sleep(2.0)
    finally:
        await vault_client.aclose()


@asynccontextmanager
async def lifespan(app: FastAPI):
    import wellbe_processing_worker.tasks  # noqa: F401 — registers Dramatiq actors
    task = asyncio.create_task(_dispatch_outbox_loop(settings))
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


settings = ProcessingWorkerSettings()
app = FastAPI(title=settings.service_name, lifespan=lifespan)

_engine = create_async_engine(settings.database_url, pool_pre_ping=True)


def _valid_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {value}")


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}


@app.get("/query/facts/{patient_id}")
async def query_facts(patient_id: str) -> list[dict[str, Any]]:
    """Return extracted facts for a patient from processing.extracted_facts."""
    pid = _valid_uuid(patient_id)
    async with AsyncSession(_engine) as session:
        result = await session.execute(
            text(
                "SELECT fact_type, entity_label, normalized_key, "
                "extraction_confidence, quality_flag "
                "FROM processing.extracted_facts "
                "WHERE patient_id = :pid "
                "ORDER BY created_at"
            ),
            {"pid": pid},
        )
        rows = result.mappings().all()
    return [dict(r) for r in rows]


@app.get("/query/graph-nodes/{patient_id}")
async def query_graph_nodes(patient_id: str) -> list[dict[str, Any]]:
    """Return KG nodes for a patient from graph.kg_nodes."""
    pid = _valid_uuid(patient_id)
    async with AsyncSession(_engine) as session:
        result = await session.execute(
            text(
                "SELECT node_type, normalized_key, display_label "
                "FROM graph.kg_nodes "
                "WHERE patient_id = :pid "
                "ORDER BY created_at"
            ),
            {"pid": pid},
        )
        rows = result.mappings().all()
    return [dict(r) for r in rows]
