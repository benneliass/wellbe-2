"""The three purposes share one request path and one failure path."""

from __future__ import annotations

import json
import logging
import random
from collections.abc import Mapping

from wellbe_agent_caller import (
    KEYWORD_PASS,
    LINK_JUDGMENT,
    VISION_READ,
    AskFailure,
    AskSuccess,
    Binding,
    Purpose,
    ask,
    register_purpose,
)
from wellbe_agent_caller.types import HttpResponse


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


def _chat(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "purpose": KEYWORD_PASS,
        "payload": {"text": "sleep cough fever headache fatigue nausea"},
        "binding": _binding(
            "openai",
            "https://api.openai.com/v1",
            "sk-sentinel-key-qq",
            "gpt-4o-mini",
            include_store_false=True,
        ),
        "env": {},
        "rng": random.Random(0),
    }
    values.update(overrides)
    return values


async def _ask(
    transport: FakeTransport, clock: Clock | None = None, **overrides: object
) -> AskSuccess | AskFailure:
    timer = clock or Clock()
    options = _chat(transport=transport, now=timer.now, sleep=timer.sleep, **overrides)
    return await ask(**options)  # type: ignore[arg-type]


def test_keywords_use_the_binding_and_keep_the_note_out_of_the_log() -> None:
    words = ["note-sentinel-qq", "sleep", "cough", "fever", "headache"]
    transport = FakeTransport([_ok(json.dumps({"keywords": words}))])
    grab = Grab()
    logger = logging.getLogger("wellbe.agent_caller")
    logger.setLevel(logging.INFO)
    logger.addHandler(grab)
    logger.propagate = False
    try:
        import asyncio

        result = asyncio.run(
            _ask(
                transport,
                payload={"text": "note-sentinel-qq sleep cough fever headache"},
            )
        )
    finally:
        logger.removeHandler(grab)
        logger.propagate = True

    assert isinstance(result, AskSuccess)
    assert result.value == {"keywords": words}
    assert result.model == "served-model"
    call = transport.calls[0]
    assert call["url"] == "https://api.openai.com/v1/chat/completions"
    payload = call["payload"]
    assert isinstance(payload, dict)
    assert payload["model"] == "gpt-4o-mini"
    assert payload["store"] is False
    assert "note-sentinel-qq" not in json.dumps(grab.blobs)
    assert "sk-sentinel-key-qq" not in json.dumps(grab.blobs)
    headers = call["headers"]
    assert isinstance(headers, dict)
    assert headers["Authorization"] == "Bearer sk-sentinel-key-qq"


def test_a_keyword_missing_from_the_note_does_not_retry() -> None:
    import asyncio

    words = ["sleep", "cough", "fever", "headache", "pneumonia"]
    transport = FakeTransport([_ok(json.dumps({"keywords": words}))])
    result = asyncio.run(
        _ask(
            transport,
            payload={"text": "note-sentinel-qq sleep cough fever headache fatigue"},
        )
    )
    assert isinstance(result, AskFailure)
    assert result.code == "invalid_output"
    assert len(transport.calls) == 1


def test_link_handle_must_be_one_this_request_issued() -> None:
    import asyncio

    payload = {"instruction": "Judge the map.", "content": "anchor h1", "issued_handles": ["h1"]}
    bad = FakeTransport(
        [_ok(json.dumps({"verdict": "link", "reason": "shared_context", "handle": "h9"}))]
    )
    rejected = asyncio.run(_ask(bad, purpose=LINK_JUDGMENT, payload=payload))
    assert isinstance(rejected, AskFailure)
    assert rejected.code == "invalid_output"
    assert len(bad.calls) == 1

    good = FakeTransport(
        [_ok(json.dumps({"verdict": "link", "reason": "shared_context", "handle": "h1"}))]
    )
    accepted = asyncio.run(_ask(good, purpose=LINK_JUDGMENT, payload=payload))
    assert isinstance(accepted, AskSuccess)
    assert accepted.value == {"verdict": "link", "reason": "shared_context", "handle": "h1"}


