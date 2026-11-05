"""A new record stores keywords and the anchor is the best shared-keyword overlap."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import replace

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from wellbe_agent_caller import Binding, known_purposes
from wellbe_agent_caller.types import HttpResponse
from wellbe_raw_context_brain.keywords import (
    KEYWORD_BAR_FLOOR,
    KEYWORD_BAR_X,
    KEYWORD_BAR_Y,
    KEYWORD_PURPOSE,
    MINI_MAP_DEPTH,
    model_payload,
)
from wellbe_raw_context_brain.persist.sql_store import SqlGraphStore
from wellbe_raw_context_brain.router import LabOptions, RawContextLab
from wellbe_raw_context_brain.types import PointerNode, VaultEvent

_PERSON = "11111111-1111-1111-1111-111111111111"
_OTHER = "22222222-2222-2222-2222-222222222222"
_KEY = "sk-test-keyword-secret"
_WORDS = ("sleep", "morning", "rest", "quiet", "water")
_NOTE = "private morning note about rest"


class _Transport:
    def __init__(self, responses: list[HttpResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []

    async def post(
        self,
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
        timeout_s: float,
    ) -> HttpResponse:
        self.calls.append({"url": url, "payload": payload, "headers": dict(headers)})
        return self.responses.pop(0)


def _binding() -> Binding:
    return Binding(
        name="keyword-test",
        base_url="https://keywords.example/v1",
        api_key=_KEY,
        model="keyword-test-model",
    )


def _hold() -> HttpResponse:
    content = json.dumps(
        {
            "action": "no_link",
            "handle": None,
            "reasonCode": "insufficient_overlap",
            "confidence": 0.2,
        }
    )
    return HttpResponse(
        status=200,
        body={"model": "keyword-test-model", "choices": [{"message": {"content": content}}]},
    )


def _ok(words: tuple[str, ...] = _WORDS) -> HttpResponse:
    content = json.dumps({"keywords": list(words)})
    return HttpResponse(
        status=200,
        body={"model": "keyword-test-model", "choices": [{"message": {"content": content}}]},
    )


def _event(
    event_id: str,
    *,
    text: str = "earlier note",
    category: str | None = "note",
    keywords: tuple[str, ...] = (),
    person_id: str = _PERSON,
) -> VaultEvent:
    return VaultEvent(
        id=event_id,
        person_id=person_id,
        captured_at="2024-02-01T00:00:00.000Z",
        source_type="note",
        text=text,
        content_hash=event_id,
        lineage_id=event_id,
        document_id=None,
        category=category,
        keywords=keywords,
    )


def _lab(transport: _Transport) -> RawContextLab:
    return RawContextLab(
        LabOptions(
            keyword_binding=_binding(),
            keyword_transport=transport,
        )
    )


def test_keyword_purpose_rejects_a_list_outside_five_to_ten() -> None:
    purpose = known_purposes()[KEYWORD_PURPOSE]
    assert purpose.check is not None
    assert purpose.schema is not None
    assert purpose.check({"keywords": list(_WORDS)}, {})
    assert not purpose.check({"keywords": ["a", "b", "c", "d"]}, {})
    assert not purpose.check({"keywords": [str(i) for i in range(11)]}, {})
    assert not purpose.check({"keywords": [" ", "b", "c", "d", "e"]}, {})
    assert KEYWORD_BAR_X == 3
    assert KEYWORD_BAR_Y == 2
    assert KEYWORD_BAR_FLOOR == 1
    assert MINI_MAP_DEPTH == 10


async def test_keywords_are_stored_once_and_a_later_placement_keeps_them() -> None:
    transport = _Transport([_ok(), _ok(("other", "words", "that", "must", "stay"))])
    lab = _lab(transport)
    lab.add_fixture(_event("new", text=_NOTE))
    first = await lab.place_bound_event(lab.vault.get("new") or _event("new"))
    second = await lab.place_bound_event(lab.vault.get("new") or _event("new"))
    assert first.keywords == _WORDS
    assert lab.vault.get("new") is not None
    assert lab.vault.get("new").keywords == _WORDS  # type: ignore[union-attr]
    assert second.keywords == ()
    assert len(transport.calls) == 1
    assert lab.accepted_neighbour_ids("new") == []


async def test_a_record_that_already_has_keywords_is_not_asked_again() -> None:
    transport = _Transport([_ok(("other", "words", "that", "must", "stay"))])
    lab = _lab(transport)
    lab.add_fixture(_event("new", text=_NOTE, keywords=_WORDS))
    result = await lab.place_bound_event(lab.vault.get("new") or _event("new"))
    assert transport.calls == []
    assert result.keywords == _WORDS


async def test_the_anchor_is_the_greatest_same_category_overlap() -> None:
    transport = _Transport([_ok(), _hold()])
    lab = _lab(transport)
    lab.add_fixture(_event("high", text="vault-high", keywords=_WORDS))
    lab.add_fixture(
        _event("mid", text="vault-mid", keywords=("sleep", "morning", "walk", "chair", "book"))
    )
    lab.add_fixture(_event("other-cat", text="vault-high", category="lab", keywords=_WORDS))
    lab.add_fixture(_event("other-person", text="vault-high", keywords=_WORDS, person_id=_OTHER))
    lab.add_fixture(_event("new", text=_NOTE))
    result = await lab.place_bound_event(lab.vault.get("new") or _event("new"))
    assert result.anchor_id == "high"
    assert result.mini_map is not None
    assert result.mini_map.anchor_id == "high"
    assert result.mini_map.bar == KEYWORD_BAR_X
    assert lab.accepted_neighbour_ids("new") == []


async def test_a_hub_is_never_the_anchor() -> None:
    transport = _Transport([_ok(), _hold()])
    lab = _lab(transport)
    lab.add_fixture(_event("hubish", text="vault-hub", keywords=_WORDS))
    lab.add_fixture(
        _event(
            "content",
            text="vault-content",
            keywords=("sleep", "morning", "rest", "alpha", "beta"),
        )
    )
    lab._nodes["hubish"] = replace(lab._nodes["hubish"], kind="pseudonode")
    lab.link_structural("hubish", "content", "membership")
    lab.add_fixture(_event("new", text=_NOTE))
    result = await lab.place_bound_event(lab.vault.get("new") or _event("new"))
    assert result.anchor_id == "content"
    assert result.mini_map is not None
    assert "hubish" not in {node.node_id for node in result.mini_map.nodes}


async def test_equal_overlap_prefers_the_lower_degree() -> None:
    transport = _Transport([_ok(), _hold()])
    lab = _lab(transport)
    shared = ("sleep", "morning", "rest", "alpha", "beta")
    other = ("sleep", "morning", "rest", "gamma", "delta")
    lab.add_fixture(_event("isolated", keywords=shared))
    lab.add_fixture(_event("busy", keywords=other))
    for index in range(3):
        lab.add_fixture(_event(f"filler-{index}", category="filler"))
        lab.link_structural("busy", f"filler-{index}")
    lab.add_fixture(_event("new", text=_NOTE))
    result = await lab.place_bound_event(lab.vault.get("new") or _event("new"))
    assert result.anchor_id == "isolated"


async def test_the_mini_map_reaches_ten_steps_and_leaves_earlier_text_out() -> None:
    transport = _Transport([_ok(), _hold()])
    lab = _lab(transport)
    chain = [f"c{index:02d}" for index in range(12)]
    for event_id in chain:
        words = _WORDS if event_id == "c00" else ("sleep", "noise", "light", "desk", "page")
        lab.add_fixture(_event(event_id, text=f"vault-text-{event_id}", keywords=words))
    for index in range(len(chain) - 1):
        lab.link_structural(chain[index], chain[index + 1])
    lab._nodes["hub"] = PointerNode(
        id="hub",
        kind="pseudonode",
        vault_event_id=None,
        member_event_ids=("c00",),
        person_id=_PERSON,
    )
    lab.link_structural("c00", "hub", "membership")
    lab.add_fixture(_event("new", text=_NOTE))
    result = await lab.place_bound_event(lab.vault.get("new") or _event("new"))
    assert result.mini_map is not None
    listed = {node.node_id for node in result.mini_map.nodes}
    assert result.anchor_id == "c00"
    assert "c10" in listed
    assert "c11" not in listed
    assert "hub" not in listed
    assert "new" in listed
    contents = {node.node_id: node.content for node in result.mini_map.nodes}
    assert contents["new"] == _NOTE
    assert all(value is None for node_id, value in contents.items() if node_id != "new")
    payload = json.dumps(model_payload(result.mini_map))
    assert _NOTE in payload
    for event_id in chain:
        assert f"vault-text-{event_id}" not in payload
        assert event_id not in payload
    assert "hub" not in payload
    assert _KEY not in payload


async def test_the_second_pass_excludes_the_first_anchor() -> None:
    transport = _Transport([_ok(), _hold()])
    lab = _lab(transport)
    lab.add_fixture(_event("first", text="vault-first", keywords=_WORDS))
    lab.add_fixture(
        _event(
            "second",
            text="vault-second",
            keywords=("sleep", "morning", "walk", "chair", "book"),
        )
    )
    lab.link_structural("first", "second")
    lab.add_fixture(_event("new", text=_NOTE))
    opened = await lab.place_bound_event(lab.vault.get("new") or _event("new"))
    again = lab.lower_keyword_bar("new")
    assert opened.anchor_id == "first"
    assert again.anchor_id == "second"
    assert again.mini_map is not None
    assert again.mini_map.bar == KEYWORD_BAR_Y
    assert "first" not in {node.node_id for node in again.mini_map.nodes}
    assert lab.accepted_neighbour_ids("new") == []


async def test_no_anchor_at_the_floor_stores_keywords_and_writes_no_link() -> None:
    transport = _Transport([_ok()])
    lab = _lab(transport)
    lab.add_fixture(
        _event("apart", keywords=("stone", "river", "cloud", "field", "path"), text="vault-apart")
    )
    lab.add_fixture(_event("new", text=_NOTE))
    result = await lab.place_bound_event(lab.vault.get("new") or _event("new"))
    assert result.anchor_id is None
    assert result.mini_map is None
    assert result.keywords == _WORDS
    assert lab.vault.get("new") is not None
    assert lab.vault.get("new").keywords == _WORDS  # type: ignore[union-attr]
    assert lab.accepted_neighbour_ids("new") == []
    assert lab._keyword_sessions["new"].bar_index == 2


async def test_a_caller_failure_stores_no_keywords_and_writes_no_link() -> None:
    failed = HttpResponse(status=400, body={"error": "no"})
    transport = _Transport([failed, _ok(), _hold()])
    lab = _lab(transport)
    lab.add_fixture(_event("high", keywords=_WORDS))
    lab.add_fixture(_event("new", text=_NOTE))
    result = await lab.place_bound_event(lab.vault.get("new") or _event("new"))
    assert result.keywords == ()
    assert result.anchor_id is None
    assert lab.vault.get("new") is not None
    assert lab.vault.get("new").keywords == ()  # type: ignore[union-attr]
    assert lab.accepted_neighbour_ids("new") == []
    assert lab.was_placed("new") is False
    recovered = await lab.place_bound_event(lab.vault.get("new") or _event("new"))
    assert recovered.keywords == _WORDS
    assert recovered.anchor_id == "high"


async def test_a_rejected_keyword_list_does_not_guess(caplog: object) -> None:
    blanks = (" ", " ", " ", " ", " ")
    transport = _Transport([_ok(blanks), _ok()])
    lab = _lab(transport)
    lab.add_fixture(_event("new", text=_NOTE))
    result = await lab.place_bound_event(lab.vault.get("new") or _event("new"))
    assert result.keywords == ()
    assert lab.was_placed("new") is True
    assert lab.accepted_neighbour_ids("new") == []
    again = await lab.place_bound_event(lab.vault.get("new") or _event("new"))
    assert again.keywords == ()
    assert len(transport.calls) == 1


async def test_logs_do_not_carry_the_note_or_the_key(caplog: object) -> None:
    caplog.set_level(logging.INFO)  # type: ignore[attr-defined]
    transport = _Transport([_ok()])
    lab = _lab(transport)
    lab.add_fixture(_event("new", text=_NOTE))
    await lab.place_bound_event(lab.vault.get("new") or _event("new"))
    written = caplog.text  # type: ignore[attr-defined]
    assert _NOTE not in written
    assert _KEY not in written
    assert "Do not name a condition" not in written
    assert transport.calls
    sent = json.dumps(transport.calls[0]["payload"])
    assert _NOTE in sent


def test_keywords_survive_a_pointer_snapshot_and_the_note_stays_out() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE graph_snapshot ("
                "person_id TEXT PRIMARY KEY, snapshot TEXT NOT NULL, updated_at TEXT)"
            )
        )
    factory = sessionmaker(bind=engine)
    transport = _Transport([_ok(), _hold()])
    with factory() as session:
        lab = RawContextLab(
            LabOptions(
                graph_store=SqlGraphStore(session, _PERSON, table_prefix=""),
                pointer_only=True,
                keyword_binding=_binding(),
                keyword_transport=transport,
            )
        )
        lab.add_fixture(_event("high", text="vault-high", keywords=_WORDS))
        lab.add_fixture(_event("new", text=_NOTE))
        result = asyncio.run(lab.place_bound_event(lab.vault.get("new") or _event("new")))
        session.commit()
        assert result.anchor_id == "high"
        stored = session.execute(
            text("SELECT snapshot FROM graph_snapshot WHERE person_id = :person_id"),
            {"person_id": _PERSON},
        ).scalar_one()
        assert _NOTE not in stored
        assert "vault-high" not in stored
        assert '"judgment":"link"' not in stored
        assert list(_WORDS)[0] in stored
        reloaded = RawContextLab(
            LabOptions(
                graph_store=SqlGraphStore(session, _PERSON, table_prefix=""),
                pointer_only=True,
                keyword_binding=_binding(),
                keyword_transport=_Transport([_ok(("other", "words", "that", "must", "stay"))]),
            )
        )
        saved = reloaded.vault.get("new")
        assert saved is not None
        assert saved.keywords == _WORDS
        assert saved.text == ""
        assert reloaded.was_placed("new") is True
