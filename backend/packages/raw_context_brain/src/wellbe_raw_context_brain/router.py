"""Person-owned raw-context router.

Route handles are opaque. The walk lives in MemorySessionStore, not in the handle.
A filter route narrows the frontier and does not open a note. Neighbour Open steps one node.
supported_leaf stays rewindable. Other terminals release the handle.
"""

from __future__ import annotations

import asyncio
import json
import math
import secrets
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from functools import cmp_to_key
from typing import Literal, cast

from wellbe_raw_context_brain.hnsw import HnswIndex
from wellbe_raw_context_brain.integrity.structural import assert_structural_ledger
from wellbe_raw_context_brain.judge import heuristic_judge, sanitize_decision
from wellbe_raw_context_brain.persist.graph_store import (
    DurableSnapshot,
    GraphStore,
    LinkAcknowledgement,
)
from wellbe_raw_context_brain.persist.session_store import (
    JsonValue,
    MemorySessionStore,
    SessionJson,
    SessionStore,
)
from wellbe_raw_context_brain.rank import (
    apply_hysteresis,
    compare_rank,
    inverse_degree,
    provenance_rank,
)
from wellbe_raw_context_brain.relation import map_relation, source_name
from wellbe_raw_context_brain.routing.interest import (
    BeginResult,
    InterestBudgets,
    PendingInterestTable,
    RejectedBegin,
    SatisfiedBegin,
    SemanticInterest,
    create_pending_interest_table,
)
from wellbe_raw_context_brain.routing.retry import AttemptInput, StopDecision, schedule_attempt
from wellbe_raw_context_brain.routing.route_sets import (
    DiscoverySource,
    RouteProvenance,
    RoutePublication,
    RouteSetLog,
    RouteSetsSnapshot,
    create_route_sets,
)
from wellbe_raw_context_brain.routing.selection import (
    LAB_CAP,
    JudgedCandidate,
    NeighborRef,
    RankedCandidate,
    ReferralRoundInput,
    SelectionInput,
    apply_referral_round,
    apply_selection,
)
from wellbe_raw_context_brain.routing.session_policy import (
    RewindTargetError,
    forward_items,
    retains_session,
    select_issued_actions,
    truncate_path,
)
from wellbe_raw_context_brain.store import (
    AdvertisementDraft,
    AdvertisementLog,
    Projection,
    Vault,
    empty_pointer,
)
from wellbe_raw_context_brain.text import edge_key, jaccard, sha256, token_vector, tokenize
from wellbe_raw_context_brain.types import (
    DETAILS,
    ControlTag,
    Exhaustion,
    ExploreInput,
    ExportItem,
    IngestInput,
    IngestResult,
    JudgeCandidate,
    JudgeDecision,
    JudgeRequest,
    Judgment,
    JudgmentRecord,
    LinkAdvertisement,
    LinkJudge,
    LocalCount,
    NextRoute,
    PointerNode,
    PruneRecord,
    Rankable,
    Relation,
    RouteKind,
    SemanticData,
    TerminalReason,
    VaultEvent,
    assert_safe_detail,
)

_POLICY_VERSION = "lab-policy-1"
_MODEL_VERSION = "lab-heuristic-1"
_PROMPT_VERSION = "lab-prompt-1"
_NO_LIMIT = 2**62
_TERMINALS = frozenset(
    {
        "supported_leaf",
        "approximate_frontier_exhausted",
        "budget_exhausted",
        "policy_blocked",
        "authorization_changed",
        "stale_snapshot",
        "dependency_unavailable",
        "insufficient_independent_evidence",
    }
)
_ROUTE_KINDS = frozenset({"facet", "temporal", "neighbour", "source", "fallback"})


def _route_token() -> str:
    """128 bits. The prefix is not entropy. The walk stays in the server record this id names."""
    return f"rh_{secrets.token_hex(16)}"


def _base36(value: int) -> str:
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if value == 0:
        return "0"
    chars: list[str] = []
    remaining = value
    while remaining:
        remaining, rem = divmod(remaining, 36)
        chars.append(digits[rem])
    return "".join(reversed(chars))


def _clamp(value: float) -> float:
    if math.isnan(value):
        return 0.0
    return min(1.0, max(0.0, value))


def _cmp_rank(left: Rankable, right: Rankable) -> int:
    delta = compare_rank(left, right)
    if delta < 0:
        return -1
    if delta > 0:
        return 1
    return 0


def _default_now() -> int:
    return int(time.time() * 1000)


async def _noop_sleep(_delay_ms: int) -> None:
    return None


def _iso_from_ms(milliseconds: int) -> str:
    moment = time.gmtime(milliseconds / 1000)
    millis = int(milliseconds) % 1000
    return time.strftime("%Y-%m-%dT%H:%M:%S", moment) + f".{millis:03d}Z"


@dataclass
class LabOptions:
    judge: LinkJudge | None = None
    seed: int = 1
    page_size: int = 5
    max_candidates: int = 8
    hop_limit: int = 4
    frontier_cap: int = 32
    expansion_budget: int = 64
    handle_ttl_ms: int = 60_000
    max_handle_uses: int = 8
    now: Callable[[], int] | None = None
    policy_version: str = _POLICY_VERSION
    retry_base_ms: int = 0
    judge_deadline_ms: int | None = None
    max_in_flight: int | None = None
    sleep: Callable[[int], Awaitable[None]] | None = None
    graph_store: GraphStore | None = None
    session_store: SessionStore | None = None
    # Durable snapshots keep pointers. Note text is read from the vault per request.
    pointer_only: bool = False


@dataclass(frozen=True)
class RouteSets:
    candidate_ids: list[str]
    selected_ids: list[str]
    exported_handles: list[str]
    pruned: list[PruneRecord]


@dataclass(frozen=True)
class CandidateSplit:
    hnsw: list[str]
    exact: list[str]


@dataclass(frozen=True)
class LocalAssessment:
    judgment: Literal["no_link", "uncertain"]
    relation: Relation
    active_edge: bool
    excerpt: str
    other_excerpt: str


@dataclass(frozen=True)
class TrailLook:
    page: SemanticData
    counts: LocalCount


@dataclass
class LocalRoute:
    route_id: str
    label: str
    kind: RouteKind
    node_ids: list[str]


@dataclass(frozen=True)
class LocalNode:
    id: str
    source_type: str
    captured_at: str
    excerpt: str
    relation: Relation | None
    on_route: bool


@dataclass(frozen=True)
class LocalOverlay:
    visited: list[str]
    frontier: list[str]
    anchor_id: str
    counts: LocalCount
    nodes: list[LocalNode]


@dataclass(frozen=True)
class ViewNode:
    id: str
    kind: Literal["event", "pseudonode"]
    source_type: str
    degree: int


@dataclass(frozen=True)
class ViewLink:
    source: int
    target: int
    reason: str


@dataclass(frozen=True)
class ViewModel:
    nodes: list[ViewNode]
    links: list[ViewLink]


@dataclass(frozen=True)
class InterestRecord:
    nonce: str
    purpose: str
    operation: str
    state: Literal["satisfied"]


@dataclass
class PruneTally:
    reason: str
    count: int


@dataclass
class LabMetrics:
    cross_person_candidates: int = 0
    unissued_handles: int = 0
    judge_attempts: int = 0
    cache_clears: int = 0
    pruned: list[PruneTally] = field(default_factory=list)
    prune_records: list[PruneRecord] = field(default_factory=list)


@dataclass
class _FrontierItem:
    node_id: str
    from_id: str
    edge_key: str
    reason: str
    rank: Rankable


@dataclass
class _HandleRecord:
    token: str
    person_id: str
    session: Literal["exploration"]
    purpose: str
    authorization_epoch: int
    snapshot_revision: int
    snapshot_digest: str
    frontier: list[_FrontierItem]
    visited_nodes: list[str]
    visited_edges: list[str]
    breadcrumb: list[str]
    hop_depth: int
    cycle_count: int
    expansions: int
    anchor_id: str
    approximate_seed: bool
    expires_at: int
    use_count: int
    max_uses: int
    route_bindings: dict[str, list[str]]
    advertised: list[LocalRoute]
    lineage_pruned: bool
    invalidated: bool
    invalid_reason: TerminalReason | None


@dataclass
class _RankedNote:
    id: str
    authorized: float
    provenance: float
    relevance: float
    novelty: float
    inverse_degree: float
    inverse_hop: float
    lineage: str
    source_type: str
    captured_at: str

    def rankable(self) -> Rankable:
        return Rankable(
            id=self.id,
            authorized=self.authorized,
            provenance=self.provenance,
            relevance=self.relevance,
            novelty=self.novelty,
            inverse_degree=self.inverse_degree,
            inverse_hop=self.inverse_hop,
        )


@dataclass
class _SelectionDraft:
    person_id: str
    candidate_ids: list[str]
    selected_ids: list[str]
    provenance: dict[str, RouteProvenance]
    pruned: list[PruneRecord]
    candidates: list[RankedCandidate]


