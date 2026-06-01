"""Map internal component rows/results to public C13 v2 DTOs.

Unsafe fields (diagnosis, ranked differential, disease probability, treatment
plan, raw PHI) are simply never constructed here — they cannot be serialized
because they are absent from the public DTOs.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from wellbe_c14_investigation.models import InvestigationRow
from wellbe_c15_theory.models import TheoryRow
from wellbe_contracts.c13_api import (
    AuditRefV2,
    InvestigationV2,
    RelevanceLinkV2,
    SourceQualityTierV2,
    TheoryV2,
)
from wellbe_contracts.c16_external import RelevanceLinkResult


def personal_workspace_id(patient_id: uuid.UUID) -> str:
    """The individual's own personal workspace. Personal-first default surface."""
    return f"ws_personal_{patient_id}"


def _safety_level_from_flags(flags: list[dict[str, object]]) -> str:
    severities = {str(f.get("severity", "")) for f in flags}
    if "urgent" in severities:
        return "urgent"
    if "attention" in severities:
        return "attention"
    return "routine"


def investigation_to_v2(
    row: InvestigationRow,
    *,
    thread_ids: list[uuid.UUID],
    audit_refs: list[AuditRefV2] | None = None,
) -> InvestigationV2:
    evidence_bundle_ref = (
        str(row.evidence_bundle_ids[0]) if row.evidence_bundle_ids else "none"
    )
    return InvestigationV2(
        investigation_id=str(row.id),
        health_thread_ids=[str(t) for t in thread_ids],
        primary_question=row.primary_question,
        scope=dict(row.scope or {}),
        status=row.status,
        safety_level=_safety_level_from_flags(list(row.safety_flags or [])),
        workspace_id=personal_workspace_id(row.patient_id),
        evidence_bundle_ref=evidence_bundle_ref,
        linked_theory_ids=[str(t) for t in (row.active_theory_ids or [])],
        missing_context_items=list(row.missing_context_items or []),
        pending_items=[{"pending_item_id": str(p)} for p in (row.pending_item_ids or [])],
        created_by={
            "actor_id": str(row.created_by_actor_id) if row.created_by_actor_id else None,
            "owner_type": row.owner_type,
        },
        created_at=row.created_at,
        updated_at=row.status_changed_at,
        audit_refs=audit_refs or [],
    )


def theory_to_v2(
    row: TheoryRow,
    *,
    audit_refs: list[AuditRefV2] | None = None,
) -> TheoryV2:
    return TheoryV2(
        theory_id=str(row.id),
        investigation_id=str(row.linked_investigation_id) if row.linked_investigation_id else "",
        health_thread_id="",
        label=row.theory_text,
        proposed_by={
            "actor_id": str(row.created_by_actor_id) if row.created_by_actor_id else None,
        },
        status=row.status,
        safety_level=row.safety_level,
        not_diagnosis=True,
        created_at=row.created_at,
        updated_at=row.updated_at,
        audit_refs=audit_refs or [],
    )


def relevance_to_v2(
    result: RelevanceLinkResult,
    *,
    investigation_id: uuid.UUID | None,
    why_relevant_summary: str,
    audit_refs: list[AuditRefV2] | None = None,
) -> RelevanceLinkV2:
    tier = SourceQualityTierV2(f"tier_{result.source_quality_tier_snapshot}")
    now = result.created_at or datetime.now(UTC)
    return RelevanceLinkV2(
        relevance_link_id=str(result.relevance_link_id),
        external_source_id=str(result.external_source_id),
        external_claim_id=str(result.external_claim_id) if result.external_claim_id else "",
        linked_thread_id=str(result.personal_node_id),
        linked_investigation_id=str(investigation_id) if investigation_id else "",
        relevance_status="context_only",
        why_relevant_summary=why_relevant_summary,
        source_quality_tier=tier,
        context_only=True,
        not_personal_evidence=True,
        obligations=["show_context_only_label", "show_source"],
        created_at=now,
        evaluated_at=now,
        audit_refs=audit_refs or [],
    )
