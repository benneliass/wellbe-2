from __future__ import annotations

import asyncio
import logging
import uuid
from types import SimpleNamespace
from typing import Any

import pytest
import wellbe_db
from sqlalchemy import Select
from sqlalchemy.dialects import postgresql
from wellbe_c9_continuity import OutOfOrderThreadEventError
from wellbe_events.retry import (
    BacklogStats,
    FailureAction,
    RetryPolicy,
    backlog_summary,
    backoff_seconds,
    decide_failure,
    format_error,
)
from wellbe_processing_worker import main
from wellbe_processing_worker.config import ProcessingWorkerSettings

POLICY = RetryPolicy(max_attempts=8, max_delay_seconds=300.0, jitter_ratio=0.1)


def no_jitter() -> float:
    return 0.0


def full_jitter() -> float:
    return 1.0


class TestBackoff:
    def test_exponential_then_capped(self):
        assert [backoff_seconds(n, POLICY) for n in range(1, 10)] == [
            2, 4, 8, 16, 32, 64, 128, 256, 300,
        ]

    def test_huge_attempts_do_not_overflow(self):
        assert backoff_seconds(10_000, POLICY) == 300

    def test_jitter_is_small_and_additive(self):
        low = decide_failure(attempts=2, exc=ValueError(), policy=POLICY, rng=no_jitter)
        high = decide_failure(attempts=2, exc=ValueError(), policy=POLICY, rng=full_jitter)
        assert low.delay_seconds == 8.0
        assert high.delay_seconds == pytest.approx(8.8)


class TestDecideFailure:
    def test_first_failure_logs_traceback_at_error(self):
        d = decide_failure(attempts=0, exc=ValueError("boom"), policy=POLICY, rng=no_jitter)
        assert d.action is FailureAction.RETRY
        assert d.attempts == 1
        assert d.delay_seconds == 2.0
        assert d.log_level == logging.ERROR
        assert d.with_traceback
        assert d.error == "ValueError: boom"

    def test_later_failures_are_single_warning_lines(self):
        d = decide_failure(attempts=3, exc=ValueError("boom"), policy=POLICY, rng=no_jitter)
        assert d.action is FailureAction.RETRY
        assert d.attempts == 4
        assert d.delay_seconds == 16.0
        assert d.log_level == logging.WARNING
        assert not d.with_traceback

    def test_dead_letters_when_attempts_reach_max(self):
        d = decide_failure(attempts=7, exc=ValueError("boom"), policy=POLICY)
        assert d.action is FailureAction.DEAD_LETTER
        assert d.attempts == 8
        assert d.delay_seconds is None
        assert d.log_level == logging.ERROR
        assert not d.with_traceback

    def test_max_attempts_one_dead_letters_with_traceback(self):
        d = decide_failure(attempts=0, exc=ValueError(), policy=RetryPolicy(max_attempts=1))
        assert d.action is FailureAction.DEAD_LETTER
        assert d.with_traceback

    def test_every_attempt_up_to_max_is_bounded(self):
        attempts, actions = 0, []
        while True:
            d = decide_failure(attempts=attempts, exc=RuntimeError(), policy=POLICY)
            actions.append(d.action)
            attempts = d.attempts
            if d.action is FailureAction.DEAD_LETTER:
                break
        assert actions == [FailureAction.RETRY] * 7 + [FailureAction.DEAD_LETTER]

    def test_invalid_policy_rejected(self):
        with pytest.raises(ValueError):
            RetryPolicy(max_attempts=0)

    def test_error_is_truncated(self):
        text = format_error(ValueError("x" * 5000))
        assert len(text) == 2000
        assert text.startswith("ValueError: xxx")


def _out_of_order() -> OutOfOrderThreadEventError:
    return OutOfOrderThreadEventError(uuid.uuid4(), expected_seq=2, got_seq=3)


class TestTransient:
    def test_out_of_order_is_deferred_without_counting(self):
        d = decide_failure(
            attempts=0, exc=_out_of_order(), policy=POLICY, transient=True, rng=no_jitter
        )
        assert d.action is FailureAction.DEFER
        assert d.attempts == 0
        assert d.delay_seconds == POLICY.transient_delay_seconds
        assert not d.with_traceback
        assert d.log_level == logging.INFO

    def test_repeat_deferral_logs_at_debug(self):
        previous = format_error(_out_of_order())
        d = decide_failure(
            attempts=0,
            exc=_out_of_order(),
            policy=POLICY,
            transient=True,
            previous_error=previous,
        )
        assert d.action is FailureAction.DEFER
        assert d.log_level == logging.DEBUG

    def test_transient_never_dead_letters_while_young(self):
        d = decide_failure(
            attempts=7, exc=_out_of_order(), policy=POLICY, transient=True, age_seconds=60
        )
        assert d.action is FailureAction.DEFER
        assert d.attempts == 7

    def test_transient_counts_once_row_is_too_old(self):
        d = decide_failure(
            attempts=0,
            exc=_out_of_order(),
            policy=POLICY,
            transient=True,
            age_seconds=POLICY.transient_max_age_seconds,
        )
        assert d.action is FailureAction.RETRY
        assert d.attempts == 1

    def test_thread_consumer_treats_out_of_order_as_transient(self):
        assert isinstance(_out_of_order(), main.THREAD_STATE_TRANSIENT_ERRORS)


