"""Ask a named purpose. This module owns the only retry loop."""

from __future__ import annotations

import asyncio
import json
import logging
import random
import threading
import time
from collections.abc import Awaitable, Callable, Mapping

from wellbe_agent_caller.bindings import resolve_binding
from wellbe_agent_caller.http import ConnectionFailure, urllib_post
from wellbe_agent_caller.types import (
    AskFailure,
    AskSuccess,
    Binding,
    FailureCode,
    HttpResponse,
    Purpose,
    Transport,
)
from wellbe_agent_caller.validate import matches

_log = logging.getLogger("wellbe.agent_caller")
_ATTEMPTS = 3
_MAX_SLEEP_S = 8.0
_RETRYABLE = frozenset({408, 500, 502, 503, 504, 529})
_BILLING_CODES = frozenset(
    {
        "credit_balance_exhausted",
        "organization_spend_limit_exceeded",
        "project_spend_limit_exceeded",
        "organization_usage_limit_exceeded",
    }
)
_REFUSAL_REASONS = frozenset({"content_filter", "refusal"})
_SCHEMA_MODES = ("json_schema", "json_object", "prompt")

_purposes: dict[str, Purpose] = {}
_in_flight = 0
_in_flight_lock = threading.Lock()


def register_purpose(purpose: Purpose) -> None:
    _purposes[purpose.name] = purpose


def known_purposes() -> Mapping[str, Purpose]:
    return dict(_purposes)


class _Clock:
    def now(self) -> float:
        return time.monotonic()

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


class _UrllibTransport:
    async def post(
        self,
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
        timeout_s: float,
    ) -> HttpResponse:
        return await asyncio.to_thread(urllib_post, url, payload, headers, timeout_s)


async def ask(
    purpose: str,
    payload: Mapping[str, object],
    *,
    binding: Binding | None = None,
    transport: Transport | None = None,
    now: Callable[[], float] | None = None,
    sleep: Callable[[float], Awaitable[None]] | None = None,
    rng: random.Random | None = None,
    max_in_flight: int = 4,
    env: Mapping[str, str] | None = None,
) -> AskSuccess | AskFailure:
    row = _purposes.get(purpose)
    if row is None:
        _record(purpose, "", 0, 0, None, "stop")
        return AskFailure(purpose=purpose, code="dependency_unavailable")
    selected = binding if binding is not None else resolve_binding(purpose, env)
    if selected is None:
        _record(purpose, "", 0, 0, None, "stop")
        return AskFailure(purpose=purpose, code="dependency_unavailable")
    if _payload_error(row, payload) is not None:
        _record(purpose, selected.name, 0, 0, None, "stop")
        return AskFailure(purpose=purpose, code="invalid_output")

    clock = _Clock()
    clock_now = now or clock.now
    clock_sleep = sleep or clock.sleep
    picker = rng or random.Random()
    client = transport or _UrllibTransport()
    started = clock_now()
    deadline = row.deadline_ms / 1000
    corrective = False
    waited = False
    last_code: FailureCode = "dependency_unavailable"

    for attempt in range(_ATTEMPTS):
        current = clock_now()
        remaining = started + deadline - current
        if remaining <= 0.05:
            _record(purpose, selected.name, attempt, 0, None, "stop")
            return AskFailure(purpose=purpose, code="dependency_unavailable")
        if attempt > 0 and not corrective and not waited:
            delay = _delay(attempt, picker)
            if delay > remaining:
                _record(purpose, selected.name, attempt, 0, None, "stop")
                return AskFailure(purpose=purpose, code="dependency_unavailable")
            if delay > 0:
                await clock_sleep(delay)
                remaining = started + deadline - clock_now()
                if remaining <= 0.05:
                    _record(purpose, selected.name, attempt, 0, None, "stop")
                    return AskFailure(purpose=purpose, code="dependency_unavailable")

        outcome = await _attempt(
            row,
            payload,
            selected,
            client,
            remaining,
            attempt,
            corrective,
            max_in_flight,
            started,
            clock_now,
            clock_sleep,
        )
        if isinstance(outcome, AskSuccess | AskFailure):
            return outcome
        if outcome == "grounded":
            return AskFailure(purpose=purpose, code="invalid_output")
        if outcome == "refused":
            return AskFailure(purpose=purpose, code="refused")
        waited = outcome == "honored"
        corrective = outcome == "shape"
        last_code = "invalid_output" if corrective else "dependency_unavailable"
    return AskFailure(purpose=purpose, code=last_code)


