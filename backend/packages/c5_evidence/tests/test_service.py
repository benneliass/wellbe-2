from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wellbe_contracts.c5_evidence import (
    ConfidenceBasis,
    EvidenceLinkType,
    EvidenceRef,
)

from wellbe_c5_evidence.service import (
    EvidenceService,
    MissingRawEventError,
    NoEvidenceRefsError,
)


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def service(mock_session):
    return EvidenceService(mock_session)


@pytest.fixture
def valid_evidence_ref():
    return EvidenceRef(
        raw_context_event_id=uuid.uuid4(),
        link_type=EvidenceLinkType.PRIMARY,
        confidence=0.90,
        confidence_basis=ConfidenceBasis.EXTRACTION_MODEL,
    )


class TestLinkFact:
    @pytest.mark.asyncio
    async def test_raises_no_evidence_refs_error_when_empty(
        self, service: EvidenceService
    ):
        with pytest.raises(NoEvidenceRefsError):
            await service.link_fact(
                fact_id=uuid.uuid4(),
                patient_id=uuid.uuid4(),
                evidence_refs=[],
                correlation_id="corr-1",
                trace_id="trace-1",
            )

    @pytest.mark.asyncio
    async def test_raises_missing_raw_event_error(
        self, service: EvidenceService, mock_session, valid_evidence_ref
    ):
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.execute.return_value = mock_result

        with pytest.raises(MissingRawEventError) as exc_info:
            await service.link_fact(
                fact_id=uuid.uuid4(),
                patient_id=uuid.uuid4(),
                evidence_refs=[valid_evidence_ref],
                correlation_id="corr-1",
                trace_id="trace-1",
            )
        assert valid_evidence_ref.raw_context_event_id in exc_info.value.missing_ids

    @pytest.mark.asyncio
    async def test_creates_link_when_event_exists(
        self, service: EvidenceService, mock_session, valid_evidence_ref
    ):
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(
            return_value=iter([(valid_evidence_ref.raw_context_event_id,)])
        )
        mock_session.execute.return_value = mock_result

        link_ids = await service.link_fact(
            fact_id=uuid.uuid4(),
            patient_id=uuid.uuid4(),
            evidence_refs=[valid_evidence_ref],
            correlation_id="corr-1",
            trace_id="trace-1",
        )
        assert len(link_ids) == 1
        assert isinstance(link_ids[0], uuid.UUID)


class TestLinkSignal:
    @pytest.mark.asyncio
    async def test_raises_no_evidence_refs_error_when_empty(
        self, service: EvidenceService
    ):
        with pytest.raises(NoEvidenceRefsError):
            await service.link_signal(
                signal_id=uuid.uuid4(),
                patient_id=uuid.uuid4(),
                evidence_refs=[],
                correlation_id="corr-1",
                trace_id="trace-1",
            )

    @pytest.mark.asyncio
    async def test_creates_links_for_multiple_refs(
        self, service: EvidenceService, mock_session
    ):
        event_id_1 = uuid.uuid4()
        event_id_2 = uuid.uuid4()
        refs = [
            EvidenceRef(
                raw_context_event_id=event_id_1,
                link_type=EvidenceLinkType.PRIMARY,
                confidence=0.85,
            ),
            EvidenceRef(
                raw_context_event_id=event_id_2,
                link_type=EvidenceLinkType.CORROBORATING,
                confidence=0.70,
            ),
        ]

        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(
            return_value=iter([(event_id_1,), (event_id_2,)])
        )
        mock_session.execute.return_value = mock_result

        link_ids = await service.link_signal(
            signal_id=uuid.uuid4(),
            patient_id=uuid.uuid4(),
            evidence_refs=refs,
            correlation_id="corr-1",
            trace_id="trace-1",
        )
        assert len(link_ids) == 2
