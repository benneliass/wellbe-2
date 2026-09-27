"""C4 Processing Worker: Dramatiq lightweight extraction jobs."""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from wellbe_c9_continuity.errors import OutOfOrderThreadEventError
from wellbe_events.retry import (
    BacklogStats,
    RetryPolicy,
    backlog_summary,
    claimable,
    decide_failure,
    failure_values,
    format_error,
    log_failure,
)

from wellbe_processing_worker.config import ProcessingWorkerSettings

logging.basicConfig(
    level=os.environ.get("WELLBE_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


def _is_pdf(vault_event: dict[str, Any]) -> bool:
    return (
        vault_event.get("mime_type") == "application/pdf"
        or vault_event.get("source_type") == "pdf"
    )


def _pdf_text_layer(content: bytes) -> str:
    """Text layer of a digital PDF ("" for image-only/unreadable documents)."""
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(content))
        return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    except Exception:
        logger.warning("could not read PDF text layer", exc_info=True)
        return ""


class VaultFetchError(RuntimeError):
    """The vault could not serve an event right now; the outbox row is retried."""


OutboxHandler = Callable[[AsyncSession, dict[str, Any], uuid.UUID], Awaitable[str | None]]


def _make_raw_context_handler(vault_client: httpx.AsyncClient) -> OutboxHandler:
    """Handler for raw_context.received: fetch the vault event and run extraction.

    Returns normally for terminal outcomes (processed, or permanently
    unprocessable) so the row is marked delivered. Raises for transient
    failures (e.g. vault unreachable) so the outbox retry policy backs off and
    eventually dead-letters instead of silently dropping data.
    """
    from wellbe_processing_worker.tasks import _extract_facts

    async def fetch(path: str, what: str) -> httpx.Response:
        resp = await vault_client.get(path)
        if resp.status_code != 200:
            raise VaultFetchError(f"{what} fetch {path} returned {resp.status_code}")
        return resp

    async def handle(
        session: AsyncSession, payload: dict[str, Any], row_id: uuid.UUID
    ) -> str | None:
        event_id = payload.get("event_id") if isinstance(payload, dict) else None
        if event_id is None:
            # Malformed event with no vault ref — can never be processed.
            return "skipped: no event_id"

        vault_resp = await vault_client.get(f"/vault/events/{event_id}")
        if vault_resp.status_code == 404:
            logger.warning("vault event %s not found (404); skipping", event_id)
            return "skipped: vault 404"
        if vault_resp.status_code != 200:
            raise VaultFetchError(f"vault event {event_id} returned {vault_resp.status_code}")

        vault_event = vault_resp.json()
        source_metadata = vault_event.get("source_metadata") or {}
        text_content = source_metadata.get("text", "")
        # The captured text lives in the raw blob, not in source_metadata (raw
        # stays raw). Fetch it so the extractor has real input; without this the
        # C4 pipeline runs on empty text and produces no facts.
        content_path = f"/vault/events/{event_id}/content"
        if not text_content and vault_event.get("source_type") == "manual_text":
            content_resp = await fetch(content_path, "content")
            text_content = content_resp.content.decode("utf-8", errors="replace")
        if not text_content and _is_pdf(vault_event):
            content_resp = await fetch(content_path, "document")
            text_content = _pdf_text_layer(content_resp.content)
            logger.info(
                "document %s: %d bytes, text layer %d chars",
                event_id,
                len(content_resp.content),
                len(text_content),
            )
        vault_event["_raw_text"] = text_content

        await _extract_facts(json.dumps(vault_event))
        return "dispatched"

    return handle


async def _dispatch_outbox_loop(settings: ProcessingWorkerSettings) -> None:
    """Background task: poll outbox for raw_context.received and dispatch to extractor."""
    vault_client = httpx.AsyncClient(base_url=settings.vault_writer_url, timeout=30.0)
    try:
        await _consume_outbox_loop(
            settings,
            event_type="raw_context.received",
            handler=_make_raw_context_handler(vault_client),
        )
    finally:
        await vault_client.aclose()


def _retry_policy(settings: ProcessingWorkerSettings) -> RetryPolicy:
    return RetryPolicy(
        max_attempts=settings.outbox_max_attempts,
        max_delay_seconds=settings.outbox_max_backoff_seconds,
    )


async def _consume_outbox_loop(
    settings: ProcessingWorkerSettings,
    *,
    event_type: str,
    handler: OutboxHandler,
    transient_errors: tuple[type[BaseException], ...] = (),
    interval: float = 2.0,
) -> None:
    """Background task: poll the outbox for one event type and run ``handler``.

    Claims claimable rows (undelivered, not dead-lettered, not backing off) with
    FOR UPDATE SKIP LOCKED so a second poller cannot double-process, runs each
    event in its own committing session, then marks successes delivered.
    Handlers are idempotent, so a redelivered event re-runs as a no-op.

    Failures are recorded on the row per ``wellbe_events.retry``: backoff with
    jitter, a single WARNING per retry, dead-lettering after
    ``outbox_max_attempts``. ``transient_errors`` are deferred briefly without
    counting toward the limit. Failure bookkeeping is written by the claim
    transaction because it already holds the row lock; a separate transaction
    would block on that lock.
    """
    from wellbe_db import create_engine, create_session_factory
    from wellbe_events.models import OutboxEventRow

    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    policy = _retry_policy(settings)
    age = func.extract("epoch", func.now() - OutboxEventRow.created_at)

    while True:
        try:
            async with session_factory() as claim_session:
                stmt = (
                    select(OutboxEventRow, age)
                    .where(claimable())
                    .where(OutboxEventRow.event_type == event_type)
                    .order_by(OutboxEventRow.created_at)
                    .limit(20)
                    .with_for_update(skip_locked=True)
                )
                claimed = (await claim_session.execute(stmt)).all()

                ids = []
                failed = 0
                for row, age_seconds in claimed:
                    try:
                        async with session_factory() as work_session:
                            outcome = await handler(work_session, row.payload, row.id)
                            await work_session.commit()
                        ids.append(row.id)
                        logger.info("%s %s -> %s", event_type, row.id, outcome or "ok")
                    except Exception as exc:
                        decision = decide_failure(
                            attempts=row.attempts,
                            exc=exc,
                            policy=policy,
                            transient=isinstance(exc, transient_errors),
                            age_seconds=float(age_seconds or 0.0),
                            previous_error=row.last_error,
                        )
                        log_failure(
                            logger,
                            decision,
                            event_type=event_type,
                            row_id=row.id,
                            exc=exc,
                            policy=policy,
                        )
                        await claim_session.execute(
                            update(OutboxEventRow)
                            .where(OutboxEventRow.id == row.id)
                            .values(**failure_values(decision))
                            .execution_options(synchronize_session=False)
                        )
                        failed += 1

                if ids:
                    await claim_session.execute(
                        update(OutboxEventRow)
                        .where(OutboxEventRow.id.in_(ids))
                        .values(delivered_at=datetime.now(UTC).replace(tzinfo=None))
                        .execution_options(synchronize_session=False)
                    )
                if ids or failed:
                    await claim_session.commit()
        except Exception:
            logger.exception("%s consumer loop error", event_type)

        await asyncio.sleep(interval)


_BACKLOG_SQL = text(
    """
    SELECT event_type,
           count(*) FILTER (WHERE dead_lettered_at IS NULL AND last_error IS NULL) AS pending,
           count(*) FILTER (WHERE dead_lettered_at IS NULL AND last_error IS NOT NULL)
               AS retrying,
           count(*) FILTER (WHERE dead_lettered_at IS NOT NULL) AS dead,
           extract(epoch FROM now() - min(created_at) FILTER (WHERE dead_lettered_at IS NULL))
               AS oldest_live_age_seconds
    FROM events.outbox_events
    WHERE delivered_at IS NULL
    GROUP BY event_type
    """
)


async def _outbox_health_loop(settings: ProcessingWorkerSettings) -> None:
    """Periodically log one line when the outbox has dead-lettered or stuck rows."""
    from wellbe_db import create_engine, create_session_factory

    session_factory = create_session_factory(create_engine(settings.database_url))
    interval = settings.outbox_health_interval_seconds
    while True:
        await asyncio.sleep(interval)
        try:
            async with session_factory() as session:
                rows = (await session.execute(_BACKLOG_SQL)).mappings().all()
            summary = backlog_summary(
                (
                    BacklogStats(
                        event_type=r["event_type"],
                        pending=r["pending"],
                        retrying=r["retrying"],
                        dead=r["dead"],
                        oldest_live_age_seconds=(
                            None
                            if r["oldest_live_age_seconds"] is None
                            else float(r["oldest_live_age_seconds"])
                        ),
                    )
                    for r in rows
                ),
                stale_after_seconds=interval,
            )
            if summary:
                logger.warning("outbox health: %s", summary)
        except Exception as exc:
            logger.warning("outbox health check failed: %s", format_error(exc, 300))


async def _handle_genesis_input_ready(
    session: AsyncSession, payload: dict[str, Any], event_id: uuid.UUID
) -> str:
    from wellbe_c9_continuity.genesis import ThreadGenesisService
    from wellbe_contracts.genesis import GenesisInputReadyPayload

    records = await ThreadGenesisService(session).handle_input_ready(
        GenesisInputReadyPayload.model_validate(payload)
    )
    return ", ".join(
        f"{r.decision.value}({r.reason_code})" + (" replay" if r.idempotent_replay else "")
        for r in records
    ) or "no facts"


# A successor transition consumed before its predecessor: retried quietly until
# the predecessor lands (see wellbe_events.retry for the age bound).
THREAD_STATE_TRANSIENT_ERRORS: tuple[type[BaseException], ...] = (OutOfOrderThreadEventError,)


async def _handle_thread_state_changed(
    session: AsyncSession, payload: dict[str, Any], event_id: uuid.UUID
) -> str:
    from wellbe_c9_continuity import ContinuityService
    from wellbe_contracts.c7_thread import ThreadStateChangedPayload

    event = ThreadStateChangedPayload.model_validate(payload)
    applied = await ContinuityService(session).reconcile_thread_state_changed(
        payload=event,
        event_id=event_id,
        correlation_id=event.correlation_id,
        trace_id=event.trace_id,
    )
    return (
        f"c9 {'applied' if applied else 'duplicate'} "
        f"{event.from_status.value}->{event.to_status.value} seq={event.transition_seq}"
    )


async def _reconcile_thread_linkage(settings: ProcessingWorkerSettings) -> None:
    """Idempotently re-project every thread's facts and every capture's edges.

    Threads created before thread linkage existed have no evidence/graph/memory
    projection, and captures processed before edge building have no edges. Every
    step is idempotent (dedup constraints, deterministic keys, observation keys),
    so this runs at each start and only writes what is missing.
    """
    from wellbe_c9_continuity.genesis.thread_linkage import ThreadLinkageService
    from wellbe_db import create_engine, create_session_factory

    from wellbe_processing_worker.tasks import _link_co_occurrence

    session_factory = create_session_factory(create_engine(settings.database_url))
    try:
        async with session_factory() as session:
            links = (
                await session.execute(
                    text(
                        """
                        SELECT user_id, target_thread_id AS thread_id, fact_ids
                        FROM genesis.genesis_decisions WHERE target_thread_id IS NOT NULL
                        UNION ALL
                        SELECT user_id, promoted_thread_id, source_fact_ids
                        FROM genesis.thread_candidates WHERE promoted_thread_id IS NOT NULL
                        """
                    )
                )
            ).mappings().all()
            captures = (
                await session.execute(
                    text(
                        """
                        SELECT raw_context_event_id, patient_id, min(captured_at) AS captured_at
                        FROM processing.extracted_facts
                        GROUP BY raw_context_event_id, patient_id
                        ORDER BY min(captured_at)
                        """
                    )
                )
            ).mappings().all()
        linked = 0
        for row in links:
            async with session_factory() as session:
                result = await ThreadLinkageService(session).link_facts(
                    patient_id=row["user_id"],
                    thread_id=row["thread_id"],
                    fact_ids=list(row["fact_ids"] or []),
                    correlation_id="reconcile-thread-linkage",
                    trace_id="reconcile-thread-linkage",
                )
                await session.commit()
                linked += result.nodes_tagged + result.memories_created
        edges = 0
        for cap in captures:
            edges += await _link_co_occurrence(
                raw_event_id=cap["raw_context_event_id"],
                patient_id=cap["patient_id"],
                captured_at=cap["captured_at"],
            )
        projections = await _reconcile_projections(session_factory)
        logger.info(
            "reconciliation done: %d thread link row(s), %d new node/memory link(s); "
            "%d capture(s), %d new edge observation(s); %d investigation/theory projection(s)",
            len(links),
            linked,
            len(captures),
            edges,
            projections,
        )
    except Exception:
        logger.exception("thread linkage reconciliation failed")


async def _reconcile_projections(session_factory: Any) -> int:
    """Place existing Investigation/Theory projection nodes into their threads."""
    from wellbe_c6_graph import GraphRepository
    from wellbe_c6_graph.projection import project_into_thread

    async with session_factory() as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT i.id AS investigation_id, i.patient_id, i.projection_node_id,
                           it.thread_id, t.id AS theory_id,
                           t.projection_node_id AS theory_node_id
                    FROM c14.investigations i
                    JOIN c14.investigation_threads it ON it.investigation_id = i.id
                    LEFT JOIN c15.theories t ON t.linked_investigation_id = i.id
                    WHERE i.projection_node_id IS NOT NULL
                    """
                )
            )
        ).mappings().all()
        graph = GraphRepository(session)
        for r in rows:
            await project_into_thread(
                graph,
                patient_id=r["patient_id"],
                projection_node_id=r["projection_node_id"],
                thread_id=r["thread_id"],
                observation_key=f"investigation:{r['investigation_id']}",
            )
            if r["theory_node_id"] is not None:
                await graph.upsert_observed_edge(
                    patient_id=r["patient_id"],
                    from_node_id=r["projection_node_id"],
                    to_node_id=r["theory_node_id"],
                    edge_type="investigates",
                    confidence=1.0,
                    observation_key=f"theory:{r['theory_id']}",
                )
                await graph.tag_nodes_with_thread(
                    patient_id=r["patient_id"],
                    node_ids=[r["theory_node_id"]],
                    thread_id=r["thread_id"],
                )
                await graph.tag_edges_within_thread(
                    patient_id=r["patient_id"], thread_id=r["thread_id"]
                )
        await session.commit()
    return len(rows)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    import wellbe_processing_worker.tasks  # noqa: F401 — registers Dramatiq actors
    tasks = [
        asyncio.create_task(_dispatch_outbox_loop(settings)),
        asyncio.create_task(
            _consume_outbox_loop(
                settings, event_type="genesis.input_ready", handler=_handle_genesis_input_ready
            )
        ),
        asyncio.create_task(
            _consume_outbox_loop(
                settings,
                event_type="thread.state_changed",
                handler=_handle_thread_state_changed,
                transient_errors=THREAD_STATE_TRANSIENT_ERRORS,
            )
        ),
        asyncio.create_task(_outbox_health_loop(settings)),
        asyncio.create_task(_reconcile_thread_linkage(settings)),
    ]
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError):
                await task


settings = ProcessingWorkerSettings()
app = FastAPI(title=settings.service_name, lifespan=lifespan)

_engine = create_async_engine(settings.database_url, pool_pre_ping=True)


def _valid_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=f"Invalid UUID: {value}") from err


@app.get("/health")
async def health() -> dict[str, str]:
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
