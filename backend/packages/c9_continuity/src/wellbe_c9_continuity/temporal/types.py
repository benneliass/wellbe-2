"""Pure data types shared between the C9 workflow and activity.

This module MUST stay dependency-free (no SQLAlchemy, no DB, no service imports)
so the Temporal workflow sandbox can import it safely. The activity name is also
defined here so the workflow can reference the activity by name without importing
the activity module (which pulls in non-deterministic DB code).
"""

from __future__ import annotations

from dataclasses import dataclass

FIRE_TIMER_ACTIVITY = "c9_fire_timer"


@dataclass
class FireTimerInput:
    pending_item_id: str
    timer_epoch: int
    requested_target_status: str | None = None
    closure_basis_single_normal_test: bool = False
    symptoms_persist: bool = False


@dataclass
class FireTimerOutput:
    action: str
    c7_rejection_code: str | None = None
