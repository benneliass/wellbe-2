"""C16 External Evidence + Research Relevance service.

Two responsibilities:
  * WEL-116 External Evidence Graph: register external sources/claims in
    ``external_kg.*`` (NO patient_id, never a personal fact) and maintain the
    editorial source-quality tier (usage NEVER upgrades a tier).
  * WEL-117 Research Relevance engine: link a personal fact to external context
    via ``external_bridge.relevance_links`` ONLY — context-only by construction.

Hard invariants (decision G1/G2): this service never writes ``graph.kg_edges``
and never asserts an external claim as a fact about the user. ``relevance_score``
is topical relatedness, separate from C5/C6 ``potential_score``.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_contracts.c16_external import (
    EXTERNAL_CLAIM_REGISTERED,
    EXTERNAL_SOURCE_REGISTERED,
    RELEVANCE_LINK_CREATED,
    RELEVANCE_SCORE_VERSION,
    SOURCE_TIER_REVIEWED,
    ExternalClaim,
    ExternalClaimKind,
    ExternalSource,
    ExternalSourceType,
    RelevanceLinkCreatedPayload,
    RelevanceLinkResult,
    RelevanceScoreInputs,
    RetractionStatus,
)
from wellbe_events import emit_event

from wellbe_c16_external.errors import (
    ExternalSourceNotFoundError,
    PersonalNodeNotFoundError,
)
from wellbe_c16_external.repository import ExternalEvidenceRepository
from wellbe_c16_external.scoring import compute_relevance_score


class ExternalEvidenceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ExternalEvidenceRepository(session)

    async def register_source(
        self,
        *,
        source_type: ExternalSourceType,
        source_quality_tier: int,
        tier_reason: str,
        title: str,
        assigned_by: str,
        correlation_id: str,
        trace_id: str,
        citation_text: str | None = None,
        url: str | None = None,
        doi: str | None = None,
        publisher: str | None = None,
        source_metadata: dict | None = None,
    ) -> ExternalSource:
        row = await self._repo.create_source(
            source_type=source_type.value,
            source_quality_tier=source_quality_tier,
            tier_reason=tier_reason,
            title=title,
            assigned_by=assigned_by,
            citation_text=citation_text,
            url=url,
            doi=doi,
            publisher=publisher,
            source_metadata=source_metadata,
        )
        await emit_event(
            session=self._session,
            event_type=EXTERNAL_SOURCE_REGISTERED,
            payload={
                "schema_version": 1,
                "external_source_id": str(row.id),
                "source_type": source_type.value,
                "source_quality_tier": source_quality_tier,
                "correlation_id": correlation_id,
                "trace_id": trace_id,
            },
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
        return ExternalSource(
            id=row.id,
            source_type=source_type,
            source_quality_tier=source_quality_tier,
            tier_reason=tier_reason,
            title=title,
            citation_text=citation_text,
            url=url,
            doi=doi,
            publisher=publisher,
            retraction_status=RetractionStatus.NOT_RETRACTED,
        )

    async def register_claim(
        self,
        *,
        source_id: uuid.UUID,
        claim_text: str,
        claim_kind: ExternalClaimKind,
        correlation_id: str,
        trace_id: str,
        population_context: dict | None = None,
        evidence_attributes: dict | None = None,
    ) -> ExternalClaim:
        source = await self._repo.get_source(source_id)
        if source is None:
            raise ExternalSourceNotFoundError(source_id)
        row = await self._repo.create_claim(
            source_id=source_id,
            claim_text=claim_text,
            claim_kind=claim_kind.value,
            population_context=population_context,
            evidence_attributes=evidence_attributes,
        )
        await emit_event(
            session=self._session,
            event_type=EXTERNAL_CLAIM_REGISTERED,
            payload={
                "schema_version": 1,
                "external_claim_id": str(row.id),
                "external_source_id": str(source_id),
                "claim_kind": claim_kind.value,
                "correlation_id": correlation_id,
                "trace_id": trace_id,
            },
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
        return ExternalClaim(
            id=row.id,
            source_id=source_id,
            claim_text=claim_text,
            claim_kind=claim_kind,
        )

    async def link_relevance(
        self,
        *,
        patient_id: uuid.UUID,
        personal_node_id: uuid.UUID,
        external_source_id: uuid.UUID,
        relevance_inputs: RelevanceScoreInputs,
        correlation_id: str,
        trace_id: str,
        external_claim_id: uuid.UUID | None = None,
        thread_id: uuid.UUID | None = None,
        created_by_actor_id: uuid.UUID | None = None,
        created_under_grant_id: uuid.UUID | None = None,
    ) -> RelevanceLinkResult:
        """Create the ONLY allowed personal<->external connection (context only).

        Tier is SNAPSHOTTED from the source at link time; the score is topical
        relatedness only. Never writes to graph.kg_edges.
        """
        node = await self._repo.get_personal_node(personal_node_id)
        if node is None:
            raise PersonalNodeNotFoundError(personal_node_id)
        source = await self._repo.get_source(external_source_id)
        if source is None:
            raise ExternalSourceNotFoundError(external_source_id)

        score = compute_relevance_score(relevance_inputs)
        tier_snapshot = source.source_quality_tier

        row = await self._repo.create_relevance_link(
            patient_id=patient_id,
            personal_node_id=personal_node_id,
            external_source_id=external_source_id,
            external_claim_id=external_claim_id,
            relevance_score=score,
            relevance_score_version=RELEVANCE_SCORE_VERSION,
            relevance_inputs=relevance_inputs.model_dump(),
            source_quality_tier_snapshot=tier_snapshot,
            thread_id=thread_id,
            created_by_actor_id=created_by_actor_id,
            created_under_grant_id=created_under_grant_id,
        )

        event_id = await emit_event(
            session=self._session,
            event_type=RELEVANCE_LINK_CREATED,
            payload=RelevanceLinkCreatedPayload(
                relevance_link_id=row.id,
                patient_id=patient_id,
                personal_node_id=personal_node_id,
                external_source_id=external_source_id,
                external_claim_id=external_claim_id,
                relevance_score=score,
                relevance_score_version=RELEVANCE_SCORE_VERSION,
                source_quality_tier_snapshot=tier_snapshot,
                correlation_id=correlation_id,
                trace_id=trace_id,
            ).model_dump(mode="json"),
            correlation_id=correlation_id,
            trace_id=trace_id,
        )

        return RelevanceLinkResult(
            relevance_link_id=row.id,
            patient_id=patient_id,
            personal_node_id=personal_node_id,
            external_source_id=external_source_id,
            external_claim_id=external_claim_id,
            relevance_score=score,
            relevance_score_version=RELEVANCE_SCORE_VERSION,
            source_quality_tier_snapshot=tier_snapshot,
            context_only=True,
            event_id=event_id,
        )

    async def list_context_for_node(
        self, *, patient_id: uuid.UUID, personal_node_id: uuid.UUID
    ) -> list[RelevanceLinkResult]:
        rows = await self._repo.list_relevance_links_for_node(
            patient_id=patient_id, personal_node_id=personal_node_id
        )
        return [
            RelevanceLinkResult(
                relevance_link_id=r.id,
                patient_id=r.patient_id,
                personal_node_id=r.personal_node_id,
                external_source_id=r.external_source_id,
                external_claim_id=r.external_claim_id,
                relevance_score=float(r.relevance_score),
                relevance_score_version=r.relevance_score_version,
                source_quality_tier_snapshot=r.source_quality_tier_snapshot,
                context_only=r.context_only,
            )
            for r in rows
        ]

    async def review_source_tier(
        self,
        *,
        source_id: uuid.UUID,
        new_tier: int,
        reason: str,
        reviewer_actor_id: uuid.UUID,
        correlation_id: str,
        trace_id: str,
    ) -> None:
        """Editorial tier change ONLY. Usage can never upgrade a tier.

        Records an auditable review row and updates the source tier in place.
        """
        source = await self._repo.get_source(source_id)
        if source is None:
            raise ExternalSourceNotFoundError(source_id)
        previous_tier = source.source_quality_tier
        await self._repo.record_tier_review(
            source_id=source_id,
            previous_tier=previous_tier,
            new_tier=new_tier,
            reason=reason,
            reviewer_actor_id=reviewer_actor_id,
        )
        source.source_quality_tier = new_tier
        await self._session.flush()
        await emit_event(
            session=self._session,
            event_type=SOURCE_TIER_REVIEWED,
            payload={
                "schema_version": 1,
                "external_source_id": str(source_id),
                "previous_tier": previous_tier,
                "new_tier": new_tier,
                "reason": reason,
                "correlation_id": correlation_id,
                "trace_id": trace_id,
            },
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
