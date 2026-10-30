"""Person-scoped raw-context exploration.

The signed-in person is the only caller. A grant does not start this walk.
The person id always comes from the principal, never from the body.

Notes are read from the vault for this request. The server stores pointers and
the exploration session. It does not keep a second copy of the note text, and
it does not write knowledge-graph edges.
"""

from __future__ import annotations

import logging
import uuid
from typing import Literal

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field
from wellbe_c2_vault.repository import VaultRepository
from wellbe_contracts.c13_api import ProblemCode
from wellbe_raw_context_brain.persist.sql_store import person_map, walk
from wellbe_raw_context_brain.relation import source_name
from wellbe_raw_context_brain.router import ViewModel
from wellbe_raw_context_brain.types import ExploreInput, SemanticData, VaultEvent

from wellbe_api.config import ApiSettings
from wellbe_api.deps import PrincipalDep, SessionDep
from wellbe_api.errors import ProblemError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2", tags=["v2-context"])


class ContextExploreRequest(BaseModel):
    purpose: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    anchor_id: str | None = None
    route_handle: str | None = None
    route_id: str | None = None
    focus_id: str | None = None
    operation: Literal["open", "continue", "rewind"] = "open"
    rewind_to_id: str | None = None
    hold_at_anchor: bool = False


class ContextRouteResponse(BaseModel):
    route_id: str
    label: str
    kind: str


class ContextMapNodeResponse(BaseModel):
    id: str
    kind: Literal["event", "pseudonode"]
    source_type: str
    degree: int
    label: str


class ContextMapLinkResponse(BaseModel):
    source: str
    target: str
    reason: str


class ContextMapResponse(BaseModel):
    nodes: list[ContextMapNodeResponse]
    links: list[ContextMapLinkResponse]


class ContextExploreResponse(BaseModel):
    route: str
    breadcrumb: list[str]
    hop_depth: int
    direct_link_count: int
    cycle_count: int
    exhaustion: str
    terminal_reason: str | None
    detail: str
    route_handle: str | None
    snapshot_revision: int
    snapshot_digest: str
    next_routes: list[ContextRouteResponse]
    opened: list[str]


def _controller_only(principal: PrincipalDep) -> str:
    if not principal.is_controller:
        raise ProblemError(
            status=403,
            code=ProblemCode.GRANT_REQUIRED,
            title="Only the person can explore their context",
            detail="A grant does not start or continue this person's raw-context walk.",
            correlation_id=principal.correlation_id,
        )
    return str(principal.patient_id)


def _page(page: SemanticData) -> ContextExploreResponse:
    return ContextExploreResponse(
        route=page.route,
        breadcrumb=list(page.breadcrumb),
        hop_depth=page.hop_depth,
        direct_link_count=page.direct_link_count,
        cycle_count=page.cycle_count,
        exhaustion=page.exhaustion,
        terminal_reason=page.terminal_reason,
        detail=page.detail,
        route_handle=page.route_handle,
        snapshot_revision=page.snapshot_revision,
        snapshot_digest=page.snapshot_digest,
        next_routes=[
            ContextRouteResponse(route_id=route.route_id, label=route.label, kind=route.kind)
            for route in page.next_routes
        ],
        opened=[item.handle for item in page.items],
    )


def _explore_input(person_id: str, body: ContextExploreRequest) -> ExploreInput:
    return ExploreInput(
        person_id=person_id,
        purpose=body.purpose,
        request_id=body.request_id,
        anchor_id=body.anchor_id,
        route_handle=body.route_handle,
        route_id=body.route_id,
        focus_id=body.focus_id,
        operation=body.operation,
        rewind_to_id=body.rewind_to_id,
        hold_at_anchor=body.hold_at_anchor,
    )


async def _event_text(client: httpx.AsyncClient, base: str, event_id: uuid.UUID) -> str:
    try:
        response = await client.get(f"{base}/vault/events/{event_id}/content")
        response.raise_for_status()
    except Exception:
        logger.warning("vault content unavailable for %s", event_id, exc_info=True)
        return ""
    return response.text


async def load_person_events(session: SessionDep, person_id: str) -> list[VaultEvent]:
    """Pointers from the vault, with excerpts read for this request only."""
    rows = await VaultRepository(session).list_events(uuid.UUID(person_id))
    if not rows:
        return []
    base = ApiSettings().vault_writer_url.rstrip("/")
    async with httpx.AsyncClient(timeout=5.0) as client:
        texts = [await _event_text(client, base, row.id) for row in rows]
    events: list[VaultEvent] = []
    for row, note in zip(rows, texts, strict=True):
        captured = row.captured_at.isoformat()
        events.append(
            VaultEvent(
                id=str(row.id),
                person_id=str(row.patient_id),
                captured_at=captured,
                source_type=row.source_type,
                text=note,
                content_hash=row.content_hash,
                lineage_id=str(row.id),
                document_id=None,
            )
        )
    return events


