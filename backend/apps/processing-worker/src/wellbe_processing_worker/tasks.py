from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import dramatiq
import wellbe_c2_vault.models  # noqa: F401 — ensure vault tables registered in Base.metadata
from dramatiq.brokers.redis import RedisBroker
from sqlalchemy import text
from wellbe_contracts.c2_vault import RawContextEvent
from wellbe_contracts.c4_processing import (
    FACT_EXTRACTED,
    FactExtractedPayload,
)
from wellbe_contracts.c5_evidence import (
    ConfidenceBasis,
    EvidenceLinkedPayload,
    EvidenceLinkType,
    EvidenceRef,
)

if TYPE_CHECKING:
    from wellbe_c4_processing.extractor import (
        ExtractionResult,
        FactExtractor,
        StructuredObservationExtractor,
    )

logger = logging.getLogger("wellbe.processing_worker.tasks")

_redis_url = os.environ.get("WELLBE_REDIS_URL", "redis://localhost:6379/0")
dramatiq.set_broker(RedisBroker(url=_redis_url))  # type: ignore[no-untyped-call]


@dramatiq.actor(max_retries=3, min_backoff=1000, max_backoff=30_000)
def extract_facts_task(event_json: str) -> None:
    """Process a raw_context.received event via lightweight Dramatiq path."""
    asyncio.run(_extract_facts(event_json))


