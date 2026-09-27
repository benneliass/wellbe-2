"""Resolve user-cited evidence refs for a theory evaluation.

A ref is accepted only when it exists, belongs to the theory's patient, and is
part of a thread linked to the theory's investigation. Each accepted ref also
yields the personal graph nodes (inside those threads) that evidence edges are
drawn from. Nothing here judges what the evidence *means* — the user decides.

Thread membership is established two ways, matching how C9 thread linkage
writes it: a C5 ``health_thread`` evidence link from the thread to the capture,
or a C6 node (keyed by the fact's normalized key) tagged with the thread.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Protocol

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_contracts.c15_theory import TheoryEvidenceRef, TheoryEvidenceRefKind

from wellbe_c15_theory.errors import (
    TheoryEvidenceNotFoundError,
    TheoryEvidenceRequiredError,
    TheoryEvidenceUnrelatedError,
    TheoryNotLinkedError,
)


@dataclass(frozen=True)
class FactInfo:
    id: uuid.UUID
    normalized_key: str
    raw_context_event_id: uuid.UUID


@dataclass(frozen=True)
class EvidenceLinkInfo:
    id: uuid.UUID
    source_type: str
    source_id: uuid.UUID
    raw_context_event_id: uuid.UUID


class EvidenceStore(Protocol):
    async def get_fact(self, patient_id: uuid.UUID, fact_id: uuid.UUID) -> FactInfo | None: ...

    async def capture_exists(self, patient_id: uuid.UUID, capture_id: uuid.UUID) -> bool: ...

    async def get_evidence_link(
        self, patient_id: uuid.UUID, link_id: uuid.UUID
    ) -> EvidenceLinkInfo | None: ...

    async def facts_for_capture(
        self, patient_id: uuid.UUID, capture_id: uuid.UUID
    ) -> list[FactInfo]: ...

    async def thread_linked_captures(
        self, patient_id: uuid.UUID, thread_ids: list[uuid.UUID]
    ) -> set[uuid.UUID]: ...

    async def thread_nodes_by_key(
        self, patient_id: uuid.UUID, keys: list[str], thread_ids: list[uuid.UUID]
    ) -> dict[str, uuid.UUID]: ...


@dataclass
class ResolvedEvidence:
    refs: list[TheoryEvidenceRef]
    # ref -> graph nodes inside the investigation's threads (may be empty).
    nodes_by_ref: dict[TheoryEvidenceRef, list[uuid.UUID]] = field(default_factory=dict)

    @property
    def node_ids(self) -> list[uuid.UUID]:
        seen: dict[uuid.UUID, None] = {}
        for nodes in self.nodes_by_ref.values():
            for n in nodes:
                seen.setdefault(n, None)
        return list(seen)

    def refs_for_node(self, node_id: uuid.UUID) -> list[TheoryEvidenceRef]:
        return [r for r, nodes in self.nodes_by_ref.items() if node_id in nodes]


async def resolve_evidence(
    store: EvidenceStore,
    *,
    patient_id: uuid.UUID,
    thread_ids: list[uuid.UUID],
    refs: list[TheoryEvidenceRef],
) -> ResolvedEvidence:
    """Validate every ref (fail on the first bad one) and map it to thread nodes."""
    unique = list(dict.fromkeys(refs))
    if not unique:
        raise TheoryEvidenceRequiredError(
            "Cite at least one piece of evidence from this investigation's threads."
        )
    if not thread_ids:
        raise TheoryNotLinkedError(
            "This theory's investigation has no linked threads to cite evidence from."
        )

    linked_captures = await store.thread_linked_captures(patient_id, thread_ids)
    resolved = ResolvedEvidence(refs=unique)

    async def nodes_for(facts: list[FactInfo]) -> list[uuid.UUID]:
        keys = list(dict.fromkeys(f.normalized_key for f in facts))
        if not keys:
            return []
        by_key = await store.thread_nodes_by_key(patient_id, keys, thread_ids)
        return list(dict.fromkeys(by_key[k] for k in keys if k in by_key))

    for ref in unique:
        kind = ref.kind.value
        if ref.kind is TheoryEvidenceRefKind.FACT:
            fact = await store.get_fact(patient_id, ref.id)
            if fact is None:
                raise TheoryEvidenceNotFoundError(kind, ref.id)
            nodes = await nodes_for([fact])
            related = bool(nodes) or fact.raw_context_event_id in linked_captures
        elif ref.kind is TheoryEvidenceRefKind.CAPTURE:
            if not await store.capture_exists(patient_id, ref.id):
                raise TheoryEvidenceNotFoundError(kind, ref.id)
            nodes = await nodes_for(await store.facts_for_capture(patient_id, ref.id))
            related = bool(nodes) or ref.id in linked_captures
        else:
            link = await store.get_evidence_link(patient_id, ref.id)
            if link is None:
                raise TheoryEvidenceNotFoundError(kind, ref.id)
            if link.source_type == "extracted_fact":
                fact = await store.get_fact(patient_id, link.source_id)
                facts = [fact] if fact is not None else []
            else:
                facts = await store.facts_for_capture(patient_id, link.raw_context_event_id)
            nodes = await nodes_for(facts)
            related = (
                (link.source_type == "health_thread" and link.source_id in thread_ids)
                or link.raw_context_event_id in linked_captures
                or bool(nodes)
            )
        if not related:
            raise TheoryEvidenceUnrelatedError(kind, ref.id)
        resolved.nodes_by_ref[ref] = nodes
    return resolved


_UUIDS = ARRAY(UUID(as_uuid=True))

_FACT_SQL = text(
    "SELECT id, normalized_key, raw_context_event_id FROM processing.extracted_facts "
    "WHERE id = :id AND patient_id = :pid"
)
_CAPTURE_SQL = text(
    "SELECT 1 FROM vault.raw_context_events WHERE id = :id AND patient_id = :pid"
)
_LINK_SQL = text(
    "SELECT id, source_type, source_id, raw_context_event_id FROM evidence.evidence_links "
    "WHERE id = :id AND patient_id = :pid"
)
_CAPTURE_FACTS_SQL = text(
    "SELECT id, normalized_key, raw_context_event_id FROM processing.extracted_facts "
    "WHERE patient_id = :pid AND raw_context_event_id = :rid"
)
_THREAD_CAPTURES_SQL = text(
    "SELECT DISTINCT raw_context_event_id FROM evidence.evidence_links "
    "WHERE patient_id = :pid AND source_type = 'health_thread' AND source_id = ANY(:tids)"
).bindparams(bindparam("tids", type_=_UUIDS))
_THREAD_NODES_SQL = text(
    "SELECT id, normalized_key FROM graph.kg_nodes "
    "WHERE patient_id = :pid AND normalized_key = ANY(:keys) AND thread_ids && :tids "
    "AND node_type NOT IN ('Investigation', 'Theory') "
    "ORDER BY last_seen_at DESC"
).bindparams(bindparam("tids", type_=_UUIDS))


class SqlEvidenceStore:
    """Read-only lookups across the C2/C4/C5/C6 schemas, always patient-anchored."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_fact(self, patient_id: uuid.UUID, fact_id: uuid.UUID) -> FactInfo | None:
        row = (
            await self._session.execute(_FACT_SQL, {"id": fact_id, "pid": patient_id})
        ).mappings().first()
        return FactInfo(**row) if row is not None else None

    async def capture_exists(self, patient_id: uuid.UUID, capture_id: uuid.UUID) -> bool:
        row = (
            await self._session.execute(_CAPTURE_SQL, {"id": capture_id, "pid": patient_id})
        ).first()
        return row is not None

    async def get_evidence_link(
        self, patient_id: uuid.UUID, link_id: uuid.UUID
    ) -> EvidenceLinkInfo | None:
        row = (
            await self._session.execute(_LINK_SQL, {"id": link_id, "pid": patient_id})
        ).mappings().first()
        return EvidenceLinkInfo(**row) if row is not None else None

    async def facts_for_capture(
        self, patient_id: uuid.UUID, capture_id: uuid.UUID
    ) -> list[FactInfo]:
        rows = (
            await self._session.execute(
                _CAPTURE_FACTS_SQL, {"pid": patient_id, "rid": capture_id}
            )
        ).mappings().all()
        return [FactInfo(**r) for r in rows]

    async def thread_linked_captures(
        self, patient_id: uuid.UUID, thread_ids: list[uuid.UUID]
    ) -> set[uuid.UUID]:
        rows = (
            await self._session.execute(
                _THREAD_CAPTURES_SQL, {"pid": patient_id, "tids": list(thread_ids)}
            )
        ).scalars().all()
        return set(rows)

    async def thread_nodes_by_key(
        self, patient_id: uuid.UUID, keys: list[str], thread_ids: list[uuid.UUID]
    ) -> dict[str, uuid.UUID]:
        rows = (
            await self._session.execute(
                _THREAD_NODES_SQL,
                {"pid": patient_id, "keys": list(keys), "tids": list(thread_ids)},
            )
        ).all()
        out: dict[str, uuid.UUID] = {}
        for node_id, key in rows:
            out.setdefault(key, node_id)
        return out
