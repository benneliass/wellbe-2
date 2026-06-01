"""C16 External Evidence Graph + Research Relevance contracts.

External medical knowledge is *context, never fact about the user* (G1/G2).
External sources/claims live in ``external_kg.*`` and connect to personal facts
ONLY via ``external_bridge.relevance_links`` — a patient-scoped, context-only,
RLS-protected bridge. ``relevance_score`` is topical relatedness, kept strictly
separate from C5/C6 ``potential_score`` (diagnostic/evidential confidence).
``source_quality_tier`` is editorial (Tier 1-5) and is NEVER usage-derived.

Authoritative decision: docs/decisions/external-evidence-graph-separation.md
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from wellbe_contracts.primitives import AwareDatetime, PatientId

# ---------------------------------------------------------------------------
# Event type constants (v1)
# ---------------------------------------------------------------------------

EXTERNAL_SOURCE_REGISTERED = "external.source_registered.v1"
EXTERNAL_CLAIM_REGISTERED = "external.claim_registered.v1"
RELEVANCE_LINK_CREATED = "external.relevance_link_created.v1"
SOURCE_TIER_REVIEWED = "external.source_tier_reviewed.v1"

RELEVANCE_SCORE_VERSION = "relevance-v1"

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ExternalSourceType(StrEnum):
    CLINICAL_GUIDELINE = "clinical_guideline"
    OFFICIAL_BODY = "official_body"
    SYSTEMATIC_REVIEW = "systematic_review"
    PEER_REVIEWED_PAPER = "peer_reviewed_paper"
    CASE_REPORT = "case_report"
    EARLY_RESEARCH = "early_research"
    MEDICAL_BLOG = "medical_blog"
    EXPERT_EXPLAINER = "expert_explainer"
    FORUM_POST = "forum_post"
    ANECDOTE = "anecdote"
    SOCIAL_POST = "social_post"


class RetractionStatus(StrEnum):
    NOT_RETRACTED = "not_retracted"
    EXPRESSION_OF_CONCERN = "expression_of_concern"
    RETRACTED = "retracted"
    SUPERSEDED = "superseded"


class ExternalClaimKind(StrEnum):
    ASSOCIATION = "association"
    RISK_FACTOR = "risk_factor"
    MECHANISM = "mechanism"
    CONTRAINDICATION = "contraindication"
    GUIDELINE_RECOMMENDATION = "guideline_recommendation"
    EDUCATIONAL_CONTEXT = "educational_context"
    ANECDOTE = "anecdote"


# Editorial source-quality tier (1 = strongest evidence, 5 = weakest/anecdote).
# Never usage-derived; only auditable editorial review can change it.
SOURCE_QUALITY_TIERS: frozenset[int] = frozenset({1, 2, 3, 4, 5})

# ---------------------------------------------------------------------------
# Relevance scoring (v1) — topical relatedness only, NOT diagnostic confidence.
# weights sum to 1.0; tier drives surfacing caps/labels, not relatedness.
# ---------------------------------------------------------------------------

RELEVANCE_WEIGHTS: dict[str, float] = {
    "entity_or_code_match": 0.35,
    "semantic_similarity": 0.25,
    "thread_context_match": 0.15,
    "population_applicability": 0.10,
    "source_currentness": 0.10,
    "reviewer_user_signal": 0.05,
}


class RelevanceScoreInputs(BaseModel):
    """Per-signal inputs in [0, 1]. The weighted sum is the relevance_score."""

    entity_or_code_match: float = Field(0.0, ge=0.0, le=1.0)
    semantic_similarity: float = Field(0.0, ge=0.0, le=1.0)
    thread_context_match: float = Field(0.0, ge=0.0, le=1.0)
    population_applicability: float = Field(0.0, ge=0.0, le=1.0)
    source_currentness: float = Field(0.0, ge=0.0, le=1.0)
    reviewer_user_signal: float = Field(0.0, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


class ExternalSource(BaseModel):
    id: UUID
    source_type: ExternalSourceType
    source_quality_tier: int = Field(ge=1, le=5)
    tier_reason: str
    title: str
    citation_text: str | None = None
    url: str | None = None
    doi: str | None = None
    publisher: str | None = None
    retraction_status: RetractionStatus = RetractionStatus.NOT_RETRACTED


class ExternalClaim(BaseModel):
    id: UUID
    source_id: UUID
    claim_text: str
    claim_kind: ExternalClaimKind


class RelevanceLinkResult(BaseModel):
    """Result of linking a personal fact to external context. Context only."""

    relevance_link_id: UUID
    patient_id: PatientId
    personal_node_id: UUID
    external_source_id: UUID
    external_claim_id: UUID | None
    relevance_score: float
    relevance_score_version: str
    source_quality_tier_snapshot: int = Field(ge=1, le=5)
    context_only: bool = True
    created_at: AwareDatetime | None = None
    event_id: UUID | None = None


# ---------------------------------------------------------------------------
# Event payloads
# ---------------------------------------------------------------------------


class RelevanceLinkCreatedPayload(BaseModel):
    schema_version: int = 1
    relevance_link_id: UUID
    patient_id: PatientId
    personal_node_id: UUID
    external_source_id: UUID
    external_claim_id: UUID | None = None
    relevance_score: float
    relevance_score_version: str
    source_quality_tier_snapshot: int
    context_only: bool = True
    correlation_id: str
    trace_id: str


__all__ = [
    "EXTERNAL_SOURCE_REGISTERED",
    "EXTERNAL_CLAIM_REGISTERED",
    "RELEVANCE_LINK_CREATED",
    "SOURCE_TIER_REVIEWED",
    "RELEVANCE_SCORE_VERSION",
    "RELEVANCE_WEIGHTS",
    "SOURCE_QUALITY_TIERS",
    "ExternalSourceType",
    "RetractionStatus",
    "ExternalClaimKind",
    "RelevanceScoreInputs",
    "ExternalSource",
    "ExternalClaim",
    "RelevanceLinkResult",
    "RelevanceLinkCreatedPayload",
]
