"""A feature registers a purpose. The caller only sends, retries, and checks the answer."""

from __future__ import annotations

import json
import logging
import random
from collections.abc import Mapping

from wellbe_agent_caller import (
    AskFailure,
    AskSuccess,
    Binding,
    Field,
    Purpose,
    ask,
    register_purpose,
)
from wellbe_agent_caller.types import HttpResponse

_LABEL = "lab_label"
_PAGE = "lab_page"
_LABEL_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["label"],
    "properties": {"label": {"type": "string"}},
}


def _label_in_note(value: object, payload: Mapping[str, object]) -> bool:
    if not isinstance(value, dict):
        return False
    label = value.get("label")
    note = payload.get("note")
    return isinstance(label, str) and isinstance(note, str) and label.casefold() in note.casefold()


register_purpose(
    Purpose(
        name=_LABEL,
        deadline_ms=15_000,
        fields=(Field("note", "text"),),
        kind="schema",
        schema=_LABEL_SCHEMA,
        instruction="Return JSON with one label taken from the note.",
        check=_label_in_note,
    )
)
register_purpose(
    Purpose(
        name=_PAGE,
        deadline_ms=15_000,
        fields=(Field("page", "image"),),
        kind="text",
        instruction="Read the page.",
    )
)


class Clock:
    def __init__(self) -> None:
        self.t = 0.0
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self.t

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.t += seconds


class FakeTransport:
    def __init__(self, responses: list[HttpResponse]) -> None:
        self._responses = responses
        self.calls: list[dict[str, object]] = []

    async def post(
        self,
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
        timeout_s: float,
    ) -> HttpResponse:
        self.calls.append(
            {"url": url, "payload": payload, "headers": dict(headers), "timeout_s": timeout_s}
        )
        return self._responses.pop(0)


