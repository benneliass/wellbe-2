"""Unit tests for thread-scoped graph read mapping (WEL-156).

Covers property-level allowlisting (no raw source text leaks into node/edge
attributes), relation passthrough (incl. the `may_explain` ceiling), and the
compact-provenance-summary contract (source ref id only, no inline provenance).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from wellbe_api.routers.graph_v2 import _edge_v2, _node_v2
from wellbe_c6_graph.models import KgEdgeRow, KgNodeRow


def _node(**kw) -> KgNodeRow:
    now = datetime(2026, 1, 1, 12, 0, 0)
    base = dict(
        id=uuid.uuid4(),
        patient_id=uuid.uuid4(),
        node_type="Symptom",
        normalized_key="headache",
        display_label="Headache",
        status="active",
        thread_ids=[],
        first_seen_at=now,
        last_seen_at=now,
        schema_version=1,
        created_at=now,
        updated_at=now,
    )
    base.update(kw)
    return KgNodeRow(**base)


def test_node_mapping_allowlists_attributes():
    node = _node(
        node_metadata={
            "source_type": "lab_report",
            "raw_text": "SECRET patient note that must not leak",
        }
    )
    out = _node_v2(node)
    assert out.type == "Symptom"
    assert out.label == "Headache"
    assert out.attributes.get("source_type") == "lab_report"
    # Property-level minimization: raw source text never travels.
    assert "raw_text" not in out.attributes
    assert "SECRET" not in str(out.attributes)


def test_edge_mapping_carries_relation_and_compact_provenance():
    n1, n2 = uuid.uuid4(), uuid.uuid4()
    now = datetime(2026, 1, 1, 12, 0, 0)
    edge = KgEdgeRow(
        id=uuid.uuid4(),
        from_node_id=n1,
        to_node_id=n2,
        edge_type="may_explain",
        potential_score=0.62,
        score_version=1,
        score_inputs={"source_ref_id": "ev-123", "internal_debug": "noise"},
        needs_rescore=False,
        thread_ids=[],
        patient_id=uuid.uuid4(),
        schema_version=1,
        created_at=now,
        updated_at=now,
    )
    out = _edge_v2(edge)
    assert out.relation == "may_explain"  # causal ceiling, never a diagnosis
    assert out.evidence_weight == 0.62
    # Compact provenance summary only — a source ref id, not the full inputs.
    assert out.attributes.get("source_ref_id") == "ev-123"
    assert "internal_debug" not in out.attributes