async def _attempt(
    row: Purpose,
    payload: Mapping[str, object],
    binding: Binding,
    transport: Transport,
    remaining: float,
    attempt: int,
    corrective: bool,
    max_in_flight: int,
    started: float,
    now: Callable[[], float],
    sleep: Callable[[float], Awaitable[None]],
) -> AskSuccess | AskFailure | str:
    """Return a finished result, or a step name: grounded, refused, shape, retry, honored."""

    global _in_flight
    with _in_flight_lock:
        if _in_flight >= max_in_flight:
            _record(row.name, binding.name, attempt, 0, None, "stop")
            return AskFailure(purpose=row.name, code="dependency_unavailable")
        _in_flight += 1
    try:
        return await _post_modes(
            row, payload, binding, transport, remaining, attempt, corrective, started, now, sleep
        )
    finally:
        with _in_flight_lock:
            _in_flight -= 1


async def _post_modes(
    row: Purpose,
    payload: Mapping[str, object],
    binding: Binding,
    transport: Transport,
    remaining: float,
    attempt: int,
    corrective: bool,
    started: float,
    now: Callable[[], float],
    sleep: Callable[[float], Awaitable[None]],
) -> AskSuccess | AskFailure | str:
    modes = _SCHEMA_MODES if row.kind == "schema" else ("prompt",)
    for mode in modes:
        left = started + (row.deadline_ms / 1000) - now()
        timeout = min(remaining, left) if left > 0 else 0
        if timeout <= 0.05:
            _record(row.name, binding.name, attempt, 0, None, "stop")
            return AskFailure(purpose=row.name, code="dependency_unavailable")
        body = _request_body(row, payload, binding, mode, corrective)
        headers = _headers(binding)
        url = f"{binding.base_url}/chat/completions"
        began = now()
        try:
            response = await transport.post(url, body, headers, timeout)
        except ConnectionFailure:
            _record(row.name, binding.name, attempt, _elapsed(began, now), None, "retry")
            return "retry"
        elapsed = _elapsed(began, now)
        if _schema_rejected(response, mode):
            _record(row.name, binding.name, attempt, elapsed, response.status, "downgrade")
            continue
        if response.status == 429 and _billing(response):
            _record(row.name, binding.name, attempt, elapsed, response.status, "stop")
            return AskFailure(purpose=row.name, code="dependency_unavailable")
        if _retryable(response):
            if response.retry_after_s is not None:
                left_after = started + (row.deadline_ms / 1000) - now()
                if response.retry_after_s > left_after:
                    _record(row.name, binding.name, attempt, elapsed, response.status, "stop")
                    return AskFailure(purpose=row.name, code="dependency_unavailable")
                await sleep(response.retry_after_s)
                _record(row.name, binding.name, attempt, elapsed, response.status, "retry")
                return "honored"
            _record(row.name, binding.name, attempt, elapsed, response.status, "retry")
            return "retry"
        if response.status < 200 or response.status >= 300:
            _record(row.name, binding.name, attempt, elapsed, response.status, "stop")
            return AskFailure(purpose=row.name, code="dependency_unavailable")
        _record(row.name, binding.name, attempt, elapsed, response.status, "ok")
        return _read_success(row, payload, response, binding.model)
    _record(row.name, binding.name, attempt, 0, 400, "stop")
    return AskFailure(purpose=row.name, code="dependency_unavailable")


def _read_success(
    row: Purpose,
    payload: Mapping[str, object],
    response: HttpResponse,
    fallback_model: str,
) -> AskSuccess | AskFailure | str:
    message = _message(response.body)
    if message is None:
        return "shape"
    if message[0] == "refused":
        return "refused"
    if message[0] == "truncated":
        return "shape"
    content = message[1]
    model = _response_model(response.body, fallback_model)
    if row.kind == "text":
        if content.strip() == "":
            return "shape"
        if not _passes_check(row, content, payload):
            return "grounded"
        return AskSuccess(purpose=row.name, value=content, model=model)
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return "shape"
    if not isinstance(parsed, dict) or row.schema is None or not matches(row.schema, parsed):
        return "shape"
    if not _passes_check(row, parsed, payload):
        return "grounded"
    return AskSuccess(purpose=row.name, value=parsed, model=model)


def _request_body(
    row: Purpose,
    payload: Mapping[str, object],
    binding: Binding,
    mode: str,
    corrective: bool,
) -> dict[str, object]:
    # OpenAI's current chat-completions field is max_completion_tokens.
    # Reasoning models reject max_tokens, temperature, top_p, and the penalties.
    # A local server still expects max_tokens and a temperature.
    if binding.completion_tokens:
        limit: dict[str, object] = {"max_completion_tokens": row.max_tokens}
    else:
        limit = {"max_tokens": row.max_tokens, "temperature": 0}
    body: dict[str, object] = {
        "model": binding.model,
        "messages": _messages(row, payload, corrective),
        **limit,
    }
    if mode == "json_schema" and row.schema is not None:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": row.name, "strict": True, "schema": row.schema},
        }
    elif mode == "json_object":
        body["response_format"] = {"type": "json_object"}
    if binding.include_store_false:
        body["store"] = False
    if binding.require_parameters and row.kind == "schema":
        body["provider"] = {"require_parameters": True}
    return body