async def _extract_facts(event_json: str) -> None:
    from wellbe_c4_processing import (
        PIPELINE_VERSION,
        ProcessingRepository,
        StructuredObservationExtractor,
        TextFactExtractor,
    )
    from wellbe_c4_processing.dispatcher import DispatchRoute, decide_route
    from wellbe_c4_processing.extractor import parse_lab_lines
    from wellbe_c5_evidence import EvidenceService
    from wellbe_db import create_engine, create_session_factory
    from wellbe_events import emit_event

    from wellbe_processing_worker.config import ProcessingWorkerSettings

    settings = ProcessingWorkerSettings()
    session_factory = create_session_factory(create_engine(settings.database_url))

    data = json.loads(event_json)
    event = RawContextEvent.model_validate(data)

    decision = decide_route(event.source_type, event.mime_type)
    # A document whose text layer was already read (digital PDF) is extracted
    # here; only image-only documents need the (not yet available) OCR workflow.
    has_text_layer = decision.route == DispatchRoute.TEMPORAL_OCR and bool(data.get("_raw_text"))
    if decision.route != DispatchRoute.DRAMATIQ_TEXT and not has_text_layer:
        logger.warning(
            "capture %s not extracted: route=%s (source_type=%s, mime=%s) has no consumer; "
            "image-only documents need OCR, which is not deployed",
            event.id,
            decision.route.value,
            event.source_type,
            event.mime_type,
        )
        return

    # Dispatch by product capture_type *inside* the text route: structured
    # lab/vital captures (capture_type=lab) get a deterministic structured
    # extractor that emits LabResult/VitalSign; symptom/note keep the free-text
    # path unchanged (docs/decisions/structured-capture-extraction-typing.md).
    source_metadata = event.source_metadata or {}
    capture_type = source_metadata.get("capture_type")

    raw_text = data.get("_raw_text", "")
    if not raw_text and event.blob_ref is None:
        raw_text = source_metadata.get("text", "")

    extractor: FactExtractor | StructuredObservationExtractor
    if capture_type == "lab":
        structured = StructuredObservationExtractor()
        results = structured.extract_lab(
            test_name=source_metadata.get("test_name", ""),
            value=source_metadata.get("value", ""),
            unit=source_metadata.get("unit"),
            reference_range=source_metadata.get("reference_range"),
            occurrence=event.captured_at,
        )
        extractor = structured
    else:
        text_extractor = TextFactExtractor()
        results = await text_extractor.extract(raw_text, event.patient_id)
        extractor = text_extractor
        if has_text_layer:
            structured = StructuredObservationExtractor()
            labs = [
                fact
                for lab in parse_lab_lines(raw_text)
                for fact in structured.extract_lab(occurrence=event.captured_at, **lab)
            ]
            if labs:
                results = [r for r in results if r.fact_type.value != "other"] + labs

    # Payloads for facts that were newly persisted in this run. On at-least-once
    # re-delivery, already-existing facts are skipped here so we do not re-link
    # evidence, re-emit events, or re-create graph nodes.
    new_fact_payloads: list[FactExtractedPayload] = []

    async with session_factory() as session:
        repo = ProcessingRepository(session)
        evidence_service = EvidenceService(session)

        for result in results:
            fact_id = _deterministic_fact_id(event.id, result)
            inserted_id = await repo.insert_fact(
                id=fact_id,
                patient_id=event.patient_id,
                raw_context_event_id=event.id,
                fact_type=result.fact_type.value,
                entity_label=result.entity_label,
                normalized_key=result.normalized_key,
                extraction_confidence=result.extraction_confidence,
                extraction_model=extractor.model_name,
                model_version=extractor.model_version,
                pipeline_version=PIPELINE_VERSION,
                quality_flag=result.quality_flag.value,
                quality_metadata=result.quality_metadata,
                captured_at=(
                    event.captured_at.replace(tzinfo=None)
                    if event.captured_at.tzinfo
                    else event.captured_at
                ),
                correlation_id=event.correlation_id,
                trace_id=event.trace_id,
                code_system=result.code_system,
                code=result.code,
                text_span_start=result.text_span_start,
                text_span_end=result.text_span_end,
                source_text_excerpt_hash=(
                    hashlib.sha256(raw_text[result.text_span_start:result.text_span_end].encode()).hexdigest()[:16]
                    if result.text_span_start is not None and result.text_span_end is not None
                    else None
                ),
                is_negated=result.is_negated,
                is_historical=result.is_historical,
                is_hypothetical=result.is_hypothetical,
                subject=result.subject.value,
            )

            # Fact already existed (redelivery): skip downstream work for it.
            if inserted_id is None:
                continue

            await evidence_service.link_fact(
                fact_id=fact_id,
                patient_id=event.patient_id,
                evidence_refs=[EvidenceRef(
                    raw_context_event_id=event.id,
                    link_type=EvidenceLinkType.PRIMARY,
                    confidence=result.extraction_confidence,
                    confidence_basis=ConfidenceBasis.EXTRACTION_MODEL,
                    relevance_span_start=result.text_span_start,
                    relevance_span_end=result.text_span_end,
                )],
                correlation_id=event.correlation_id,
                trace_id=event.trace_id,
            )

            payload = FactExtractedPayload(
                fact_id=fact_id,
                patient_id=event.patient_id,
                raw_context_event_id=event.id,
                fact_type=result.fact_type,
                entity_label=result.entity_label,
                normalized_key=result.normalized_key,
                extraction_confidence=result.extraction_confidence,
                quality_flag=result.quality_flag,
                correlation_id=event.correlation_id,
                trace_id=event.trace_id,
            )
            await emit_event(
                session=session,
                event_type=FACT_EXTRACTED,
                payload=payload.model_dump(mode="json"),
                correlation_id=event.correlation_id,
                trace_id=event.trace_id,
            )
            new_fact_payloads.append(payload)

        await session.commit()

    # Canonical C6 dispatch: invoke graph-node creation inline using the real,
    # deterministic fact_id. The processing-worker runs only the FastAPI app
    # (no Dramatiq consumer), so .send() enqueues are never processed; the inline
    # call is the single live path. Graph node upsert is idempotent on
    # (patient_id, node_type, normalized_key), so this is safe under redelivery.
    for fact_payload in new_fact_payloads:
        await _create_graph_node(fact_payload.model_dump_json())

    logger.info(
        "capture %s (%s) extracted %d fact(s), %d new: %s",
        event.id,
        capture_type or event.source_type,
        len(results),
        len(new_fact_payloads),
        ", ".join(f"{p.fact_type.value}:{p.normalized_key}" for p in new_fact_payloads) or "-",
    )
    if not results:
        logger.warning(
            "capture %s produced no facts (source_type=%s, text_len=%d)",
            event.id,
            event.source_type,
            len(raw_text),
        )

    await _link_co_occurrence(
        raw_event_id=event.id, patient_id=event.patient_id, captured_at=event.captured_at
    )

    # Capture processing is now complete (C4 facts + C5 evidence + C6 nodes). Emit
    # the synthetic genesis.input_ready signal — the single, well-defined trigger
    # for thread genesis (triage-decision-contract.md §1). Emission reads all facts
    # for the capture (not only newly-inserted ones), so a redelivery that re-runs
    # extraction still produces a complete payload; genesis itself dedups on a
    # deterministic decision hash, so re-emission is a no-op downstream.
    await _emit_genesis_input_ready(event)


