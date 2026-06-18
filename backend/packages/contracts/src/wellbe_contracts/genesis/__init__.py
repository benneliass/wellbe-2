"""Thread genesis contracts (continuity/triage genesis capability).

Genesis is the continuity/triage step that turns C4 facts + C6 resolution into
exactly one durable outcome per health-relevant input: attach to a thread, create
a thread, create/update a pending candidate, or record no-thread-with-reason.

Authoritative decisions:
- docs/decisions/thread-genesis-from-capture.md (WEL-170)
- docs/decisions/thread-genesis-triage-decision-contract.md (WEL-171, S1)
- docs/decisions/thread-genesis-concern-resolution-key.md (WEL-171, S3)
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from wellbe_contracts.primitives import AwareDatetime, EventId, PatientId

# ---------------------------------------------------------------------------
# Event type constants
# ---------------------------------------------------------------------------

# Synthetic event emitted only after, for a capture: capture write completed,
# fact extraction completed, graph/entity resolution attempted, and evidence
# references are available. This — not raw fact.extracted, not graph.cluster_updated
# — is the genesis trigger (triage-decision-contract.md §1).
GENESIS_INPUT_READY = "genesis.input_ready"

# The triage policy version that produced a decision. A re-evaluation under a new
# policy version writes a NEW decision record that supersedes the prior one rather
# than mutating it (append-only ledger).
GENESIS_POLICY_VERSION = 1

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class GenesisDecision(StrEnum):
    """The exactly-one durable outcome genesis produces per health-relevant input.

    The default for an uncertain but health-relevant signal is
    ``CREATE_OR_UPDATE_PENDING_CANDIDATE`` — never auto-thread (would alarm) and
    never ``NO_THREAD_WITH_REASON`` (would silently lose a real signal).
    ``NO_THREAD_WITH_REASON`` is reserved for inputs evaluated and found NOT
    concern-forming.
    """

    ATTACH_TO_EXISTING_THREAD = "attach"
    CREATE_NEW_THREAD = "create"
    CREATE_OR_UPDATE_PENDING_CANDIDATE = "candidate"
    NO_THREAD_WITH_REASON = "no_thread"


class ConcernType(StrEnum):
    """Coarse concern category — part of the concern resolution key."""

    SYMPTOM = "symptom"
    CONDITION = "condition"
    LAB_ABNORMALITY = "lab_abnormality"
    MEDICATION_ISSUE = "medication_issue"
    CARE_GAP = "care_gap"
    FOLLOW_UP_TASK = "follow_up_task"
    QUESTION_OR_WORRY = "question_or_worry"
    PROCEDURE_OR_TEST = "procedure_or_test"
    VISIT_PREPARATION = "visit_preparation"
    OTHER = "other"


class SourceContextClass(StrEnum):
    """How the concern was surfaced — distinguishes meaning for the key."""

    SYMPTOM_MENTION = "symptom_mention"
    LAB_ABNORMALITY = "lab_abnormality"
    CLINICIAN_INSTRUCTION = "clinician_instruction"
    MEDICATION_ISSUE = "medication_issue"
    USER_NOTE = "user_note"
    IMPORT = "import"
    OTHER = "other"


class GraphResolutionStatus(StrEnum):
    """Whether C6 entity resolution was available when genesis ran.

    Genesis is NOT blocked when resolution is weak; the concern key falls back to
    a deterministic MVP normalization and may be reconciled as C6 matures.
    """

    RESOLVED = "resolved"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class CandidateStatus(StrEnum):
    """Lifecycle of a pending thread candidate.

    ``pending``    — visible under "Things noticed", not yet an active thread;
    ``promoted``   — confirmed/auto-promoted into a C7 thread (``promoted_thread_id``);
    ``dismissed``  — user stopped tracking (evidence + triage history preserved);
    ``merged``     — folded into another thread/candidate;
    ``expired``    — aged out (post-MVP expiry policy).
    """

    PENDING = "pending"
    PROMOTED = "promoted"
    DISMISSED = "dismissed"
    MERGED = "merged"
    EXPIRED = "expired"


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------


class ConcernKey(BaseModel):
    """User-scoped dedup key. Stable enough to dedup, not so specific it fragments.

    Excludes ``capture_id`` and ``fact_id`` by design — those belong in the
    decision record and evidence records, not the dedup key
    (concern-resolution-key.md §2).
    """

    model_config = ConfigDict(frozen=True)

    user_id: PatientId
    concern_type: ConcernType
    normalized_concept_id: str
    body_site: str | None = None
    laterality: str | None = None
    episode_bucket: str
    source_context_class: SourceContextClass


class GenesisFactInput(BaseModel):
    """One C4 fact (+ optional C6 resolution) considered by genesis for a capture."""

    fact_id: UUID
    raw_context_event_id: EventId
    fact_type: str
    entity_label: str
    normalized_key: str
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    # C6 resolution (nullable — genesis runs even when resolution is weak).
    graph_node_id: UUID | None = None
    graph_cluster_id: UUID | None = None
    normalized_concept_id: str | None = None
    # Optional clinical qualifiers when extraction provides them.
    body_site: str | None = None
    laterality: str | None = None
    # Event/onset date preferred over ingestion time for episode bucketing.
    event_date: AwareDatetime | None = None
    is_negated: bool = False
    is_historical: bool = False
    is_hypothetical: bool = False
    # True only when a clinical source explicitly flagged this lab/vital as
    # abnormal/out-of-range. Used by the genesis auto-create policy: a thread is
    # auto-opened only for clinically-asserted concerns (clinician diagnosis/
    # instruction, or an explicitly-flagged-abnormal lab), never for an
    # ordinary symptom mention (which routes to a candidate).
    abnormal_flag: bool = False


class GenesisInputReadyPayload(BaseModel):
    """Payload for the ``genesis.input_ready`` outbox event consumed by genesis."""

    schema_version: int = 1
    patient_id: PatientId
    capture_id: EventId
    source_event_id: EventId
    captured_at: AwareDatetime
    facts: list[GenesisFactInput] = Field(default_factory=list)
    graph_resolution_status: GraphResolutionStatus = GraphResolutionStatus.UNAVAILABLE
    correlation_id: str
    trace_id: str


class GenesisDecisionRecord(BaseModel):
    """Read model for one append-only triage decision record (the genesis ledger).

    Carries exactly the fields decided in triage-decision-contract.md §3. The
    record is append-only and idempotent on ``decision_inputs_hash``; an intentional
    re-evaluation under a new ``policy_version`` writes a new record with
    ``supersedes_decision_id`` set.
    """

    model_config = ConfigDict(from_attributes=True)

    decision_id: UUID
    user_id: PatientId
    source_event_id: EventId
    capture_id: EventId
    fact_ids: list[UUID] = Field(default_factory=list)
    graph_node_id: UUID | None = None
    graph_cluster_id: UUID | None = None
    concern_key: dict[str, object] = Field(default_factory=dict)
    episode_bucket: str
    decision: GenesisDecision
    reason_code: str
    confidence: float | None = None
    policy_version: int
    target_thread_id: UUID | None = None
    candidate_id: UUID | None = None
    created_thread_id: UUID | None = None
    evidence_link_ids: list[UUID] = Field(default_factory=list)
    decision_inputs_hash: str
    created_at: AwareDatetime
    supersedes_decision_id: UUID | None = None
    idempotent_replay: bool = False


class ThreadCandidate(BaseModel):
    """Read model for a pending thread candidate (the "Things noticed" object).

    A candidate is the non-alarming, lossless destination for weak/ambiguous
    concern-bearing signals. Create/update is idempotent on the concern key +
    episode bucket (NOT the source event), so repeated mentions of one concern
    update the same candidate (``seen_count`` increments) rather than fragmenting.
    Minimal MVP contract per thread-genesis-pending-candidate-object.md (S2a).
    """

    model_config = ConfigDict(from_attributes=True)

    candidate_id: UUID
    user_id: PatientId
    concern_key: dict[str, object] = Field(default_factory=dict)
    episode_bucket: str
    display_title: str
    candidate_type: ConcernType
    source_capture_ids: list[UUID] = Field(default_factory=list)
    source_fact_ids: list[UUID] = Field(default_factory=list)
    source_graph_entity_ids: list[UUID] = Field(default_factory=list)
    evidence_link_ids: list[UUID] = Field(default_factory=list)
    status: CandidateStatus = CandidateStatus.PENDING
    confidence: float | None = None
    reason_code: str | None = None
    first_seen_at: AwareDatetime
    last_seen_at: AwareDatetime
    seen_count: int = 1
    promoted_thread_id: UUID | None = None
    created_at: AwareDatetime
    updated_at: AwareDatetime


__all__ = [
    # Event type constants
    "GENESIS_INPUT_READY",
    "GENESIS_POLICY_VERSION",
    # Enums
    "GenesisDecision",
    "ConcernType",
    "SourceContextClass",
    "GraphResolutionStatus",
    "CandidateStatus",
    # Core types
    "ConcernKey",
    "GenesisFactInput",
    "GenesisInputReadyPayload",
    "GenesisDecisionRecord",
    "ThreadCandidate",
]
