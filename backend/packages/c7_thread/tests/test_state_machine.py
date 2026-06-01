from __future__ import annotations

import pytest
from wellbe_c7_thread.errors import ClosureSafetyError, InvalidTransitionError
from wellbe_c7_thread.state_machine import (
    FLAG_AI_FINAL_DIAGNOSIS,
    FLAG_CLOSURE_SINGLE_NORMAL_TEST,
    FLAG_SYMPTOMS_PERSIST,
    evaluate_safety_guards,
    validate_edge,
    validate_transition,
)
from wellbe_contracts.c7_thread import (
    ALLOWED_TRANSITIONS,
    HealthThreadStatus,
    TransitionGuardContext,
    is_edge_allowed,
)

ALL_STATUSES = list(HealthThreadStatus)


def _all_allowed_edges() -> list[tuple[HealthThreadStatus, HealthThreadStatus]]:
    return [(f, t) for f, targets in ALLOWED_TRANSITIONS.items() for t in targets]


def _all_disallowed_edges() -> list[tuple[HealthThreadStatus, HealthThreadStatus]]:
    edges = []
    for f in ALL_STATUSES:
        for t in ALL_STATUSES:
            if not is_edge_allowed(f, t):
                edges.append((f, t))
    return edges


class TestEdgeValidity:
    @pytest.mark.parametrize("from_status,to_status", _all_allowed_edges())
    def test_every_allowed_edge_succeeds(self, from_status, to_status):
        # Should not raise (closure edges use a safe default guard context).
        validate_transition(
            from_status=from_status,
            to_status=to_status,
            guard_context=TransitionGuardContext(),
        )

    @pytest.mark.parametrize("from_status,to_status", _all_disallowed_edges())
    def test_every_disallowed_edge_fails(self, from_status, to_status):
        with pytest.raises(InvalidTransitionError):
            validate_edge(from_status, to_status)

    def test_closed_reopened_round_trip_allowed(self):
        validate_edge(HealthThreadStatus.CLOSED, HealthThreadStatus.REOPENED)
        validate_edge(HealthThreadStatus.REOPENED, HealthThreadStatus.ACTIVE_UNRESOLVED)

    def test_archived_is_terminal(self):
        assert ALLOWED_TRANSITIONS[HealthThreadStatus.ARCHIVED] == frozenset()


class TestSafetyGuards:
    def test_closure_on_single_normal_test_is_rejected(self):
        with pytest.raises(ClosureSafetyError) as exc:
            evaluate_safety_guards(
                to_status=HealthThreadStatus.CLOSED,
                guard_context=TransitionGuardContext(
                    closure_basis_single_normal_test=True
                ),
            )
        assert FLAG_CLOSURE_SINGLE_NORMAL_TEST in exc.value.violations

    def test_persistent_symptoms_block_closure(self):
        with pytest.raises(ClosureSafetyError) as exc:
            evaluate_safety_guards(
                to_status=HealthThreadStatus.CLOSED,
                guard_context=TransitionGuardContext(symptoms_persist=True),
            )
        assert FLAG_SYMPTOMS_PERSIST in exc.value.violations

    def test_ai_final_diagnosis_rejected_on_any_transition(self):
        with pytest.raises(ClosureSafetyError) as exc:
            evaluate_safety_guards(
                to_status=HealthThreadStatus.EXPLAINED,
                guard_context=TransitionGuardContext(ai_final_diagnosis_claim=True),
            )
        assert FLAG_AI_FINAL_DIAGNOSIS in exc.value.violations

    def test_explained_to_closed_allowed_when_safe(self):
        validate_transition(
            from_status=HealthThreadStatus.EXPLAINED,
            to_status=HealthThreadStatus.CLOSED,
            guard_context=TransitionGuardContext(),
        )

    def test_non_closure_target_ignores_closure_flags(self):
        # symptoms_persist only blocks closure, not other transitions.
        evaluate_safety_guards(
            to_status=HealthThreadStatus.WATCHFUL_WAITING,
            guard_context=TransitionGuardContext(symptoms_persist=True),
        )
