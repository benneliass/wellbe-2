"""C7 Health Thread Engine + State Machine."""

from wellbe_c7_thread.errors import (
    ClosureSafetyError,
    InvalidTransitionError,
    SystemThreadRequiresEvidenceError,
    ThreadError,
    ThreadNotFoundError,
    VersionConflictError,
)
from wellbe_c7_thread.service import ThreadService
from wellbe_c7_thread.state_machine import (
    evaluate_safety_guards,
    validate_edge,
    validate_transition,
)

__all__ = [
    "ThreadService",
    "ThreadError",
    "ThreadNotFoundError",
    "InvalidTransitionError",
    "ClosureSafetyError",
    "VersionConflictError",
    "SystemThreadRequiresEvidenceError",
    "validate_edge",
    "validate_transition",
    "evaluate_safety_guards",
]
