"""C13 thread-scoped graph read contracts (WEL-156).

Implements docs/decisions/graph-query-api-contract.md:

- A typed REST read scoped to a single authorized ``thread_id`` (not a graph
  query language passthrough, not GraphQL).
- Neutral canonical node-link JSON (``nodes[]`` + ``edges[]``) carrying a
  ``schema_version`` so the response is not coupled to one viz library.
- Edge ``relation`` uses the constrained personal-graph vocabulary; ``may_explain``
  is the strongest (causal) relation exposed — never a diagnosis assertion.
- Compact provenance summaries travel on node/edge metadata (source type,
  evidence weight); full provenance is fetched from a separate scoped endpoint.
- Out-of-thread adjacent nodes are structurally omitted.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class GraphNodeV2(BaseModel):
    id: str
    type: str
    label: str
    status: str
    # Compact, allowlisted attributes only (no raw source text).
    attributes: dict[str, Any] = Field(default_factory=dict)


class GraphEdgeV2(BaseModel):
    id: str
    source: str
    target: str
    # Constrained personal-graph vocabulary; `may_explain` is the ceiling.
    relation: str
    # Evidence weight in [0,1] — NOT a diagnostic probability.
    evidence_weight: float
    attributes: dict[str, Any] = Field(default_factory=dict)


class GraphPageInfo(BaseModel):
    has_more: bool = False
    next_page_token: str | None = None
    node_count: int = 0
    edge_count: int = 0
    truncated: bool = False


class ThreadSubgraphV2(BaseModel):
    schema_version: Literal["c13.graph.subgraph.v2"] = "c13.graph.subgraph.v2"
    thread_id: str
    nodes: list[GraphNodeV2] = Field(default_factory=list)
    edges: list[GraphEdgeV2] = Field(default_factory=list)
    page_info: GraphPageInfo = Field(default_factory=GraphPageInfo)


__all__ = [
    "GraphEdgeV2",
    "GraphNodeV2",
    "GraphPageInfo",
    "ThreadSubgraphV2",
]
