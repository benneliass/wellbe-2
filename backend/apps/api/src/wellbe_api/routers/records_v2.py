"""C13 /v2 personal records reads: Results and Documents.

Self-scoped, read-only views over the caller's own C2 captures and C4 extracted
facts, backing the web Results and Documents screens. Values, units, and
reference ranges are passed through exactly as the source gave them; see
``wellbe_api.records.engine`` for the (literal, non-diagnostic) range comparison
and the derived document processing state.
"""

from __future__ import annotations

from fastapi import APIRouter
from wellbe_contracts.records import DocumentsResponseV2, ResultsResponseV2

from wellbe_api.deps import PrincipalDep, SessionDep, audit_ref, require_access
from wellbe_api.records.engine import load_documents, load_results

router = APIRouter(prefix="/v2", tags=["v2-records"])

_RESOURCE = "raw_context"


@router.get("/results", response_model=ResultsResponseV2)
async def get_results(principal: PrincipalDep, session: SessionDep) -> ResultsResponseV2:
    await require_access(principal, session, action="read", resource_type=_RESOURCE)

    result = await load_results(session=session, patient_id=principal.patient_id)

    await audit_ref(
        session,
        event_type="c13.results.read",
        principal=principal,
        summary="Results (lab/vital observations) read",
        extra={"analyte_count": len(result.analytes)},
    )
    await session.commit()
    return result


@router.get("/documents", response_model=DocumentsResponseV2)
async def get_documents(principal: PrincipalDep, session: SessionDep) -> DocumentsResponseV2:
    await require_access(principal, session, action="read", resource_type=_RESOURCE)

    result = await load_documents(session=session, patient_id=principal.patient_id)

    await audit_ref(
        session,
        event_type="c13.documents.read",
        principal=principal,
        summary="Uploaded documents read",
        extra={"document_count": len(result.documents)},
    )
    await session.commit()
    return result
