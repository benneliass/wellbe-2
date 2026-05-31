"""C6 safety constants and edge guards for the Health Investigation OS retrofit.

These mirror the schema-level CHECK constraints in migration 008 and the three
approved decision records (WEL-130/128/129). They exist so that unsafe edges are
rejected in the service layer *before* hitting the database — defense in depth, not
relying on C10 (the Safety Gate) as the only boundary.
"""

from __future__ import annotations

# Personal-graph node types (graph.kg_nodes). Investigation/Theory are projections
# of the C14/C15 aggregates; the authoritative lifecycle lives in those services.
PERSONAL_NODE_TYPES: frozenset[str] = frozenset({
    "ConditionHypothesis", "Symptom", "Medication", "LabResult", "Procedure",
    "VitalSign", "Allergy", "Immunization", "SocialFactor", "FamilyHistory", "Other",
    "Investigation", "Theory",
})

# Edge codes that may be stored in the personal graph (graph.kg_edges).
PERSONAL_EDGE_CODES: frozenset[str] = frozenset({
    "may_explain", "associated_with", "temporal_sequence", "treats", "worsens",
    "alleviates", "co_occurs_with", "contradicts", "refines", "supersedes",
    "evidence_for", "evidence_against", "investigates",
})

# Registered in graph.edge_types but FORBIDDEN inside the personal graph — the only
# personal<->external connection is external_bridge.relevance_links (context only).
FORBIDDEN_PERSONAL_EDGE_CODES: frozenset[str] = frozenset({"relevance_link"})

# Diagnostic / causal-overreach verbs that must NEVER exist as edge codes anywhere.
# `may_explain` is the strongest causal edge permitted (the safety ceiling).
PROHIBITED_EDGE_CODES: frozenset[str] = frozenset({
    "causes", "diagnoses", "confirms_diagnosis", "rules_out", "proves",
    "confirms_dx", "diagnosis_of",
})


def validate_personal_edge_type(edge_type: str) -> None:
    """Raise ValueError if ``edge_type`` may not be stored in the personal graph.

    Enforces, in order:
      * no diagnostic / causal-overreach verbs (G1),
      * relevance_link is external-only (G2),
      * the edge code is a known personal edge code.
    """
    if edge_type in PROHIBITED_EDGE_CODES:
        raise ValueError(
            f"prohibited edge type '{edge_type}': diagnostic/causal-overreach edges are "
            f"never allowed; 'may_explain' is the strongest permitted causal edge"
        )
    if edge_type in FORBIDDEN_PERSONAL_EDGE_CODES:
        raise ValueError(
            f"edge type '{edge_type}' is external-context only and must be stored in "
            f"external_bridge.relevance_links, never in the personal graph"
        )
    if edge_type not in PERSONAL_EDGE_CODES:
        raise ValueError(f"unknown personal edge type '{edge_type}'")
