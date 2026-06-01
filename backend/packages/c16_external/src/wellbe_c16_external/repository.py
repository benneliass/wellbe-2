from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_c6_graph.external import ExternalEvidenceSourceRow, RelevanceLinkRow
from wellbe_c6_graph.models import KgNodeRow

from wellbe_c16_external.models import ExternalClaimRow, SourceQualityReviewRow


def _naive_utcnow() -> datetime:
    # external_kg.* / external_bridge.* timestamp columns are written naive-UTC
    # to match the rest of the graph schema convention.
    return datetime.now(UTC).replace(tzinfo=None)


class ExternalEvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_source(
        self,
        *,
        source_type: str,
        source_quality_tier: int,
        tier_reason: str,
        title: str,
        assigned_by: str,
        citation_text: str | None = None,
        url: str | None = None,
        doi: str | None = None,
        publisher: str | None = None,
        source_metadata: dict | None = None,
    ) -> ExternalEvidenceSourceRow:
        now = _naive_utcnow()
        row = ExternalEvidenceSourceRow(
            id=uuid.uuid4(),
            source_type=source_type,
            source_quality_tier=source_quality_tier,
            tier_reason=tier_reason,
            title=title,
            citation_text=citation_text,
            url=url,
            doi=doi,
            publisher=publisher,
            retraction_status="not_retracted",
            assigned_by=assigned_by,
            assigned_at=now,
            source_metadata=source_metadata,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_source(self, source_id: uuid.UUID) -> ExternalEvidenceSourceRow | None:
        stmt = select(ExternalEvidenceSourceRow).where(ExternalEvidenceSourceRow.id == source_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def create_claim(
        self,
        *,
        source_id: uuid.UUID,
        claim_text: str,
        claim_kind: str,
        population_context: dict | None = None,
        evidence_attributes: dict | None = None,
    ) -> ExternalClaimRow:
        row = ExternalClaimRow(
            id=uuid.uuid4(),
            source_id=source_id,
            claim_text=claim_text,
            claim_kind=claim_kind,
            population_context=population_context,
            evidence_attributes=evidence_attributes,
            created_at=_naive_utcnow(),
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_personal_node(self, node_id: uuid.UUID) -> KgNodeRow | None:
        stmt = select(KgNodeRow).where(KgNodeRow.id == node_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def create_relevance_link(
        self,
        *,
        patient_id: uuid.UUID,
        personal_node_id: uuid.UUID,
        external_source_id: uuid.UUID,
        external_claim_id: uuid.UUID | None,
        relevance_score: float,
        relevance_score_version: str,
        relevance_inputs: dict,
        source_quality_tier_snapshot: int,
        thread_id: uuid.UUID | None,
        created_by_actor_id: uuid.UUID | None,
        created_under_grant_id: uuid.UUID | None,
    ) -> RelevanceLinkRow:
        row = RelevanceLinkRow(
            id=uuid.uuid4(),
            patient_id=patient_id,
            personal_node_id=personal_node_id,
            thread_id=thread_id,
            external_source_id=external_source_id,
            external_claim_id=external_claim_id,
            edge_type="relevance_link",
            relevance_score=Decimal(str(round(relevance_score, 4))),
            relevance_score_version=relevance_score_version,
            relevance_inputs=relevance_inputs,
            source_quality_tier_snapshot=source_quality_tier_snapshot,
            context_only=True,
            created_by_actor_id=created_by_actor_id,
            created_under_grant_id=created_under_grant_id,
            created_at=_naive_utcnow(),
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_relevance_links_for_node(
        self, *, patient_id: uuid.UUID, personal_node_id: uuid.UUID
    ) -> list[RelevanceLinkRow]:
        stmt = (
            select(RelevanceLinkRow)
            .where(
                RelevanceLinkRow.patient_id == patient_id,
                RelevanceLinkRow.personal_node_id == personal_node_id,
            )
            .order_by(RelevanceLinkRow.relevance_score.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def record_tier_review(
        self,
        *,
        source_id: uuid.UUID,
        previous_tier: int | None,
        new_tier: int,
        reason: str,
        reviewer_actor_id: uuid.UUID,
    ) -> SourceQualityReviewRow:
        row = SourceQualityReviewRow(
            id=uuid.uuid4(),
            source_id=source_id,
            previous_tier=previous_tier,
            new_tier=new_tier,
            reason=reason,
            reviewer_actor_id=reviewer_actor_id,
            reviewed_at=_naive_utcnow(),
        )
        self._session.add(row)
        await self._session.flush()
        return row
