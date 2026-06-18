"""Concern resolution key derivation, idempotency hashing, and the B0 classifier.

Implements the approved concern-key contract
(docs/decisions/thread-genesis-concern-resolution-key.md): a user-scoped key that
is stable enough to dedup without being so specific that every mention fragments.
``capture_id`` / ``fact_id`` are deliberately excluded from the key.

The classifier here is the B0 *skeleton*: it records the decided safe defaults
(uncertain-but-health-relevant -> candidate; clearly non-concern -> no-thread).
The high-confidence auto-create classification (attach / create) is layered on in
Story B1.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime

from wellbe_contracts.genesis import (
    GENESIS_POLICY_VERSION,
    ConcernKey,
    ConcernType,
    GenesisDecision,
    GenesisFactInput,
    SourceContextClass,
)

# C4 fact_type -> coarse concern_type for the key.
_FACT_TYPE_TO_CONCERN_TYPE: dict[str, ConcernType] = {
    "symptom": ConcernType.SYMPTOM,
    "finding": ConcernType.CONDITION,
    "dx_mention": ConcernType.CONDITION,
    "lab_result": ConcernType.LAB_ABNORMALITY,
    "vital_sign": ConcernType.LAB_ABNORMALITY,
    "medication": ConcernType.MEDICATION_ISSUE,
    "allergy": ConcernType.MEDICATION_ISSUE,
    "procedure": ConcernType.PROCEDURE_OR_TEST,
    "immunization": ConcernType.PROCEDURE_OR_TEST,
}

# C4 fact_type -> how the concern was surfaced.
_FACT_TYPE_TO_SOURCE_CONTEXT: dict[str, SourceContextClass] = {
    "symptom": SourceContextClass.SYMPTOM_MENTION,
    "finding": SourceContextClass.SYMPTOM_MENTION,
    "dx_mention": SourceContextClass.CLINICIAN_INSTRUCTION,
    "lab_result": SourceContextClass.LAB_ABNORMALITY,
    "vital_sign": SourceContextClass.LAB_ABNORMALITY,
    "medication": SourceContextClass.MEDICATION_ISSUE,
    "allergy": SourceContextClass.MEDICATION_ISSUE,
}

# Fact types that, on their own, are not active concerns to track.
_NON_CONCERN_FACT_TYPES: frozenset[str] = frozenset(
    {"other", "family_history", "social_history"}
)


def _episode_bucket(when: datetime) -> str:
    """Bucket an episode by calendar month of the event/onset date.

    Per the concern-key decision, prefer event/onset date over ingestion time so a
    backdated or late-logged mention groups into the correct episode.
    """
    return f"{when.year:04d}-{when.month:02d}"


def derive_concern_key(
    *,
    user_id: uuid.UUID,
    fact: GenesisFactInput,
    captured_at: datetime,
) -> ConcernKey:
    """Derive the user-scoped concern resolution key for one fact.

    ``normalized_concept_id`` prefers the C6 resolved concept and falls back to a
    deterministic MVP normalization (prefixed so it is never confused with a
    resolved C6 id and can be reconciled as C6 matures).
    """
    concept_id = fact.normalized_concept_id or f"fallback:{fact.normalized_key}"
    concern_type = _FACT_TYPE_TO_CONCERN_TYPE.get(fact.fact_type, ConcernType.OTHER)
    source_context = _FACT_TYPE_TO_SOURCE_CONTEXT.get(
        fact.fact_type, SourceContextClass.USER_NOTE
    )
    episode_when = fact.event_date or captured_at
    return ConcernKey(
        user_id=user_id,
        concern_type=concern_type,
        normalized_concept_id=concept_id,
        body_site=fact.body_site,
        laterality=fact.laterality,
        episode_bucket=_episode_bucket(episode_when),
        source_context_class=source_context,
    )


def decision_inputs_hash(
    *,
    concern_key: ConcernKey,
    source_event_id: uuid.UUID,
    policy_version: int = GENESIS_POLICY_VERSION,
) -> str:
    """Deterministic idempotency hash over the routing inputs.

    Keyed by the concern key (which already includes user_id + episode_bucket) +
    policy_version + the source genesis event identity. Redelivery of the same
    genesis event for the same concern is therefore a no-op; a re-evaluation under
    a new ``policy_version`` produces a distinct hash (and a superseding record).
    """
    parts = (
        str(concern_key.user_id),
        concern_key.concern_type.value,
        concern_key.normalized_concept_id,
        concern_key.body_site or "",
        concern_key.laterality or "",
        concern_key.episode_bucket,
        concern_key.source_context_class.value,
        str(policy_version),
        str(source_event_id),
    )
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def candidate_key(concern_key: ConcernKey) -> str:
    """Deterministic dedup key for a pending candidate.

    Unlike ``decision_inputs_hash`` (which is per genesis event), this excludes the
    source event and policy version so repeated mentions of the same concern across
    captures update the SAME candidate rather than creating duplicates.
    """
    parts = (
        str(concern_key.user_id),
        concern_key.concern_type.value,
        concern_key.normalized_concept_id,
        concern_key.body_site or "",
        concern_key.laterality or "",
        concern_key.episode_bucket,
        concern_key.source_context_class.value,
    )
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def calm_display_title(facts: list[GenesisFactInput]) -> str:
    """A calm, personal-first candidate title (never clinical/alarming).

    Uses the entity label of the most confident concern-forming fact (falling back
    to any fact), title-cased — e.g. "Cough", "Cholesterol". Any user-facing text
    still passes the C10 gate at render time.
    """
    pool = [f for f in facts if _is_concern_forming(f)] or list(facts)
    best = max(pool, key=lambda f: f.extraction_confidence)
    label = best.entity_label.strip() or best.normalized_key
    return label[:1].upper() + label[1:] if label else "Something I noticed"


def _is_concern_forming(fact: GenesisFactInput) -> bool:
    """A fact is concern-forming unless it is negated/historical/hypothetical or a
    non-concern fact type (incidental, family/social history)."""
    if fact.is_negated or fact.is_historical or fact.is_hypothetical:
        return False
    return fact.fact_type not in _NON_CONCERN_FACT_TYPES


def classify_concern_group(
    facts: list[GenesisFactInput],
) -> tuple[GenesisDecision, str, float | None]:
    """B0 skeleton classifier for a group of facts sharing one concern key.

    Returns ``(decision, reason_code, confidence)``. B0 records only the decided
    safe defaults:

    - any concern-forming fact in the group  -> CANDIDATE (never auto-thread here;
      strong-signal auto-create is Story B1), reason ``default_candidate_pending_classification``.
    - no concern-forming fact                -> NO_THREAD_WITH_REASON, reason
      ``not_concern_forming``.

    This honours the hard invariant that ``NO_THREAD_WITH_REASON`` is never used as
    a substitute for routing a real signal — uncertain signals become candidates.
    """
    concern_facts = [f for f in facts if _is_concern_forming(f)]
    if not concern_facts:
        return GenesisDecision.NO_THREAD_WITH_REASON, "not_concern_forming", None
    confidence = max(f.extraction_confidence for f in concern_facts)
    return (
        GenesisDecision.CREATE_OR_UPDATE_PENDING_CANDIDATE,
        "default_candidate_pending_classification",
        confidence,
    )
