"""C13 /v2 Home signals summary route (WEL-91).

A typed REST read that composes the coverage-aware, never-alarm Home "signals"
line from the caller's own C6 graph nodes, replacing the hard-coded mock. See
docs/decisions/signals-summary-semantics.md.
"""

from __future__ import annotations

from fastapi import APIRouter
from wellbe_contracts.signals import SignalsSummaryV2

from wellbe_api.deps import PrincipalDep, SessionDep, audit_ref, require_access
from wellbe_api.signals.engine import summarize_signals

router = APIRouter(prefix="/v2", tags=["v2-signals"])

_RESOURCE = "knowledge_graph"


@router.get("/signals", response_model=SignalsSummaryV2)
async def get_signals(
    principal: PrincipalDep,
    session: SessionDep,
) -> SignalsSummaryV2:
    # Self-scoped read of the caller's own signal-bearing data.
    await require_access(
        principal, session, action="read", resource_type=_RESOURCE
    )

    result = await summarize_signals(
        session=session,
        patient_id=principal.patient_id,
        correlation_id=principal.correlation_id,
    )
    summary = result.summary
    assert summary is not None

    await audit_ref(
        session,
        event_type="c13.signals.read",
        principal=principal,
        summary="Home coverage-aware signals summary read",
        extra={
            "areas_with_data": summary.areas_with_data,
            "areas_total": summary.areas_total,
            "suppressed": summary.suppressed,
        },
    )
    await session.commit()

    return summary
