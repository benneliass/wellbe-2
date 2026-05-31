from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from wellbe_events import emit_event
from wellbe_platform import get_trace_id

from wellbe_c1_consent.models import (
    ConsentScopeRow,
    PatientPrivacyPreferenceRow,
    RevocationLogRow,
    ShareGrantRow,
)

_SCOPE_CACHE_PREFIX = "consent:scope"
_SCOPE_CACHE_TTL = 300


class ConsentService:
    def __init__(self, session: AsyncSession, redis: aioredis.Redis) -> None:
        self._session = session
        self._redis = redis

    async def check_scope(
        self,
        actor_id: UUID,
        resource_type: str,
        resource_id: UUID | None,
        action: str,
    ) -> bool:
        resource_key = resource_id or "*"
        cache_key = f"{_SCOPE_CACHE_PREFIX}:{actor_id}:{resource_type}:{action}:{resource_key}"
        cached = await self._redis.get(cache_key)
        if cached is not None:
            return cached == b"1"

        now = datetime.now(UTC)
        stmt = select(ConsentScopeRow.id).where(
            and_(
                ConsentScopeRow.subject_id == actor_id,
                ConsentScopeRow.resource_type == resource_type,
                ConsentScopeRow.action == action,
                ConsentScopeRow.revoked_at.is_(None),
                ConsentScopeRow.valid_from <= now,
                (ConsentScopeRow.valid_until.is_(None)) | (ConsentScopeRow.valid_until > now),
            )
        )
        if resource_id is not None:
            stmt = stmt.where(
                (ConsentScopeRow.resource_id == resource_id)
                | (ConsentScopeRow.resource_id.is_(None))
            )

        result = await self._session.execute(stmt.limit(1))
        allowed = result.scalar_one_or_none() is not None

        await self._redis.set(cache_key, b"1" if allowed else b"0", ex=_SCOPE_CACHE_TTL)
        return allowed

    async def create_share_grant(
        self,
        *,
        grantor_id: UUID,
        grantee_type: str,
        grantee_user_id: UUID | None = None,
        grantee_identifier_hash: str | None = None,
        resource_selector: str | None = None,
        thread_ids: list[UUID] | None = None,
        actions: list[str],
        data_categories: list[str],
        purpose: str | None = None,
        expires_at: datetime | None = None,
        consent_snapshot_id: UUID,
        grant_token_hash: str | None = None,
        policy_version: int = 1,
        created_by: UUID,
        metadata: dict | None = None,
    ) -> ShareGrantRow:
        row = ShareGrantRow(
            grantor_id=grantor_id,
            grantee_user_id=grantee_user_id,
            grantee_identifier_hash=grantee_identifier_hash,
            grantee_type=grantee_type,
            resource_selector=resource_selector,
            thread_ids=[str(tid) for tid in (thread_ids or [])],
            actions=actions,
            data_categories=data_categories,
            purpose=purpose,
            expires_at=expires_at,
            consent_snapshot_id=consent_snapshot_id,
            grant_token_hash=grant_token_hash,
            policy_version=policy_version,
            created_by=created_by,
            grant_metadata=metadata or {},
        )
        self._session.add(row)
        await self._session.flush()

        await emit_event(
            self._session,
            event_type="share_grant.created",
            payload={
                "grant_id": str(row.id),
                "grantor_id": str(grantor_id),
                "grantee_type": grantee_type,
            },
            correlation_id=str(row.id),
            trace_id=get_trace_id(),
        )
        return row

    async def revoke_grant(
        self,
        grant_id: UUID,
        revoked_by: UUID,
        reason: str,
    ) -> None:
        now = datetime.now(UTC)

        await self._session.execute(
            update(ShareGrantRow)
            .where(ShareGrantRow.id == grant_id)
            .values(
                status="revoked",
                revoked_at=now,
                revoked_by=revoked_by,
                revocation_reason=reason,
            )
        )

        log_entry = RevocationLogRow(
            grant_id=grant_id,
            revoked_by=revoked_by,
            revoked_at=now,
            reason=reason,
            event_type="share_grant.revoked",
        )
        self._session.add(log_entry)
        await self._session.flush()

        pattern = f"{_SCOPE_CACHE_PREFIX}:*"
        async for key in self._redis.scan_iter(match=pattern, count=200):
            await self._redis.delete(key)

        await emit_event(
            self._session,
            event_type="share_grant.revoked",
            payload={
                "grant_id": str(grant_id),
                "revoked_by": str(revoked_by),
                "reason": reason,
            },
            correlation_id=str(grant_id),
            trace_id=get_trace_id(),
        )

    async def authorized_population_scope(
        self,
        actor_id: UUID,
        purpose: str,
    ) -> bool:
        stmt = select(PatientPrivacyPreferenceRow).where(
            and_(
                PatientPrivacyPreferenceRow.patient_id == actor_id,
                PatientPrivacyPreferenceRow.capability == "cross_patient_analysis",
                PatientPrivacyPreferenceRow.status == "enabled",
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
