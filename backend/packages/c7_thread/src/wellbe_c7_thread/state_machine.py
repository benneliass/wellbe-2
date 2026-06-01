"""C7 domain transition logic: edge validity + contextual safety guards.

This module is pure (no I/O) so it can be exhaustively unit-tested. The
``transition_thread`` service composes it with persistence and the outbox.
"""

from __future__ import annotations

from wellbe_contracts.c7_thread import (
    HealthThreadStatus,
    TransitionGuardContext,
    is_edge_allowed,
)

from wellbe_c7_thread.errors import ClosureSafetyError, InvalidTransitionError

# Safety-flag codes recorded on the transition row when a guard rejects.
FLAG_CLOSURE_SINGLE_NORMAL_TEST = "closure_blocked_single_normal_test"
FLAG_SYMPTOMS_PERSIST = "closure_blocked_symptoms_persist"
FLAG_AI_FINAL_DIAGNOSIS = "ai_final_diagnosis_rejected"


def validate_edge(
    from_status: HealthThreadStatus, to_status: HealthThreadStatus
) -> None:
    """Raise InvalidTransitionError if the edge is not structurally allowed."""
    if not is_edge_allowed(from_status, to_status):
        raise InvalidTransitionError(from_status, to_status)


def evaluate_safety_guards(
    *,
    to_status: HealthThreadStatus,
    guard_context: TransitionGuardContext,
) -> None:
    """Evaluate contextual closure-safety guards.

    Raises ClosureSafetyError if a non-negotiable safety rule is violated.
    These rules apply regardless of whether the edge is structurally allowed.
    """
    violations: list[str] = []

    # An AI-asserted final diagnosis is never permitted on any transition.
    if guard_context.ai_final_diagnosis_claim:
        violations.append(FLAG_AI_FINAL_DIAGNOSIS)

    # Closure-specific guards.
    if to_status is HealthThreadStatus.CLOSED:
        if guard_context.closure_basis_single_normal_test:
            violations.append(FLAG_CLOSURE_SINGLE_NORMAL_TEST)
        if guard_context.symptoms_persist:
            violations.append(FLAG_SYMPTOMS_PERSIST)

    if violations:
        raise ClosureSafetyError(violations)


def validate_transition(
    *,
    from_status: HealthThreadStatus,
    to_status: HealthThreadStatus,
    guard_context: TransitionGuardContext,
) -> None:
    """Full domain validation: edge validity first, then safety guards."""
    validate_edge(from_status, to_status)
    evaluate_safety_guards(to_status=to_status, guard_context=guard_context)
