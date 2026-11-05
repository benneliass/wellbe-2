"""The small map's caller decides the link. A failure does not use the overlap heuristic."""

from __future__ import annotations

import json
import logging

from wellbe_agent_caller import Binding, known_purposes
from wellbe_agent_caller.types import HttpResponse
from wellbe_raw_context_brain.judge import _MAP_PURPOSE, MapDecision, sanitize_map_decision
from wellbe_raw_context_brain.router import LabOptions, RawContextLab
from wellbe_raw_context_brain.types import VaultEvent

_PERSON = "11111111-1111-1111-1111-111111111111"
_KEY = "sk-map-secret"
_WORDS = ("sleep", "morning", "rest", "quiet", "water")
_NOTE = "private morning note about rest"
_EARLIER = "earlier-vault-secret"


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


class _Reader:
    def __init__(self, texts: dict[str, str]) -> None:
        self.texts = texts
        self.reads: list[str] = []

    async def read(self, event_id: str) -> str:
        self.reads.append(event_id)
        if event_id not in self.texts:
            raise RuntimeError("unexpected read")
        return self.texts[event_id]


def _binding() -> Binding:
    return Binding(
        name="map-test",
        base_url="https://map.example/v1",
        api_key=_KEY,
        model="map-test-model",
    )


def _body(content: str) -> HttpResponse:
    return HttpResponse(
        status=200,
        body={"model": "map-test-model", "choices": [{"message": {"content": content}}]},
    )


def _keywords() -> HttpResponse:
    return _body(json.dumps({"keywords": list(_WORDS)}))


def _decision(
    action: str,
    handle: str | None = None,
    reason: str = "shared_context",
) -> HttpResponse:
    return _body(
        json.dumps(
            {"action": action, "handle": handle, "reasonCode": reason, "confidence": 0.6}
        )
    )


def _user_text(call: dict[str, object]) -> str:
    payload = call["payload"]
    assert isinstance(payload, dict)
    messages = payload["messages"]
    assert isinstance(messages, list)
    for message in messages:
        if isinstance(message, dict) and message.get("role") == "user":
            content = message.get("content")
            if isinstance(content, str):
                return content
    return ""


def _event(
    event_id: str,
    *,
    text: str,
    keywords: tuple[str, ...] = (),
    category: str | None = "note",
) -> VaultEvent:
    return VaultEvent(
        id=event_id,
        person_id=_PERSON,
        captured_at="2024-02-01T00:00:00.000Z",
        source_type="note",
        text=text,
        content_hash=event_id,
        lineage_id=event_id,
        document_id=None,
        category=category,
        keywords=keywords,
    )


def _lab(
    transport: _Transport,
    reader: _Reader | None = None,
    *,
    binding: Binding | None = None,
) -> RawContextLab:
    return RawContextLab(
        LabOptions(
            keyword_binding=_binding() if binding is None else binding,
            keyword_transport=transport,
            content_reader=reader,
        )
    )


def test_map_purpose_accepts_only_an_issued_handle() -> None:
    purpose = known_purposes()[_MAP_PURPOSE]
    assert purpose.check is not None
    issued = {"issued_handles": ["ih_1"]}
    assert purpose.check(
        {"action": "link", "handle": "ih_1", "reasonCode": "shared_context", "confidence": 0.4},
        issued,
    )
    assert not purpose.check(
        {"action": "link", "handle": "other", "reasonCode": "shared_context", "confidence": 0.4},
        issued,
    )
    clinical = sanitize_map_decision(
        MapDecision(action="link", handle="ih_1", reason_code="diagnosed cancer", confidence=0.9)
    )
    assert clinical.action == "uncertain"
    assert clinical.reason_code == "insufficient_overlap"
    assert clinical.handle is None


async def test_a_link_is_drawn_only_to_the_anchor(caplog: object) -> None:
    caplog.set_level(logging.INFO)  # type: ignore[attr-defined]
    transport = _Transport([_keywords(), _decision("link", "ih_1")])
    lab = _lab(transport)
    lab.add_fixture(_event("high", text=_EARLIER, keywords=_WORDS))
    lab.add_fixture(_event("new", text=_NOTE))
    result = await lab.place_bound_event(lab.vault.get("new") or _event("new", text=_NOTE))
    assert result.anchor_id == "high"
    assert result.judgments[0].accepted is True
    assert lab.accepted_neighbour_ids("new") == ["high"]
    sent = json.dumps(transport.calls[1]["payload"])
    written = caplog.text  # type: ignore[attr-defined]
    assert _EARLIER not in sent
    assert _NOTE in sent
    assert _NOTE not in written
    assert _KEY not in written
    assert "Do not diagnose" not in written


async def test_a_link_to_another_listed_node_is_not_kept() -> None:
    transport = _Transport([_keywords(), _decision("link", "ih_3")])
    lab = _lab(transport)
    lab.add_fixture(_event("high", text=_EARLIER, keywords=_WORDS))
    lab.add_fixture(
        _event(
            "side",
            text="side-secret",
            keywords=("sleep", "noise", "light", "desk", "page"),
        )
    )
    lab.link_structural("high", "side")
    lab.add_fixture(_event("new", text=_NOTE))
    await lab.place_bound_event(lab.vault.get("new") or _event("new", text=_NOTE))
    assert lab.accepted_neighbour_ids("new") == []