class TestBacklogSummary:
    def test_quiet_when_only_fresh_pending(self):
        stats = [BacklogStats("genesis.input_ready", 3, 0, 0, 10.0)]
        assert backlog_summary(stats, stale_after_seconds=300) is None
        assert backlog_summary([]) is None

    def test_reports_dead_retrying_and_stale(self):
        stats = [
            BacklogStats("thread.state_changed", 0, 0, 2, None),
            BacklogStats("genesis.input_ready", 1, 0, 0, 900.0),
            BacklogStats("raw_context.received", 0, 1, 0, 5.0),
        ]
        assert backlog_summary(stats, stale_after_seconds=300) == (
            "genesis.input_ready: pending=1 retrying=0 dead=0 oldest=900s; "
            "raw_context.received: pending=0 retrying=1 dead=0 oldest=5s; "
            "thread.state_changed: pending=0 retrying=0 dead=2"
        )


class _Result:
    def __init__(self, rows: list[tuple[Any, float]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[Any, float]]:
        return self._rows


class _Session:
    def __init__(self, store: dict[str, Any]) -> None:
        self._store = store

    async def __aenter__(self) -> _Session:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def execute(self, stmt: Any) -> _Result:
        if isinstance(stmt, Select):
            return _Result(self._store["rows"])
        self._store["updates"].append(str(stmt.compile(dialect=postgresql.dialect())))
        self._store["params"].append(stmt.compile(dialect=postgresql.dialect()).params)
        return _Result([])

    async def commit(self) -> None:
        self._store["commits"] += 1


async def _run_one_poll(
    monkeypatch: pytest.MonkeyPatch,
    rows: list[SimpleNamespace],
    handler: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    store: dict[str, Any] = {
        "rows": [(r, 1.0) for r in rows],
        "updates": [],
        "params": [],
        "commits": 0,
    }
    monkeypatch.setattr(wellbe_db, "create_engine", lambda url: None)
    monkeypatch.setattr(wellbe_db, "create_session_factory", lambda engine: lambda: _Session(store))

    async def stop(_: float) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr(main.asyncio, "sleep", stop)
    with pytest.raises(asyncio.CancelledError):
        await main._consume_outbox_loop(
            ProcessingWorkerSettings(), event_type="thread.state_changed", handler=handler, **kwargs
        )
    return store


def _row(attempts: int = 0, last_error: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), payload={}, attempts=attempts, last_error=last_error)


class TestConsumeLoop:
    async def test_out_of_order_is_deferred_quietly(self, monkeypatch, caplog):
        async def handler(session: Any, payload: Any, row_id: Any) -> str:
            raise _out_of_order()

        caplog.set_level(logging.DEBUG, logger=main.logger.name)
        store = await _run_one_poll(
            monkeypatch,
            [_row()],
            handler,
            transient_errors=main.THREAD_STATE_TRANSIENT_ERRORS,
        )
        [update_sql] = store["updates"]
        assert "next_attempt_at=(now() +" in update_sql
        assert "dead_lettered_at" not in update_sql
        assert store["params"][0]["attempts"] == 0
        assert store["commits"] == 1
        records = [r for r in caplog.records if r.name == main.logger.name]
        assert [r.levelno for r in records] == [logging.INFO]
        assert records[0].exc_info is None
        assert "deferred" in records[0].getMessage()

    async def test_exhausted_row_is_dead_lettered_with_one_error_line(self, monkeypatch, caplog):
        async def handler(session: Any, payload: Any, row_id: Any) -> str:
            raise RuntimeError("poison")

        caplog.set_level(logging.DEBUG, logger=main.logger.name)
        store = await _run_one_poll(monkeypatch, [_row(attempts=7)], handler)
        [update_sql] = store["updates"]
        assert "dead_lettered_at=now()" in update_sql
        assert store["params"][0]["attempts"] == 8
        assert store["params"][0]["last_error"] == "RuntimeError: poison"
        records = [r for r in caplog.records if r.name == main.logger.name]
        assert [r.levelno for r in records] == [logging.ERROR]
        assert records[0].exc_info is None
        assert "dead-lettered" in records[0].getMessage()

    async def test_success_marks_delivered_and_failures_do_not_block_batch(self, monkeypatch):
        bad, good = _row(), _row()

        async def handler(session: Any, payload: Any, row_id: Any) -> str:
            if row_id == bad.id:
                raise RuntimeError("poison")
            return "ok"

        store = await _run_one_poll(monkeypatch, [bad, good], handler)
        assert len(store["updates"]) == 2
        assert "attempts=" in store["updates"][0]
        assert "delivered_at=" in store["updates"][1]
        assert store["commits"] == 2  # the good row's work session + the claim session
