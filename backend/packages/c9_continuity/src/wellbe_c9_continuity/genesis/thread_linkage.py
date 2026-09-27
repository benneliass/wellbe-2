"""Project a thread's facts into the rest of the system (C5 / C6 / C8).

A Health Thread is only useful if what it was opened from is reachable from it.
Whenever facts join a thread (genesis create/attach, or a controller confirming a
"Things noticed" candidate) this service:

1. links each fact's raw capture to the thread as C5 evidence (idempotent on the
   ``uq_evidence_link_dedup`` constraint),
2. tags the facts' C6 nodes with the thread id (the thread-scoped graph view is
   anchored on ``kg_nodes.thread_ids``) and re-derives edge thread scope,
3. writes one visible C8 *clinical* pointer memory per fact (idempotent on a
   deterministic key; C8 stores pointers, never copies the clinical value).

Negated facts ("no fever") never join a thread's graph or memory. The caller owns
the commit so linkage lands atomically with the thread/decision that caused it.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from sqlalchemy import RowMapping, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_c5_evidence.service import EvidenceService
from wellbe_c6_graph import GraphRepository
from wellbe_c8_memories import MemoryService
from wellbe_c8_memories.models import MemoryEntryRow
from wellbe_contracts.c5_evidence import ConfidenceBasis, EvidenceLinkType, EvidenceRef
from wellbe_contracts.c8_memory import MemorySourceRef, MemoryType, SourceRefType

logger = logging.getLogger("wellbe.c9.thread_linkage")

_FACTS_SQL = text(
    """
    SELECT id, raw_context_event_id, normalized_key, entity_label, fact_type,
           is_negated, extraction_confidence
    FROM processing.extracted_facts
    WHERE patient_id = :pid AND id = ANY(:ids)
    """
)


@dataclass
class ThreadLinkageResult:
    thread_id: uuid.UUID
    facts: int = 0
    evidence_links: list[uuid.UUID] = field(default_factory=list)
    nodes_tagged: int = 0
    edges_tagged: int = 0
    memories_created: int = 0


class ThreadLinkageService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._graph = GraphRepository(session)
        self._evidence = EvidenceService(session)
        self._memory = MemoryService(session)

    async def link_facts(
        self,
        *,
        patient_id: uuid.UUID,
        thread_id: uuid.UUID,
        fact_ids: list[uuid.UUID],
        correlation_id: str,
        trace_id: str,
        link_evidence: bool = True,
        linked_by: str = "system",
    ) -> ThreadLinkageResult:
        result = ThreadLinkageResult(thread_id=thread_id)
        if not fact_ids:
            return result
        rows = (
            await self._session.execute(
                _FACTS_SQL, {"pid": patient_id, "ids": list(fact_ids)}
            )
        ).mappings().all()
        facts = [r for r in rows if not r["is_negated"]]
        result.facts = len(facts)
        if not facts:
            return result

        if link_evidence:
            refs: dict[uuid.UUID, EvidenceRef] = {}
            for f in facts:
                refs.setdefault(
                    f["raw_context_event_id"],
                    EvidenceRef(
                        raw_context_event_id=f["raw_context_event_id"],
                        link_type=EvidenceLinkType.PRIMARY,
                        confidence=f["extraction_confidence"],
                        confidence_basis=ConfidenceBasis.EXTRACTION_MODEL,
                    ),
                )
            result.evidence_links = await self._evidence.link_thread(
                thread_id=thread_id,
                patient_id=patient_id,
                evidence_refs=list(refs.values()),
                correlation_id=correlation_id,
                trace_id=trace_id,
                linked_by=linked_by,
            )

        node_by_fact: dict[uuid.UUID, uuid.UUID] = {}
        for f in facts:
            node = await self._graph.get_node_by_key(
                patient_id=patient_id, normalized_key=f["normalized_key"]
            )
            if node is not None:
                node_by_fact[f["id"]] = node.id
        result.nodes_tagged = await self._graph.tag_nodes_with_thread(
            patient_id=patient_id,
            node_ids=list(set(node_by_fact.values())),
            thread_id=thread_id,
        )
        result.edges_tagged = await self._graph.tag_edges_within_thread(
            patient_id=patient_id, thread_id=thread_id
        )

        for f in facts:
            if await self._ensure_clinical_memory(
                patient_id=patient_id,
                thread_id=thread_id,
                fact=f,
                node_id=node_by_fact.get(f["id"]),
                correlation_id=correlation_id,
                trace_id=trace_id,
            ):
                result.memories_created += 1

        logger.info(
            "thread %s linkage: facts=%d evidence_links=%d nodes_tagged=%d "
            "edges_tagged=%d memories_created=%d",
            thread_id,
            result.facts,
            len(result.evidence_links),
            result.nodes_tagged,
            result.edges_tagged,
            result.memories_created,
        )
        return result

    async def _ensure_clinical_memory(
        self,
        *,
        patient_id: uuid.UUID,
        thread_id: uuid.UUID,
        fact: RowMapping,
        node_id: uuid.UUID | None,
        correlation_id: str,
        trace_id: str,
    ) -> bool:
        f = fact
        key = f"c8:thread:{thread_id}:fact:{f['id']}"
        exists = await self._session.execute(
            select(MemoryEntryRow.memory_entry_id).where(MemoryEntryRow.idempotency_key == key)
        )
        if exists.scalar_one_or_none() is not None:
            return False
        source_refs = [
            MemorySourceRef(
                source_ref_id=f["id"],
                source_ref_type=SourceRefType.C4_EXTRACTED_FACT,
            )
        ]
        if node_id is not None:
            source_refs.append(
                MemorySourceRef(source_ref_id=node_id, source_ref_type=SourceRefType.C6_KG_NODE)
            )
        await self._memory.create_entry(
            patient_id=patient_id,
            thread_id=thread_id,
            memory_type=MemoryType.CLINICAL,
            source_refs=source_refs,
            created_by_actor={"type": "system", "component": "c9.thread_linkage"},
            title=str(f["entity_label"])[:200],
            payload={"fact_type": f["fact_type"]},
            make_visible=True,
            evidence_raw_event_ids=[f["raw_context_event_id"]],
            idempotency_key=key,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
        return True