class RawContextLab:
    def __init__(self, options: LabOptions | None = None) -> None:
        options = options or LabOptions()
        self.vault = Vault()
        self.log = AdvertisementLog()
        self.projection = Projection()
        self.metrics = LabMetrics()
        self.authorization_epoch = 1
        self._judge = options.judge or heuristic_judge()
        self._seed = options.seed
        self._page_size = options.page_size
        self._max_candidates = options.max_candidates
        self._hop_limit = options.hop_limit
        self._frontier_cap = options.frontier_cap
        self._expansion_budget = options.expansion_budget
        self._handle_ttl_ms = options.handle_ttl_ms
        self._max_handle_uses = options.max_handle_uses
        self._now = options.now or _default_now
        self._retry_base_ms = options.retry_base_ms
        self._judge_deadline_ms = (
            _NO_LIMIT if options.judge_deadline_ms is None else options.judge_deadline_ms
        )
        self._max_in_flight = _NO_LIMIT if options.max_in_flight is None else options.max_in_flight
        self._sleep = options.sleep or _noop_sleep
        self._policy_version = options.policy_version
        self._graph_store = options.graph_store
        self._session_store: SessionStore = options.session_store or MemorySessionStore()
        self._pointer_only = options.pointer_only
        self._in_flight = 0
        self._nodes: dict[str, PointerNode] = {}
        self._indexes: dict[str, HnswIndex] = {}
        self._controls: dict[str, set[ControlTag]] = {}
        self._handles: dict[str, _HandleRecord] = {}
        self._look_token: str | None = None
        self._pit: PendingInterestTable = create_pending_interest_table()
        self._interest_log: dict[str, InterestRecord] = {}
        self._route_log: RouteSetLog = create_route_sets()
        self._acknowledgements: list[LinkAcknowledgement] = []
        self._hydrating = False
        self._placed: set[str] = set()
        self._idempotency: dict[str, IngestResult] = {}
        self._last_primary: dict[str, str] = {}
        self._export_cache: dict[str, str] = {}
        self._item_counter = 0
        self._selection_draft: _SelectionDraft | None = None
        self._hydrate()

    def route_sets(self, person_id: str) -> RouteSets | None:
        latest = self._route_log.latest(person_id)
        if latest is None:
            return None
        return RouteSets(
            candidate_ids=list(latest.sets.candidate),
            selected_ids=list(latest.sets.selected),
            exported_handles=list(latest.sets.export),
            pruned=self._route_log.prune_audit(latest.revision),
        )

    def route_history(self, person_id: str) -> list[int]:
        return [revision.revision for revision in self._route_log.history(person_id)]

    def interest(self, person_id: str, request_id: str) -> InterestRecord | None:
        return self._interest_log.get(self._page_key(person_id, request_id))

    @property
    def hnsw_search_count(self) -> int:
        return sum(index.search_count for index in self._indexes.values())

    def pointer(self, node_id: str) -> PointerNode | None:
        return self._nodes.get(node_id)

    def controls_for(self, event_id: str) -> list[ControlTag]:
        return list(self._controls.get(event_id, ()))

    def mint_control(self, event_id: str, tag: ControlTag) -> None:
        if not self.vault.has(event_id):
            raise ValueError("unknown event")
        tags = self._controls.get(event_id)
        if tags is None:
            tags = set()
            self._controls[event_id] = tags
        tags.add(tag)

    def set_authorization_epoch(self, epoch: int) -> None:
        if epoch == self.authorization_epoch:
            return
        self.authorization_epoch = epoch
        self._clear_export_cache()
        for handle in self._handles.values():
            if handle.authorization_epoch != epoch:
                handle.invalidated = True
                handle.invalid_reason = "authorization_changed"

    def begin_rebuild(self) -> None:
        self.projection.status = "rebuilding"

    def finish_rebuild(self) -> None:
        self.log.verify_digests()
        assert_structural_ledger(self.log.ads, list(self._nodes.values()))
        self.projection.rebuild(self.log.ads)
        self._save_durable()

    def was_placed(self, event_id: str) -> bool:
        return event_id in self._placed

    def accepted_neighbour_ids(self, event_id: str) -> list[str]:
        """Accepted one-hop neighbours. This is the bounded set, not the vault."""
        return self.projection.neighbors(event_id)

    def bind_vault_events(self, events: Sequence[VaultEvent]) -> None:
        """Attach vault excerpts for this request. Does not store the text."""
        for event in events:
            current = self.vault.get(event.id)
            if current is None:
                self.vault.append(event)
                if event.id not in self._nodes:
                    self._nodes[event.id] = empty_pointer(event)
            else:
                self.vault.replace(event)
            if current is None or not current.text:
                self._index_for(event.person_id).add(event.id, token_vector(event.text))

    def add_fixture(self, event: VaultEvent) -> None:
        self.vault.append(event)
        self._nodes[event.id] = empty_pointer(event)
        self._index_for(event.person_id).add(event.id, token_vector(event.text))
        self._save_durable()

    def link_structural(
        self,
        from_id: str,
        to_id: str,
        reason_code: str = "recorded_association",
    ) -> LinkAdvertisement:
        evidence = tuple(node_id for node_id in (from_id, to_id) if self.vault.has(node_id))
        ad = self._append_ad(
            AdvertisementDraft(
                person_id=self._person_for(from_id, to_id),
                origin="policy",
                model_version=None,
                prompt_version=None,
                policy_version=self._policy_version,
                evidence_ids=evidence,
                from_id=from_id,
                to_id=to_id,
                judgment="link",
                reason_code=reason_code,
                relation=map_relation("policy", reason_code),
                proposed_confidence=0.4,
                confidence=0.4,
                created_at=_iso_from_ms(self._now()),
                supersedes_id=None,
                withdrawn=False,
            )
        )
        self.projection.apply(ad)
        self._save_durable()
        return ad

    def record_model_judgment(
        self,
        *,
        from_id: str,
        to_id: str,
        judgment: Judgment,
        reason_code: str,
        proposed_confidence: float,
        evidence_ids: Sequence[str],
    ) -> LinkAdvertisement:
        clean = sanitize_decision(
            JudgeDecision(
                handle="local",
                judgment=judgment,
                reason_code=reason_code,
                confidence=proposed_confidence,
            )
        )
        evidence = tuple(evidence_ids)
        confidence = self._cap_confidence(
            from_id,
            to_id,
            _clamp(clean.confidence),
            evidence,
            "model",
        )
        existing = self.projection.edge_between(from_id, to_id)
        ad = self._append_ad(
            AdvertisementDraft(
                person_id=self._person_for(from_id, to_id),
                origin="model",
                model_version=_MODEL_VERSION,
                prompt_version=_PROMPT_VERSION,
                policy_version=self._policy_version,
                evidence_ids=evidence,
                from_id=from_id,
                to_id=to_id,
                judgment=clean.judgment,
                reason_code=clean.reason_code,
                relation=map_relation("model", clean.reason_code),
                proposed_confidence=proposed_confidence,
                confidence=confidence,
                created_at=_iso_from_ms(self._now()),
                supersedes_id=None if existing is None else existing.ad_id,
                withdrawn=False,
            )
        )
        if self.projection.apply(ad):
            self._invalidate_for_snapshot()
        self._save_durable()
        return ad

    def correct(
        self,
        *,
        from_id: str,
        to_id: str,
        judgment: Judgment,
        confidence: float,
        evidence_ids: Sequence[str],
    ) -> LinkAdvertisement:
        existing = self.projection.edge_between(from_id, to_id)
        ad = self._append_ad(
            AdvertisementDraft(
                person_id=self._person_for(from_id, to_id),
                origin="user_correction",
                model_version=None,
                prompt_version=None,
                policy_version=self._policy_version,
                evidence_ids=tuple(evidence_ids),
                from_id=from_id,
                to_id=to_id,
                judgment=judgment,
                reason_code="user_correction",
                relation=map_relation("user_correction", "user_correction"),
                proposed_confidence=confidence,
                confidence=confidence,
                created_at=_iso_from_ms(self._now()),
                supersedes_id=None if existing is None else existing.ad_id,
                withdrawn=False,
            )
        )
        self.projection.apply(ad)
        self._invalidate_for_snapshot()
        self._save_durable()
        return ad

    def withdraw(self, ad_id: str) -> LinkAdvertisement:
        previous = self.log.get(ad_id)
        if previous is None:
            raise ValueError("unknown advertisement")
        ad = self._append_ad(
            AdvertisementDraft(
                person_id=previous.person_id,
                origin="user_correction",
                model_version=None,
                prompt_version=None,
                policy_version=self._policy_version,
                evidence_ids=tuple(previous.evidence_ids),
                from_id=previous.from_id,
                to_id=previous.to_id,
                judgment=previous.judgment,
                reason_code="withdrawal",
                relation=map_relation("user_correction", "withdrawal"),
                proposed_confidence=0,
                confidence=0,
                created_at=_iso_from_ms(self._now()),
                supersedes_id=ad_id,
                withdrawn=True,
            )
        )
        self.projection.apply(ad)
        self._drop_acknowledgement(previous.person_id, previous.from_id, previous.to_id)
        self._invalidate_for_snapshot()
        self._clear_export_cache()
        self._save_durable()
        return ad

    async def ingest(self, ingest_input: IngestInput) -> IngestResult:
        cache_key = f"{ingest_input.person_id}|{ingest_input.idempotency_key}"
        cached = self._idempotency.get(cache_key)
        if cached is not None:
            return cached

        event_id = f"evt_{sha256(cache_key)[:16]}"
        if not self.vault.has(event_id):
            event = VaultEvent(
                id=event_id,
                person_id=ingest_input.person_id,
                captured_at=ingest_input.captured_at,
                source_type=ingest_input.source_type,
                text=ingest_input.text,
                content_hash=sha256(ingest_input.text),
                lineage_id=ingest_input.lineage_id,
                document_id=ingest_input.document_id,
                independence=ingest_input.independence,
                source_arrival=ingest_input.source_arrival,
                copied_from_id=ingest_input.copied_from_id,
            )
            self.vault.append(event)
            self._nodes[event.id] = empty_pointer(event)
            self._index_for(ingest_input.person_id).add(event.id, token_vector(event.text))
            if ingest_input.document_id:
                self._attach_hub(event)

        if self.projection.status == "rebuilding":
            return self._remember(
                ingest_input,
                IngestResult(
                    event_id=event_id,
                    candidate_count=0,
                    export_bytes=0,
                    judgments=(),
                    terminal_reason="dependency_unavailable",
                    detail=DETAILS["dependency_unavailable"],
                    route_revision=None,
                    pruned=(),
                ),
            )

        bound = self.vault.get(event_id)
        if bound is None:
            raise ValueError("unknown event")
        return self._remember(ingest_input, await self.place_bound_event(bound))

    async def place_bound_event(self, event: VaultEvent) -> IngestResult:
        """Judge one vault record that is already bound. A repeat does not add links."""
        if event.id in self._placed:
            return IngestResult(
                event_id=event.id,
                candidate_count=0,
                export_bytes=0,
                judgments=(),
                terminal_reason=None,
                detail="",
                route_revision=None,
                pruned=(),
            )
        event_id = event.id
        candidate_ids = self._select_candidates(
            event.person_id,
            event.text,
            event_id,
            event.captured_at,
        )
        issued: dict[str, str] = {}
        judge_candidates: list[JudgeCandidate] = []
        for node_id in candidate_ids:
            exported = self._export_node(node_id, "candidate")
            if exported is None:
                continue
            issued[exported.handle] = node_id
            judge_candidates.append(_judge_candidate(exported))
        published = self._publish_selection(event.person_id, issued)
        request = JudgeRequest(
            new_handle="ch_new",
            excerpt=event.text[:180],
            source_type=event.source_type,
            captured_at=event.captured_at,
            candidates=tuple(judge_candidates),
        )
        export_bytes = _request_bytes(request)
        try:
            decisions = await self._judge_with_retry(request)
        except Exception:
            return IngestResult(
                event_id=event_id,
                candidate_count=len(judge_candidates),
                export_bytes=export_bytes,
                judgments=(),
                terminal_reason="dependency_unavailable",
                detail=DETAILS["dependency_unavailable"],
                route_revision=published[0],
                pruned=tuple(published[1]),
            )

        judgments: list[JudgmentRecord] = []
        for raw in decisions:
            decision = sanitize_decision(raw)
            other_id = issued.get(decision.handle)
            if other_id is None:
                self.metrics.unissued_handles += 1
                judgments.append(
                    JudgmentRecord(
                        handle=decision.handle,
                        judgment=decision.judgment,
                        reason_code=decision.reason_code,
                        accepted=False,
                    )
                )
                continue
            other = self._nodes.get(other_id)
            if other is None or other.person_id != event.person_id:
                self.metrics.cross_person_candidates += 1
                judgments.append(
                    JudgmentRecord(
                        handle=decision.handle,
                        judgment=decision.judgment,
                        reason_code=decision.reason_code,
                        accepted=False,
                    )
                )
                continue
            evidence_ids = (event_id, other_id)
            confidence = self._cap_confidence(
                event_id,
                other_id,
                _clamp(decision.confidence),
                evidence_ids,
                "model",
            )
            existing = self.projection.edge_between(event_id, other_id)
            ad = self._append_ad(
                AdvertisementDraft(
                    person_id=event.person_id,
                    origin="model",
                    model_version=_MODEL_VERSION,
                    prompt_version=_PROMPT_VERSION,
                    policy_version=self._policy_version,
                    evidence_ids=evidence_ids,
                    from_id=event_id,
                    to_id=other_id,
                    judgment=decision.judgment,
                    reason_code=decision.reason_code,
                    relation=map_relation("model", decision.reason_code),
                    proposed_confidence=_clamp(decision.confidence),
                    confidence=confidence,
                    created_at=event.captured_at,
                    supersedes_id=None if existing is None else existing.ad_id,
                    withdrawn=False,
                )
            )
            self.projection.apply(ad)
            judgments.append(
                JudgmentRecord(
                    handle=decision.handle,
                    judgment=decision.judgment,
                    reason_code=decision.reason_code,
                    accepted=True,
                )
            )

        await self._judge_referral_round(
            IngestInput(
                person_id=event.person_id,
                text=event.text,
                source_type=event.source_type,
                captured_at=event.captured_at,
                lineage_id=event.lineage_id,
                idempotency_key=event.id,
                independence=event.independence,
                source_arrival=event.source_arrival,
                copied_from_id=event.copied_from_id,
                document_id=event.document_id,
            ),
            event_id,
            issued,
            judgments,
        )
        self._placed.add(event.id)
        self._save_durable()
        return IngestResult(
            event_id=event_id,
            candidate_count=len(judge_candidates),
            export_bytes=export_bytes,
            judgments=tuple(judgments),
            terminal_reason=None,
            detail="",
            route_revision=published[0],
            pruned=tuple(published[1]),
        )

    def explore(self, explore_input: ExploreInput) -> SemanticData:
        operation = _operation_name(explore_input)
        nonce: str | None = None
        if explore_input.request_id:
            began = self._begin_interest(
                self._semantic_interest(explore_input, operation),
                explore_input.route_handle
                or explore_input.anchor_id
                or explore_input.query
                or "open",
            )
            if isinstance(began, RejectedBegin):
                return self._stopped("policy_blocked", DETAILS["wrong_purpose"])
            if isinstance(began, SatisfiedBegin):
                saved = began.result
                if isinstance(saved, SemanticData):
                    return self._replay(saved)
                return self._stopped("dependency_unavailable")
            if began.joined:
                return self._stopped("dependency_unavailable")
            nonce = began.nonce
        if explore_input.route_handle:
            data = self._continue_handle(explore_input)
        else:
            data = self._open_route(explore_input)
        if nonce:
            self._pit.satisfy(nonce, data)
            self._interest_log[self._page_key(explore_input.person_id, nonce)] = InterestRecord(
                nonce=nonce,
                purpose=explore_input.purpose,
                operation=operation,
                state="satisfied",
            )
        return data

    def local_routes(self, route_handle: str) -> list[LocalRoute]:
        record = self._handles.get(route_handle)
        if record is None or record.invalidated:
            return []
        return [
            LocalRoute(
                route_id=route.route_id,
                label=route.label,
                kind=route.kind,
                node_ids=list(route.node_ids),
            )
            for route in record.advertised
        ]

    def local_overlay(self, route_handle: str) -> LocalOverlay | None:
        record = self._handles.get(route_handle)
        if record is None:
            return None
        if record.anchor_id:
            reach = self._reachable(record.anchor_id)
        else:
            reach = _Reach(count=len(record.visited_nodes), capped=False)
        seen: list[str] = []
        known: set[str] = set()
        for node_id in [*record.visited_nodes, *[item.node_id for item in record.frontier]]:
            if node_id in known:
                continue
            known.add(node_id)
            seen.append(node_id)
        return LocalOverlay(
            visited=list(record.visited_nodes),
            frontier=[item.node_id for item in record.frontier],
            anchor_id=record.anchor_id,
            counts=LocalCount(
                explored_count=len(record.visited_nodes),
                unexplored_count=max(
                    0,
                    reach.count - len(record.visited_nodes),
                    len(record.frontier),
                ),
                reachable_count=reach.count,
                count_label="approximate" if reach.capped or record.approximate_seed else "exact",
            ),
            nodes=[self._local_node(node_id, record) for node_id in seen],
        )

    def describe_trail(self, person_id: str, trail: Sequence[str]) -> TrailLook:
        if self._look_token:
            self._handles.pop(self._look_token, None)
            self._look_token = None
        ids = [
            node_id
            for node_id in trail
            if (node := self._nodes.get(node_id)) is not None and node.person_id == person_id
        ]
        if not ids:
            page = self._stopped("supported_leaf")
            return TrailLook(
                page=page,
                counts=LocalCount(
                    explored_count=0,
                    unexplored_count=0,
                    reachable_count=0,
                    count_label="exact",
                ),
            )
        anchor = ids[0]
        record = self._blank_handle(
            ExploreInput(person_id=person_id, purpose="look", request_id="", anchor_id=anchor)
        )
        self._look_token = record.token
        record.anchor_id = anchor
        record.visited_nodes.append(anchor)
        record.breadcrumb.append(self._breadcrumb_label(anchor))
        self._expand(record, anchor)
        for node_id in ids[1:]:
            previous = record.visited_nodes[-1] if record.visited_nodes else None
            if previous is None or node_id not in self.projection.neighbors(previous):
                break
            if node_id in record.visited_nodes:
                record.cycle_count += 1
                continue
            key = edge_key(previous, node_id)
            record.frontier = [item for item in record.frontier if item.node_id != node_id]
            record.visited_nodes.append(node_id)
            record.visited_edges.append(key)
            record.hop_depth += 1
            record.breadcrumb.append(self._breadcrumb_label(node_id))
            self._expand(record, node_id)
        page = self._finish(record, [], [], None)
        overlay = self.local_overlay(record.token)
        counts = (
            overlay.counts
            if overlay is not None
            else LocalCount(
                explored_count=len(record.visited_nodes),
                unexplored_count=0,
                reachable_count=len(record.visited_nodes),
                count_label="exact",
            )
        )
        return TrailLook(page=page, counts=counts)

    def local_assessments(self, person_id: str) -> list[LocalAssessment]:
        rows: list[LocalAssessment] = []
        for ad in self.log.ads:
            if ad.withdrawn or ad.judgment == "link":
                continue
            origin = self._nodes.get(ad.from_id)
            if origin is None or origin.person_id != person_id:
                continue
            if ad.judgment != "no_link" and ad.judgment != "uncertain":
                continue
            from_event = self.vault.get(ad.from_id)
            to_event = self.vault.get(ad.to_id)
            rows.append(
                LocalAssessment(
                    judgment=ad.judgment,
                    relation=ad.relation,
                    active_edge=self.projection.edge_between(ad.from_id, ad.to_id) is not None,
                    excerpt=ad.from_id if from_event is None else from_event.text[:80],
                    other_excerpt=ad.to_id if to_event is None else to_event.text[:80],
                )
            )
        return rows[-12:]

    def candidate_split(self, person_id: str, text: str, self_id: str) -> CandidateSplit:
        exact = self._exact_candidates(person_id, text, self_id)
        index = self._indexes.get(person_id)
        hnsw = (
            [
                hit.id
                for hit in index.search(token_vector(text), 16)
                if hit.id != self_id
            ]
            if index is not None
            else []
        )
        return CandidateSplit(hnsw=hnsw, exact=exact)

    def view(self, person_id: str) -> ViewModel:
        nodes = [node for node in self._nodes.values() if node.person_id == person_id]
        index = {node.id: position for position, node in enumerate(nodes)}
        links: list[ViewLink] = []
        for edge in self.projection.accepted():
            source = index.get(edge.from_id)
            target = index.get(edge.to_id)
            if source is None or target is None:
                continue
            links.append(ViewLink(source=source, target=target, reason=edge.reason_code))
        view_nodes = [
            ViewNode(
                id=node.id,
                kind=node.kind,
                source_type=_source_type(self.vault.get(node.id)),
                degree=self.projection.degree(node.id),
            )
            for node in nodes
        ]
        return ViewModel(nodes=view_nodes, links=links)

    def expire_exploration(self) -> None:
        self._handles.clear()
        self._session_store.clear()
        self._pit.clear()
        self._interest_log.clear()

    def acknowledge(self, person_id: str, from_id: str, to_id: str) -> None:
        endpoint_ids = _endpoint_ids(from_id, to_id)
        nxt = LinkAcknowledgement(
            person_id=person_id,
            endpoint_ids=endpoint_ids,
            acknowledged=True,
            updated_at=_iso_from_ms(self._now()),
        )
        for index, row in enumerate(self._acknowledgements):
            if row.person_id == person_id and row.endpoint_ids == endpoint_ids:
                self._acknowledgements[index] = nxt
                self._save_durable()
                return
        self._acknowledgements.append(nxt)
        self._save_durable()

    def _open_route(self, explore_input: ExploreInput) -> SemanticData:
        if self.projection.status == "rebuilding":
            return self._stopped("dependency_unavailable")
        if explore_input.anchor_id:
            node = self._nodes.get(explore_input.anchor_id)
            if node is None or node.person_id != explore_input.person_id:
                return self._stopped("policy_blocked", DETAILS["unknown_anchor"])
        elif not explore_input.query and self._person_count(explore_input.person_id) == 0:
            return self._stopped("supported_leaf")
        elif not explore_input.query:
            return self._stopped("policy_blocked", DETAILS["unknown_anchor"])

        record = self._blank_handle(explore_input)
        if explore_input.anchor_id:
            record.anchor_id = explore_input.anchor_id
            record.approximate_seed = False
            record.visited_nodes.append(explore_input.anchor_id)
            record.breadcrumb.append(self._breadcrumb_label(explore_input.anchor_id))
            self._expand(record, explore_input.anchor_id)
            if explore_input.hold_at_anchor:
                return self._finish(record, [], [], None)
        elif explore_input.query:
            record.approximate_seed = True
            seeds = self._select_candidates(explore_input.person_id, explore_input.query, "", "")
            for node_id in seeds:
                record.frontier.append(self._frontier_from(node_id, "semantic_candidate"))
            if not seeds:
                reason: TerminalReason = (
                    "supported_leaf"
                    if self._person_count(explore_input.person_id) == 0
                    else "approximate_frontier_exhausted"
                )
                return self._stopped(reason)
            record.anchor_id = seeds[0]
        return self._step(record)

    def _replay(self, saved: SemanticData) -> SemanticData:
        record = self._load_handle(saved.route)
        if record is not None and record.authorization_epoch != self.authorization_epoch:
            return self._stopped("authorization_changed")
        if (
            saved.snapshot_revision != self.projection.revision
            or saved.snapshot_digest != self.projection.digest
        ):
            return self._stopped("stale_snapshot")
        return saved

    def _continue_handle(self, explore_input: ExploreInput) -> SemanticData:
        record = self._load_handle(explore_input.route_handle or "")
        if record is None:
            return self._stopped("policy_blocked", DETAILS["unknown_handle"])
        if record.person_id != explore_input.person_id:
            return self._stopped("policy_blocked")
        if record.purpose != explore_input.purpose:
            return self._stopped("policy_blocked", DETAILS["wrong_purpose"])
        if explore_input.operation == "assess_link":
            return self._stopped("policy_blocked", DETAILS["wrong_operation"])
        if (
            record.authorization_epoch != self.authorization_epoch
            or record.invalid_reason == "authorization_changed"
        ):
            return self._stopped("authorization_changed")
        if (
            record.invalidated
            or record.invalid_reason == "stale_snapshot"
            or record.snapshot_revision != self.projection.revision
            or record.snapshot_digest != self.projection.digest
        ):
            return self._stopped("stale_snapshot")
        if explore_input.focus_id and not explore_input.route_id:
            return self._stopped("policy_blocked")
        if explore_input.route_id and explore_input.focus_id:
            bound = record.route_bindings.get(explore_input.route_id, [])
            if explore_input.focus_id not in bound:
                return self._stopped("policy_blocked")
        if self._now() > record.expires_at:
            return self._stopped("policy_blocked", DETAILS["handle_expired"])
        if record.use_count >= record.max_uses:
            return self._stopped("policy_blocked", DETAILS["handle_use_limit"])
        if explore_input.operation == "rewind":
            if not explore_input.rewind_to_id:
                return self._stopped("policy_blocked", DETAILS["rewind_target"])
            record.use_count += 1
            return self._rewind(record, explore_input.rewind_to_id)
        searches = self.hnsw_search_count
        record.use_count += 1
        aside: list[_FrontierItem] = []
        if explore_input.route_id:
            bound = record.route_bindings.get(explore_input.route_id, [])
            if not bound:
                return self._stopped("supported_leaf")
            chosen = next(
                (route for route in record.advertised if route.route_id == explore_input.route_id),
                None,
            )
            retrieves = (
                chosen is not None and chosen.kind in {"facet", "temporal", "source"}
            )
            if retrieves:
                record.frontier = [item for item in record.frontier if item.node_id in bound]
                return self._finish(record, [], [], None)
            if explore_input.focus_id:
                aside = [item for item in record.frontier if item.node_id != explore_input.focus_id]
                record.frontier = [
                    item for item in record.frontier if item.node_id == explore_input.focus_id
                ]
            else:
                record.frontier = [item for item in record.frontier if item.node_id in bound]
        data = self._step(record, aside, one=bool(explore_input.focus_id))
        if self.hnsw_search_count != searches:
            raise RuntimeError("continuation must not rerun candidate search")
        return data

    def _rewind(self, record: _HandleRecord, target_id: str) -> SemanticData:
        cut = truncate_path(record.visited_nodes, target_id)
        if isinstance(cut, RewindTargetError):
            return self._stopped("policy_blocked", DETAILS["rewind_target"])
        index = len(cut.visited) - 1
        record.visited_nodes = list(cut.visited)
        record.breadcrumb = record.breadcrumb[: len(cut.visited)]
        record.hop_depth = max(0, index)
        edges: list[str] = []
        for position in range(1, len(record.visited_nodes)):
            previous = record.visited_nodes[position - 1]
            current = record.visited_nodes[position]
            edges.append(edge_key(previous, current))
        record.visited_edges = edges
        record.frontier = [
            item
            for item in record.frontier
            if item.from_id in record.visited_nodes and item.node_id not in record.visited_nodes
        ]
        self._expand(record, target_id)
        return self._finish(record, [], [], None)

    def _step(
        self,
        record: _HandleRecord,
        aside: list[_FrontierItem] | None = None,
        *,
        one: bool = False,
    ) -> SemanticData:
        held_aside = [] if aside is None else aside
        limit = 1 if one else self._page_size
        items: list[ExportItem] = []
        already: list[str] = []

        def done(terminal: TerminalReason | None) -> SemanticData:
            self._restore_frontier(record, held_aside)
            return self._finish(record, items, already, terminal)

        while len(items) < limit:
            if record.expansions >= self._expansion_budget or record.hop_depth >= self._hop_limit:
                return done("budget_exhausted")
            forward = self._forward_items(record)
            forward.sort(key=cmp_to_key(lambda left, right: _cmp_rank(left.rank, right.rank)))
            if not forward:
                break
            nxt = forward[0]
            record.frontier = [item for item in record.frontier if item is not nxt]
            if nxt.node_id in record.visited_nodes or nxt.edge_key in record.visited_edges:
                record.cycle_count += 1
                already.append("already_explored")
                continue
            record.visited_nodes.append(nxt.node_id)
            record.visited_edges.append(nxt.edge_key)
            record.hop_depth += 1
            record.breadcrumb.append(self._breadcrumb_label(nxt.node_id))
            exported = self._export_node(nxt.node_id, nxt.reason)
            if exported is not None:
                items.append(exported)
            self._expand(record, nxt.node_id)
        return done(None)

    def _finish(
        self,
        record: _HandleRecord,
        items: list[ExportItem],
        already: list[str],
        terminal: TerminalReason | None,
    ) -> SemanticData:
        terminal_reason = terminal
        exhaustion: Exhaustion = "not_yet_exhausted"
        if terminal_reason is None and not self._forward_items(record):
            if record.lineage_pruned and not self._component_covered(record):
                terminal_reason = "insufficient_independent_evidence"
                exhaustion = "exact"
            elif not items and not already:
                if record.approximate_seed and not self._component_covered(record):
                    terminal_reason = "approximate_frontier_exhausted"
                else:
                    terminal_reason = "supported_leaf"
                exhaustion = (
                    "approximate"
                    if terminal_reason == "approximate_frontier_exhausted"
                    else "exact"
                )
        elif terminal_reason == "budget_exhausted":
            exhaustion = "not_yet_exhausted"
        elif terminal_reason is not None:
            exhaustion = "exact"

        detail = (
            DETAILS[terminal_reason]
            if terminal_reason is not None
            else "exploration can continue from the saved frontier"
        )
        assert_safe_detail(detail)

        next_routes: tuple[NextRoute, ...] = ()
        if terminal_reason is None:
            advertised = self._advertise(record)
            record.advertised = advertised
            record.route_bindings = {route.route_id: list(route.node_ids) for route in advertised}
            next_routes = tuple(
                NextRoute(route_id=route.route_id, label=route.label, kind=route.kind)
                for route in advertised
            )
        elif not retains_session(terminal_reason):
            record.invalidated = True
            record.invalid_reason = terminal_reason
        self._persist_session(record)

        current = record.visited_nodes[-1] if record.visited_nodes else record.anchor_id
        return SemanticData(
            route=record.token,
            breadcrumb=tuple(record.breadcrumb[-8:]),
            hop_depth=record.hop_depth,
            direct_link_count=self.projection.degree(current) if current else 0,
            cycle_count=record.cycle_count,
            exhaustion=exhaustion,
            items=tuple(items),
            already_explored=tuple(already),
            next_routes=next_routes,
            terminal_reason=terminal_reason,
            detail=detail,
            route_handle=record.token if retains_session(terminal_reason) else None,
            snapshot_revision=self.projection.revision,
            snapshot_digest=self.projection.digest,
        )

    def _expand(self, record: _HandleRecord, node_id: str) -> None:
        lineage_counts: dict[str, int] = {}
        for item in record.frontier:
            event = self.vault.get(item.node_id)
            lineage = item.node_id if event is None else event.lineage_id
            lineage_counts[lineage] = lineage_counts.get(lineage, 0) + 1
        ranked: list[_FrontierItem] = []
        for other in self.projection.neighbors(node_id):
            record.expansions += 1
            if record.expansions > self._expansion_budget:
                self.metrics.pruned.append(PruneTally(reason="expansion_budget", count=1))
                break
            key = edge_key(node_id, other)
            if other in record.visited_nodes or key in record.visited_edges:
                record.cycle_count += 1
                continue
            if any(item.node_id == other and item.from_id == node_id for item in record.frontier):
                continue
            event = self.vault.get(other)
            lineage = other if event is None else event.lineage_id
            seen = lineage_counts.get(lineage, 0)
            if seen >= LAB_CAP:
                record.lineage_pruned = True
                self.metrics.pruned.append(PruneTally(reason="lineage_cap", count=1))
                continue
            lineage_counts[lineage] = seen + 1
            edge = self.projection.edge_between(node_id, other)
            ranked.append(
                self._frontier_from(
                    other,
                    "recorded_association" if edge is None else edge.reason_code,
                    key=key,
                    hop=record.hop_depth,
                    confidence=0.4 if edge is None else edge.confidence,
                    from_id=node_id,
                )
            )
        ranked.sort(key=cmp_to_key(lambda left, right: _cmp_rank(left.rank, right.rank)))
        room = self._frontier_cap - len(record.frontier)
        if len(ranked) > max(0, room):
            overflow = ranked[max(0, room) :]
            self.metrics.pruned.append(PruneTally(reason="frontier_cap", count=len(overflow)))
            for item in overflow:
                self.metrics.prune_records.append(
                    PruneRecord(id=item.node_id, reason="frontier_cap")
                )
        if room > 0:
            record.frontier.extend(ranked[:room])

    def _advertise(self, record: _HandleRecord) -> list[LocalRoute]:
        routes: list[LocalRoute] = []
        anchor = self.vault.get(record.anchor_id)
        current_id = record.visited_nodes[-1] if record.visited_nodes else record.anchor_id
        current = self.vault.get(current_id)
        frontier_ids = [item.node_id for item in self._forward_items(record)]
        serial = 0

        def push(kind: RouteKind, label: str, node_ids: list[str]) -> None:
            nonlocal serial
            limit = 7 if kind == "fallback" else 6
            if len(routes) >= limit:
                return
            if kind != "fallback" and not node_ids:
                return
            serial += 1
            routes.append(
                LocalRoute(route_id=f"nr_{serial}", label=label, kind=kind, node_ids=list(node_ids))
            )

        for node_id in frontier_ids[:3]:
            push("neighbour", f"Open {node_id}", [node_id])
        by_type: dict[str, list[str]] = {}
        earlier: list[str] = []
        later: list[str] = []
        for node_id in frontier_ids:
            event = self.vault.get(node_id)
            if event is None:
                continue
            group = by_type.get(event.source_type)
            if group is None:
                group = []
                by_type[event.source_type] = group
            group.append(node_id)
            if anchor is not None and event.captured_at < anchor.captured_at:
                earlier.append(node_id)
            if anchor is not None and event.captured_at > anchor.captured_at:
                later.append(node_id)
        first_type = next(iter(by_type.items()), None)
        if first_type is not None:
            push("facet", f"Only {source_name(first_type[0]).lower()}s", first_type[1])
        if earlier:
            push("temporal", "Earlier context", earlier)
        if later:
            push("temporal", "Later context", later)
        source_ids: list[str] = []
        for node_id in frontier_ids:
            if current is not None and current.copied_from_id == node_id:
                source_ids.append(node_id)
                continue
            node = self._nodes.get(node_id)
            if (
                node is not None
                and node.kind == "pseudonode"
                and current_id in node.member_event_ids
            ):
                source_ids.append(node_id)
        if source_ids:
            push("source", "Original record", source_ids)
        push("fallback", "Stop here", [])
        return select_issued_actions(routes)

    def _select_candidates(
        self,
        person_id: str,
        text: str,
        self_id: str,
        captured_at: str,
    ) -> list[str]:
        exact = self._exact_candidates(person_id, text, self_id)
        index = self._indexes.get(person_id)
        hits = index.search(token_vector(text), 16) if index is not None else []
        distances = {hit.id: hit.distance for hit in hits}
        union = set(exact)
        union.update(hit.id for hit in hits)
        ranked: list[_RankedNote] = []
        for node_id in union:
            if node_id == self_id:
                continue
            node = self._nodes.get(node_id)
            if node is None or node.person_id != person_id:
                self.metrics.cross_person_candidates += 1
                continue
            tags = self._controls.get(node_id)
            if tags is not None and ("no-model" in tags or "no-forward" in tags):
                continue
            event = self.vault.get(node_id)
            degree = self.projection.degree(node_id)
            distance = distances.get(node_id)
            event_text = "" if event is None else event.text
            similarity = jaccard(text, event_text) if distance is None else 1 - distance
            ranked.append(
                _RankedNote(
                    id=node_id,
                    authorized=1,
                    provenance=1,
                    relevance=similarity,
                    novelty=1,
                    inverse_degree=inverse_degree(degree),
                    inverse_hop=1,
                    lineage=node_id if event is None else event.lineage_id,
                    source_type="hub" if event is None else event.source_type,
                    captured_at="" if event is None else event.captured_at,
                )
            )
        ranked.sort(
            key=cmp_to_key(lambda left, right: _cmp_rank(left.rankable(), right.rankable()))
        )
        held = apply_hysteresis(ranked, self._last_primary.get(person_id))
        if held.held_previous:
            self.metrics.pruned.append(PruneTally(reason="hysteresis_hold", count=1))
            if held.ranked:
                self.metrics.prune_records.append(
                    PruneRecord(id=held.ranked[0].id, reason="hysteresis_hold")
                )
        ordered = held.ranked
        token_ids = self._token_matches(person_id, text, self_id)
        hnsw_ids = {hit.id for hit in hits}
        neighbor_ids = {node_id for node_id in exact if node_id not in token_ids}
        candidates = [
            RankedCandidate(
                id=item.id,
                lineage=item.lineage,
                source_type=item.source_type,
                facet=item.source_type,
                reason=self._discovery_of(item.id, token_ids, neighbor_ids, hnsw_ids),
                captured_at=item.captured_at,
                relevance=item.relevance,
                neighbors=self._candidate_neighbors(person_id, text, item.id, self_id),
            )
            for item in ordered
        ]
        selection = apply_selection(
            SelectionInput(candidates=tuple(candidates), captured_at=captured_at or None)
        )
        kept = list(selection.kept[: self._max_candidates])
        pruned = [
            *selection.pruned,
            *[
                PruneRecord(id=node_id, reason="candidate_cap")
                for node_id in selection.kept[self._max_candidates :]
            ],
        ]
        for row in pruned:
            self.metrics.pruned.append(PruneTally(reason=row.reason, count=1))
            self.metrics.prune_records.append(row)
        kept_ids = set(kept)
        provenance: dict[str, RouteProvenance] = {}
        for rank, item in enumerate(ordered):
            prune = next((row for row in pruned if row.id == item.id), None)
            if prune is not None:
                prune_reason: str | None = prune.reason
            elif item.id in kept_ids:
                prune_reason = None
            else:
                prune_reason = "candidate_cap"
            provenance[item.id] = RouteProvenance(
                discovery=self._discovery_of(item.id, token_ids, neighbor_ids, hnsw_ids),
                rank=rank,
                prune_reason=prune_reason,
                export_handle=None,
            )
        self._selection_draft = _SelectionDraft(
            person_id=person_id,
            candidate_ids=[item.id for item in ordered],
            selected_ids=kept,
            provenance=provenance,
            pruned=list(pruned),
            candidates=candidates,
        )
        if kept:
            self._last_primary[person_id] = kept[0]
        return kept

    async def _judge_with_retry(self, request: JudgeRequest) -> list[JudgeDecision]:
        started_at = self._now()
        last_error: BaseException = RuntimeError("dependency_unavailable")
        for attempt in range(3):
            decision = schedule_attempt(
                AttemptInput(
                    attempt=attempt,
                    now=self._now(),
                    started_at=started_at,
                    deadline_ms=self._judge_deadline_ms,
                    base_ms=self._retry_base_ms,
                    in_flight=self._in_flight,
                    max_in_flight=self._max_in_flight,
                    seed=self._seed,
                )
            )
            if isinstance(decision, StopDecision):
                raise RuntimeError(decision.reason)
            if attempt > 0 and decision.delay_ms > 0:
                await self._sleep(decision.delay_ms)
            self.metrics.judge_attempts += 1
            self._in_flight += 1
            try:
                return await self._judge.judge(request)
            except Exception as error:
                last_error = error
            finally:
                self._in_flight -= 1
        raise last_error

    async def _judge_referral_round(
        self,
        ingest_input: IngestInput,
        event_id: str,
        issued: dict[str, str],
        judgments: list[JudgmentRecord],
    ) -> None:
        draft = self._selection_draft
        if draft is None:
            return
        judged: list[JudgedCandidate] = []
        for handle, node_id in issued.items():
            row = next((item for item in judgments if item.handle == handle), None)
            candidate = next((item for item in draft.candidates if item.id == node_id), None)
            if row is None or candidate is None:
                continue
            judged.append(
                JudgedCandidate(
                    id=node_id,
                    judgment=row.judgment,
                    relevance=candidate.relevance,
                    neighbors=candidate.neighbors,
                )
            )
        round_result = apply_referral_round(
            ReferralRoundInput(judged=tuple(judged), tried=tuple(issued.values()))
        )
        if not round_result.referrals:
            return
        extra = []
        extra_issued: dict[str, str] = {}
        for node_id in round_result.referrals:
            exported = self._export_node(node_id, "referral")
            if exported is None:
                continue
            extra_issued[exported.handle] = node_id
            extra.append(_judge_candidate(exported))
        if not extra:
            return
        try:
            decisions = await self._judge_with_retry(
                JudgeRequest(
                    new_handle="ch_new",
                    excerpt=ingest_input.text[:180],
                    source_type=ingest_input.source_type,
                    captured_at=ingest_input.captured_at,
                    candidates=tuple(extra),
                )
            )
        except Exception:
            return
        for raw in decisions:
            decision = sanitize_decision(raw)
            other_id = extra_issued.get(decision.handle)
            if other_id is None:
                continue
            evidence_ids = (event_id, other_id)
            confidence = self._cap_confidence(
                event_id,
                other_id,
                _clamp(decision.confidence),
                evidence_ids,
                "model",
            )
            existing = self.projection.edge_between(event_id, other_id)
            ad = self._append_ad(
                AdvertisementDraft(
                    person_id=ingest_input.person_id,
                    origin="model",
                    model_version=_MODEL_VERSION,
                    prompt_version=_PROMPT_VERSION,
                    policy_version=self._policy_version,
                    evidence_ids=evidence_ids,
                    from_id=event_id,
                    to_id=other_id,
                    judgment=decision.judgment,
                    reason_code=decision.reason_code,
                    relation=map_relation("model", decision.reason_code),
                    proposed_confidence=_clamp(decision.confidence),
                    confidence=confidence,
                    created_at=ingest_input.captured_at,
                    supersedes_id=None if existing is None else existing.ad_id,
                    withdrawn=False,
                )
            )
            self.projection.apply(ad)
            issued[decision.handle] = other_id
            judgments.append(
                JudgmentRecord(
                    handle=decision.handle,
                    judgment=decision.judgment,
                    reason_code=decision.reason_code,
                    accepted=True,
                )
            )

    def _begin_interest(self, interest: SemanticInterest, work_key: str) -> BeginResult:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._begin_interest_async(interest, work_key))
        return self._pit.begin(interest, work_key)

    async def _begin_interest_async(self, interest: SemanticInterest, work_key: str) -> BeginResult:
        return self._pit.begin(interest, work_key)

    def _semantic_interest(self, explore_input: ExploreInput, operation: str) -> SemanticInterest:
        return SemanticInterest(
            person_id=explore_input.person_id,
            purpose=explore_input.purpose,
            authorization_epoch=self.authorization_epoch,
            snapshot_revision=self.projection.revision,
            snapshot_digest=self.projection.digest,
            budgets=InterestBudgets(
                deadline_ms=self._judge_deadline_ms,
                max_in_flight=self._max_in_flight,
            ),
            operation=operation,
            nonce=explore_input.request_id,
        )

    def _publish_selection(
        self,
        person_id: str,
        issued: Mapping[str, str],
    ) -> tuple[int, list[PruneRecord]]:
        draft = self._selection_draft
        if draft is None or draft.person_id != person_id:
            return (0, [])
        provenance = dict(draft.provenance)
        export_handles: list[str] = []
        for handle, node_id in issued.items():
            export_handles.append(handle)
            row = provenance.get(node_id)
            if row is not None:
                provenance[node_id] = RouteProvenance(
                    discovery=row.discovery,
                    rank=row.rank,
                    prune_reason=row.prune_reason,
                    export_handle=handle,
                )
        published = self._route_log.publish(
            RoutePublication(
                person_id=person_id,
                sets=RouteSetsSnapshot(
                    candidate=tuple(draft.candidate_ids),
                    selected=tuple(draft.selected_ids),
                    export=tuple(export_handles),
                ),
                provenance=provenance,
            )
        )
        return (published.revision, list(draft.pruned))

    def _remember(self, ingest_input: IngestInput, result: IngestResult) -> IngestResult:
        assert_safe_detail(result.detail)
        self._idempotency[f"{ingest_input.person_id}|{ingest_input.idempotency_key}"] = result
        self._save_durable()
        return result

    def _cap_confidence(
        self,
        from_id: str,
        to_id: str,
        proposed: float,
        evidence_ids: Sequence[str],
        origin: Literal["model", "user_correction", "policy"],
    ) -> float:
        if origin != "model":
            return proposed
        existing = self.projection.edge_between(from_id, to_id)
        if existing is None:
            return proposed
        previous = {
            lineage
            for lineage in (self._known_family(node_id) for node_id in existing.evidence_ids)
            if lineage is not None
        }
        independent = [
            lineage
            for lineage in (self._known_family(node_id) for node_id in evidence_ids)
            if lineage is not None and lineage not in previous
        ]
        if not independent and proposed > existing.confidence:
            return existing.confidence
        return proposed

    def _known_family(self, node_id: str) -> str | None:
        event = self.vault.get(node_id)
        if event is None or event.independence == "unknown":
            return None
        return event.lineage_id

    def _exact_candidates(self, person_id: str, text: str, self_id: str) -> list[str]:
        tokens = set(tokenize(text))
        matched: list[str] = []
        for event in self.vault.list():
            if event.person_id != person_id or event.id == self_id:
                continue
            if any(word in tokens for word in tokenize(event.text)):
                matched.append(event.id)
        ids = set(matched)
        seeds = [self_id, *matched] if self_id else matched
        for node_id in seeds:
            for other in self.projection.neighbors(node_id):
                if other == self_id:
                    continue
                node = self._nodes.get(other)
                if node is not None and node.person_id == person_id:
                    ids.add(other)
        return list(ids)

    def _token_matches(self, person_id: str, text: str, self_id: str) -> set[str]:
        tokens = set(tokenize(text))
        matched: set[str] = set()
        for event in self.vault.list():
            if event.person_id != person_id or event.id == self_id:
                continue
            if any(word in tokens for word in tokenize(event.text)):
                matched.add(event.id)
        return matched

    def _candidate_neighbors(
        self,
        person_id: str,
        text: str,
        node_id: str,
        self_id: str,
    ) -> tuple[NeighborRef, ...]:
        neighbors: list[NeighborRef] = []
        for neighbor in self.projection.neighbors(node_id):
            if neighbor == self_id:
                continue
            node = self._nodes.get(neighbor)
            if node is None or node.person_id != person_id:
                continue
            tags = self._controls.get(neighbor)
            if tags is not None and ("no-model" in tags or "no-forward" in tags):
                continue
            event = self.vault.get(neighbor)
            event_text = "" if event is None else event.text
            neighbors.append(NeighborRef(id=neighbor, relevance=jaccard(text, event_text)))
        return tuple(neighbors)

    def _discovery_of(
        self,
        node_id: str,
        token_ids: set[str],
        neighbor_ids: set[str],
        hnsw_ids: set[str],
    ) -> DiscoverySource:
        if node_id in token_ids:
            return "exact"
        if node_id in hnsw_ids:
            return "hnsw"
        if node_id in neighbor_ids:
            return "neighbor"
        return "exact"

    def _frontier_from(
        self,
        node_id: str,
        reason: str,
        *,
        key: str | None = None,
        hop: int = 0,
        confidence: float = 0.4,
        from_id: str = "",
    ) -> _FrontierItem:
        degree = self.projection.degree(node_id)
        return _FrontierItem(
            node_id=node_id,
            from_id=from_id,
            edge_key=f"seed|{node_id}" if key is None else key,
            reason=reason,
            rank=Rankable(
                id=node_id,
                authorized=1,
                provenance=float(provenance_rank("policy")),
                relevance=confidence,
                novelty=1,
                inverse_degree=inverse_degree(degree),
                inverse_hop=1 / (1 + hop),
            ),
        )

    def _forward_items(self, record: _HandleRecord) -> list[_FrontierItem]:
        tip = record.visited_nodes[-1] if record.visited_nodes else ""
        return forward_items(record.frontier, tip)

    def _restore_frontier(self, record: _HandleRecord, aside: list[_FrontierItem]) -> None:
        for item in aside:
            if item.node_id in record.visited_nodes:
                continue
            if any(saved.node_id == item.node_id for saved in record.frontier):
                continue
            record.frontier.append(item)

    def _component_covered(self, record: _HandleRecord) -> bool:
        start = record.anchor_id or (record.visited_nodes[0] if record.visited_nodes else "")
        if not start:
            return True
        seen: set[str] = set()
        queue = [start]
        while queue:
            node_id = queue.pop(0)
            if not node_id or node_id in seen:
                continue
            seen.add(node_id)
            if node_id not in record.visited_nodes:
                return False
            for neighbor in self.projection.neighbors(node_id):
                if neighbor not in seen:
                    queue.append(neighbor)
        return True

    def _reachable(self, anchor_id: str) -> _Reach:
        seen: set[str] = set()
        queue = [anchor_id]
        while queue and len(seen) < 200:
            node_id = queue.pop(0)
            if not node_id or node_id in seen:
                continue
            seen.add(node_id)
            for neighbor in self.projection.neighbors(node_id):
                if neighbor not in seen:
                    queue.append(neighbor)
        return _Reach(count=len(seen), capped=any(node_id not in seen for node_id in queue))

    def _blank_handle(self, explore_input: ExploreInput) -> _HandleRecord:
        token = _route_token()
        record = _HandleRecord(
            token=token,
            person_id=explore_input.person_id,
            session="exploration",
            purpose=explore_input.purpose,
            authorization_epoch=self.authorization_epoch,
            snapshot_revision=self.projection.revision,
            snapshot_digest=self.projection.digest,
            frontier=[],
            visited_nodes=[],
            visited_edges=[],
            breadcrumb=[],
            hop_depth=0,
            cycle_count=0,
            expansions=0,
            anchor_id="",
            approximate_seed=False,
            expires_at=self._now() + self._handle_ttl_ms,
            use_count=0,
            max_uses=self._max_handle_uses,
            route_bindings={},
            advertised=[],
            lineage_pruned=False,
            invalidated=False,
            invalid_reason=None,
        )
        self._handles[token] = record
        self._persist_session(record)
        return record

    def _export_node(self, node_id: str, reason: str) -> ExportItem | None:
        cache_id = f"{self.authorization_epoch}|{self.projection.revision}|{node_id}|{reason}"
        node = self._nodes.get(node_id)
        if node is None:
            return None
        tags = self._controls.get(node_id)
        if tags is not None and ("no-model" in tags or "no-forward" in tags):
            return None
        event = self.vault.get(node_id)
        self._item_counter += 1
        handle = f"ih_{_base36(self._item_counter)}"
        if event is None:
            excerpt = f"document hub with {len(node.member_event_ids)} source members"
        elif tags is not None and "summary-only" in tags:
            excerpt = f"{event.source_type} {event.captured_at}"
        else:
            excerpt = event.text[:180]
        self._export_cache[cache_id] = handle
        return ExportItem(
            handle=handle,
            excerpt=excerpt,
            source_type="hub" if event is None else event.source_type,
            captured_at="" if event is None else event.captured_at,
            reason=reason,
            requires_confirmation=tags is not None and "requires-confirmation" in tags,
        )

    def _breadcrumb_label(self, node_id: str) -> str:
        event = self.vault.get(node_id)
        if event is None:
            return "Record"
        return f"{source_name(event.source_type)} {event.captured_at[:10]}"

    def _local_node(self, node_id: str, record: _HandleRecord) -> LocalNode:
        event = self.vault.get(node_id)
        relation: Relation | None = None
        for other in self.projection.neighbors(node_id):
            if other not in record.visited_nodes:
                continue
            edge = self.projection.edge_between(node_id, other)
            if edge is not None:
                relation = edge.relation
                break
        if event is None:
            return LocalNode(
                id=node_id,
                source_type="hub",
                captured_at="",
                excerpt="document hub",
                relation=relation,
                on_route=node_id in record.visited_nodes,
            )
        return LocalNode(
            id=node_id,
            source_type=event.source_type,
            captured_at=event.captured_at[:10],
            excerpt=event.text[:80],
            relation=relation,
            on_route=node_id in record.visited_nodes,
        )

    def _stopped(self, reason: TerminalReason, detail: str | None = None) -> SemanticData:
        text = DETAILS[reason] if detail is None else detail
        assert_safe_detail(text)
        if reason == "approximate_frontier_exhausted":
            exhaustion: Exhaustion = "approximate"
        elif reason == "budget_exhausted":
            exhaustion = "not_yet_exhausted"
        else:
            exhaustion = "exact"
        return SemanticData(
            route="stopped",
            breadcrumb=(),
            hop_depth=0,
            direct_link_count=0,
            cycle_count=0,
            exhaustion=exhaustion,
            items=(),
            already_explored=(),
            next_routes=(),
            terminal_reason=reason,
            detail=text,
            route_handle=None,
            snapshot_revision=self.projection.revision,
            snapshot_digest=self.projection.digest,
        )

    def _invalidate_for_snapshot(self) -> None:
        for handle in self._handles.values():
            if handle.snapshot_revision != self.projection.revision:
                handle.invalidated = True
                if handle.invalid_reason is None:
                    handle.invalid_reason = "stale_snapshot"

    def _clear_export_cache(self) -> None:
        if self._export_cache:
            self.metrics.cache_clears += 1
        self._export_cache.clear()

    def _attach_hub(self, event: VaultEvent) -> None:
        if not event.document_id:
            return
        hub_id = f"hub_{event.person_id}_{event.document_id}"
        hub = self._nodes.get(hub_id)
        if hub is None:
            hub = PointerNode(
                id=hub_id,
                kind="pseudonode",
                vault_event_id=None,
                member_event_ids=(),
                person_id=event.person_id,
            )
        hub = replace(hub, member_event_ids=(*hub.member_event_ids, event.id))
        self._nodes[hub_id] = hub
        self.link_structural(event.id, hub_id, "membership")

    def _drop_acknowledgement(self, person_id: str, from_id: str, to_id: str) -> None:
        endpoint_ids = _endpoint_ids(from_id, to_id)
        self._acknowledgements = [
            row
            for row in self._acknowledgements
            if not (row.person_id == person_id and row.endpoint_ids == endpoint_ids)
        ]

    def _hydrate(self) -> None:
        if self._graph_store is None:
            return
        snapshot = self._graph_store.load()
        self._placed = set(snapshot.placed_event_ids)
        if not snapshot.events and not snapshot.advertisements and not snapshot.nodes:
            return
        self._hydrating = True
        try:
            for event in snapshot.events:
                self.vault.append(event)
                if event.text:
                    self._index_for(event.person_id).add(event.id, token_vector(event.text))
            for node in snapshot.nodes:
                self._nodes[node.id] = node
            for event in snapshot.events:
                if event.id not in self._nodes:
                    self._nodes[event.id] = empty_pointer(event)
            self.log.restore(snapshot.advertisements)
            assert_structural_ledger(self.log.ads, list(self._nodes.values()))
            self.projection.rebuild(self.log.ads)
            if snapshot.projection_digest and snapshot.projection_digest != self.projection.digest:
                raise ValueError("graph store snapshot is unreadable")
            if snapshot.projection_revision is not None:
                self.projection.revision = snapshot.projection_revision
            self._acknowledgements.extend(snapshot.acknowledgements)
        finally:
            self._hydrating = False

    def _save_durable(self) -> None:
        if self._graph_store is None or self._hydrating:
            return
        events = tuple(self.vault.list())
        if self._pointer_only:
            events = tuple(replace(event, text="") for event in events)
        self._graph_store.save(
            DurableSnapshot(
                events=events,
                advertisements=tuple(self.log.ads),
                nodes=tuple(self._nodes.values()),
                acknowledgements=tuple(self._acknowledgements),
                projection_revision=self.projection.revision,
                projection_digest=self.projection.digest,
                placed_event_ids=tuple(sorted(self._placed)),
            )
        )

    def _persist_session(self, record: _HandleRecord) -> None:
        self._session_store.put(record.token, _session_body(record))

    def _load_handle(self, token: str) -> _HandleRecord | None:
        live = self._handles.get(token)
        if live is not None:
            return live
        stored = self._session_store.get(token)
        if stored is None:
            return None
        record = _handle_from_session(stored)
        self._handles[token] = record
        return record

    def _person_for(self, from_id: str, to_id: str) -> str:
        left = self._nodes.get(from_id)
        right = self._nodes.get(to_id)
        person_id = None if left is None else left.person_id
        if person_id is None and right is not None:
            person_id = right.person_id
        if person_id is None:
            raise ValueError("advertisement endpoints have no person")
        return person_id

    def _append_ad(self, draft: AdvertisementDraft) -> LinkAdvertisement:
        return self.log.append(draft)

    def _index_for(self, person_id: str) -> HnswIndex:
        index = self._indexes.get(person_id)
        if index is None:
            index = HnswIndex(self._seed)
            self._indexes[person_id] = index
        return index

    def _person_count(self, person_id: str) -> int:
        return sum(
            1
            for node in self._nodes.values()
            if node.person_id == person_id and node.kind == "event"
        )

    def _page_key(self, person_id: str, request_id: str) -> str:
        return f"{person_id}|{request_id}"


