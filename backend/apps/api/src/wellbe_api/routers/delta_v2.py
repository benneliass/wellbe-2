"""C13 /v2 "What changed?" delta digest route (WEL-56).

A typed REST read that composes a calm, source-linked change-event digest across
the caller's own open loops (C9) and thread lifecycle (C7), wiring the Home
"What changed?" pill. See docs/decisions/delta-semantics-window.md.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query
from wellbe_contracts.delta import DeltaDigestV2

from wellbe_api.delta.engine import build_digest
from wellbe_api.deps import PrincipalDep, SessionDep, audit_ref, require_access

router = APIRouter(prefix="/v2", tags=["v2-delta"])

_RESOURCE = "health_thread"


@router.get("/delta", response_model=DeltaDigestV2)
async def get_delta(
    principal: PrincipalDep,
    session: SessionDep,
    since: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> DeltaDigestV2:
    # Self-scoped read of the caller's own continuity + thread state.
    await require_access(
        principal, session, action="read", resource_type=_RESOURCE
    )

    result = await build_digest(
        session=session, patient_id=principal.patient_id, since=since, limit=limit
    )

    await audit_ref(
        session,
        event_type="c13.delta.read",
        principal=principal,
        summary="What-changed delta digest read",
        extra={"event_count": len(result.events), "window": result.window_label},
    )
    await session.commit()

    return DeltaDigestV2(
        window_since=result.window_since,
        window_label=result.window_label,
        events=result.events,
        note=result.note,
    )
