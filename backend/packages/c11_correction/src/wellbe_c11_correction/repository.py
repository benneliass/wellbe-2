from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_contracts.c11_correction import (
    ActorAuthority,
    CorrectionStatus,
    CorrectionTargetKind,
    CorrectionType,
)

from wellbe_c11_correction.models import (
    CorrectionResolutionEventRow,
    CorrectionRow,
    CorrectionTargetRow,
)
from wellbe_c11_correction.resolver import CandidateCorrection


def _naive_utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CorrectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_correction(
        self,
        *,
        correction_id: uuid.UUID,
        patient_id: uuid.UUID,
        status: CorrectionStatus,
        correction_type: CorrectionType,
        actor_authority: ActorAuthority,
        actor_ref: dict,
        raw_correction_event_id: uuid.UUID,
        proposed_payload: dict,
        idempotency_key: str,
        rationale: str | None = None,
        effective_at: datetime | None = None,
        applied_at: datetime | None = None,
        supersedes_correction_id: uuid.UUID | None = None,
        grant_id: uuid.UUID | None = None,
        role_binding_id: uuid.UUID | None = None,
    ) -> CorrectionRow:
        row = CorrectionRow(
            correction_id=correction_id,
            patient_id=patient_id,
            status=status.value,
            correction_type=correction_type.value,
            actor_authority=actor_authority.value,
            actor_ref=actor_ref,
            grant_id=grant_id,
            role_binding_id=role_binding_id,
            raw_correction_event_id=raw_correction_event_id,
            rationale=rationale,
            proposed_payload=proposed_payload,
            applied_at=applied_at,
            effective_at=effective_at,
            supersedes_correction_id=supersedes_correction_id,
            created_at=_naive_utcnow(),
            idempotency_key=idempotency_key,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def insert_target(
        self,
        *,
        correction_id: uuid.UUID,
        patient_id: uuid.UUID,
        target_kind: CorrectionTargetKind,
        target_id: uuid.UUID,
        field_path: str | None,
        semantic_rank: int,
        target_version: str | None = None,
        base_value_hash: str | None = None,
        proposed_value_hash: str | None = None,
    ) -> CorrectionTargetRow:
        row = CorrectionTargetRow(
            correction_target_id=uuid.uuid4(),
            correction_id=correction_id,
            patient_id=patient_id,
            target_kind=target_kind.value,
            target_id=target_id,
            target_version=target_version,
            field_path=field_path,
            base_value_hash=base_value_hash,
            proposed_value_hash=proposed_value_hash,
            semantic_rank=semantic_rank,
            created_at=_naive_utcnow(),
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, correction_id: uuid.UUID) -> CorrectionRow | None:
        return await self._session.get(CorrectionRow, correction_id)

    async def list_for_patient(
        self, patient_id: uuid.UUID, *, limit: int = 200
    ) -> list[CorrectionRow]:
        stmt = (
            select(CorrectionRow)
            .where(CorrectionRow.patient_id == patient_id)
            .order_by(CorrectionRow.created_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def mark_applied(
        self,
        *,
        row: CorrectionRow,
        actor_authority: ActorAuthority,
        accepted_by_controller_actor: dict | None = None,
    ) -> None:
        """Transition a pending proposal to applied (C11 lifecycle row only)."""
        now = _naive_utcnow()
        row.status = CorrectionStatus.APPLIED.value
        row.actor_authority = actor_authority.value
        row.accepted_by_controller_actor = accepted_by_controller_actor
        row.accepted_at = now
        row.applied_at = now
        await self._session.flush()

    async def insert_resolution_event(
        self,
        *,
        correction_id: uuid.UUID,
        patient_id: uuid.UUID,
        target_kind: str,
        target_id: uuid.UUID,
        field_path: str | None,
        resolution_action: str,
        idempotency_key: str,
        prior_active_correction_id: uuid.UUID | None = None,
        new_active_correction_id: uuid.UUID | None = None,
    ) -> None:
        row = CorrectionResolutionEventRow(
            resolution_event_id=uuid.uuid4(),
            correction_id=correction_id,
            patient_id=patient_id,
            target_kind=target_kind,
            target_id=target_id,
            field_path=field_path,
            resolution_action=resolution_action,
            prior_active_correction_id=prior_active_correction_id,
            new_active_correction_id=new_active_correction_id,
            occurred_at=_naive_utcnow(),
            idempotency_key=idempotency_key,
        )
        self._session.add(row)
        await self._session.flush()

    async def load_candidates(
        self, *, patient_id: uuid.UUID, target_kind: CorrectionTargetKind, target_id: uuid.UUID
    ) -> list[CandidateCorrection]:
        """Load applied correction candidates for a target from the SQL view."""
        stmt = text(
            """
            SELECT correction_id, correction_type, actor_authority, authority_rank,
                   semantic_rank, field_path, effective_at, applied_at,
                   supersedes_correction_id, proposed_payload
            FROM c11.applied_correction_candidates_v
            WHERE patient_id = :patient_id
              AND target_kind = :target_kind
              AND target_id = :target_id
            """
        )
        result = await self._session.execute(
            stmt,
            {
                "patient_id": str(patient_id),
                "target_kind": target_kind.value,
                "target_id": str(target_id),
            },
        )
        candidates: list[CandidateCorrection] = []
        for r in result.mappings():
            candidates.append(
                CandidateCorrection(
                    correction_id=r["correction_id"],
                    correction_type=CorrectionType(r["correction_type"]),
                    actor_authority=ActorAuthority(r["actor_authority"]),
                    authority_rank=int(r["authority_rank"]),
                    semantic_rank=int(r["semantic_rank"]),
                    field_path=r["field_path"],
                    effective_at=r["effective_at"],
                    applied_at=r["applied_at"],
                    supersedes_correction_id=r["supersedes_correction_id"],
                    proposed_payload=r["proposed_payload"] or {},
                )
            )
        return candidates

    async def targets_for(self, correction_id: uuid.UUID) -> list[CorrectionTargetRow]:
        stmt = select(CorrectionTargetRow).where(
            CorrectionTargetRow.correction_id == correction_id
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
