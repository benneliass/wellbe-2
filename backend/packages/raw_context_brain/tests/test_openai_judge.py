"""The context judge keeps its question and sends it through the shared caller."""

from __future__ import annotations

import json

from wellbe_agent_caller import Binding
from wellbe_agent_caller.types import HttpResponse
from wellbe_raw_context_brain.judge import OpenAiJudge, OpenAiJudgeOptions
from wellbe_raw_context_brain.types import JudgeCandidate, JudgeRequest


class FakeTransport:
    def __init__(self, response: HttpResponse) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    async def post(
        self,
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
        timeout_s: float,
    ) -> HttpResponse:
        self.calls.append({"url": url, "payload": payload, "headers": headers})
        return self.response


def _request() -> JudgeRequest:
    return JudgeRequest(
        new_handle="ch_new",
        excerpt="morning cough",
        source_type="manual_text",
        captured_at="2026-11-05T00:00:00Z",
        candidates=(
            JudgeCandidate(
                handle="h1",
                excerpt="evening cough",
                source_type="manual_text",
                captured_at="2026-11-04T00:00:00Z",
            ),
        ),
    )


async def test_judge_uses_the_binding_and_drops_a_clinical_reason() -> None:
    body = {
        "model": "served-model",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": json.dumps(
                        {
                            "decisions": [
                                {
                                    "handle": "h1",
                                    "judgment": "link",
                                    "reasonCode": "diagnosed today",
                                    "confidence": 0.9,
                                }
                            ]
                        }
                    )
                },
            }
        ],
    }
    transport = FakeTransport(HttpResponse(status=200, body=body))
    binding = Binding(
        name="lab",
        base_url="http://127.0.0.1:9/v1",
        api_key="sk-test",
        model="lab-model",
    )
    judge = OpenAiJudge(OpenAiJudgeOptions(binding=binding, transport=transport))
    decisions = await judge.judge(_request())
    assert decisions[0].judgment == "uncertain"
    assert decisions[0].reason_code == "insufficient_overlap"
    assert transport.calls[0]["url"] == "http://127.0.0.1:9/v1/chat/completions"
    payload = transport.calls[0]["payload"]
    assert isinstance(payload, dict)
    assert payload["model"] == "lab-model"
    assert "api.openai.com" not in str(transport.calls[0]["url"])


async def test_judge_without_a_binding_fails_closed(monkeypatch: object) -> None:
    from pytest import MonkeyPatch

    assert isinstance(monkeypatch, MonkeyPatch)
    for name in (
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "WELLBE_AGENT_BINDING",
        "WELLBE_AGENT_BINDING_CONTEXT_JUDGE_DECISIONS",
        "WELLBE_AGENT_LOCAL_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    judge = OpenAiJudge(OpenAiJudgeOptions())
    try:
        await judge.judge(_request())
    except RuntimeError as error:
        assert str(error) == "dependency_unavailable"
    else:
        raise AssertionError("expected a typed failure")