@dataclass(frozen=True)
class _Reach:
    count: int
    capped: bool


def _operation_name(explore_input: ExploreInput) -> str:
    if not explore_input.route_handle:
        return "open"
    if explore_input.operation == "open":
        return "continue"
    return explore_input.operation


def _endpoint_ids(from_id: str, to_id: str) -> tuple[str, str]:
    if from_id <= to_id:
        return (from_id, to_id)
    return (to_id, from_id)


def _source_type(event: VaultEvent | None) -> str:
    if event is None:
        return "hub"
    return event.source_type


def _judge_candidate(exported: ExportItem) -> JudgeCandidate:
    return JudgeCandidate(
        handle=exported.handle,
        excerpt=exported.excerpt,
        source_type=exported.source_type,
        captured_at=exported.captured_at,
    )


def _request_bytes(request: JudgeRequest) -> int:
    payload = {
        "newHandle": request.new_handle,
        "excerpt": request.excerpt,
        "sourceType": request.source_type,
        "capturedAt": request.captured_at,
        "candidates": [
            {
                "handle": candidate.handle,
                "excerpt": candidate.excerpt,
                "sourceType": candidate.source_type,
                "capturedAt": candidate.captured_at,
            }
            for candidate in request.candidates
        ],
    }
    return len(json.dumps(payload, separators=(",", ":")).encode())