def test_vision_sends_one_image_and_no_schema() -> None:
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
    result = asyncio.run(
        _ask(
            transport,
            purpose=VISION_READ,
            payload={"page": "abc", "media_type": "image/png"},
            binding=binding,
        )
    )
    assert isinstance(result, AskSuccess)
    assert result.value == "platelet count 240"
    body = transport.calls[0]["payload"]
    assert isinstance(body, dict)
    assert "response_format" not in body
    assert "store" not in body
    assert "provider" not in body
    messages = body["messages"]
    assert isinstance(messages, list)
    user = messages[-1]["content"]
    assert isinstance(user, list)
    assert user[0]["image_url"]["url"] == "data:image/png;base64,abc"
    headers = transport.calls[0]["headers"]
    assert isinstance(headers, dict)
    assert headers["Authorization"] == "Bearer sk-or-sentinel"
    assert headers["X-OpenRouter-Title"] == "WellBe"


def test_server_error_retries_and_a_bad_key_does_not() -> None:
    import asyncio

    clock = Clock()
    retried = FakeTransport(
        [
            HttpResponse(status=503, body={}),
            _ok(json.dumps({"keywords": ["sleep", "cough", "fever", "headache", "fatigue"]})),
        ]
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

    words = ["sleep", "cough", "fever", "headache", "fatigue"]
    transport = FakeTransport(
        [
            HttpResponse(
                status=400, body={"error": {"message": "response_format is not supported"}}
            ),
            _ok(json.dumps({"keywords": words})),
        ]
    )
    result = asyncio.run(_ask(transport))
    assert isinstance(result, AskSuccess)
    first = transport.calls[0]["payload"]
    second = transport.calls[1]["payload"]
    assert isinstance(first, dict) and isinstance(second, dict)
    assert first["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": KEYWORD_PASS,
            "strict": True,
            "schema": first["response_format"]["json_schema"]["schema"],  # type: ignore[index]
        },
    }
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


def test_a_fourth_purpose_registers_without_a_new_client() -> None:
    import asyncio

    register_purpose(
        Purpose(
            name="lab_probe",
            kind="text",
            deadline_ms=5_000,
            max_tokens=20,
            send_fields=("content",),
            instruction="Reply with the word ready.",
        )
    )
    transport = FakeTransport([_ok("ready")])
    result = asyncio.run(_ask(transport, purpose="lab_probe", payload={"content": "ping"}))
    assert isinstance(result, AskSuccess)
    assert result.value == "ready"
    body = transport.calls[0]["payload"]
    assert isinstance(body, dict)
    assert body["model"] == "gpt-4o-mini"


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
    first = FakeTransport(
        [_ok(json.dumps({"keywords": ["sleep", "cough", "fever", "headache", "fatigue"]}))]
    )
    second = FakeTransport(
        [
            _ok(
                json.dumps(
                    {"verdict": "standalone", "reason": "insufficient_overlap", "handle": None}
                )
            )
        ]
    )
    keyword = asyncio.run(_ask(first, binding=openai))
    link = asyncio.run(
        _ask(
            second,
            purpose=LINK_JUDGMENT,
            payload={"instruction": "Judge.", "content": "map", "issued_handles": ["h1"]},
            binding=router,
        )
    )
    assert isinstance(keyword, AskSuccess)
    assert isinstance(link, AskSuccess)
    assert first.calls[0]["url"] == "https://api.openai.com/v1/chat/completions"
    assert second.calls[0]["url"] == "https://openrouter.ai/api/v1/chat/completions"
    first_headers = first.calls[0]["headers"]
    second_headers = second.calls[0]["headers"]
    assert isinstance(first_headers, dict) and isinstance(second_headers, dict)
    assert first_headers["Authorization"] == "Bearer sk-one"
    assert second_headers["Authorization"] == "Bearer sk-or-two"
    link_body = second.calls[0]["payload"]
    assert isinstance(link_body, dict)
    assert link_body["provider"] == {"require_parameters": True}


def test_bindings_read_separate_keys() -> None:
    from wellbe_agent_caller.bindings import load_bindings, resolve_binding

    env: Mapping[str, str] = {
        "OPENAI_API_KEY": "sk-personal",
        "OPENROUTER_API_KEY": "sk-or-router",
        "WELLBE_AGENT_OPENROUTER_MODEL": "openai/gpt-4o",
        "WELLBE_AGENT_BINDING": "openrouter",
        "WELLBE_AGENT_BINDING_VISION_READ": "openai",
    }
    table = load_bindings(env)
    assert table["openai"].api_key == "sk-personal"
    assert table["openrouter"].model == "openai/gpt-4o"
    assert resolve_binding(KEYWORD_PASS, env, table) == table["openrouter"]
    assert resolve_binding(VISION_READ, env, table) == table["openai"]
    assert resolve_binding(KEYWORD_PASS, {}, table) is None