class Grab(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.blobs: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.blobs.append(f"{record.getMessage()} {record.__dict__}")


def _binding(name: str, url: str, key: str, model: str, **kwargs: object) -> Binding:
    return Binding(name=name, base_url=url, api_key=key, model=model, **kwargs)  # type: ignore[arg-type]


def _ok(content: str, model: str = "served-model") -> HttpResponse:
    return HttpResponse(
        status=200,
        body={
            "model": model,
            "choices": [{"finish_reason": "stop", "message": {"content": content}}],
        },
    )


def _openai() -> Binding:
    return _binding(
        "openai",
        "https://api.openai.com/v1",
        "sk-sentinel-key-qq",
        "gpt-4o-mini",
        include_store_false=True,
        completion_tokens=True,
    )


async def _ask(
    transport: FakeTransport, clock: Clock | None = None, **overrides: object
) -> AskSuccess | AskFailure:
    timer = clock or Clock()
    options: dict[str, object] = {
        "purpose": _LABEL,
        "payload": {"note": "note-sentinel-qq sleep"},
        "binding": _openai(),
        "env": {},
        "rng": random.Random(0),
        "transport": transport,
        "now": timer.now,
        "sleep": timer.sleep,
    }
    options.update(overrides)
    return await ask(**options)  # type: ignore[arg-type]


def test_a_registered_purpose_uses_its_binding_and_keeps_the_note_out_of_the_log() -> None:
    import asyncio

    transport = FakeTransport([_ok(json.dumps({"label": "sleep"}))])
    grab = Grab()
    logger = logging.getLogger("wellbe.agent_caller")
    logger.setLevel(logging.INFO)
    logger.addHandler(grab)
    logger.propagate = False
    try:
        result = asyncio.run(_ask(transport))
    finally:
        logger.removeHandler(grab)
        logger.propagate = True

    assert isinstance(result, AskSuccess)
    assert result.value == {"label": "sleep"}
    assert result.model == "served-model"
    call = transport.calls[0]
    assert call["url"] == "https://api.openai.com/v1/chat/completions"
    payload = call["payload"]
    assert isinstance(payload, dict)
    assert payload["model"] == "gpt-4o-mini"
    assert payload["store"] is False
    assert payload["max_completion_tokens"] == 1024
    assert "max_tokens" not in payload
    assert "temperature" not in payload
    logged = json.dumps(grab.blobs)
    assert "note-sentinel-qq" not in logged
    assert "sk-sentinel-key-qq" not in logged
    assert "sleep" not in logged
    headers = call["headers"]
    assert isinstance(headers, dict)
    assert headers["Authorization"] == "Bearer sk-sentinel-key-qq"


def test_a_failed_check_does_not_retry() -> None:
    import asyncio

    transport = FakeTransport([_ok(json.dumps({"label": "pneumonia"}))])
    result = asyncio.run(_ask(transport))
    assert isinstance(result, AskFailure)
    assert result.code == "invalid_output"
    assert result.purpose == _LABEL
    assert len(transport.calls) == 1


def test_an_image_field_is_sent_as_given_and_text_has_no_schema() -> None:
    import asyncio

    transport = FakeTransport([_ok("platelet count 240")])
    binding = _binding(
        "openrouter",
        "https://openrouter.ai/api/v1",
        "sk-or-sentinel",
        "openai/gpt-4o-mini",
        require_parameters=True,
        headers=(("X-OpenRouter-Title", "WellBe"),),
    )
    page = "data:image/png;base64,abc"
    result = asyncio.run(
        _ask(transport, purpose=_PAGE, payload={"page": page}, binding=binding)
    )
    assert isinstance(result, AskSuccess)
    assert result.value == "platelet count 240"
    body = transport.calls[0]["payload"]
    assert isinstance(body, dict)
    assert "response_format" not in body
    assert "provider" not in body
    assert body["max_tokens"] == 1024
    assert body["temperature"] == 0
    assert "max_completion_tokens" not in body
    messages = body["messages"]
    assert isinstance(messages, list)
    user = messages[-1]["content"]
    assert isinstance(user, list)
    assert user[0]["image_url"]["url"] == page
    headers = transport.calls[0]["headers"]
    assert isinstance(headers, dict)
    assert headers["Authorization"] == "Bearer sk-or-sentinel"


def test_server_error_retries_and_a_bad_key_does_not() -> None:
    import asyncio

    clock = Clock()
    retried = FakeTransport(
        [HttpResponse(status=503, body={}), _ok(json.dumps({"label": "sleep"}))]
    )
    recovered = asyncio.run(_ask(retried, clock))
    assert isinstance(recovered, AskSuccess)
    assert len(retried.calls) == 2
    assert clock.sleeps

    denied = FakeTransport([HttpResponse(status=401, body={})])
    failed = asyncio.run(_ask(denied))
    assert isinstance(failed, AskFailure)
    assert failed.code == "dependency_unavailable"
    assert len(denied.calls) == 1


def test_retry_after_beyond_the_deadline_stops() -> None:
    import asyncio

    clock = Clock()
    transport = FakeTransport(
        [HttpResponse(status=429, body={"error": {"code": "rate_limit"}}, retry_after_s=30)]
    )
    result = asyncio.run(_ask(transport, clock))
    assert isinstance(result, AskFailure)
    assert result.code == "dependency_unavailable"
    assert len(transport.calls) == 1
    assert clock.sleeps == []


def test_unsupported_schema_downgrades_once() -> None:
    import asyncio

    transport = FakeTransport(
        [
            HttpResponse(
                status=400,
                body={"error": {"message": "response_format is not supported"}},
            ),
            _ok(json.dumps({"label": "sleep"})),
        ]
    )
    result = asyncio.run(_ask(transport))
    assert isinstance(result, AskSuccess)
    first = transport.calls[0]["payload"]
    second = transport.calls[1]["payload"]
    assert isinstance(first, dict) and isinstance(second, dict)
    first_format = first["response_format"]
    assert isinstance(first_format, dict)
    assert first_format["type"] == "json_schema"
    assert second["response_format"] == {"type": "json_object"}


def test_missing_binding_and_a_full_gate_do_not_call() -> None:
    import asyncio

    transport = FakeTransport([])
    missing = asyncio.run(_ask(transport, binding=None, env={}))
    assert isinstance(missing, AskFailure)
    assert missing.code == "dependency_unavailable"
    assert transport.calls == []

    blocked = FakeTransport([_ok("{}")])
    full = asyncio.run(_ask(blocked, max_in_flight=0))
    assert isinstance(full, AskFailure)
    assert blocked.calls == []


def test_a_second_purpose_uses_the_same_caller() -> None:
    import asyncio

    register_purpose(
        Purpose(
            name="lab_echo",
            deadline_ms=5_000,
            fields=(Field("content", "text"),),
            kind="text",
            instruction="Reply with the word ready.",
        )
    )
    transport = FakeTransport([_ok("ready")])
    result = asyncio.run(_ask(transport, purpose="lab_echo", payload={"content": "ping"}))
    assert isinstance(result, AskSuccess)
    assert result.value == "ready"


def test_two_purposes_keep_their_own_bindings() -> None:
    import asyncio

    openai = _binding(
        "openai",
        "https://api.openai.com/v1",
        "sk-one",
        "gpt-4o-mini",
        include_store_false=True,
    )
    router = _binding(
        "openrouter",
        "https://openrouter.ai/api/v1",
        "sk-or-two",
        "openai/gpt-4o-mini",
        require_parameters=True,
    )
    first = FakeTransport([_ok(json.dumps({"label": "sleep"}))])
    second = FakeTransport([_ok("ready")])
    label = asyncio.run(_ask(first, binding=openai))
    page = asyncio.run(
        _ask(
            second,
            purpose=_PAGE,
            payload={"page": "data:image/jpeg;base64,abc"},
            binding=router,
        )
    )
    assert isinstance(label, AskSuccess)
    assert isinstance(page, AskSuccess)
    assert first.calls[0]["url"] == "https://api.openai.com/v1/chat/completions"
    assert second.calls[0]["url"] == "https://openrouter.ai/api/v1/chat/completions"
    first_headers = first.calls[0]["headers"]
    second_headers = second.calls[0]["headers"]
    assert isinstance(first_headers, dict) and isinstance(second_headers, dict)
    assert first_headers["Authorization"] == "Bearer sk-one"
    assert second_headers["Authorization"] == "Bearer sk-or-two"
    routed = FakeTransport([_ok(json.dumps({"label": "sleep"}))])
    routed_result = asyncio.run(_ask(routed, binding=router))
    assert isinstance(routed_result, AskSuccess)
    routed_body = routed.calls[0]["payload"]
    assert isinstance(routed_body, dict)
    assert routed_body["provider"] == {"require_parameters": True}


def test_bindings_read_separate_keys() -> None:
    from wellbe_agent_caller.bindings import load_bindings, resolve_binding

    env: Mapping[str, str] = {
        "OPENAI_API_KEY": "sk-personal",
        "OPENROUTER_API_KEY": "sk-or-router",
        "WELLBE_AGENT_OPENROUTER_MODEL": "openai/gpt-4o",
        "WELLBE_AGENT_BINDING": "openrouter",
        "WELLBE_AGENT_BINDING_LAB_PAGE": "openai",
    }
    table = load_bindings(env)
    assert table["openai"].api_key == "sk-personal"
    assert table["openrouter"].model == "openai/gpt-4o"
    assert resolve_binding(_LABEL, env, table) == table["openrouter"]
    assert resolve_binding(_PAGE, env, table) == table["openai"]
    assert resolve_binding(_LABEL, {}, table) is None