def _messages(
    row: Purpose,
    payload: Mapping[str, object],
    corrective: bool,
) -> list[dict[str, object]]:
    instruction = row.instruction
    messages: list[dict[str, object]] = []
    if isinstance(instruction, str) and instruction:
        messages.append({"role": "system", "content": instruction})
    user = _user_content(row, payload)
    if user is not None:
        messages.append({"role": "user", "content": user})
    if corrective and row.kind == "schema":
        messages.append(
            {"role": "user", "content": "Return JSON that matches the requested object."}
        )
    return messages


def _user_content(
    row: Purpose, payload: Mapping[str, object]
) -> str | list[dict[str, object]] | None:
    texts: list[str] = []
    images: list[str] = []
    for field in row.fields:
        value = payload.get(field.name)
        if field.kind == "text" and isinstance(value, str):
            texts.append(value)
        elif field.kind == "image" and isinstance(value, str):
            images.append(value)
    text = "\n".join(texts)
    if not images:
        return text or None
    parts: list[dict[str, object]] = []
    if text:
        parts.append({"type": "text", "text": text})
    for url in images:
        parts.append({"type": "image_url", "image_url": {"url": url}})
    return parts


def _headers(binding: Binding) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if binding.api_key:
        headers["Authorization"] = f"Bearer {binding.api_key}"
    for name, value in binding.headers:
        headers[name] = value
    return headers


def _payload_error(row: Purpose, payload: Mapping[str, object]) -> str | None:
    expected = {field.name for field in row.fields}
    if set(payload) != expected:
        return "fields"
    for field in row.fields:
        value = payload[field.name]
        if field.kind == "context":
            if value is None:
                return "context"
            continue
        if not isinstance(value, str) or value == "":
            return field.kind
    return None


def _passes_check(row: Purpose, value: object, payload: Mapping[str, object]) -> bool:
    if row.check is None:
        return True
    return row.check(value, payload)


def _schema_rejected(response: HttpResponse, mode: str) -> bool:
    if response.status != 400 or mode == "prompt":
        return False
    blob = json.dumps(response.body, default=str)
    return "response_format" in blob or "json_schema" in blob


def _billing(response: HttpResponse) -> bool:
    return _error_code(response.body) in _BILLING_CODES


def _retryable(response: HttpResponse) -> bool:
    if response.status in _RETRYABLE:
        return True
    if response.status != 429:
        return False
    return _error_code(response.body) not in _BILLING_CODES


def _error_code(body: object) -> str:
    if not isinstance(body, dict):
        return ""
    error = body.get("error")
    if not isinstance(error, dict):
        return ""
    code = error.get("code")
    return code if isinstance(code, str) else ""


def _message(body: object) -> tuple[str, str] | None:
    if not isinstance(body, dict):
        return None
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return None
    choice = choices[0]
    finish = choice.get("finish_reason")
    message = choice.get("message")
    if not isinstance(message, dict):
        return None
    refusal = message.get("refusal")
    if isinstance(refusal, str) and refusal:
        return ("refused", "")
    if isinstance(finish, str) and finish in _REFUSAL_REASONS:
        return ("refused", "")
    content = message.get("content")
    if not isinstance(content, str):
        return None
    if finish == "length":
        return ("truncated", "")
    return ("ok", content)


def _response_model(body: object, fallback: str) -> str:
    if isinstance(body, dict):
        model = body.get("model")
        if isinstance(model, str) and model:
            return model
    return fallback


def _delay(attempt: int, rng: random.Random) -> float:
    cap = min(_MAX_SLEEP_S, 0.5 * 2**attempt)
    return rng.uniform(0, cap)


def _elapsed(began: float, now: Callable[[], float]) -> int:
    return max(0, int((now() - began) * 1000))


def _record(
    purpose: str,
    binding: str,
    attempt: int,
    elapsed_ms: int,
    status: int | None,
    decision: str,
) -> None:
    _log.info(
        "agent_call",
        extra={
            "purpose": purpose,
            "binding": binding,
            "attempt": attempt,
            "elapsed_ms": elapsed_ms,
            "status": status,
            "decision": decision,
        },
    )