def _session_body(record: _HandleRecord) -> SessionJson:
    frontier: list[JsonValue] = [_frontier_json(item) for item in record.frontier]
    advertised: list[JsonValue] = [_route_json(route) for route in record.advertised]
    bindings: list[JsonValue] = [
        [route_id, list(node_ids)] for route_id, node_ids in record.route_bindings.items()
    ]
    body: dict[str, JsonValue] = {
        "token": record.token,
        "person_id": record.person_id,
        "session": record.session,
        "purpose": record.purpose,
        "authorization_epoch": record.authorization_epoch,
        "snapshot_revision": record.snapshot_revision,
        "snapshot_digest": record.snapshot_digest,
        "frontier": frontier,
        "visited_nodes": list(record.visited_nodes),
        "visited_edges": list(record.visited_edges),
        "breadcrumb": list(record.breadcrumb),
        "hop_depth": record.hop_depth,
        "cycle_count": record.cycle_count,
        "expansions": record.expansions,
        "anchor_id": record.anchor_id,
        "approximate_seed": record.approximate_seed,
        "expires_at": record.expires_at,
        "use_count": record.use_count,
        "max_uses": record.max_uses,
        "route_bindings": bindings,
        "advertised": advertised,
        "lineage_pruned": record.lineage_pruned,
        "invalidated": record.invalidated,
        "invalid_reason": record.invalid_reason,
    }
    return body


