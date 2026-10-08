"""Tests for the local Dev-workspace seed (wellbe_api.dev_seed).

These lock in the properties the cluster relies on: the committed dataset is
well-formed against the live capture/thread contracts, the user-action plan only
walks valid lifecycle edges, and the seed is safe to re-run (deterministic capture
keys + a hard dev-only gate). No network is used.
"""

from __future__ import annotations

import json
import uuid

import httpx
import pytest
from wellbe_api import dev_seed
from wellbe_api.published_cases import PUBLISHED_CASES
from wellbe_api.routers.capture_v1 import CaptureType
from wellbe_contracts.c7_thread import ALLOWED_TRANSITIONS, HealthThreadStatus


def test_capture_dataset_matches_contract() -> None:
    valid_types = {t.value for t in CaptureType}
    for capture in dev_seed.CAPTURES:
        assert capture["capture_type"] in valid_types
        payload = capture["payload"]
        assert isinstance(payload, dict) and payload
        if capture["capture_type"] == "symptom":
            assert (payload.get("description") or "").strip()
        elif capture["capture_type"] == "note":
            assert (payload.get("text") or "").strip()
        elif capture["capture_type"] == "lab":
            assert (payload.get("test_name") or "").strip()
            assert str(payload.get("value") or "").strip()


def test_candidate_plan_is_well_formed() -> None:
    """Every plan rule has a known action; confirms carry a walk, others do not."""
    for rule in dev_seed.CANDIDATE_PLAN:
        assert (rule.get("match") or "").strip()  # type: ignore[union-attr]
        assert rule["action"] in {"confirm", "dismiss", "leave"}
        if rule["action"] == "confirm":
            assert isinstance(rule.get("walk"), list)
        else:
            assert "walk" not in rule


def _assert_walk(walk: list[str]) -> None:
    current = HealthThreadStatus.DRAFT
    for target_value in walk:
        target = HealthThreadStatus(target_value)
        assert target in ALLOWED_TRANSITIONS[current], (
            f"{current} -> {target} is not an allowed edge"
        )
        current = target


def test_confirm_walks_are_valid_lifecycle_edges() -> None:
    """Every confirm walk must be a path of structurally allowed transitions
    starting from a freshly-created (``draft``) thread — the status a candidate
    confirmation produces. The empty-plan walk is checked too."""
    for rule in dev_seed.CANDIDATE_PLAN:
        if rule["action"] != "confirm":
            continue
        _assert_walk(list(rule["walk"]))  # type: ignore[arg-type]
    _assert_walk(list(dev_seed.CONFIRM_WALK))


def test_investigation_and_packet_reference_confirmed_threads() -> None:
    """Investigation/visit-packet thread keys must be confirmable in the plan, so
    they actually resolve to threads at seed time (no dangling references)."""
    confirmable = {
        str(r["match"]).lower() for r in dev_seed.CANDIDATE_PLAN if r["action"] == "confirm"
    }
    for key in dev_seed.INVESTIGATION["link_threads"]:  # type: ignore[union-attr]
        assert key.lower() in confirmable
    for key in dev_seed.VISIT_PACKET["link_threads"]:  # type: ignore[union-attr]
        assert key.lower() in confirmable


def test_capture_idempotency_keys_are_deterministic_and_unique() -> None:
    keys = [dev_seed._capture_idempotency_key(i, c) for i, c in enumerate(dev_seed.CAPTURES)]
    # Deterministic: recomputing yields identical keys.
    again = [dev_seed._capture_idempotency_key(i, c) for i, c in enumerate(dev_seed.CAPTURES)]
    assert keys == again
    # Unique per capture, and valid UUIDs.
    assert len(set(keys)) == len(keys)
    for key in keys:
        uuid.UUID(key)


def test_headers_carry_controller_self_identity() -> None:
    pid = "de7a0000-0000-4000-8000-000000000001"
    headers = dev_seed._headers(pid)
    assert headers["X-Wellbe-Actor-Id"] == pid
    assert headers["X-Wellbe-Patient-Id"] == pid
    assert headers["X-Wellbe-Actor-Type"] == "controller"
    assert "Idempotency-Key" not in headers
    assert dev_seed._headers(pid, idempotency_key="k")["Idempotency-Key"] == "k"


def test_published_cases_replace_invented_captures() -> None:
    """Eighteen unique published-case notes, each carrying its source URL."""
    assert len(PUBLISHED_CASES) == 18
    assert len(dev_seed.CAPTURES) == 18
    sources = [c["source"] for c in dev_seed.CAPTURES]
    assert sources == [f"published-case:{c['case_id']}" for c in PUBLISHED_CASES]
    assert len(set(sources)) == 18
    blob = "\n".join(str(c["payload"]["text"]) for c in dev_seed.CAPTURES)
    assert "Could the morning cough" not in blob
    assert "Capture patient concern verbatim" not in blob
    urls = [c["source_url"] for c in PUBLISHED_CASES]
    assert len(set(urls)) == 18
    for case in PUBLISHED_CASES:
        assert case["source_url"] in case["text"]
        assert case["text"].startswith(f"Published sample case {case['case_id']}:")
    by_id = {c["case_id"]: c["text"] for c in PUBLISHED_CASES}
    assert "\nTimeline:" not in by_id["C009"]
    assert "\nTimeline:" not in by_id["C011"]
    assert "Outcome recorded:" in by_id["C009"]
    assert "Outcome recorded:" in by_id["C011"]
    assert dev_seed.INVESTIGATION["link_threads"] == []
    assert dev_seed.VISIT_PACKET["link_threads"] == []
    assert dev_seed.CANDIDATE_PLAN == []