CO_OCCURRENCE_WINDOW = timedelta(hours=48)
_CO_OCCURRENCE_FACT_TYPES = ["symptom", "lab_result", "medication", "vital_sign", "finding"]
_CO_OCCURRENCE_SQL = text(
    """
    SELECT raw_context_event_id, normalized_key, extraction_confidence
    FROM processing.extracted_facts
    WHERE patient_id = :pid
      AND NOT is_negated AND NOT is_hypothetical
      AND fact_type = ANY(:types)
      AND captured_at BETWEEN :start AND :end
    ORDER BY captured_at DESC
    LIMIT 200
    """
)


async def _link_co_occurrence(
    *, raw_event_id: uuid.UUID, patient_id: uuid.UUID, captured_at: datetime
) -> int:
    """Record ``co_occurs_with`` observations between this capture's concepts and
    every concept seen within ``CO_OCCURRENCE_WINDOW`` (including each other).

    One observation per (capture, capture) pair, so redelivery never inflates
    support. Edge thread scope is re-derived for threads both endpoints share.
    """
    from wellbe_c6_graph import GraphRepository
    from wellbe_db import create_engine, create_session_factory

    from wellbe_processing_worker.config import ProcessingWorkerSettings

    settings = ProcessingWorkerSettings()
    session_factory = create_session_factory(create_engine(settings.database_url))
    captured = captured_at.replace(tzinfo=None) if captured_at.tzinfo else captured_at

    async with session_factory() as session:
        graph = GraphRepository(session)
        rows = (
            await session.execute(
                _CO_OCCURRENCE_SQL,
                {
                    "pid": patient_id,
                    "types": _CO_OCCURRENCE_FACT_TYPES,
                    "start": captured - CO_OCCURRENCE_WINDOW,
                    "end": captured + CO_OCCURRENCE_WINDOW,
                },
            )
        ).mappings().all()

        nodes: dict[str, Any] = {}
        for r in rows:
            if r["normalized_key"] not in nodes:
                nodes[r["normalized_key"]] = await graph.get_node_by_key(
                    patient_id=patient_id, normalized_key=r["normalized_key"]
                )
        mine = [r for r in rows if r["raw_context_event_id"] == raw_event_id]
        changed = 0
        threads: set[uuid.UUID] = set()
        seen_pairs: set[tuple[str, ...]] = set()
        for a in mine:
            for b in rows:
                node_a, node_b = nodes.get(a["normalized_key"]), nodes.get(b["normalized_key"])
                if node_a is None or node_b is None or node_a.id == node_b.id:
                    continue
                captures = sorted((str(a["raw_context_event_id"]), str(b["raw_context_event_id"])))
                key = (*sorted((str(node_a.id), str(node_b.id))), *captures)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                _, did_change = await graph.upsert_observed_edge(
                    patient_id=patient_id,
                    from_node_id=node_a.id,
                    to_node_id=node_b.id,
                    edge_type="co_occurs_with",
                    confidence=min(a["extraction_confidence"], b["extraction_confidence"]),
                    observation_key="|".join(captures),
                )
                if did_change:
                    changed += 1
                    threads |= set(node_a.thread_ids or []) & set(node_b.thread_ids or [])
        for thread_id in threads:
            await graph.tag_edges_within_thread(patient_id=patient_id, thread_id=thread_id)
        await session.commit()

    logger.info(
        "capture %s co-occurrence: %d concept(s) in window, %d edge observation(s) recorded",
        raw_event_id,
        len(nodes),
        changed,
    )
    return changed