def _frontier_json(item: _FrontierItem) -> JsonValue:
    return {
        "node_id": item.node_id,
        "from_id": item.from_id,
        "edge_key": item.edge_key,
        "reason": item.reason,
        "rank": {
            "id": item.rank.id,
            "authorized": item.rank.authorized,
            "provenance": item.rank.provenance,
            "relevance": item.rank.relevance,
            "novelty": item.rank.novelty,
            "inverse_degree": item.rank.inverse_degree,
            "inverse_hop": item.rank.inverse_hop,
        },
    }


def _route_json(route: LocalRoute) -> JsonValue:
    return {
        "route_id": route.route_id,
        "label": route.label,
        "kind": route.kind,
        "node_ids": list(route.node_ids),
    }


def _handle_from_session(stored: SessionJson) -> _HandleRecord:
    bindings: dict[str, list[str]] = {}
    raw_bindings = stored.get("route_bindings")
    if isinstance(raw_bindings, list):
        for entry in raw_bindings:
            if not isinstance(entry, list) or len(entry) != 2:
                continue
            route_id, node_ids = entry
            if not isinstance(route_id, str) or not isinstance(node_ids, list):
                continue
            bindings[route_id] = [node_id for node_id in node_ids if isinstance(node_id, str)]
    advertised: list[LocalRoute] = []
    raw_routes = stored.get("advertised")
    if isinstance(raw_routes, list):
        for entry in raw_routes:
            route = _route_from_json(entry)
            if route is not None:
                advertised.append(route)
    frontier: list[_FrontierItem] = []
    raw_frontier = stored.get("frontier")
    if isinstance(raw_frontier, list):
        for entry in raw_frontier:
            item = _frontier_from_json(entry)
            if item is not None:
                frontier.append(item)
    invalid_reason = _terminal_or_none(stored.get("invalid_reason"))
    return _HandleRecord(
        token=_required_str(stored, "token"),
        person_id=_required_str(stored, "person_id"),
        session="exploration",
        purpose=_required_str(stored, "purpose"),
        authorization_epoch=_required_int(stored, "authorization_epoch"),
        snapshot_revision=_required_int(stored, "snapshot_revision"),
        snapshot_digest=_required_str(stored, "snapshot_digest"),
        frontier=frontier,
        visited_nodes=_string_list(stored.get("visited_nodes")),
        visited_edges=_string_list(stored.get("visited_edges")),
        breadcrumb=_string_list(stored.get("breadcrumb")),
        hop_depth=_required_int(stored, "hop_depth"),
        cycle_count=_required_int(stored, "cycle_count"),
        expansions=_required_int(stored, "expansions"),
        anchor_id=_required_str(stored, "anchor_id"),
        approximate_seed=stored.get("approximate_seed") is True,
        expires_at=_required_int(stored, "expires_at"),
        use_count=_required_int(stored, "use_count"),
        max_uses=_required_int(stored, "max_uses"),
        route_bindings=bindings,
        advertised=advertised,
        lineage_pruned=stored.get("lineage_pruned") is True,
        invalidated=stored.get("invalidated") is True,
        invalid_reason=invalid_reason,
    )


