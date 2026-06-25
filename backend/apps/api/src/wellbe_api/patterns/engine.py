"""Non-diagnostic pattern engine — read-time slice of WEL-79.

Per docs/decisions/pattern-detection-semantics.md, this surfaces co-occurrence
candidates over the user's *own* C6 knowledge graph with mandatory caveats. It
implements the read-time semantics of the five intelligence engines:

- **Pattern Detection** — selects associative/temporal/`may_explain` edges above
  a configurable evidence floor and phrases them non-diagnostically.
- **Temporal Analysis** — ranks candidates by evidence weight, boosting
  `temporal_sequence` ("often follows") and recently-seen endpoints.
- **Confounder Detection** — flags endpoints that are hubs (high degree) so a
  common factor is offered as an alternative explanation, never suppressed.
- **Missing-Data** — annotates candidates whose support is sparse instead of
  hiding them.
- **Contradiction Resolution** — surfaces `contradicts` edges as named
  contradictions and NEVER auto-resolves them.

Every candidate is source-linked (no orphan claims) and the composed wording is
gated by C10 before release (fail-closed). The strongest relation phrasing is
"may be related to" (the `may_explain` ceiling); causal/diagnostic phrasing is
never produced.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_c6_graph.models import KgEdgeRow, KgNodeRow
from wellbe_c6_graph.repository import GraphRepository
from wellbe_contracts.c10_safety import (
    C10Decision,
    C10SafetyEvaluationRequestV1,
    ClaimMapEntry,
    ClaimType,
    EngineRiskTier,
    EvidenceRef,
    EvidenceRefType,
    OutputFormat,
    OutputType,
    ProvenanceCompleteness,
    ReviewMarker,
    SourceType,
    UrgencyClass,
    UrgencyContext,
    UrgencySource,
    WorkspaceType,
)
from wellbe_contracts.patterns import (
    EvidenceTier,
    PatternCandidateV2,
    PatternSourceRef,
)

from wellbe_api.config import ApiSettings

_settings = ApiSettings()
_POLICY_VERSION = "patterns-c10-v1"

# Associative / temporal / causal-ceiling edges eligible for surfacing.
# `may_explain` is the strongest causal edge permitted (the safety ceiling);
# therapeutic verbs (treats/worsens/alleviates) are intentionally excluded from
# the read surface to avoid implying advice. `contradicts` is handled separately.
_RELATION_PHRASE: dict[str, str] = {
    "co_occurs_with": "appears with",
    "associated_with": "appears with",
    "temporal_sequence": "often follows",
    "may_explain": "may be related to",
}
_CONTRADICTION_CODE = "contradicts"
_PATTERN_EDGE_CODES = [*_RELATION_PHRASE.keys(), _CONTRADICTION_CODE]

# Below this evidence weight, a candidate is treated as sparse (missing-data).
_SPARSE_FLOOR = 0.34
# Minimum weight to surface at all.
_SURFACE_FLOOR = 0.15
# Endpoint degree at or above this is treated as a hub (confounder candidate).
_HUB_DEGREE = 3

_BASE_CAVEAT = (
    "This is a pattern in your own records — not a cause, and not a diagnosis."
)
_CONTRADICTION_CAVEAT = (
    "Your records contain conflicting information here. It's kept as-is, "
    "not resolved — bring it up with a clinician if it matters to you."
)


@dataclass
class PatternResult:
    candidates: list[PatternCandidateV2] = field(default_factory=list)
    note: str = ""


def _tier(weight: float) -> EvidenceTier:
    if weight >= 0.66:
        return EvidenceTier.STRONGER
    if weight >= _SPARSE_FLOOR:
        return EvidenceTier.MODERATE
    return EvidenceTier.EARLY


def _alt_explanations(code: str) -> list[str]:
    if code == "temporal_sequence":
        return [
            "One coming before the other doesn't mean one caused the other.",
            "A common trigger, or chance, could explain the order.",
        ]
    return [
        "Two things appearing together can be coincidence.",
        "A shared cause, or how often you log each, could explain it.",
    ]


def _missing_data_note(edge: KgEdgeRow) -> str | None:
    inputs = edge.score_inputs if isinstance(edge.score_inputs, dict) else None
    occurrences = None
    if inputs is not None:
        occurrences = inputs.get("occurrences") or inputs.get("sample_size")
    if edge.potential_score < _SPARSE_FLOOR or (
        isinstance(occurrences, int) and occurrences < 3
    ):
        return (
            "Based on only a little data so far — this may change as you log more."
        )
    if inputs is None:
        return "Limited supporting detail is recorded for this connection."
    return None


def _build_candidate(
    *,
    edge: KgEdgeRow,
    nodes: dict[uuid.UUID, KgNodeRow],
    degree: dict[uuid.UUID, int],
) -> PatternCandidateV2 | None:
    subject = nodes.get(edge.from_node_id)
    obj = nodes.get(edge.to_node_id)
    if subject is None or obj is None:
        return None

    is_contradiction = edge.edge_type == _CONTRADICTION_CODE
    if is_contradiction:
        phrase = "conflicts with"
        caveat = _CONTRADICTION_CAVEAT
        alts: list[str] = []
    else:
        resolved = _RELATION_PHRASE.get(edge.edge_type)
        if resolved is None:
            return None
        phrase = resolved
        caveat = _BASE_CAVEAT
        alts = _alt_explanations(edge.edge_type)

    confounder_note = None
    hub = max(degree.get(edge.from_node_id, 0), degree.get(edge.to_node_id, 0))
    if hub >= _HUB_DEGREE and not is_contradiction:
        confounder_note = (
            "This links to several things in your records — a common factor "
            "could explain it rather than a direct link."
        )

    return PatternCandidateV2(
        id=str(edge.id),
        subject_label=subject.display_label,
        relation_phrase=phrase,
        object_label=obj.display_label,
        relation_code=edge.edge_type,
        evidence_tier=_tier(edge.potential_score),
        evidence_weight=edge.potential_score,
        caveat=caveat,
        alternative_explanations=alts,
        missing_data_note=None if is_contradiction else _missing_data_note(edge),
        confounder_note=confounder_note,
        is_contradiction=is_contradiction,
        sources=[
            PatternSourceRef(source_id=str(subject.id), label=subject.display_label),
            PatternSourceRef(source_id=str(obj.id), label=obj.display_label),
        ],
    )


def _rank_key(c: PatternCandidateV2, last_seen: dict[str, float]) -> tuple[Any, ...]:
    # Contradictions first (they must never be buried), then temporal ("often
    # follows") candidates, then by evidence weight and recency.
    temporal_boost = 1 if c.relation_code == "temporal_sequence" else 0
    recency = max((last_seen.get(s.source_id, 0.0) for s in c.sources), default=0.0)
    return (c.is_contradiction, temporal_boost, c.evidence_weight, recency)


def build_candidates(
    *, edges: list[KgEdgeRow], nodes: dict[uuid.UUID, KgNodeRow]
) -> list[PatternCandidateV2]:
    """Pure transform: edges + node map -> ranked non-diagnostic candidates."""
    degree: dict[uuid.UUID, int] = {}
    for e in edges:
        degree[e.from_node_id] = degree.get(e.from_node_id, 0) + 1
        degree[e.to_node_id] = degree.get(e.to_node_id, 0) + 1

    candidates: list[PatternCandidateV2] = []
    for e in edges:
        if e.edge_type != _CONTRADICTION_CODE and e.potential_score < _SURFACE_FLOOR:
            continue
        cand = _build_candidate(edge=e, nodes=nodes, degree=degree)
        if cand is not None:
            candidates.append(cand)

    last_seen = {
        str(n.id): n.last_seen_at.timestamp()
        for n in nodes.values()
        if n.last_seen_at
    }
    candidates.sort(key=lambda c: _rank_key(c, last_seen), reverse=True)
    return candidates


def _build_eval_request(
    *, candidates: list[PatternCandidateV2], patient_id: uuid.UUID, correlation_id: str
) -> C10SafetyEvaluationRequestV1:
    parts: list[str] = []
    claim_map: list[ClaimMapEntry] = []
    cursor = 0
    for idx, c in enumerate(candidates):
        line = f"{c.subject_label} {c.relation_phrase} {c.object_label}."
        start = cursor
        end = start + len(line)
        cursor = end + 1
        claim_map.append(
            ClaimMapEntry(
                claim_id=f"pattern:{idx}",
                char_start=start,
                char_end=end,
                claim_type=ClaimType.DERIVED_PATTERN,
                personal_specific=True,
                external_context_only=False,
                evidence_refs=[
                    EvidenceRef(
                        evidence_ref_id=f"pattern:{idx}",
                        ref_type=EvidenceRefType.GRAPH_EDGE,
                        source_type=SourceType.PATIENT_ENTERED_NOTE,
                        source_id=c.id,
                    )
                ],
                provenance_complete=True,
                uncertainty_label="observed_pattern",
            )
        )
        parts.append(line)

    has_claims = bool(claim_map)
    return C10SafetyEvaluationRequestV1(
        request_id=str(uuid.uuid4()),
        requested_at=datetime.now(UTC),
        idempotency_key=f"patterns:{correlation_id}",
        output_text="\n".join(parts) if parts else "No patterns to surface.",
        output_format=OutputFormat.STRUCTURED_BLOCKS,
        output_type=OutputType.OTHER,
        target_audience="patient",
        surface="pattern_check",
        review_markers=[
            ReviewMarker.AI_SUMMARIZED,
            ReviewMarker.NOT_CLINICIAN_REVIEWED,
        ],
        urgency=UrgencyContext(
            urgency_class=UrgencyClass.NONE, urgency_source=UrgencySource.NONE
        ),
        claim_map=claim_map,
        claim_map_complete=True,
        no_health_claims_asserted=not has_claims,
        engine_name="pattern_engine",
        engine_version="1.0",
        engine_risk_tier=EngineRiskTier.HIGH,
        upstream_run_id=correlation_id,
        actor_id=str(patient_id),
        workspace_id=str(patient_id),
        workspace_type=WorkspaceType.INDIVIDUAL,
        active_role_type="controller",
        purpose_code="pattern_check",
        access_decision_id="self",
        access_predicate_hash="self",
        c10_policy_version=_POLICY_VERSION,
        deterministic_ruleset_version=_POLICY_VERSION,
        nemo_guardrails_config_id=_POLICY_VERSION,
        llama_guard_policy_version=_POLICY_VERSION,
        risk_tier_policy_version=_POLICY_VERSION,
        correlation_id=correlation_id,
        patient_id=str(patient_id),
        provenance_completeness=(
            ProvenanceCompleteness.COMPLETE
            if has_claims
            else ProvenanceCompleteness.NOT_APPLICABLE_NO_HEALTH_CLAIMS
        ),
    )


def gate_candidates(
    *, candidates: list[PatternCandidateV2], patient_id: uuid.UUID, correlation_id: str
) -> C10Decision:
    """Run the composed pattern wording through the C10 gate (fail-closed)."""
    from wellbe_c10_safety import SafetyGateEvaluator

    evaluator = SafetyGateEvaluator(
        token_secret=_settings.c10_token_secret.get_secret_value()
    )
    request = _build_eval_request(
        candidates=candidates, patient_id=patient_id, correlation_id=correlation_id
    )
    return evaluator.evaluate(request).decision


async def detect_patterns(
    *, session: AsyncSession, patient_id: uuid.UUID, correlation_id: str, limit: int = 50
) -> PatternResult:
    """Full pipeline: read graph -> build candidates -> C10 gate."""
    repo = GraphRepository(session)
    edges = await repo.edges_for_patient(
        patient_id=patient_id, edge_types=_PATTERN_EDGE_CODES, limit=limit
    )
    if not edges:
        return PatternResult(
            candidates=[],
            note=(
                "No patterns yet. As you log more — symptoms, results, notes — "
                "I'll surface connections across your own records here, always "
                "source-linked and never as a diagnosis."
            ),
        )

    node_ids = {e.from_node_id for e in edges} | {e.to_node_id for e in edges}
    nodes = await repo.nodes_by_ids(patient_id=patient_id, node_ids=list(node_ids))
    candidates = build_candidates(edges=edges, nodes=nodes)

    if not candidates:
        return PatternResult(candidates=[], note="No patterns to surface yet.")

    decision = gate_candidates(
        candidates=candidates, patient_id=patient_id, correlation_id=correlation_id
    )
    if decision not in {C10Decision.ALLOW, C10Decision.ALLOW_WITH_OBLIGATIONS}:
        # Fail closed: never surface ungated wording.
        return PatternResult(
            candidates=[],
            note=(
                "I couldn't safely surface patterns from your records right now. "
                "If you have a health concern, please reach out to a clinician."
            ),
        )

    return PatternResult(
        candidates=candidates,
        note=(
            "These are connections across your own records — observations, not "
            "conclusions. Each is source-linked and none is a diagnosis."
        ),
    )
