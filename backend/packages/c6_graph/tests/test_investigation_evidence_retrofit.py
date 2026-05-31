"""WEL-135 — C6 retrofit safety contracts (unit level).

These assert the service-layer guards that mirror migration 008's DB constraints.
Live DB-constraint verification (relevance_link rejected by CHECK, RLS, trigger,
external isolation) is exercised against the kind-desktop cluster Postgres.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest

from wellbe_c6_graph.constants import (
    FORBIDDEN_PERSONAL_EDGE_CODES,
    PERSONAL_NODE_TYPES,
    PROHIBITED_EDGE_CODES,
    validate_personal_edge_type,
)
from wellbe_c6_graph.repository import GraphRepository


class TestNewNodeTypes:
    def test_investigation_and_theory_are_allowed_personal_node_types(self):
        assert "Investigation" in PERSONAL_NODE_TYPES
        assert "Theory" in PERSONAL_NODE_TYPES

    def test_no_bare_condition_node_type(self):
        # Investigate, never diagnose — there is no 'Condition' node type.
        assert "Condition" not in PERSONAL_NODE_TYPES


class TestEdgeGuards:
    def test_new_evidential_and_process_edges_allowed(self):
        for code in ("evidence_for", "evidence_against", "investigates", "may_explain"):
            validate_personal_edge_type(code)  # must not raise

    def test_relevance_link_forbidden_in_personal_graph(self):
        assert "relevance_link" in FORBIDDEN_PERSONAL_EDGE_CODES
        with pytest.raises(ValueError, match="external-context only"):
            validate_personal_edge_type("relevance_link")

    @pytest.mark.parametrize("verb", sorted(PROHIBITED_EDGE_CODES))
    def test_diagnostic_verbs_rejected(self, verb: str):
        with pytest.raises(ValueError, match="prohibited edge type"):
            validate_personal_edge_type(verb)

    def test_may_explain_is_strongest_causal_edge(self):
        # may_explain allowed; causes/proves/etc. prohibited.
        validate_personal_edge_type("may_explain")
        for verb in ("causes", "proves", "diagnoses", "rules_out", "confirms_diagnosis"):
            with pytest.raises(ValueError):
                validate_personal_edge_type(verb)

    def test_unknown_edge_type_rejected(self):
        with pytest.raises(ValueError, match="unknown personal edge type"):
            validate_personal_edge_type("definitely_not_a_real_edge")


class TestRepositoryGuard:
    """The repository guards even without a DB session — validation runs first,
    so the coroutine raises before touching ``session``."""

    def test_insert_edge_rejects_relevance_link_before_db(self):
        repo = GraphRepository(session=None)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="external-context only"):
            asyncio.run(
                repo.insert_edge(
                    from_node_id=uuid.uuid4(),
                    to_node_id=uuid.uuid4(),
                    edge_type="relevance_link",
                    potential_score=0.5,
                    patient_id=uuid.uuid4(),
                )
            )

    def test_insert_edge_rejects_diagnostic_verb_before_db(self):
        repo = GraphRepository(session=None)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="prohibited edge type"):
            asyncio.run(
                repo.insert_edge(
                    from_node_id=uuid.uuid4(),
                    to_node_id=uuid.uuid4(),
                    edge_type="causes",
                    potential_score=0.9,
                    patient_id=uuid.uuid4(),
                )
            )
