from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from wellbe_c4_processing.models import ExtractedFactRow, HealthSignalRow


class ProcessingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_fact(
        self,
        *,
        id: uuid.UUID,
        patient_id: uuid.UUID,
        raw_context_event_id: uuid.UUID,
        fact_type: str,
        entity_label: str,
        normalized_key: str,
        extraction_confidence: float,
        extraction_model: str,
        model_version: str,
        pipeline_version: str,
        quality_flag: str,
        captured_at: datetime,
        correlation_id: str,
        trace_id: str,
        code_system: str | None = None,
        code: str | None = None,
        text_span_start: int | None = None,
        text_span_end: int | None = None,
        source_text_excerpt_hash: str | None = None,
        quality_metadata: dict | None = None,
        is_negated: bool = False,
        is_historical: bool = False,
        is_hypothetical: bool = False,
        subject: str = "patient",
    ) -> uuid.UUID:
        now = datetime.now(timezone.utc)
        row = ExtractedFactRow(
            id=id,
            patient_id=patient_id,
            raw_context_event_id=raw_context_event_id,
            fact_type=fact_type,
            entity_label=entity_label,
            normalized_key=normalized_key,
            extraction_confidence=extraction_confidence,
            extraction_model=extraction_model,
            model_version=model_version,
            pipeline_version=pipeline_version,
            quality_flag=quality_flag,
            quality_metadata=quality_metadata,
            is_negated=is_negated,
            is_historical=is_historical,
            is_hypothetical=is_hypothetical,
            subject=subject,
            captured_at=captured_at,
            extracted_at=now,
            correlation_id=correlation_id,
            trace_id=trace_id,
            schema_version=1,
            created_at=now,
            code_system=code_system,
            code=code,
            text_span_start=text_span_start,
            text_span_end=text_span_end,
            source_text_excerpt_hash=source_text_excerpt_hash,
        )
        self._session.add(row)
        await self._session.flush()
        return row.id

    async def insert_signal(
        self,
        *,
        id: uuid.UUID,
        patient_id: uuid.UUID,
        raw_context_event_ids: list[uuid.UUID],
        signal_type: str,
        signal_value: float,
        extraction_confidence: float,
        extraction_model: str,
        model_version: str,
        pipeline_version: str,
        quality_flag: str,
        captured_at_start: datetime,
        captured_at_end: datetime,
        correlation_id: str,
        trace_id: str,
        signal_unit: str | None = None,
        signal_direction: str | None = None,
        aggregation_method: str | None = None,
        observation_window: str | None = None,
        quality_metadata: dict | None = None,
    ) -> uuid.UUID:
        now = datetime.now(timezone.utc)
        row = HealthSignalRow(
            id=id,
            patient_id=patient_id,
            raw_context_event_ids=raw_context_event_ids,
            signal_type=signal_type,
            signal_value=signal_value,
            signal_unit=signal_unit,
            signal_direction=signal_direction,
            aggregation_method=aggregation_method,
            observation_window=observation_window,
            extraction_confidence=extraction_confidence,
            extraction_model=extraction_model,
            model_version=model_version,
            pipeline_version=pipeline_version,
            quality_flag=quality_flag,
            quality_metadata=quality_metadata,
            captured_at_start=captured_at_start,
            captured_at_end=captured_at_end,
            extracted_at=now,
            correlation_id=correlation_id,
            trace_id=trace_id,
            schema_version=1,
            created_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row.id
