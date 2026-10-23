"""Raw Context Brain records.

Field names are the product form of the lab types. The canonical ledger hash
covers every field except id and digest, including person_id. Evidence ids are
sorted. Key order is fixed so a rebuild can verify the digest.

This module does not choose category values, keyword floors, or ranking weights.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Protocol

Judgment = Literal["link", "no_link", "uncertain"]
Origin = Literal["model", "user_correction", "policy"]
ControlTag = Literal["no-model", "no-forward", "summary-only", "requires-confirmation"]
TerminalReason = Literal[
    "supported_leaf",
    "approximate_frontier_exhausted",
    "budget_exhausted",
    "policy_blocked",
    "authorization_changed",
    "stale_snapshot",
    "dependency_unavailable",
    "insufficient_independent_evidence",
]
Exhaustion = Literal["exact", "approximate", "not_yet_exhausted"]
Relation = Literal[
    "explicitly_linked",
    "same_record_group",
    "derived_or_copied",
    "near_in_time",
    "possible_semantic_association",
    "possible_inconsistency",
]
Independence = Literal["source_family", "unknown"]
SourceArrival = Literal["typed", "copied", "imported"]
RouteKind = Literal["facet", "temporal", "neighbour", "source", "fallback"]
PointerKind = Literal["event", "pseudonode"]

DETAILS: dict[str, str] = {
    "authorization_changed": "authorization epoch changed; restart exploration",
    "stale_snapshot": "topology snapshot changed; continuation handle is stale",
    "dependency_unavailable": "topology is rebuilding or a dependency did not answer",
    "policy_blocked": "local policy denied this route",
    "budget_exhausted": "hop, size, or deadline budget is exhausted",
    "supported_leaf": "accepted links from this snapshot are exhausted",
    "approximate_frontier_exhausted": (
        "approximate candidate frontier is exhausted; "
        "this is not proof that no related context exists"
    ),
    "insufficient_independent_evidence": "not enough independent source evidence to add a link",
    "handle_expired": "continuation handle expired",
    "handle_use_limit": "continuation handle use limit reached",
    "unknown_handle": "continuation handle is not recognized",
    "unknown_anchor": "anchor is not in this person's map",
    "wrong_purpose": "this handle is bound to a different purpose",
    "wrong_operation": "this handle cannot perform that operation",
    "rewind_target": "rewind target is not on this exploration path",
}


def assert_safe_detail(detail: str) -> None:
    if re.search(r"no relevant context", detail, re.IGNORECASE):
        raise ValueError("empty or failed results must not be phrased as no relevant context")


@dataclass(frozen=True)
class VaultEvent:
    id: str
    person_id: str
    captured_at: str
    source_type: str
    text: str
    content_hash: str
    lineage_id: str
    document_id: str | None
    keyword: str | None = None
    independence: Independence = "source_family"
    source_arrival: SourceArrival = "typed"
    copied_from_id: str | None = None


@dataclass(frozen=True)
class PointerNode:
    """Pointer into the vault. Must not carry source text."""

    id: str
    kind: PointerKind
    vault_event_id: str | None
    member_event_ids: tuple[str, ...]
    person_id: str


@dataclass(frozen=True)
class LinkAdvertisement:
    id: str
    person_id: str
    sequence: int
    origin: Origin
    digest: str
    model_version: str | None
    prompt_version: str | None
    policy_version: str
    evidence_ids: tuple[str, ...]
    from_id: str
    to_id: str
    judgment: Judgment
    reason_code: str
    relation: Relation
    proposed_confidence: float
    confidence: float
    created_at: str
    supersedes_id: str | None
    withdrawn: bool


@dataclass(frozen=True)
class AcceptedEdge:
    ad_id: str
    from_id: str
    to_id: str
    confidence: float
    reason_code: str
    relation: Relation
    evidence_ids: tuple[str, ...]
    origin: Origin


@dataclass(frozen=True)
class ExportItem:
    handle: str
    excerpt: str
    source_type: str
    captured_at: str
    reason: str
    requires_confirmation: bool


@dataclass(frozen=True)
class JudgeCandidate:
    handle: str
    excerpt: str
    source_type: str
    captured_at: str


@dataclass(frozen=True)
class JudgeRequest:
    new_handle: str
    excerpt: str
    source_type: str
    captured_at: str
    candidates: tuple[JudgeCandidate, ...]


@dataclass(frozen=True)
class JudgeDecision:
    handle: str
    judgment: Judgment
    reason_code: str
    confidence: float


class LinkJudge(Protocol):
    async def judge(self, request: JudgeRequest) -> list[JudgeDecision]: ...


@dataclass(frozen=True)
class NextRoute:
    route_id: str
    label: str
    kind: RouteKind


@dataclass(frozen=True)
class SemanticData:
    route: str
    breadcrumb: tuple[str, ...]
    hop_depth: int
    direct_link_count: int
    cycle_count: int
    exhaustion: Exhaustion
    items: tuple[ExportItem, ...]
    already_explored: tuple[str, ...]
    next_routes: tuple[NextRoute, ...]
    terminal_reason: TerminalReason | None
    detail: str
    route_handle: str | None
    snapshot_revision: int
    snapshot_digest: str


@dataclass(frozen=True)
class LocalCount:
    explored_count: int
    unexplored_count: int
    reachable_count: int
    count_label: Literal["exact", "approximate"]


@dataclass(frozen=True)
class IngestInput:
    person_id: str
    text: str
    source_type: str
    captured_at: str
    lineage_id: str
    idempotency_key: str
    independence: Independence = "source_family"
    source_arrival: SourceArrival = "typed"
    copied_from_id: str | None = None
    document_id: str | None = None


@dataclass(frozen=True)
class JudgmentRecord:
    handle: str
    judgment: Judgment
    reason_code: str
    accepted: bool


@dataclass(frozen=True)
class PruneRecord:
    id: str
    reason: str


@dataclass(frozen=True)
class IngestResult:
    event_id: str
    candidate_count: int
    export_bytes: int
    judgments: tuple[JudgmentRecord, ...]
    terminal_reason: TerminalReason | None
    detail: str
    route_revision: int | None
    pruned: tuple[PruneRecord, ...]


@dataclass(frozen=True)
class Rankable:
    """Higher values win. Fields are numeric ranks, including fractional relevance and degree."""

    id: str
    authorized: float
    provenance: float
    relevance: float
    novelty: float
    inverse_degree: float
    inverse_hop: float


@dataclass
class ExploreInput:
    person_id: str
    purpose: str
    request_id: str
    anchor_id: str | None = None
    route_handle: str | None = None
    route_id: str | None = None
    focus_id: str | None = None
    operation: Literal["open", "continue", "rewind", "assess_link"] = "open"
    rewind_to_id: str | None = None
    hold_at_anchor: bool = False
    authorization_epoch: int = 0
    query: str | None = None
