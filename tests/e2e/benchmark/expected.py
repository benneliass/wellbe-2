"""Deterministic "should-be" expected results for the WellBe benchmark corpus.

This module is the single source of truth for the E2E benchmark validation. Every
number is the CURRENT-IMPLEMENTATION, DETERMINISTIC prediction taken verbatim from
``docs/analysis/benchmark-expected-results.md`` section 5.1 (``blind_pre_diagnosis``
mode), cross-checked against the measured live state recorded in
``docs/analysis/benchmark-prediction-vs-actual.md``.

Why these are the "should be" numbers
-------------------------------------
The benchmark seed harness rewrites every event's ``source_type`` to ``manual_text``,
so 100% of events are processed by the rule-based ``TextFactExtractor`` (a 10-symptom /
4-medication keyword matcher with an ``OTHER`` fallback). The auto-linker, the five
intelligence engines, and the Health Thread state machine are NOT wired into this
ingestion path, so edges, threads, and engine outputs are all zero. The pipeline that
actually runs on this corpus is C2 (vault) -> C4 (extract) -> C5 (evidence) -> C6
(graph).

Evidence-link cardinality (C5)
------------------------------
These expectations encode the CORRECTED, post-fix behaviour:

  * exactly ONE PRIMARY evidence link per fact (links == facts),
  * no orphan links (every link points at a fact that exists),
  * exactly-once end-to-end processing under at-least-once delivery.

The pre-fix live measurement (2026-05-31) showed ~2x link rows and 201 orphan links;
that was tracked and resolved by WEL-103 (non-idempotent C5 linking) and WEL-104
(double end-to-end processing), both Done. The deterministic invariant the prediction
asserted ("one PRIMARY link per fact") is therefore now true at the row level too.
"""

from __future__ import annotations

from dataclasses import dataclass

MODE = "blind_pre_diagnosis"

# The only KG node types the keyword extractor can ever emit on this corpus.
ALLOWED_NODE_TYPES: frozenset[str] = frozenset({"Other", "Symptom", "Medication"})


@dataclass(frozen=True)
class CaseExpectation:
    """Deterministic per-case expected pipeline output (blind mode, current impl)."""

    case_id: str
    patient_id: str
    # C2 vault rows == ingested raw events (no vault-level dedup).
    events: int
    # C4 facts (>= events only when an event contains 2 distinct symptom keywords).
    facts_total: int
    fact_types: dict[str, int]
    # C5 evidence links == facts (one PRIMARY link per fact, post WEL-103/104).
    # C6 nodes after (patient_id, node_type, normalized_key) dedup.
    nodes_total: int
    node_types: dict[str, int]
    # Distinct post-dedup Symptom / Medication node identities (normalized_key).
    symptom_nodes: frozenset[str]
    medication_nodes: frozenset[str]
    # C6 edges: the auto-linker has no caller, so always zero on this corpus.
    edges: int


CASES: tuple[CaseExpectation, ...] = (
    CaseExpectation(
        case_id="C01",
        patient_id="61b3a25e-867f-50f2-9e6f-0483ec54e245",
        events=51,
        facts_total=51,
        fact_types={"other": 45, "symptom": 6},
        nodes_total=47,
        node_types={"Other": 45, "Symptom": 2},
        symptom_nodes=frozenset({"fever", "pain"}),
        medication_nodes=frozenset(),
        edges=0,
    ),
    CaseExpectation(
        case_id="C02",
        patient_id="00697626-0025-5d87-9576-20367e50c0e1",
        events=47,
        facts_total=47,
        fact_types={"other": 45, "symptom": 2},
        nodes_total=46,
        node_types={"Other": 45, "Symptom": 1},
        symptom_nodes=frozenset({"insomnia"}),
        medication_nodes=frozenset(),
        edges=0,
    ),
    CaseExpectation(
        case_id="C03",
        patient_id="cd2e1041-bc5b-5c4e-adae-1786c640079e",
        events=36,
        facts_total=37,
        fact_types={"other": 30, "symptom": 7},
        nodes_total=33,
        node_types={"Other": 30, "Symptom": 3},
        symptom_nodes=frozenset({"fatigue", "fever", "cough"}),
        medication_nodes=frozenset(),
        edges=0,
    ),
    CaseExpectation(
        case_id="C04",
        patient_id="23b1d00e-65db-530a-9d4b-5bde4dc39a3f",
        events=36,
        facts_total=39,
        fact_types={"other": 32, "symptom": 6, "medication": 1},
        nodes_total=35,
        node_types={"Other": 32, "Symptom": 2, "Medication": 1},
        symptom_nodes=frozenset({"pain", "chest_pain"}),
        medication_nodes=frozenset({"aspirin"}),
        edges=0,
    ),
    CaseExpectation(
        case_id="C05",
        patient_id="8e2138f0-a50a-5f54-a42e-719254a5fafd",
        events=27,
        facts_total=27,
        fact_types={"other": 22, "symptom": 4, "medication": 1},
        nodes_total=25,
        node_types={"Other": 22, "Symptom": 2, "Medication": 1},
        symptom_nodes=frozenset({"pain", "fatigue"}),
        medication_nodes=frozenset({"aspirin"}),
        edges=0,
    ),
)

CASES_BY_ID: dict[str, CaseExpectation] = {c.case_id: c for c in CASES}
PATIENT_IDS: tuple[str, ...] = tuple(c.patient_id for c in CASES)

# Consolidated cross-case totals (benchmark-expected-results.md section 5.1 TOTAL row).
# After a full pipeline reset + blind-only seed, the global pipeline tables contain
# ONLY these five cases, so global counts must equal these totals exactly.
TOTAL_EVENTS = sum(c.events for c in CASES)          # 197
TOTAL_FACTS = sum(c.facts_total for c in CASES)       # 201
TOTAL_NODES = sum(c.nodes_total for c in CASES)       # 186
TOTAL_EDGES = sum(c.edges for c in CASES)             # 0
TOTAL_LINKS = TOTAL_FACTS                              # 201 (one PRIMARY link per fact)
