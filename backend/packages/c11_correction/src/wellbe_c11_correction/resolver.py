"""Shared deterministic correction resolver (the C11 seam used by C6, C8, C13).

This is a PURE function over a set of applied correction candidates for a single
``(target_kind, target_id)``. It must produce the same output regardless of the
input order — every downstream read path calls this so corrected views never
diverge.

Resolution rule (decision: correction-service-layered-provenance.md):
1. Specificity: a field-specific correction wins over a whole-object correction
   for that field; whole-object corrections still apply to fields without a more
   specific correction.
2. Applied-only: callers pass applied candidates only (the SQL view filters).
3. Supersession: if B supersedes A, A is inactive for the overlapping field.
4. Authority rank (controller 100 > accepted 90 > delegated 80 > role 20 > system 10).
5. Semantic rank: withdraw/mark_incorrect > replace_value > mark_stale > add_context.
6. Effective/valid time: most recent effective_at wins.
7. Transaction time: later applied_at wins.
8. Final tie-break: lexical order of correction_id (UUIDv7/ULID preferred).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from wellbe_contracts.c11_correction import (
    RESOLUTION_RULE_VERSION,
    RESOLVED_VIEW_MIN_AUTHORITY_RANK,
    SEMANTIC_TYPE_RANK,
    ActorAuthority,
    CorrectionTargetKind,
    CorrectionType,
    ResolvedOverlay,
)

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)

# Correction types that remove/suppress rather than replace a value.
_WITHDRAWING_TYPES = {
    CorrectionType.WITHDRAW_FROM_CURRENT_VIEW,
    CorrectionType.MARK_INCORRECT,
}


@dataclass(frozen=True)
class CandidateCorrection:
    """An applied correction candidate for resolution. Order-independent."""

    correction_id: UUID
    correction_type: CorrectionType
    actor_authority: ActorAuthority
    authority_rank: int
    semantic_rank: int
    field_path: str | None
    effective_at: datetime | None
    applied_at: datetime | None
    supersedes_correction_id: UUID | None
    proposed_payload: dict = field(default_factory=dict)


def _aware(dt: datetime | None) -> datetime:
    if dt is None:
        return _EPOCH
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _sort_key(c: CandidateCorrection) -> tuple:
    # Higher authority, higher semantic rank, later effective, later applied win.
    # correction_id ascending is the final deterministic tie-break, so we negate
    # everything else and keep the id ascending.
    return (
        -c.authority_rank,
        -SEMANTIC_TYPE_RANK.get(c.correction_type, c.semantic_rank),
        -_aware(c.effective_at).timestamp(),
        -_aware(c.applied_at).timestamp(),
        str(c.correction_id),
    )


def _winner_state(c: CandidateCorrection) -> tuple[str, str]:
    """Map the winning correction type to (resolved_state, explanation_code)."""
    if c.correction_type in _WITHDRAWING_TYPES:
        return "withdrawn", f"withdrawn_by:{c.correction_type.value}"
    if c.correction_type == CorrectionType.MARK_STALE:
        return "stale", "marked_stale"
    if c.correction_type == CorrectionType.ADD_MISSING_CONTEXT:
        return "augmented", "context_added"
    return "overlaid", f"overlaid_by:{c.correction_type.value}"


def resolve_overlays(
    *,
    target_kind: CorrectionTargetKind,
    target_id: UUID,
    field_path: str | None,
    candidates: list[CandidateCorrection],
    min_authority_rank: int = RESOLVED_VIEW_MIN_AUTHORITY_RANK,
) -> ResolvedOverlay:
    """Resolve the overlay state for one (target, field_path).

    ``candidates`` should be all applied corrections for the target (any field).
    Specificity is applied here: field-specific corrections win over whole-object
    corrections for the requested ``field_path``.
    """
    # Only candidates admitted to the resolved view (authority >= threshold).
    admitted = [c for c in candidates if c.authority_rank >= min_authority_rank]

    # Specificity: prefer corrections whose field_path matches the requested one;
    # fall back to whole-object (field_path is None) corrections for that field.
    field_specific = [c for c in admitted if c.field_path == field_path and field_path is not None]
    whole_object = [c for c in admitted if c.field_path is None]
    applicable = field_specific if field_specific else whole_object
    if field_path is None:
        # Requesting the whole object: only whole-object corrections apply.
        applicable = whole_object

    if not applicable:
        return ResolvedOverlay(
            target_kind=target_kind,
            target_id=target_id,
            field_path=field_path,
            resolved_state="base",
            active_correction_id=None,
            inactive_correction_ids=[],
            resolved_value=None,
            resolution_rule_version=RESOLUTION_RULE_VERSION,
            explanation_code="no_applied_corrections",
        )

    # Supersession: drop any correction that is explicitly superseded by another
    # applicable correction.
    superseded_ids = {
        c.supersedes_correction_id
        for c in applicable
        if c.supersedes_correction_id is not None
    }
    active_candidates = [c for c in applicable if c.correction_id not in superseded_ids]
    if not active_candidates:
        active_candidates = applicable  # defensive: never empty out the set

    ordered = sorted(active_candidates, key=_sort_key)
    winner = ordered[0]
    inactive = [c.correction_id for c in applicable if c.correction_id != winner.correction_id]

    resolved_state, explanation = _winner_state(winner)
    _value_states = ("overlaid", "augmented", "stale")
    resolved_value = winner.proposed_payload if resolved_state in _value_states else None

    return ResolvedOverlay(
        target_kind=target_kind,
        target_id=target_id,
        field_path=field_path,
        resolved_state=resolved_state,
        active_correction_id=winner.correction_id,
        inactive_correction_ids=inactive,
        resolved_value=resolved_value,
        resolution_rule_version=RESOLUTION_RULE_VERSION,
        explanation_code=explanation,
    )