async def _emit_genesis_input_ready(event: RawContextEvent) -> None:
    """Assemble and emit genesis.input_ready for a fully-processed capture."""
    from wellbe_c4_processing import ProcessingRepository
    from wellbe_c6_graph import GraphRepository
    from wellbe_contracts.genesis import (
        GENESIS_INPUT_READY,
        GenesisFactInput,
        GenesisInputReadyPayload,
        GraphResolutionStatus,
    )
    from wellbe_db import create_engine, create_session_factory
    from wellbe_events import emit_event

    from wellbe_processing_worker.config import ProcessingWorkerSettings

    settings = ProcessingWorkerSettings()
    session_factory = create_session_factory(create_engine(settings.database_url))

    def _aware(value: datetime) -> datetime:
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)

    async with session_factory() as session:
        repo = ProcessingRepository(session)
        graph = GraphRepository(session)
        fact_rows = await repo.list_facts_for_capture(event.id)
        if not fact_rows:
            return

        genesis_facts: list[GenesisFactInput] = []
        resolved = 0
        for row in fact_rows:
            node = await graph.get_node_by_key(
                patient_id=row.patient_id, normalized_key=row.normalized_key
            )
            if node is not None:
                resolved += 1
            genesis_facts.append(
                GenesisFactInput(
                    fact_id=row.id,
                    raw_context_event_id=row.raw_context_event_id,
                    fact_type=row.fact_type,
                    entity_label=row.entity_label,
                    normalized_key=row.normalized_key,
                    extraction_confidence=row.extraction_confidence,
                    graph_node_id=node.id if node is not None else None,
                    event_date=_aware(row.captured_at),
                    is_negated=row.is_negated,
                    is_historical=row.is_historical,
                    is_hypothetical=row.is_hypothetical,
                )
            )

        if resolved == len(fact_rows):
            graph_status = GraphResolutionStatus.RESOLVED
        elif resolved > 0:
            graph_status = GraphResolutionStatus.PARTIAL
        else:
            graph_status = GraphResolutionStatus.UNAVAILABLE

        payload = GenesisInputReadyPayload(
            patient_id=event.patient_id,
            capture_id=event.id,
            source_event_id=event.id,
            captured_at=_aware(event.captured_at),
            facts=genesis_facts,
            graph_resolution_status=graph_status,
            correlation_id=event.correlation_id,
            trace_id=event.trace_id,
        )

        await emit_event(
            session=session,
            event_type=GENESIS_INPUT_READY,
            payload=payload.model_dump(mode="json"),
            correlation_id=event.correlation_id,
            trace_id=event.trace_id,
        )
        await session.commit()


def _deterministic_fact_id(
    raw_event_id: uuid.UUID, result: ExtractionResult
) -> uuid.UUID:
    """Derive a stable fact id from the raw event and the fact's natural key.

    Re-processing the same raw context event yields the same fact id, which makes
    fact insertion (ON CONFLICT id DO NOTHING) and evidence linking idempotent
    under at-least-once delivery.
    """
    natural_key = "|".join(
        str(part)
        for part in (
            raw_event_id,
            result.fact_type.value,
            result.normalized_key,
            result.text_span_start,
            result.text_span_end,
            result.subject.value,
            result.is_negated,
            result.is_historical,
            result.is_hypothetical,
        )
    )
    return uuid.uuid5(uuid.NAMESPACE_OID, natural_key)


