"""When to wait and when to stop. This module does not sleep.

Deadline, in-flight cap, and the attempt limit share the terminal reason
dependency_unavailable. The caller waits delay_ms, then asks again.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

_ATTEMPT_LIMIT = 3


@dataclass(frozen=True)
class AttemptInput:
    attempt: int
    now: int
    started_at: int
    deadline_ms: int
    base_ms: int
    in_flight: int
    max_in_flight: int
    seed: int


@dataclass(frozen=True)
class WaitDecision:
    action: Literal["wait"]
    delay_ms: int


@dataclass(frozen=True)
class StopDecision:
    action: Literal["stop"]
    reason: Literal["dependency_unavailable"]


AttemptDecision = WaitDecision | StopDecision


def schedule_attempt(attempt: AttemptInput) -> AttemptDecision:
    if attempt.now > attempt.started_at + attempt.deadline_ms:
        return _stop()
    if attempt.in_flight >= attempt.max_in_flight:
        return _stop()
    if attempt.attempt >= _ATTEMPT_LIMIT:
        return _stop()
    delay_ms = attempt.base_ms * 2**attempt.attempt + ((attempt.seed + attempt.attempt) % 3)
    return WaitDecision(action="wait", delay_ms=delay_ms)


def _stop() -> StopDecision:
    return StopDecision(action="stop", reason="dependency_unavailable")
