"""C13 /v2 thread-scoped graph read route (WEL-156).

A typed REST read over the existing C6 Knowledge Graph, scoped to a single
authorized thread. Returns neutral node-link JSON with compact provenance.
Out-of-thread adjacency is structurally omitted. See
docs/decisions/graph-query-api-contract.md.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from wellbe_c6_graph.constants import PERSONAL_EDGE_CODES
from wellbe_c6_graph.models import KgEdgeRow, KgNodeRow
from wellbe_c6_graph.repository import GraphRepository
from wellbe_c7_thread.repository import ThreadRepository
from wellbe_contracts.c6_graph import (
    GraphEdgeV2,
    GraphNodeV2,
    GraphPageInfo,
    ThreadSubgraphV2,
)
from wellbe_contracts.c13_api import ProblemCode

from wellbe_api.deps import PrincipalDep, SessionDep, audit_ref, require_access
from wellbe_api.errors import ProblemError

router = APIRouter(prefix="/v2", tags=["v2-graph"])

_RESOURCE = "knowledge_graph"

_MAX_NODES_CEILING = 500
_MAX_EDGES_CEILING = 1000

_NODE_TYPES = {
    "ConditionHypothesis", "Symptom", "Medication", "LabResult", "Procedure",
    "VitalSign", "Allergy", "Immunization", "SocialFactor", "FamilyHistory",
    "Other", "Investigation", "Theory",
}


def _node_v2(row: KgNodeRow) -> GraphNodeV2:
    meta = row.node_metadata or {}
    # Property-level allowlist: only compact, non-source-text attributes travel.
    attributes = {
        "first_seen_at": row.first_seen_at.isoformat() if row.first_seen_at else None,
        "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
    }
    if isinstance(meta, dict) and "source_type" in meta:
        attributes["source_type"] = meta["source_type"]
    return GraphNodeV2(
        id=str(row.id),
        type=row.node_type,
        label=row.display_label,
        status=row.status,
        attributes=attributes,
    )


def _edge_v2(row: KgEdgeRow) -> GraphEdgeV2:
    inputs = row.score_inputs if isinstance(row.score_inputs, dict) else {}
    attributes: dict = {}
    # Compact provenance summary only; full provenance via a separate scoped
    # endpoint (not inlined) per the approved contract.
    src_ref = inputs.get("source_ref_id") or inputs.get("evidence_link_id")
    if src_ref is not None:
        attributes["source_ref_id"] = str(src_ref)
    return GraphEdgeV2(
        id=str(row.id),
        source=str(row.from_node_id),
        target=str(row.to_node_id),
        relation=row.edge_type,
        evidence_weight=row.potential_score,
        attributes=attributes,
    )


@router.get("/graph/threads/{thread_id}", response_model=ThreadSubgraphV2)
async def get_thread_subgraph(
    thread_id: uuid.UUID,
    principal: PrincipalDep,
    session: SessionDep,
    max_nodes: Annotated[int, Query(ge=1, le=_MAX_NODES_CEILING)] = 200,
    max_edges: Annotated[int, Query(ge=1, le=_MAX_EDGES_CEILING)] = 400,
    node_types: Annotated[list[str] | None, Query()] = None,
    edge_types: Annotated[list[str] | None, Query()] = None,
) -> ThreadSubgraphV2:
    # Authorize before validation; non-leaking errors (AIP-211).
    await require_access(
        principal, session, action="read", resource_type=_RESOURCE, resource_id=thread_id
    )

    # Object-level authorization: the thread must exist AND belong to the caller.
    # A non-owned/absent thread returns the same 404 so existence is not disclosed.
    thread = await ThreadRepository(session).get(thread_id)
    if thread is None or thread.patient_id != principal.patient_id:
        raise ProblemError(
            status=404,
            code=ProblemCode.GRANT_REQUIRED,
            title="Thread not found",
            detail="No thread with that id is visible to the principal.",
            correlation_id=principal.correlation_id,
        )

    # Validate filter allowlists (RFC 9457 problem on bad input).
    if node_types:
        bad = [t for t in node_types if t not in _NODE_TYPES]
        if bad:
            raise ProblemError(
                status=422,
                code=ProblemCode.PROVENANCE_MISSING,
                title="Unknown node_types filter",
                detail=f"Unsupported node types: {', '.join(bad)}.",
                correlation_id=principal.correlation_id,
            )
    if edge_types:
        bad = [t for t in edge_types if t not in PERSONAL_EDGE_CODES]
        if bad:
            raise ProblemError(
                status=422,
                code=ProblemCode.PROVENANCE_MISSING,
                title="Unknown edge_types filter",
                detail=f"Unsupported edge types: {', '.join(bad)}.",
                correlation_id=principal.correlation_id,
            )

    repo = GraphRepository(session)
    # Fetch one over the ceiling to detect truncation.
    node_rows = await repo.nodes_for_thread(
        patient_id=principal.patient_id,
        thread_id=thread_id,
        node_types=node_types,
        limit=max_nodes + 1,
    )
    truncated = len(node_rows) > max_nodes
    node_rows = node_rows[:max_nodes]
    node_ids = [r.id for r in node_rows]

    edge_rows = await repo.edges_among_nodes(
        patient_id=principal.patient_id,
        thread_id=thread_id,
        node_ids=node_ids,
        edge_types=edge_types,
        limit=max_edges + 1,
    )
    if len(edge_rows) > max_edges:
        truncated = True
        edge_rows = edge_rows[:max_edges]

    nodes = [_node_v2(r) for r in node_rows]
    edges = [_edge_v2(r) for r in edge_rows]

    await audit_ref(
        session,
        event_type="c13.graph.read",
        principal=principal,
        summary="Thread-scoped graph read",
        extra={
            "thread_id": str(thread_id),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "truncated": truncated,
        },
    )
    await session.commit()

    return ThreadSubgraphV2(
        thread_id=str(thread_id),
        nodes=nodes,
        edges=edges,
        page_info=GraphPageInfo(
            has_more=truncated,
            next_page_token=None,
            node_count=len(nodes),
            edge_count=len(edges),
            truncated=truncated,
        ),
    )
