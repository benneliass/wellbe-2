"""C13 /v2 Visit Packet routes (WEL-30 / WEL-68).

User-controlled, source-linked clinician packet with a C10 pre-share gate and a
named-recipient, time-boxed, passcode-protected, revocable share link. See
docs/decisions/visit-packet-composition-gating.md.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Header
from wellbe_contracts.c10_safety import C10Decision, C10ReasonCode
from wellbe_contracts.c13_api import ProblemCode
from wellbe_contracts.visit_packet import (
    ExportPacketResponse,
    GenerateVisitPacketRequest,
    PacketSourceRef,
    PacketStatus,
    SharedPacketView,
    ShareLinkStatus,
    SharePacketRequest,
    SharePacketResponse,
    UpdatePacketRequest,
    VisitPacketStatementV2,
    VisitPacketV2,
)

from wellbe_api.deps import Principal, PrincipalDep, SessionDep, audit_ref, require_access
from wellbe_api.errors import ProblemError
from wellbe_api.visit_packet.compose import compose_statements
from wellbe_api.visit_packet.models import PacketRow, ShareLinkRow, StatementRow
from wellbe_api.visit_packet.repository import VisitPacketRepository
from wellbe_api.visit_packet.share import mint_share_token, run_share_gate, sha256_hex

router = APIRouter(prefix="/v2", tags=["v2-visit-packet"])

_RESOURCE = "visit_packet"


def _statement_v2(row: StatementRow) -> VisitPacketStatementV2:
    return VisitPacketStatementV2(
        statement_id=str(row.id),
        layer=row.layer,
        section=row.section,
        ordinal=row.ordinal,
        text=row.text,
        classification=row.classification,
        source_refs=[PacketSourceRef(**sr) for sr in (row.source_refs or [])],
        absent=row.absent,
        absence_reason=row.absence_reason,
        included=row.included,
    )


def _packet_v2(packet: PacketRow, statements: list[StatementRow]) -> VisitPacketV2:
    return VisitPacketV2(
        packet_id=str(packet.id),
        patient_id=str(packet.patient_id),
        title=packet.title,
        status=PacketStatus(packet.status),
        thread_ids=[str(t) for t in (packet.thread_ids or [])],
        time_window_start=packet.time_window_start,
        time_window_end=packet.time_window_end,
        statements=[_statement_v2(s) for s in statements],
        created_at=packet.created_at,
        updated_at=packet.updated_at,
    )


async def _load_owned_packet(
    repo: VisitPacketRepository, principal: Principal, packet_id: uuid.UUID
) -> PacketRow:
    packet = await repo.get_packet(packet_id)
    if packet is None or packet.patient_id != principal.patient_id:
        raise ProblemError(
            status=404,
            code=ProblemCode.GRANT_REQUIRED,
            title="Visit packet not found",
            detail="No visit packet with that id is visible to the principal.",
            correlation_id=principal.correlation_id,
        )
    return packet


@router.post("/visit-packets", response_model=VisitPacketV2, status_code=201)
async def generate_visit_packet(
    body: GenerateVisitPacketRequest, principal: PrincipalDep, session: SessionDep
) -> VisitPacketV2:
    await require_access(principal, session, action="write", resource_type=_RESOURCE)

    try:
        thread_ids = [uuid.UUID(t) for t in body.thread_ids]
    except ValueError as exc:
        raise ProblemError(
            status=422,
            code=ProblemCode.PROVENANCE_MISSING,
            title="Invalid thread id",
            detail="thread_ids must be valid UUIDs.",
            correlation_id=principal.correlation_id,
        ) from exc

    repo = VisitPacketRepository(session)
    packet = await repo.create_packet(
        PacketRow(
            patient_id=principal.patient_id,
            title=body.title,
            status=PacketStatus.DRAFT.value,
            thread_ids=[str(t) for t in thread_ids],
            time_window_start=body.time_window_start,
            time_window_end=body.time_window_end,
        )
    )

    statements = await compose_statements(
        session=session,
        packet_id=packet.id,
        patient_id=principal.patient_id,
        thread_ids=thread_ids,
        include_summary=body.include_summary,
        prep_questions=body.prep.questions,
        prep_goals=body.prep.goals,
        prep_observations=body.prep.observations,
    )
    await repo.add_statements(statements)

    await audit_ref(
        session,
        event_type="c13.visit_packet.generated",
        principal=principal,
        summary="Visit packet generated",
        extra={"packet_id": str(packet.id), "statement_count": len(statements)},
    )
    await session.commit()

    rows = await repo.statements_for_packet(packet.id)
    return _packet_v2(packet, rows)


@router.get("/visit-packets/{packet_id}", response_model=VisitPacketV2)
async def get_visit_packet(
    packet_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> VisitPacketV2:
    await require_access(
        principal, session, action="read", resource_type=_RESOURCE, resource_id=packet_id
    )
    repo = VisitPacketRepository(session)
    packet = await _load_owned_packet(repo, principal, packet_id)
    rows = await repo.statements_for_packet(packet.id)
    return _packet_v2(packet, rows)


@router.patch("/visit-packets/{packet_id}", response_model=VisitPacketV2)
async def update_visit_packet(
    packet_id: uuid.UUID,
    body: UpdatePacketRequest,
    principal: PrincipalDep,
    session: SessionDep,
) -> VisitPacketV2:
    """Toggle statement inclusion. Deselected statements are kept and marked,
    never silently dropped (decision: deselection visibility)."""
    await require_access(
        principal, session, action="write", resource_type=_RESOURCE, resource_id=packet_id
    )
    repo = VisitPacketRepository(session)
    packet = await _load_owned_packet(repo, principal, packet_id)

    for inc in body.inclusions:
        try:
            sid = uuid.UUID(inc.statement_id)
        except ValueError:
            continue
        row = await repo.get_statement(sid)
        if row is not None and row.packet_id == packet.id:
            row.included = inc.included
    await session.flush()
    await session.commit()

    rows = await repo.statements_for_packet(packet.id)
    return _packet_v2(packet, rows)


@router.post(
    "/visit-packets/{packet_id}/share",
    response_model=SharePacketResponse,
    status_code=201,
)
async def share_visit_packet(
    packet_id: uuid.UUID,
    body: SharePacketRequest,
    principal: PrincipalDep,
    session: SessionDep,
) -> SharePacketResponse:
    await require_access(
        principal, session, action="write", resource_type=_RESOURCE, resource_id=packet_id
    )
    repo = VisitPacketRepository(session)
    packet = await _load_owned_packet(repo, principal, packet_id)
    statements = await repo.statements_for_packet(packet.id)

    # C10 pre-share gate (fail-closed). Blocks new AI diagnosis, unsupported
    # claims, diagnosis/panic language before anything leaves the personal core.
    evaluation = run_share_gate(
        statements=statements,
        patient_id=principal.patient_id,
        purpose=body.purpose,
        correlation_id=principal.correlation_id,
        packet_id=packet.id,
    )
    if evaluation.decision not in {C10Decision.ALLOW, C10Decision.ALLOW_WITH_OBLIGATIONS}:
        await audit_ref(
            session,
            event_type="c13.visit_packet.share_blocked",
            principal=principal,
            summary="Visit packet share blocked by C10 safety gate",
            extra={
                "packet_id": str(packet.id),
                "reason_codes": list(evaluation.reason_codes),
            },
        )
        await session.commit()
        code = ProblemCode.POLICY_UNAVAILABLE
        if C10ReasonCode.C10_DIAGNOSIS_ASSERTION in evaluation.reason_codes:
            code = ProblemCode.THEORY_DIAGNOSIS_VIOLATION
        elif C10ReasonCode.C10_PROVENANCE_MISSING in evaluation.reason_codes:
            code = ProblemCode.PROVENANCE_MISSING
        raise ProblemError(
            status=422,
            code=code,
            title="Packet cannot be shared",
            detail=(
                "The safety gate blocked this packet from being shared "
                f"(decision={evaluation.decision.value}). Remove or correct the "
                "flagged statements and try again."
            ),
            correlation_id=principal.correlation_id,
        )

    # C1 grant + revocable, time-boxed, passcode-protected link.
    raw_token, token_hash = mint_share_token()
    expires_at = datetime.now(UTC) + timedelta(hours=body.expires_in_hours)
    recipient_hash = sha256_hex(body.recipient_identifier) if body.recipient_identifier else None
    passcode_hash = sha256_hex(body.passcode) if body.passcode else None

    grant_id = uuid.uuid4()
    link = await repo.add_share_link(
        ShareLinkRow(
            packet_id=packet.id,
            patient_id=principal.patient_id,
            grant_id=grant_id,
            token_hash=token_hash,
            passcode_hash=passcode_hash,
            recipient_name=body.recipient_name,
            recipient_identifier_hash=recipient_hash,
            purpose=body.purpose,
            info_scope=body.info_scope,
            c10_decision=evaluation.decision.value,
            c10_render_token=(evaluation.render_token.token if evaluation.render_token else None),
            status=ShareLinkStatus.ACTIVE.value,
            expires_at=expires_at.replace(tzinfo=None),
        )
    )
    packet.status = PacketStatus.SHARED.value
    packet.updated_at = datetime.now(UTC).replace(tzinfo=None)

    await audit_ref(
        session,
        event_type="c13.visit_packet.share_link.created",
        principal=principal,
        summary=f"Visit packet shared with {body.recipient_name}",
        visibility=["controller_visible"],
        extra={
            "packet_id": str(packet.id),
            "share_link_id": str(link.id),
            "grant_id": str(grant_id),
            "expires_at": expires_at.isoformat(),
            "passcode_required": passcode_hash is not None,
        },
    )
    await session.commit()

    return SharePacketResponse(
        share_link_id=str(link.id),
        grant_id=str(grant_id),
        share_token=raw_token,
        passcode_required=passcode_hash is not None,
        expires_at=expires_at,
        c10_decision=evaluation.decision.value,
    )


@router.post("/visit-packets/{packet_id}/share/{link_id}/revoke", status_code=204)
async def revoke_share_link(
    packet_id: uuid.UUID,
    link_id: uuid.UUID,
    principal: PrincipalDep,
    session: SessionDep,
) -> None:
    await require_access(
        principal, session, action="write", resource_type=_RESOURCE, resource_id=packet_id
    )
    repo = VisitPacketRepository(session)
    await _load_owned_packet(repo, principal, packet_id)
    link = await repo.get_share_link(link_id)
    if link is None or link.packet_id != packet_id or link.patient_id != principal.patient_id:
        raise ProblemError(
            status=404,
            code=ProblemCode.GRANT_REQUIRED,
            title="Share link not found",
            detail="No share link with that id is visible to the principal.",
            correlation_id=principal.correlation_id,
        )
    link.status = ShareLinkStatus.REVOKED.value
    link.revoked_at = datetime.now(UTC).replace(tzinfo=None)
    await session.flush()

    # Future access only: revocation stops the link; an already-exported copy
    # cannot be recalled (decision: honest revocation semantics).
    await audit_ref(
        session,
        event_type="c13.visit_packet.share_link.revoked",
        principal=principal,
        summary="Visit packet share link revoked",
        extra={"packet_id": str(packet_id), "share_link_id": str(link_id)},
    )
    await session.commit()


@router.post("/visit-packets/{packet_id}/export", response_model=ExportPacketResponse)
async def export_visit_packet(
    packet_id: uuid.UUID, principal: PrincipalDep, session: SessionDep
) -> ExportPacketResponse:
    """Export a copy. This is a distinct, clearly-warned state from a controlled
    link share: an exported copy cannot be recalled."""
    await require_access(
        principal, session, action="write", resource_type=_RESOURCE, resource_id=packet_id
    )
    repo = VisitPacketRepository(session)
    packet = await _load_owned_packet(repo, principal, packet_id)
    rows = await repo.statements_for_packet(packet.id)
    await audit_ref(
        session,
        event_type="c13.visit_packet.exported",
        principal=principal,
        summary="Visit packet exported as a copy",
        extra={"packet_id": str(packet.id)},
    )
    await session.commit()
    return ExportPacketResponse(packet=_packet_v2(packet, rows))


@router.get("/share/{token}", response_model=SharedPacketView)
async def read_shared_packet(
    token: str,
    session: SessionDep,
    passcode: Annotated[str | None, Header(alias="X-Share-Passcode")] = None,
) -> SharedPacketView:
    """Public recipient read of a shared packet. Returns 404 for any unknown,
    revoked, expired, or passcode-failing link (no information leak)."""
    repo = VisitPacketRepository(session)
    link = await repo.share_link_by_token_hash(sha256_hex(token))

    def _gone() -> ProblemError:
        return ProblemError(
            status=404,
            code=ProblemCode.GRANT_REVOKED,
            title="This link is no longer active",
            detail="The share link is invalid, has been revoked, or has expired.",
            correlation_id="share-link",
        )

    if link is None or link.status != ShareLinkStatus.ACTIVE.value:
        raise _gone()
    if link.expires_at <= datetime.now(UTC).replace(tzinfo=None):
        raise _gone()
    if link.passcode_hash is not None and (
        passcode is None or sha256_hex(passcode) != link.passcode_hash
    ):
        raise _gone()

    packet = await repo.get_packet(link.packet_id)
    if packet is None:
        raise _gone()
    rows = await repo.statements_for_packet(packet.id)
    visible = [s for s in rows if s.included]
    return SharedPacketView(
        title=packet.title,
        statements=[_statement_v2(s) for s in visible],
        expires_at=link.expires_at,
    )