FACT_TYPE_TO_NODE_TYPE: dict[str, str] = {
    "symptom": "Symptom",
    "finding": "ConditionHypothesis",
    "medication": "Medication",
    "lab_result": "LabResult",
    "allergy": "Allergy",
    "procedure": "Procedure",
    "dx_mention": "ConditionHypothesis",
    "vital_sign": "VitalSign",
    "immunization": "Immunization",
    "family_history": "FamilyHistory",
    "social_history": "SocialFactor",
    "other": "Other",
}


@dramatiq.actor(max_retries=3, min_backoff=1000, max_backoff=30_000)
def create_graph_node_task(fact_extracted_json: str) -> None:
    """Create/upsert a KG node from a fact.extracted event."""
    asyncio.run(_create_graph_node(fact_extracted_json))


async def _create_graph_node(fact_extracted_json: str) -> None:
    from wellbe_c6_graph import GraphRepository
    from wellbe_db import create_engine, create_session_factory
    from wellbe_events import emit_event

    from wellbe_processing_worker.config import ProcessingWorkerSettings

    settings = ProcessingWorkerSettings()
    session_factory = create_session_factory(create_engine(settings.database_url))

    data = json.loads(fact_extracted_json)
    payload = FactExtractedPayload.model_validate(data)

    node_type = FACT_TYPE_TO_NODE_TYPE.get(payload.fact_type.value, "Other")

    async with session_factory() as session:
        repo = GraphRepository(session)
        node = await repo.upsert_node(
            patient_id=payload.patient_id,
            node_type=node_type,
            normalized_key=payload.normalized_key,
            display_label=payload.entity_label,
        )

        await emit_event(
            session=session,
            event_type="graph.node_created",
            payload={
                "node_id": str(node.id),
                "patient_id": str(payload.patient_id),
                "node_type": node_type,
                "normalized_key": payload.normalized_key,
                "fact_id": str(payload.fact_id),
            },
            correlation_id=payload.correlation_id,
            trace_id=payload.trace_id,
        )

        await session.commit()


@dramatiq.actor(max_retries=3, min_backoff=1000, max_backoff=30_000)
def score_graph_edges_task(evidence_linked_json: str) -> None:
    """Score/rescore edges when new evidence is linked."""
    asyncio.run(_score_graph_edges(evidence_linked_json))


async def _score_graph_edges(evidence_linked_json: str) -> None:
    from wellbe_c6_graph import GraphRepository, PotentialScoreComputer, ScoreInput
    from wellbe_db import create_engine, create_session_factory
    from wellbe_events import emit_event

    from wellbe_processing_worker.config import ProcessingWorkerSettings

    settings = ProcessingWorkerSettings()
    session_factory = create_session_factory(create_engine(settings.database_url))

    data = json.loads(evidence_linked_json)
    payload = EvidenceLinkedPayload.model_validate(data)

    async with session_factory() as session:
        repo = GraphRepository(session)
        scorer = PotentialScoreComputer()

        edges = await repo.get_edges_needing_rescore(limit=50)
        for edge in edges:
            score_input = ScoreInput(
                link_type=payload.link_type,
                confidence=payload.confidence,
                edge_category=edge.edge_type,
            )
            result = scorer.compute([score_input])

            edge.potential_score = result.potential_score
            edge.score_version = result.score_version
            edge.score_inputs = result.score_inputs
            edge.needs_rescore = False
            edge.updated_at = datetime.now(UTC)

            await emit_event(
                session=session,
                event_type="graph.edge_scored",
                payload={
                    "edge_id": str(edge.id),
                    "patient_id": str(edge.patient_id),
                    "potential_score": result.potential_score,
                    "score_version": result.score_version,
                },
                correlation_id=payload.correlation_id,
                trace_id=payload.trace_id,
            )

        await session.commit()
