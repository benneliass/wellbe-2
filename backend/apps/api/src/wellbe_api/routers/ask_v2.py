"""C13 /v2 Ask WellBe route (WEL-166).

A closed-corpus, non-diagnostic answer engine. The composed answer is grounded
only in the user's own threads + pending items, passes the C10 gate before
release, and falls into first-class modes (answered / no_sources /
out_of_scope_redirect / urgent / blocked). See
docs/decisions/ask-answer-engine-semantics.md.
"""

from __future__ import annotations

from fastapi import APIRouter
from wellbe_contracts.ask import AskAnswerV2, AskMode, AskRequest

from wellbe_api.ask.engine import answer_question
from wellbe_api.deps import PrincipalDep, SessionDep, audit_ref, require_access

router = APIRouter(prefix="/v2", tags=["v2-ask"])

_RESOURCE = "ask_wellbe"

_AUDIT_EVENT = {
    AskMode.ANSWERED: "c13.ask.answered",
    AskMode.NO_SOURCES: "c13.ask.no_sources",
    AskMode.OUT_OF_SCOPE_REDIRECT: "c13.ask.redirected",
    AskMode.URGENT: "c13.ask.urgent",
    AskMode.BLOCKED: "c13.ask.blocked",
}


@router.post("/ask", response_model=AskAnswerV2)
async def ask_wellbe(
    body: AskRequest, principal: PrincipalDep, session: SessionDep
) -> AskAnswerV2:
    await require_access(principal, session, action="read", resource_type=_RESOURCE)

    question = body.question.strip()
    result = await answer_question(
        session=session,
        patient_id=principal.patient_id,
        question=question,
        correlation_id=principal.correlation_id,
    )

    answer_text = "\n".join(s.text for s in result.statements)
    citations = [s.citation for s in result.statements if s.citation is not None]

    await audit_ref(
        session,
        event_type=_AUDIT_EVENT.get(result.mode, "c13.ask.answered"),
        principal=principal,
        summary=f"Ask WellBe: {result.mode.value}",
        extra={"mode": result.mode.value, "citation_count": len(citations)},
    )
    await session.commit()

    return AskAnswerV2(
        query=question,
        mode=result.mode,
        answer_text=answer_text,
        citations=citations,
        next_steps=result.next_steps,
        c10_decision="allow" if result.mode is AskMode.ANSWERED else None,
    )
