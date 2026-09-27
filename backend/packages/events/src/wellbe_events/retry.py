"""Outbox consumer retry policy: bounded backoff, dead-lettering and quiet logs.

A consumer that fails to handle an outbox row records the failure on the row
(``attempts``, ``last_error``, ``next_attempt_at``) instead of retrying it on
every poll. After ``max_attempts`` failures the row is dead-lettered
(``dead_lettered_at``) and no longer claimed; ``scripts/ops/outbox.py requeue``
puts it back.

Transient errors (e.g. C9's ``OutOfOrderThreadEventError``: a predecessor event
has not been consumed yet) are expected to resolve on their own. They are
deferred for a short delay without counting toward ``max_attempts`` and without
a traceback. So that a transient condition that never clears cannot block a row
forever, transient failures of a row older than ``transient_max_age_seconds``
are counted like any other failure.

``decide_failure`` is pure so the policy is testable without a database.
"""

from __future__ import annotations

import logging
import random
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from typing import Any

from sqlalchemy import ColumnElement, and_, func, or_

from wellbe_events.models import OutboxEventRow

MAX_ERROR_CHARS = 2000


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 12
    max_delay_seconds: float = 300.0
    jitter_ratio: float = 0.1
    transient_delay_seconds: float = 5.0
    transient_max_age_seconds: float = 3600.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")


class FailureAction(StrEnum):
    RETRY = "retry"
    DEAD_LETTER = "dead_letter"
    DEFER = "defer"  # transient: retry soon, attempts not incremented


@dataclass(frozen=True)
class FailureDecision:
    action: FailureAction
    attempts: int
    delay_seconds: float | None
    error: str
    log_level: int
    with_traceback: bool


def format_error(exc: BaseException, limit: int = MAX_ERROR_CHARS) -> str:
    """``ExceptionClass: message``, truncated to ``limit`` characters."""
    text = f"{type(exc).__name__}: {exc}"
    return text if len(text) <= limit else text[: limit - 1] + "…"


def backoff_seconds(attempts: int, policy: RetryPolicy) -> float:
    """``min(2**attempts, max_delay)`` seconds, before jitter."""
    return float(min(2 ** min(attempts, 30), policy.max_delay_seconds))


def _jittered(delay: float, policy: RetryPolicy, rng: Callable[[], float]) -> float:
    return delay * (1.0 + policy.jitter_ratio * rng())


def decide_failure(
    *,
    attempts: int,
    exc: BaseException,
    policy: RetryPolicy,
    transient: bool = False,
    age_seconds: float = 0.0,
    previous_error: str | None = None,
    rng: Callable[[], float] = random.random,
) -> FailureDecision:
    """Decide what to do with an outbox row whose handler raised ``exc``.

    ``attempts`` is the row's counted failures before this one, ``age_seconds``
    the time since the row was created, ``previous_error`` its ``last_error``.
    """
    error = format_error(exc)

    if transient and age_seconds < policy.transient_max_age_seconds:
        first_seen = previous_error is None or not previous_error.startswith(
            f"{type(exc).__name__}:"
        )
        return FailureDecision(
            action=FailureAction.DEFER,
            attempts=attempts,
            delay_seconds=_jittered(policy.transient_delay_seconds, policy, rng),
            error=error,
            log_level=logging.INFO if first_seen else logging.DEBUG,
            with_traceback=False,
        )

    new_attempts = attempts + 1
    if new_attempts >= policy.max_attempts:
        return FailureDecision(
            action=FailureAction.DEAD_LETTER,
            attempts=new_attempts,
            delay_seconds=None,
            error=error,
            log_level=logging.ERROR,
            with_traceback=new_attempts == 1,
        )
    return FailureDecision(
        action=FailureAction.RETRY,
        attempts=new_attempts,
        delay_seconds=_jittered(backoff_seconds(new_attempts, policy), policy, rng),
        error=error,
        log_level=logging.ERROR if new_attempts == 1 else logging.WARNING,
        with_traceback=new_attempts == 1,
    )


def failure_values(decision: FailureDecision) -> dict[str, Any]:
    """Column values to persist ``decision`` on the outbox row."""
    values: dict[str, Any] = {"attempts": decision.attempts, "last_error": decision.error}
    if decision.action is FailureAction.DEAD_LETTER:
        values["dead_lettered_at"] = func.now()
        values["next_attempt_at"] = None
    else:
        assert decision.delay_seconds is not None
        values["next_attempt_at"] = func.now() + timedelta(seconds=decision.delay_seconds)
    return values


def log_failure(
    logger: logging.Logger,
    decision: FailureDecision,
    *,
    event_type: str,
    row_id: object,
    exc: BaseException,
    policy: RetryPolicy,
) -> None:
    error_class = type(exc).__name__
    exc_info = exc if decision.with_traceback else None
    if decision.action is FailureAction.DEFER:
        logger.log(
            decision.log_level,
            "%s %s deferred (%s); retrying in %.0fs",
            event_type,
            row_id,
            decision.error,
            decision.delay_seconds,
        )
    elif decision.action is FailureAction.DEAD_LETTER:
        logger.error(
            "%s %s dead-lettered after %d attempt(s): %s "
            "(inspect/requeue with scripts/ops/outbox.py)",
            event_type,
            row_id,
            decision.attempts,
            error_class,
            exc_info=exc_info,
        )
    else:
        logger.log(
            decision.log_level,
            "%s %s failed (attempt %d/%d, %s); retrying in %.0fs",
            event_type,
            row_id,
            decision.attempts,
            policy.max_attempts,
            error_class,
            decision.delay_seconds,
            exc_info=exc_info,
        )


def claimable() -> ColumnElement[bool]:
    """Rows a consumer may claim now: undelivered, live, and not backing off."""
    return and_(
        OutboxEventRow.delivered_at.is_(None),
        OutboxEventRow.dead_lettered_at.is_(None),
        or_(
            OutboxEventRow.next_attempt_at.is_(None),
            OutboxEventRow.next_attempt_at <= func.now(),
        ),
    )


@dataclass(frozen=True)
class BacklogStats:
    event_type: str
    pending: int
    retrying: int
    dead: int
    oldest_live_age_seconds: float | None


def backlog_summary(
    stats: Iterable[BacklogStats], *, stale_after_seconds: float = 300.0
) -> str | None:
    """One-line health summary, or None when nothing is dead, retrying or stale."""
    parts = []
    for s in sorted(stats, key=lambda s: s.event_type):
        stale = (s.oldest_live_age_seconds or 0.0) >= stale_after_seconds
        if not (s.dead or s.retrying or stale):
            continue
        oldest = (
            f" oldest={s.oldest_live_age_seconds:.0f}s"
            if s.oldest_live_age_seconds is not None
            else ""
        )
        parts.append(
            f"{s.event_type}: pending={s.pending} retrying={s.retrying} dead={s.dead}{oldest}"
        )
    return "; ".join(parts) if parts else None
