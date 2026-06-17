"""C13 /v2 non-diagnostic pattern read route (WEL-79).

A typed REST read that surfaces co-occurrence candidates across the caller's own
C6 knowledge graph, with mandatory caveats, qualitative evidence tiers, source
links, and preserved (never auto-resolved) contradictions. The composed wording
is C10-gated (fail-closed). See docs/decisions/pattern-detection-semantics.md.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from wellbe_contracts.patterns import PatternsResponseV2

from wellbe_api.deps import PrincipalDep, SessionDep, audit_ref, require_access
from wellbe_api.patterns.engine import detect_patterns

router = APIRouter(prefix="/v2", tags=["v2-patterns"])

_RESOURCE = "knowledge_graph"


@router.get("/patterns", response_model=PatternsResponseV2)
async def get_patterns(
    principal: PrincipalDep,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> PatternsResponseV2:
    # The pattern surface reads across all of the caller's own threads, so it is
    # authorized as a self-scoped read of the personal knowledge graph.
    await require_access(
        principal, session, action="read", resource_type=_RESOURCE
    )

    result = await detect_patterns(
        session=session,
        patient_id=principal.patient_id,
        correlation_id=principal.correlation_id,
        limit=limit,
    )

    await audit_ref(
        session,
        event_type="c13.patterns.read",
        principal=principal,
        summary="Non-diagnostic pattern read",
        extra={
            "pattern_count": len(result.candidates),
            "contradiction_count": sum(
                1 for c in result.candidates if c.is_contradiction
            ),
        },
    )
    await session.commit()

    return PatternsResponseV2(patterns=result.candidates, note=result.note)