async def run_walk(
    session: SessionDep,
    person_id: str,
    events: list[VaultEvent],
    explore_input: ExploreInput,
) -> SemanticData:
    page = await session.run_sync(
        lambda sync_session: walk(sync_session, person_id, events, explore_input)
    )
    await session.commit()
    return page


_SKIP = {
    "a", "an", "the", "and", "or", "of", "with", "to", "for", "in", "on", "at", "from", "by", "as",
    "into", "over", "after", "before", "despite", "than", "more", "most", "many", "very", "began",
    "begin", "beginning", "showed", "shown", "described", "present", "since", "during", "without",
    "within", "not", "no", "its", "their", "this", "that", "were", "was", "are", "is", "been",
    "had", "have", "has",
}
_WEAK = {
    "loose", "recurrent", "marked", "additional", "longstanding", "high", "multiple", "negative",
    "elevated", "repeated", "persistent", "persisted", "unintentional", "exact", "value",
    "associated",
}
_PLAIN_REASON = {
    "explicitly_linked": "you linked these",
    "same_record_group": "same record",
    "derived_or_copied": "copied from another record",
    "near_in_time": "close in time",
    "possible_semantic_association": "may relate",
    "possible_inconsistency": "may not match",
    "recorded_association": "may relate",
}


def _present(word: str) -> str:
    if not word:
        return ""
    if len(word) <= 6 and word == word.upper():
        return word
    if any(char.isupper() for char in word[1:]):
        return word
    return word[0].upper() + word[1:].lower()


def circle_label(text: str, source_type: str, captured_at: str) -> str:
    """One word from the note for the circle. A date stands in when the note is empty."""
    line = text.split("\n", 1)[0].strip()
    colon = line.find(":")
    head = line[:colon].strip() if 0 < colon <= 28 else line
    cleaned = head.replace(";", " ").replace(",", " ").replace(".", " ").replace("/", " ")
    words = [word for word in cleaned.split() if len(word) > 1]
    specific = [
        word
        for word in words
        if word.lower() not in _SKIP and word.lower() not in _WEAK and len(word) <= 14
    ]
    pick = specific[0] if specific else next((word for word in words if len(word) <= 14), "")
    shown = _present(pick)
    if shown:
        return shown
    day = captured_at[:10]
    name = source_name(source_type)
    return f"{name} {day}" if day else name


def _map_response(model: ViewModel, events: list[VaultEvent]) -> ContextMapResponse:
    by_id = {event.id: event for event in events}
    nodes = [
        ContextMapNodeResponse(
            id=node.id,
            kind=node.kind,
            source_type=node.source_type,
            degree=node.degree,
            label="Record" if node.kind == "pseudonode" else circle_label(
                "" if (event := by_id.get(node.id)) is None else event.text,
                node.source_type,
                "" if event is None else event.captured_at,
            ),
        )
        for node in model.nodes
    ]
    ids = [node.id for node in model.nodes]
    links = [
        ContextMapLinkResponse(
            source=ids[link.source],
            target=ids[link.target],
            reason=_PLAIN_REASON.get(link.reason, "may relate"),
        )
        for link in model.links
        if 0 <= link.source < len(ids) and 0 <= link.target < len(ids)
    ]
    return ContextMapResponse(nodes=nodes, links=links)


async def run_map(session: SessionDep, person_id: str, events: list[VaultEvent]) -> ViewModel:
    return await session.run_sync(
        lambda sync_session: person_map(sync_session, person_id, events)
    )


@router.get("/context/map", response_model=ContextMapResponse)
async def context_map(principal: PrincipalDep, session: SessionDep) -> ContextMapResponse:
    person_id = _controller_only(principal)
    events = await load_person_events(session, person_id)
    model = await run_map(session, person_id, events)
    return _map_response(model, events)


@router.post("/context/explore", response_model=ContextExploreResponse)
async def explore_context(
    body: ContextExploreRequest,
    principal: PrincipalDep,
    session: SessionDep,
) -> ContextExploreResponse:
    person_id = _controller_only(principal)
    events = await load_person_events(session, person_id)
    page = await run_walk(session, person_id, events, _explore_input(person_id, body))
    return _page(page)
