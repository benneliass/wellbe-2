"""Place C14/C15 projection nodes (Investigation / Theory) into a thread's graph."""

from __future__ import annotations

import uuid

from wellbe_c6_graph.repository import GraphRepository

PROJECTION_NODE_TYPES = frozenset({"Investigation", "Theory"})


async def project_into_thread(
    graph: GraphRepository,
    *,
    patient_id: uuid.UUID,
    projection_node_id: uuid.UUID,
    thread_id: uuid.UUID,
    observation_key: str,
    edge_type: str = "investigates",
) -> int:
    """Scope the projection node to ``thread_id`` and connect it to the thread's
    personal nodes (``projection -[edge_type]-> member``). Idempotent.

    Returns the number of member nodes the projection is connected to.
    """
    await graph.tag_nodes_with_thread(
        patient_id=patient_id, node_ids=[projection_node_id], thread_id=thread_id
    )
    members = await graph.nodes_for_thread(patient_id=patient_id, thread_id=thread_id)
    connected = 0
    for node in members:
        if node.id == projection_node_id or node.node_type in PROJECTION_NODE_TYPES:
            continue
        await graph.upsert_observed_edge(
            patient_id=patient_id,
            from_node_id=projection_node_id,
            to_node_id=node.id,
            edge_type=edge_type,
            confidence=1.0,
            observation_key=observation_key,
        )
        connected += 1
    await graph.tag_edges_within_thread(patient_id=patient_id, thread_id=thread_id)
    return connected