def _frontier_from_json(value: object) -> _FrontierItem | None:
    if not isinstance(value, dict):
        return None
    raw_rank = value.get("rank")
    if not isinstance(raw_rank, dict):
        return None
    node_id = value.get("node_id")
    if not isinstance(node_id, str):
        return None
    from_id = value.get("from_id")
    edge = value.get("edge_key")
    reason = value.get("reason")
    rank_id = raw_rank.get("id")
    if not isinstance(from_id, str) or not isinstance(edge, str) or not isinstance(reason, str):
        return None
    if not isinstance(rank_id, str):
        return None
    return _FrontierItem(
        node_id=node_id,
        from_id=from_id,
        edge_key=edge,
        reason=reason,
        rank=Rankable(
            id=rank_id,
            authorized=_float_field(raw_rank, "authorized"),
            provenance=_float_field(raw_rank, "provenance"),
            relevance=_float_field(raw_rank, "relevance"),
            novelty=_float_field(raw_rank, "novelty"),
            inverse_degree=_float_field(raw_rank, "inverse_degree"),
            inverse_hop=_float_field(raw_rank, "inverse_hop"),
        ),
    )


def _route_from_json(value: object) -> LocalRoute | None:
    if not isinstance(value, dict):
        return None
    route_id = value.get("route_id")
    label = value.get("label")
    kind = value.get("kind")
    node_ids = value.get("node_ids")
    if not isinstance(route_id, str) or not isinstance(label, str) or not isinstance(kind, str):
        return None
    if kind not in _ROUTE_KINDS or not isinstance(node_ids, list):
        return None
    return LocalRoute(
        route_id=route_id,
        label=label,
        kind=cast(RouteKind, kind),
        node_ids=[node_id for node_id in node_ids if isinstance(node_id, str)],
    )


def _terminal_or_none(value: object) -> TerminalReason | None:
    if isinstance(value, str) and value in _TERMINALS:
        return cast(TerminalReason, value)
    return None


def _required_str(stored: Mapping[str, JsonValue], key: str) -> str:
    value = stored.get(key)
    if isinstance(value, str):
        return value
    return ""


def _required_int(stored: Mapping[str, JsonValue], key: str) -> int:
    value = stored.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        return 0
    return int(value)


def _float_field(stored: Mapping[str, JsonValue], key: str) -> float:
    value = stored.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        return 0.0
    return float(value)


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