async def test_open_reads_one_node_and_a_walk_does_not_read() -> None:
    reader = _Reader({"side": "side-secret"})
    transport = _Transport(
        [
            _keywords(),
            _decision("open_content", "ih_3"),
            _decision("walk", "ih_1"),
            _decision("link", "ih_1"),
        ]
    )
    lab = _lab(transport, reader)
    lab.add_fixture(_event("high", text=_EARLIER, keywords=_WORDS))
    lab.add_fixture(
        _event("side", text="side-secret", keywords=("sleep", "noise", "light", "desk", "page"))
    )
    lab.link_structural("high", "side")
    lab.add_fixture(
        _event(
            "hidden",
            text="hidden-secret",
            keywords=("stone", "river", "cloud", "field", "path"),
        )
    )
    lab.add_fixture(_event("new", text=_NOTE))
    await lab.place_bound_event(lab.vault.get("new") or _event("new", text=_NOTE))
    assert reader.reads == ["side"]
    assert lab.accepted_neighbour_ids("new") == ["high"]
    opened = _user_text(transport.calls[2])
    linked = json.loads(_user_text(transport.calls[3]))
    assert isinstance(linked, dict)
    assert "side-secret" in opened
    assert "hidden-secret" not in opened
    assert "hidden-secret" not in json.dumps(linked)
    assert _EARLIER not in json.dumps(linked)
    assert linked.get("vantage") == "ih_1"


async def test_standalone_and_uncertain_keep_history_and_draw_no_line() -> None:
    transport = _Transport([_keywords(), _decision("standalone", reason="standalone")])
    lab = _lab(transport)
    lab.add_fixture(_event("high", text=_EARLIER, keywords=_WORDS))
    lab.add_fixture(_event("new", text=_NOTE))
    await lab.place_bound_event(lab.vault.get("new") or _event("new", text=_NOTE))
    assert lab.accepted_neighbour_ids("new") == []
    assert lab.log.ads[-1].judgment == "no_link"
    assert lab.log.ads[-1].reason_code == "standalone"
    assert lab.vault.get("new") is not None


async def test_a_clinical_reason_abstains() -> None:
    transport = _Transport([_keywords(), _decision("link", "ih_1", reason="diagnosed cancer")])
    lab = _lab(transport)
    lab.add_fixture(_event("high", text=_EARLIER, keywords=_WORDS))
    lab.add_fixture(_event("new", text=_NOTE))
    result = await lab.place_bound_event(lab.vault.get("new") or _event("new", text=_NOTE))
    assert result.judgments[0].judgment == "uncertain"
    assert lab.accepted_neighbour_ids("new") == []


async def test_reject_map_asks_the_next_lower_bar() -> None:
    transport = _Transport([_keywords(), _decision("reject_map"), _decision("link", "ih_1")])
    lab = _lab(transport)
    lab.add_fixture(_event("aaa", text="vault-aaa", keywords=_WORDS))
    lab.add_fixture(
        _event("bbb", text="vault-bbb", keywords=("sleep", "morning", "walk", "chair", "book"))
    )
    lab.add_fixture(_event("new", text=_NOTE))
    result = await lab.place_bound_event(lab.vault.get("new") or _event("new", text=_NOTE))
    assert result.anchor_id == "bbb"
    assert lab.accepted_neighbour_ids("new") == ["bbb"]
    assert lab.vault.get("new") is not None


async def test_a_map_caller_failure_does_not_use_the_overlap_heuristic() -> None:
    failed = HttpResponse(status=400, body={"error": "down"})
    transport = _Transport([_keywords(), failed, _decision("link", "ih_1")])
    lab = _lab(transport)
    lab.add_fixture(_event("high", text="morning fever and chills", keywords=_WORDS))
    lab.add_fixture(_event("new", text="morning fever and chills"))
    first = await lab.place_bound_event(lab.vault.get("new") or _event("new", text="x"))
    assert first.terminal_reason == "dependency_unavailable"
    assert lab.accepted_neighbour_ids("new") == []
    assert lab.was_placed("new") is False
    saved = lab.vault.get("new")
    assert saved is not None and saved.keywords == _WORDS
    second = await lab.place_bound_event(saved)
    assert second.anchor_id == "high"
    assert lab.accepted_neighbour_ids("new") == ["high"]


async def test_a_missing_binding_does_not_fall_back_to_the_heuristic() -> None:
    transport = _Transport([_keywords(), _decision("link", "ih_1")])
    configured = RawContextLab(LabOptions(keyword_transport=transport))
    note = "morning fever and chills"
    configured.add_fixture(_event("high", text=note, keywords=_WORDS))
    configured.add_fixture(_event("new", text=note))
    await configured.place_bound_event(configured.vault.get("new") or _event("new", text=note))
    assert configured.accepted_neighbour_ids("new") == []
    assert configured.vault.get("new") is not None

    heuristic = RawContextLab()
    heuristic.add_fixture(_event("high", text=note))
    heuristic.add_fixture(_event("new", text=note))
    await heuristic.place_bound_event(heuristic.vault.get("new") or _event("new", text=note))
    assert heuristic.accepted_neighbour_ids("new") == ["high"]
