"""Temporal activities for C9. Non-deterministic work (DB, C7 calls) lives here."""

from __future__ import annotations

import os
import uuid

from temporalio import activity
from wellbe_contracts.c7_thread import HealthThreadStatus, TransitionGuardContext
from wellbe_db import create_engine, create_session_factory

from wellbe_c9_continuity.service import ContinuityService
from wellbe_c9_continuity.temporal.types import (
    FIRE_TIMER_ACTIVITY,
    FireTimerInput,
    FireTimerOutput,
)


def _database_url() -> str:
    url = os.environ.get("WELLBE_DATABASE_URL")
    if not url:
        raise RuntimeError("WELLBE_DATABASE_URL must be set for the continuity worker")
    return url


@activity.defn(name=FIRE_TIMER_ACTIVITY)
async def fire_timer_activity(payload: FireTimerInput) -> FireTimerOutput:
    """Re-read the ledger and run the race-safe timer-fire protocol."""
    engine = create_engine(_database_url())
    factory = create_session_factory(engine)
    try:
        async with factory() as session, session.begin():
            svc = ContinuityService(session)
            target = (
                HealthThreadStatus(payload.requested_target_status)
                if payload.requested_target_status
                else None
            )
            result = await svc.fire_timer(
                pending_item_id=uuid.UUID(payload.pending_item_id),
                timer_epoch=payload.timer_epoch,
                requested_target_status=target,
                guard_context=TransitionGuardContext(
                    closure_basis_single_normal_test=payload.closure_basis_single_normal_test,
                    symptoms_persist=payload.symptoms_persist,
                ),
            )
        return FireTimerOutput(
            action=result.action.value,
            c7_rejection_code=result.c7_rejection_code,
        )
    finally:
        await engine.dispose()