async def test_each_candidate_is_acted_on_at_most_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dev_seed,
        "CANDIDATE_PLAN",
        [
            {"match": "knee", "action": "confirm", "walk": ["active_unresolved"]},
            {"match": "pain", "action": "confirm", "walk": ["active_unresolved"]},
        ],
    )
    """A broad keyword ("pain") must not re-confirm what "knee" already confirmed.

    Genesis may list "Knee pain" before "Pain"; the candidate snapshot is not
    refreshed between rules, so without claiming, the second confirm hits 409.
    """
    knee, pain = str(uuid.uuid4()), str(uuid.uuid4())
    candidates = [
        {"candidate_id": knee, "title": "Knee pain", "status": "pending"},
        {"candidate_id": pain, "title": "Pain", "status": "pending"},
    ]
    confirmed_ids: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/confirm"):
            cid = path.split("/")[-2]
            if cid in confirmed_ids:
                return httpx.Response(409, json={"title": "Candidate is not pending"})
            confirmed_ids.append(cid)
            return httpx.Response(200, json={"thread_id": str(uuid.uuid4())})
        return httpx.Response(200, json={})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://api"
    ) as client:
        confirmed = await dev_seed._act_on_candidates(client, str(uuid.uuid4()), candidates)

    assert confirmed_ids == [knee, pain]
    assert set(confirmed) == {"knee", "pain"}


async def test_empty_plan_confirms_each_pending_candidate_once() -> None:
    """No dismiss. Already-confirmed candidates are skipped, including a 409."""
    assert dev_seed.CANDIDATE_PLAN == []
    first, second, already = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    candidates = [
        {"candidate_id": first, "title": "Pain", "status": "pending"},
        {"candidate_id": already, "title": "Pain", "status": "confirmed"},
        {"candidate_id": second, "title": "Cough", "status": "pending"},
    ]
    confirmed_ids: list[str] = []
    targets: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/confirm"):
            cid = path.split("/")[-2]
            if cid == second:
                return httpx.Response(409, json={"title": "Candidate is not pending"})
            confirmed_ids.append(cid)
            return httpx.Response(200, json={"thread_id": str(uuid.uuid4())})
        if path.endswith("/transition"):
            targets.append(json.loads(request.content))
            return httpx.Response(200, json={})
        return httpx.Response(500, json={})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://api"
    ) as client:
        confirmed = await dev_seed._act_on_candidates(client, str(uuid.uuid4()), candidates)

    assert confirmed_ids == [first]
    assert already not in confirmed
    assert second not in confirmed
    assert list(confirmed) == [first]
    assert targets == [{"target_status": "active_unresolved", "reason_code": "dev_seed"}]


async def test_seed_is_a_noop_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WELLBE_DEV_SEED_ENABLED", raising=False)
    # No API base / patient id set: if the gate did not short-circuit, this would
    # raise. A clean return proves the dev-only gate holds.
    await dev_seed.seed()


async def test_seed_requires_patient_id_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WELLBE_DEV_SEED_ENABLED", "true")
    monkeypatch.delenv("WELLBE_DEV_PATIENT_ID", raising=False)
    with pytest.raises(RuntimeError):
        await dev_seed.seed()


class _HeaderClient:
    """Stand-in for the seed's HTTP client. No network."""

    def __init__(self, threads_status: list[int]) -> None:
        self._threads_status = list(threads_status)

    async def __aenter__(self) -> _HeaderClient:
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False

    async def get(self, path: str, **_kwargs: object) -> httpx.Response:
        if path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if path == "/v1/threads":
            status = self._threads_status.pop(0) if self._threads_status else 401
            return httpx.Response(status, json={})
        raise AssertionError(path)


def _install_seed_doubles(monkeypatch: pytest.MonkeyPatch, threads_status: list[int]) -> list[str]:
    order: list[str] = []

    def client(*_args: object, **_kwargs: object) -> _HeaderClient:
        return _HeaderClient(threads_status)

    async def account(_patient_id: uuid.UUID) -> None:
        order.append("account")

    async def read() -> str:
        order.append("read")
        return dev_seed.SEED_REVISION

    async def reset() -> None:
        order.append("reset")

    async def no_sleep(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setenv("WELLBE_DEV_SEED_ENABLED", "true")
    monkeypatch.setenv("WELLBE_DEV_PATIENT_ID", str(uuid.uuid4()))
    monkeypatch.setattr(dev_seed.httpx, "AsyncClient", client)
    monkeypatch.setattr(dev_seed, "_seed_dev_account", account)
    monkeypatch.setattr(dev_seed, "_read_seed_revision", read)
    monkeypatch.setattr(dev_seed, "_reset_dev_data", reset)
    monkeypatch.setattr(dev_seed.asyncio, "sleep", no_sleep)
    return order


async def test_seed_does_not_reset_when_dev_headers_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order = _install_seed_doubles(monkeypatch, [401])
    with pytest.raises(RuntimeError, match="Refusing to reset"):
        await dev_seed.seed()
    assert order == []


async def test_matching_revision_skips_reset_after_dev_headers_succeed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order = _install_seed_doubles(monkeypatch, [401, 200])
    await dev_seed.seed()
    assert order == ["account", "read"]


def test_patient_with_another_account_is_left_in_place() -> None:
    assert dev_seed._patient_has_other_account("https://wellbe-auth.example", "demo")
    assert not dev_seed._patient_has_other_account(None, None)
    assert not dev_seed._patient_has_other_account("dev-local", "dev-controller")
