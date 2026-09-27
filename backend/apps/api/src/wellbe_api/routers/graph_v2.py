"""C13 /v2 thread-scoped graph read route (WEL-156).

A typed REST read over the existing C6 Knowledge Graph, scoped to a single
authorized thread. Returns neutral node-link JSON with compact provenance. See
docs/decisions/graph-query-api-contract.md.

For the controller reading their own data, the view also carries a bounded 1-hop
neighbourhood: the controller's own nodes one edge away from the thread, marked
``attributes.in_thread = false``. For any grant-based principal, out-of-thread
adjacency stays structurally omitted, exactly as the approved contract requires.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Query
from wellbe_c6_graph.constants import PERSONAL_EDGE_CODES
from wellbe_c6_graph.models import KgEdgeRow, KgNodeRow
from wellbe_c6_graph.repository import GraphRepository
from wellbe_c7_thread.repository import ThreadRepository
from wellbe_c15_theory.normalizer import strip_question_frame
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
# Total node budget (thread + neighbours) once the 1-hop expansion kicks in, and
# how many boundary edges are scanned to find neighbours. Keeps the read cheap.
_NEIGHBOUR_NODE_BUDGET = 50
_NEIGHBOUR_EDGE_SCAN = 200

_NODE_TYPES = {
    "ConditionHypothesis", "Symptom", "Medication", "LabResult", "Procedure",
    "VitalSign", "Allergy", "Immunization", "SocialFactor", "FamilyHistory",
    "Other", "Investigation", "Theory",
}


def _node_v2(row: KgNodeRow, *, in_thread: bool = True) -> GraphNodeV2:
    meta = row.node_metadata or {}
    # Property-level allowlist: only compact, non-source-text attributes travel.
    attributes: dict[str, Any] = {
        "first_seen_at": row.first_seen_at.isoformat() if row.first_seen_at else None,
        "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
        "in_thread": in_thread,
    }
    if isinstance(meta, dict) and "source_type" in meta:
        attributes["source_type"] = meta["source_type"]
    label = row.display_label
    if row.node_type == "Theory":
        label = strip_question_frame(label)
    return GraphNodeV2(
        id=str(row.id),
        type=row.node_type,
        label=label,
        status=row.status,
        attributes=attributes,
    )


def _edge_v2(row: KgEdgeRow) -> GraphEdgeV2:
    inputs = row.score_inputs if isinstance(row.score_inputs, dict) else {}
    attributes: dict[str, Any] = {}
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


async def _one_hop(
    repo: GraphRepository,
    *,
    patient_id: uuid.UUID,
    thread_node_ids: list[uuid.UUID],
    budget: int,
    node_types: list[str] | None,
    edge_types: list[str] | None,
) -> tuple[list[KgNodeRow], list[KgEdgeRow], bool]:
    """Neighbours one edge away from the thread, strongest edges first.

    Returns ``(neighbour_nodes, edges, dropped)``: the edges are only those whose
    both endpoints end up in the view, and ``dropped`` is True when candidates
    were left out because the node budget ran out.
    """
    if budget <= 0 or not thread_node_ids:
        return [], [], False
    in_thread = set(thread_node_ids)
    boundary = await repo.edges_touching_nodes(
        patient_id=patient_id,
        node_ids=thread_node_ids,
        edge_types=edge_types,
        limit=_NEIGHBOUR_EDGE_SCAN,
    )
    candidates: list[uuid.UUID] = []
    for e in boundary:
        for end in (e.from_node_id, e.to_node_id):
            if end not in in_thread and end not in candidates:
                candidates.append(end)

    found = await repo.nodes_by_ids(patient_id=patient_id, node_ids=candidates)
    eligible = [
        found[c]
        for c in candidates
        if c in found and (not node_types or found[c].node_type in node_types)
    ]
    neighbours = eligible[:budget]
    visible = in_thread | {n.id for n in neighbours}
    edges = [e for e in boundary if e.from_node_id in visible and e.to_node_id in visible]
    return neighbours, edges, len(eligible) > budget


@router.get("/graph/threads/{thread_id}", response_model=ThreadSubgraphV2)
async def get_thread_subgraph(
    thread_id: uuid.UUID,
    principal: PrincipalDep,
    session: SessionDep,
    max_nodes: Annotated[int, Query(ge=1, le=_MAX_NODES_CEILING)] = 200,
    max_edges: Annotated[int, Query(ge=1, le=_MAX_EDGES_CEILING)] = 400,
    node_types: Annotated[list[str] | None, Query()] = None,
    edge_types: Annotated[list[str] | None, Query()] = None,
    include_neighbors: Annotated[bool, Query()] = True,
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

    neighbour_rows: list[KgNodeRow] = []
    if include_neighbors and principal.is_controller:
        neighbour_rows, boundary_edges, dropped = await _one_hop(
            repo,
            patient_id=principal.patient_id,
            thread_node_ids=node_ids,
            budget=min(max_nodes, _NEIGHBOUR_NODE_BUDGET) - len(node_rows),
            node_types=node_types,
            edge_types=edge_types,
        )
        truncated = truncated or dropped
        seen = {e.id for e in edge_rows}
        edge_rows += [e for e in boundary_edges if e.id not in seen]

    if len(edge_rows) > max_edges:
        truncated = True
        edge_rows = edge_rows[:max_edges]

    nodes = [_node_v2(r) for r in node_rows]
    nodes += [_node_v2(r, in_thread=False) for r in neighbour_rows]
    edges = [_edge_v2(r) for r in edge_rows]

    await audit_ref(
        session,
        event_type="c13.graph.read",
        principal=principal,
        summary="Thread-scoped graph read",
        extra={
            "thread_id": str(thread_id),
            "node_count": len(nodes),
            "neighbour_count": len(neighbour_rows),
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
