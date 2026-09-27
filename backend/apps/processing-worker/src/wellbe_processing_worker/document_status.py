"""Stored document processing status transitions (processing.document_processing_status).

The vault writer inserts ``received``; the raw-context handler moves a document
to ``processing`` when it picks it up, then to ``processed`` (facts stored),
``needs_ocr`` (no readable text) or ``failed`` (the attempt raised; the outbox
retries it). Every write commits in its own session so a status survives the
rollback of a failed work session. Writes are best-effort: a status that cannot
be written is logged and never blocks extraction.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from typing import Any, Protocol

from wellbe_contracts.c4_processing import DocumentProcessingStatus

logger = logging.getLogger(__name__)

DOCUMENT_SOURCE_TYPES = frozenset({"pdf", "photo"})


def is_document(vault_event: dict[str, Any]) -> bool:
    meta = vault_event.get("source_metadata") or {}
    return (
        vault_event.get("source_type") in DOCUMENT_SOURCE_TYPES
        or meta.get("capture_type") == "document"
    )


class DocumentStatusTracker(Protocol):
    async def mark(
        self,
        event_id: uuid.UUID,
        patient_id: uuid.UUID,
        status: DocumentProcessingStatus,
        *,
        detail: str | None = None,
        new_attempt: bool = False,
    ) -> None: ...

    async def finish(
        self, event_id: uuid.UUID, patient_id: uuid.UUID, *, detail_if_empty: str
    ) -> DocumentProcessingStatus: ...


class DbDocumentStatusTracker:
    def __init__(self, session_factory: Callable[[], Any]) -> None:
        self._session_factory = session_factory

    async def mark(
        self,
        event_id: uuid.UUID,
        patient_id: uuid.UUID,
        status: DocumentProcessingStatus,
        *,
        detail: str | None = None,
        new_attempt: bool = False,
    ) -> None:
        from wellbe_c4_processing import ProcessingRepository

        try:
            async with self._session_factory() as session:
                await ProcessingRepository(session).set_document_status(
                    raw_context_event_id=event_id,
                    patient_id=patient_id,
                    status=status,
                    detail=detail,
                    new_attempt=new_attempt,
                )
                await session.commit()
        except Exception:
            logger.exception("document %s: could not store status %s", event_id, status.value)

    async def finish(
        self, event_id: uuid.UUID, patient_id: uuid.UUID, *, detail_if_empty: str
    ) -> DocumentProcessingStatus:
        """Terminal status from what was stored: facts -> processed, none -> needs_ocr."""
        from wellbe_c4_processing import ProcessingRepository

        facts = 0
        try:
            async with self._session_factory() as session:
                facts = await ProcessingRepository(session).count_facts_for_capture(event_id)
        except Exception:
            logger.exception("document %s: could not count facts", event_id)
            return DocumentProcessingStatus.PROCESSING
        status = (
            DocumentProcessingStatus.PROCESSED if facts > 0 else DocumentProcessingStatus.NEEDS_OCR
        )
        await self.mark(
            event_id, patient_id, status, detail=None if facts > 0 else detail_if_empty
        )
        return status


def default_tracker() -> DbDocumentStatusTracker:
    from wellbe_db import create_engine, create_session_factory

    from wellbe_processing_worker.config import ProcessingWorkerSettings

    settings = ProcessingWorkerSettings()
    return DbDocumentStatusTracker(create_session_factory(create_engine(settings.database_url)))
