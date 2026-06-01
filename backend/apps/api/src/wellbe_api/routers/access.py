"""C13 /v2 access predicate, grants, workspaces, and audit routes.

Personal-first: the controller's own personal workspace is always present and the
controller always evaluates to ``allow`` on their own data. Grants are how the
individual extends access to *others*; capabilities default-deny.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from wellbe_c1_consent import ConsentService
from wellbe_c1_consent.models import ShareGrantRow
from wellbe_contracts.c13_api import (
    AccessPredicateV2,
    AuditRefV2,
    GrantCapabilitiesV2,
    GrantV2,
    WorkspaceV2,
)
from wellbe_events.models import OutboxEventRow

from wellbe_api import mappers
from wellbe_api.deps import PrincipalDep, SessionDep, audit_ref, get_redis

router = APIRouter(prefix="/v2", tags=["v2-access"])


class AccessEvaluateRequest(BaseModel):
    resource_type: str
    action: str
    resource_id: uuid.UUID | None = None
    purpose_code: str = "personal_care"


class CreateGrantRequest(BaseModel):
    grantee_type: str
    grantee_user_id: uuid.UUID | None = None
    actions: list[str] = Field(default_factory=lambda: ["read"])
    data_categories: list[str] = Field(default_factory=lambda: ["all"])
    thread_ids: list[uuid.UUID] = Field(default_factory=list)
    purpose: str | None = None
    expires_at: datetime | None = None


class RevokeGrantRequest(BaseModel):
    reason: str = "user_revoked"


@router.post("/access/evaluate", response_model=AccessPredicateV2)
async def access_evaluate(
    body: AccessEvaluateRequest, principal: PrincipalDep, session: SessionDep
) -> AccessPredicateV2:
    now = datetime.now(UTC)
    if principal.is_controller:
        decision, reasons = "allow", ["controller_self_access"]
        caps = {"can_read": True, "can_comment": True, "can_contribute": True}
    else:
        consent = ConsentService(session, get_redis())
        allowed = await consent.check_scope(
            actor_id=principal.actor_id,
            resource_type=body.resource_type,
            resource_id=body.resource_id,
            action=body.action,
        )
        decision = "allow" if allowed else "deny"
        reasons = ["grant_satisfied"] if allowed else ["grant_required"]
        caps = {"can_read": allowed}
    audit = await audit_ref(
        session,
        event_type="c13.access.evaluated",
        principal=principal,
        summary=f"Access {decision} for {body.action} on {body.resource_type}",
        extra={"decision": decision, "action": body.action},
    )
    await session.commit()
    return AccessPredicateV2(
        access_predicate_hash=f"ap_{uuid.uuid4().hex}",
        decision=decision,  # type: ignore[arg-type]
        decision_reason_codes=reasons,
        purpose_code=body.purpose_code,
        scope_codes=[body.action],
        capabilities=caps,
        valid_until=now.replace(microsecond=0),
        policy_version="c1.v1",
        evaluated_at=now,
        audit_event_id=audit.audit_event_id,
    )


@router.get("/workspaces", response_model=list[WorkspaceV2])
async def list_workspaces(principal: PrincipalDep, session: SessionDep) -> list[WorkspaceV2]:
    return [_personal_workspace(principal)]


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceV2)
async def get_workspace(
    workspace_id: str, principal: PrincipalDep, session: SessionDep
) -> WorkspaceV2:
    from fastapi import HTTPException  # noqa: PLC0415

    ws = _personal_workspace(principal)
    if workspace_id != ws.workspace_id:
        raise HTTPException(status_code=404, detail="workspace_not_found")
    return ws


@router.get("/grants", response_model=list[GrantV2])
async def list_grants(principal: PrincipalDep, session: SessionDep) -> list[GrantV2]:
    stmt = (
        select(ShareGrantRow)
        .where(ShareGrantRow.grantor_id == principal.patient_id)
        .order_by(desc(ShareGrantRow.created_at))
        .limit(200)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_grant_to_v2(r, principal.patient_id) for r in rows]


@router.post("/grants", response_model=GrantV2, status_code=201)
async def create_grant(
    body: CreateGrantRequest, principal: PrincipalDep, session: SessionDep
) -> GrantV2:
    consent = ConsentService(session, get_redis())
    row = await consent.create_share_grant(
        grantor_id=principal.patient_id,
        grantee_type=body.grantee_type,
        grantee_user_id=body.grantee_user_id,
        thread_ids=body.thread_ids,
        actions=body.actions,
        data_categories=body.data_categories,
        purpose=body.purpose,
        expires_at=body.expires_at,
        consent_snapshot_id=uuid.uuid4(),
        created_by=principal.actor_id,
    )
    await audit_ref(
        session,
        event_type="c13.grant.created",
        principal=principal,
        summary="Grant created",
        extra={"grant_id": str(row.id), "grantee_type": body.grantee_type},
    )
    await session.commit()
    return _grant_to_v2(row, principal.patient_id)


@router.post("/grants/{grant_id}/revoke", response_model=GrantV2)
async def revoke_grant(
    grant_id: uuid.UUID,
    body: RevokeGrantRequest,
    principal: PrincipalDep,
    session: SessionDep,
) -> GrantV2:
    from fastapi import HTTPException  # noqa: PLC0415

    consent = ConsentService(session, get_redis())
    existing = await session.get(ShareGrantRow, grant_id)
    if existing is None or existing.grantor_id != principal.patient_id:
        raise HTTPException(status_code=404, detail="grant_not_found")
    await consent.revoke_grant(grant_id, revoked_by=principal.actor_id, reason=body.reason)
    await audit_ref(
        session,
        event_type="c13.grant.revoked",
        principal=principal,
        summary="Grant revoked",
        extra={"grant_id": str(grant_id), "reason": body.reason},
    )
    await session.commit()
    refreshed = await session.get(ShareGrantRow, grant_id)
    assert refreshed is not None
    return _grant_to_v2(refreshed, principal.patient_id)


@router.get("/audit/my-events", response_model=list[AuditRefV2])
async def my_audit_events(principal: PrincipalDep, session: SessionDep) -> list[AuditRefV2]:
    pid = str(principal.patient_id)
    stmt = (
        select(OutboxEventRow)
        .where(OutboxEventRow.payload["patient_id"].astext == pid)
        .where(OutboxEventRow.event_type.like("c13.%"))
        .order_by(desc(OutboxEventRow.created_at))
        .limit(200)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        AuditRefV2(
            audit_event_id=str(r.id),
            correlation_id=r.correlation_id,
            trace_id=r.trace_id,
            visibility=["controller_visible"],
            event_summary=str(r.payload.get("summary", r.event_type)),
        )
        for r in rows
    ]


def _personal_workspace(principal: PrincipalDep) -> WorkspaceV2:
    now = datetime.now(UTC)
    return WorkspaceV2(
        workspace_id=mappers.personal_workspace_id(principal.patient_id),
        workspace_type="personal",
        display_name="My Health",
        controller_subject_ref=str(principal.patient_id),
        membership_state="active",
        active_role_binding={"role_type": "controller", "state": "active"},
        capability_summary={"can_read": True, "can_contribute": True},
        data_access_not_implied=True,
        created_at=now,
        updated_at=now,
    )


def _grant_to_v2(row: ShareGrantRow, patient_id: uuid.UUID) -> GrantV2:
    actions = list(row.actions or [])
    caps = GrantCapabilitiesV2(
        can_read="read" in actions,
        can_search="search" in actions,
        can_comment="comment" in actions,
        can_export="export" in actions,
        can_invite="invite" in actions,
        can_contribute="contribute" in actions,
        can_request_correction="request_correction" in actions,
        can_view_external_context="view_external_context" in actions,
    )
    grantee_ref = str(row.grantee_user_id) if row.grantee_user_id else (
        row.grantee_identifier_hash or "unknown"
    )
    return GrantV2(
        grant_id=str(row.id),
        grant_type=row.grantee_type,
        subject_ref=str(patient_id),
        grantee_ref=grantee_ref,
        workspace_id=mappers.personal_workspace_id(patient_id),
        role_binding_id="",
        scope_codes=actions,
        scope_profile_version=str(row.policy_version),
        purpose_code=row.purpose or "unspecified",
        status=row.status,
        starts_at=row.accepted_at or row.created_at,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        capabilities=caps,
        resource_constraints_summary=(
            f"{len(row.thread_ids or [])} thread(s)" if row.thread_ids else "selector"
        ),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
