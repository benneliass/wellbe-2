"""C14 Investigation service.

Owns investigation workflow status; C7 stays authoritative for thread closure.
Closing an investigation is gated by InvestigationThreadCouplingPolicy against
C7 ThreadClosureSnapshots (G4). All state changes emit transactional outbox
events. C14 raises safety flags but never mutates thread state directly.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_contracts.c7_thread import ThreadClosureSnapshot
from wellbe_contracts.c14_investigation import (
    INVESTIGATION_CLOSED,
    INVESTIGATION_CREATED,
    INVESTIGATION_LINKED_TO_THREAD,
    INVESTIGATION_SAFETY_FLAG_RAISED,
    INVESTIGATION_STATE_CHANGED,
    CloseEvaluation,
    InvestigationClosedPayload,
    InvestigationCreatedPayload,
    InvestigationLinkedToThreadPayload,
    InvestigationOwnerType,
    InvestigationSafetyFlag,
    InvestigationSafetyFlagRaisedPayload,
    InvestigationStateChangedPayload,
    InvestigationStatus,
    InvestigationTransitionResult,
    ThreadRelationship,
)
from wellbe_events import emit_event

from wellbe_c14_investigation import coupling
from wellbe_c14_investigation.errors import (
    ClosureBlockedByThreadError,
    InvestigationNotFoundError,
    InvestigationVersionConflictError,
)
from wellbe_c14_investigation.repository import InvestigationRepository
from wellbe_c14_investigation.state_machine import validate_investigation_edge

# Thread relationships whose closure gates investigation closure.
_CLOSURE_RELEVANT_RELATIONSHIPS = (
    ThreadRelationship.PRIMARY.value,
    ThreadRelationship.SECONDARY.value,
)


class ClosureSnapshotProvider:
    """Protocol-ish: anything exposing get_closure_snapshot(thread_id)."""

    async def get_closure_snapshot(
        self, thread_id: uuid.UUID
    ) -> ThreadClosureSnapshot:  # pragma: no cover
        raise NotImplementedError


class InvestigationService:
    def __init__(
        self, session: AsyncSession, thread_service: ClosureSnapshotProvider
    ) -> None:
        self._session = session
        self._repo = InvestigationRepository(session)
        self._threads = thread_service

    async def create_investigation(
        self,
        *,
        patient_id: uuid.UUID,
        primary_question: str,
        owner_type: InvestigationOwnerType,
        correlation_id: str,
        trace_id: str,
        owner_grant_id: uuid.UUID | None = None,
        created_by_actor_id: uuid.UUID | None = None,
        investigation_id: uuid.UUID | None = None,
    ) -> uuid.UUID:
        iid = investigation_id or uuid.uuid4()
        await self._repo.create(
            investigation_id=iid,
            patient_id=patient_id,
            primary_question=primary_question,
            owner_type=owner_type.value,
            owner_grant_id=owner_grant_id,
            created_by_actor_id=created_by_actor_id,
        )
        # C6 projection node (graph is a projection, not source of truth).
        node_id = await self._repo.create_projection_node(
            patient_id=patient_id,
            investigation_id=iid,
            display_label=primary_question[:200],
            status="open",
        )
        await self._repo.set_projection_node(iid, node_id)
        await emit_event(
            session=self._session,
            event_type=INVESTIGATION_CREATED,
            payload=InvestigationCreatedPayload(
                investigation_id=iid,
                patient_id=patient_id,
                primary_question=primary_question,
                owner_type=owner_type,
                projection_node_id=node_id,
                correlation_id=correlation_id,
                trace_id=trace_id,
            ).model_dump(mode="json"),
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
        return iid

    async def link_thread(
        self,
        *,
        investigation_id: uuid.UUID,
        thread_id: uuid.UUID,
        relationship: ThreadRelationship,
        correlation_id: str,
        trace_id: str,
    ) -> None:
        row = await self._repo.get(investigation_id)
        if row is None:
            raise InvestigationNotFoundError(investigation_id)
        await self._repo.link_thread(
            investigation_id=investigation_id,
            thread_id=thread_id,
            patient_id=row.patient_id,
            relationship=relationship.value,
        )
        await emit_event(
            session=self._session,
            event_type=INVESTIGATION_LINKED_TO_THREAD,
            payload=InvestigationLinkedToThreadPayload(
                investigation_id=investigation_id,
                patient_id=row.patient_id,
                thread_id=thread_id,
                relationship=relationship,
                correlation_id=correlation_id,
                trace_id=trace_id,
            ).model_dump(mode="json"),
            correlation_id=correlation_id,
            trace_id=trace_id,
        )

    async def evaluate_close(self, investigation_id: uuid.UUID) -> CloseEvaluation:
        """Ask C7 whether linked threads permit closing this investigation."""
        links = await self._repo.get_linked_threads(
            investigation_id, relationships=_CLOSURE_RELEVANT_RELATIONSHIPS
        )
        snapshots = [
            await self._threads.get_closure_snapshot(thread_id)
            for thread_id, _ in links
        ]
        return coupling.evaluate_close(snapshots)

    async def transition(
        self,
        *,
        investigation_id: uuid.UUID,
        target_status: InvestigationStatus,
        reason_code: str,
        idempotency_key: str,
        correlation_id: str,
        trace_id: str,
        actor_id: uuid.UUID | None = None,
        expected_version: int | None = None,
    ) -> InvestigationTransitionResult:
        existing = await self._repo.find_transition_by_idempotency(
            investigation_id, idempotency_key
        )
        if existing is not None:
            return InvestigationTransitionResult(
                investigation_id=investigation_id,
                from_status=InvestigationStatus(existing.from_status),
                to_status=InvestigationStatus(existing.to_status),
                status_version=existing.transition_seq + 1,
                event_id=existing.event_id,
                idempotent_replay=True,
            )

        row = await self._repo.get_for_update(investigation_id)
        if row is None:
            raise InvestigationNotFoundError(investigation_id)

        current_status = InvestigationStatus(row.status)
        current_version = row.status_version

        if expected_version is not None and expected_version != current_version:
            raise InvestigationVersionConflictError(expected_version, current_version)

        # Workflow edge validity first.
        validate_investigation_edge(current_status, target_status)

        # Closure is additionally gated by C7's authoritative snapshots.
        if target_status is InvestigationStatus.CLOSED:
            evaluation = await self.evaluate_close(investigation_id)
            if not evaluation.allowed:
                raise ClosureBlockedByThreadError(evaluation)

        new_version = current_version + 1
        transition_seq = await self._repo.next_transition_seq(investigation_id)

        payload = InvestigationStateChangedPayload(
            investigation_id=investigation_id,
            patient_id=row.patient_id,
            from_status=current_status,
            to_status=target_status,
            status_version=new_version,
            reason_code=reason_code,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
        event_id = await emit_event(
            session=self._session,
            event_type=INVESTIGATION_STATE_CHANGED,
            payload=payload.model_dump(mode="json"),
            correlation_id=correlation_id,
            trace_id=trace_id,
        )

        affected = await self._repo.update_status(
            investigation_id=investigation_id,
            new_status=target_status.value,
            new_version=new_version,
            expected_version=current_version,
            status_reason=reason_code,
        )
        if affected == 0:
            raise InvestigationVersionConflictError(current_version, -1)

        await self._repo.insert_transition(
            investigation_id=investigation_id,
            patient_id=row.patient_id,
            from_status=current_status.value,
            to_status=target_status.value,
            transition_seq=transition_seq,
            reason_code=reason_code,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            event_id=event_id,
        )

        if target_status is InvestigationStatus.CLOSED:
            links = await self._repo.get_linked_threads(investigation_id)
            await emit_event(
                session=self._session,
                event_type=INVESTIGATION_CLOSED,
                payload=InvestigationClosedPayload(
                    investigation_id=investigation_id,
                    patient_id=row.patient_id,
                    linked_thread_ids=[tid for tid, _ in links],
                    correlation_id=correlation_id,
                    trace_id=trace_id,
                ).model_dump(mode="json"),
                correlation_id=correlation_id,
                trace_id=trace_id,
            )

        return InvestigationTransitionResult(
            investigation_id=investigation_id,
            from_status=current_status,
            to_status=target_status,
            status_version=new_version,
            event_id=event_id,
            idempotent_replay=False,
        )

    async def raise_safety_flag(
        self,
        *,
        investigation_id: uuid.UUID,
        flag: InvestigationSafetyFlag,
        correlation_id: str,
        trace_id: str,
    ) -> None:
        """Record a safety flag and emit it. C7 decides any escalation."""
        row = await self._repo.get(investigation_id)
        if row is None:
            raise InvestigationNotFoundError(investigation_id)
        await self._repo.append_safety_flag(
            investigation_id=investigation_id, flag=flag.model_dump(mode="json")
        )
        await emit_event(
            session=self._session,
            event_type=INVESTIGATION_SAFETY_FLAG_RAISED,
            payload=InvestigationSafetyFlagRaisedPayload(
                investigation_id=investigation_id,
                patient_id=row.patient_id,
                flag=flag,
                correlation_id=correlation_id,
                trace_id=trace_id,
            ).model_dump(mode="json"),
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
