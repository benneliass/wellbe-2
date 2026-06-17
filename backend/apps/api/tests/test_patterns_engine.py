"""Unit tests for the non-diagnostic pattern engine (WEL-79).

Covers the read-time semantics of the five intelligence engines: co-occurrence
phrasing (never causal/diagnostic), qualitative evidence tiers, missing-data and
confounder annotations, surface floor, preserved (never auto-resolved)
contradictions, ranking, and that composed wording passes the C10 gate.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from wellbe_api.patterns import engine
from wellbe_contracts.c10_safety import C10Decision
from wellbe_contracts.patterns import EvidenceTier


@dataclass
class _Node:
    id: uuid.UUID
    display_label: str
    last_seen_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class _Edge:
    from_node_id: uuid.UUID
    to_node_id: uuid.UUID
    edge_type: str
    potential_score: float
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    score_inputs: dict | None = None


def _pair(label_a: str, label_b: str) -> tuple[_Node, _Node]:
    return _Node(uuid.uuid4(), label_a), _Node(uuid.uuid4(), label_b)


def test_relation_phrasing_is_non_diagnostic():
    a, b = _pair("Headache", "Poor sleep")
    nodes = {a.id: a, b.id: b}
    cases = {
        "co_occurs_with": "appears with",
        "associated_with": "appears with",
        "temporal_sequence": "often follows",
        "may_explain": "may be related to",
    }
    for code, phrase in cases.items():
        edge = _Edge(a.id, b.id, code, 0.7)
        cands = engine.build_candidates(edges=[edge], nodes=nodes)
        assert len(cands) == 1
        assert cands[0].relation_phrase == phrase
        # Never causal/diagnostic wording.
        assert "cause" not in cands[0].relation_phrase
        assert "diagnos" not in cands[0].relation_phrase


def test_evidence_tier_is_qualitative():
    a, b = _pair("Fatigue", "Low iron")
    nodes = {a.id: a, b.id: b}
    assert (
        engine.build_candidates(
            edges=[_Edge(a.id, b.id, "co_occurs_with", 0.8)], nodes=nodes
        )[0].evidence_tier
        is EvidenceTier.STRONGER
    )
    assert (
        engine.build_candidates(
            edges=[_Edge(a.id, b.id, "co_occurs_with", 0.5)], nodes=nodes
        )[0].evidence_tier
        is EvidenceTier.MODERATE
    )
    assert (
        engine.build_candidates(
            edges=[_Edge(a.id, b.id, "co_occurs_with", 0.2)], nodes=nodes
        )[0].evidence_tier
        is EvidenceTier.EARLY
    )


def test_sparse_support_gets_missing_data_note():
    a, b = _pair("Nausea", "New medication")
    nodes = {a.id: a, b.id: b}
    cand = engine.build_candidates(
        edges=[_Edge(a.id, b.id, "co_occurs_with", 0.25)], nodes=nodes
    )[0]
    assert cand.missing_data_note is not None


def test_every_candidate_is_source_linked_with_caveat():
    a, b = _pair("Dizziness", "Skipped meals")
    nodes = {a.id: a, b.id: b}
    cand = engine.build_candidates(
        edges=[_Edge(a.id, b.id, "associated_with", 0.6)], nodes=nodes
    )[0]
    assert len(cand.sources) == 2
    assert cand.caveat
    assert cand.alternative_explanations  # mandatory alt explanations


def test_surface_floor_drops_weak_non_contradiction():
    a, b = _pair("X", "Y")
    nodes = {a.id: a, b.id: b}
    cands = engine.build_candidates(
        edges=[_Edge(a.id, b.id, "co_occurs_with", 0.05)], nodes=nodes
    )
    assert cands == []


def test_contradiction_is_surfaced_and_not_resolved():
    a, b = _pair("Logged: took aspirin", "Logged: no aspirin")
    nodes = {a.id: a, b.id: b}
    # A contradiction and an associative edge between the same nodes both exist.
    edges = [
        _Edge(a.id, b.id, "contradicts", 0.05),  # below floor, still surfaced
        _Edge(a.id, b.id, "co_occurs_with", 0.7),
    ]
    cands = engine.build_candidates(edges=edges, nodes=nodes)
    contradictions = [c for c in cands if c.is_contradiction]
    assert len(contradictions) == 1  # surfaced despite low weight
    # Both the contradiction AND the other edge survive -> never auto-resolved.
    assert len(cands) == 2
    assert contradictions[0].relation_phrase == "conflicts with"
    # Contradictions rank first so they are never buried.
    assert cands[0].is_contradiction is True


def test_hub_node_gets_confounder_note():
    hub = _Node(uuid.uuid4(), "Stress")
    others = [_Node(uuid.uuid4(), f"Symptom {i}") for i in range(3)]
    nodes = {hub.id: hub, **{n.id: n for n in others}}
    edges = [_Edge(hub.id, n.id, "co_occurs_with", 0.6) for n in others]
    cands = engine.build_candidates(edges=edges, nodes=nodes)
    assert all(c.confounder_note is not None for c in cands)


def test_composed_patterns_pass_c10_gate():
    a, b = _pair("Headache", "Poor sleep")
    nodes = {a.id: a, b.id: b}
    cands = engine.build_candidates(
        edges=[_Edge(a.id, b.id, "may_explain", 0.6)], nodes=nodes
    )
    decision = engine.gate_candidates(
        candidates=cands, patient_id=uuid.uuid4(), correlation_id="test-corr"
    )
    assert decision in {C10Decision.ALLOW, C10Decision.ALLOW_WITH_OBLIGATIONS}
