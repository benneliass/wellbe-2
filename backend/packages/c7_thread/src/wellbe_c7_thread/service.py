"""C7 Health Thread service.

``transition_thread`` is the single domain command for changing a thread's
lifecycle state. No other component may patch ``health_threads.status`` directly.

Per docs/decisions/health-thread-state-machine-enforcement.md, one Postgres
transaction: load FOR UPDATE, validate edge + safety guards, increment
status_version, append a transition row, and emit a ``thread.state_changed``
outbox event. The caller owns the commit (matching C5's EvidenceService).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_contracts.c7_thread import (
    THREAD_STATE_CHANGED,
    HealthThreadStatus,
    ThreadActor,
    ThreadEvidenceRef,
    ThreadStateChangedPayload,
    ThreadTransitionResult,
    TransitionGuardContext,
)
from wellbe_events import emit_event

from wellbe_c7_thread.errors import ThreadNotFoundError, VersionConflictError
from wellbe_c7_thread.repository import ThreadRepository
from wellbe_c7_thread.state_machine import validate_transition


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ThreadService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ThreadRepository(session)

    async def create_thread(
        self,
        *,
        patient_id: uuid.UUID,
        title: str,
        thread_id: uuid.UUID | None = None,
    ) -> uuid.UUID:
        """Create a new thread in ``draft`` status. Returns the thread id."""
        tid = thread_id or uuid.uuid4()
        await self._repo.create_thread(thread_id=tid, patient_id=patient_id, title=title)
        return tid

    async def transition_thread(
        self,
        *,
        thread_id: uuid.UUID,
        target_status: HealthThreadStatus,
        actor: ThreadActor,
        reason_code: str,
        idempotency_key: str,
        correlation_id: str,
        trace_id: str,
        evidence_refs: list[ThreadEvidenceRef] | None = None,
        guard_context: TransitionGuardContext | None = None,
        expected_version: int | None = None,
        metadata: dict[str, object] | None = None,
    ) -> ThreadTransitionResult:
        evidence_refs = evidence_refs or []
        guard_context = guard_context or TransitionGuardContext()
        metadata = metadata or {}

        # 1. Idempotency: a replay of the same (thread, key) returns the prior result.
        existing = await self._repo.find_transition_by_idempotency(thread_id, idempotency_key)
        if existing is not None:
            return ThreadTransitionResult(
                thread_id=thread_id,
                from_status=HealthThreadStatus(existing.from_status),
                to_status=HealthThreadStatus(existing.to_status),
                status_version=existing.transition_seq + 1,
                transition_seq=existing.transition_seq,
                event_id=existing.event_id,
                safety_flags=list(existing.safety_flags or []),
                idempotent_replay=True,
            )

        # 2. Lock the thread row for the duration of the transaction.
        row = await self._repo.get_for_update(thread_id)
        if row is None:
            raise ThreadNotFoundError(thread_id)

        current_status = HealthThreadStatus(row.status)
        current_version = row.status_version

        # 3. Optimistic concurrency check (if the caller pinned a version).
        if expected_version is not None and expected_version != current_version:
            raise VersionConflictError(expected_version, current_version)

        # 4. Domain validation: structural edge + contextual safety guards.
        validate_transition(
            from_status=current_status,
            to_status=target_status,
            guard_context=guard_context,
        )

        new_version = current_version + 1
        transition_seq = await self._repo.next_transition_seq(thread_id)

        # 5. Emit the durable outbox event (same transaction as the state change).
        payload = ThreadStateChangedPayload(
            thread_id=thread_id,
            patient_id=row.patient_id,
            from_status=current_status,
            to_status=target_status,
            transition_seq=transition_seq,
            actor=actor,
            reason_code=reason_code,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            trace_id=trace_id,
            evidence_refs=evidence_refs,
            safety_flags=[],
            metadata=metadata,
        )
        event_id = await emit_event(
            session=self._session,
            event_type=THREAD_STATE_CHANGED,
            payload=payload.model_dump(mode="json"),
            correlation_id=correlation_id,
            trace_id=trace_id,
        )

        # 6. Conditional status update — 0 rows means a concurrent writer won.
        affected = await self._repo.update_status(
            thread_id=thread_id,
            new_status=target_status.value,
            new_version=new_version,
            expected_version=current_version,
            status_changed_at=_utcnow(),
        )
        if affected == 0:
            raise VersionConflictError(current_version, -1)

        # 7. Append the immutable transition row.
        await self._repo.insert_transition(
            transition_id=uuid.uuid4(),
            thread_id=thread_id,
            from_status=current_status.value,
            to_status=target_status.value,
            transition_seq=transition_seq,
            actor_type=actor.type.value,
            actor_id=actor.id,
            reason_code=reason_code,
            evidence_refs=[ref.model_dump(mode="json") for ref in evidence_refs],
            safety_flags=[],
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            event_id=event_id,
        )

        return ThreadTransitionResult(
            thread_id=thread_id,
            from_status=current_status,
            to_status=target_status,
            status_version=new_version,
            transition_seq=transition_seq,
            event_id=event_id,
            safety_flags=[],
            idempotent_replay=False,
        )
