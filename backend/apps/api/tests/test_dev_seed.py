"""Tests for the local Dev-workspace seed (wellbe_api.dev_seed).

These lock in the two properties the cluster relies on: the committed dataset is
well-formed against the live capture/thread contracts, and the seed is safe to
re-run (deterministic capture keys + a hard dev-only gate). No network is used.
"""

from __future__ import annotations

import uuid

import pytest
from wellbe_api import dev_seed
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


def test_thread_walks_are_valid_lifecycle_edges() -> None:
    """Every seeded walk must be a path of structurally allowed transitions
    starting from the create-time ``draft`` status."""
    for spec in dev_seed.THREADS:
        assert (spec["title"] or "").strip()  # type: ignore[union-attr]
        current = HealthThreadStatus.DRAFT
        for target_value in spec["walk"]:  # type: ignore[union-attr]
            target = HealthThreadStatus(target_value)
            assert target in ALLOWED_TRANSITIONS[current], (
                f"{current} -> {target} is not an allowed edge"
            )
            current = target


def test_capture_idempotency_keys_are_deterministic_and_unique() -> None:
    keys = [
        dev_seed._capture_idempotency_key(i, c)
        for i, c in enumerate(dev_seed.CAPTURES)
    ]
    # Deterministic: recomputing yields identical keys.
    again = [
        dev_seed._capture_idempotency_key(i, c)
        for i, c in enumerate(dev_seed.CAPTURES)
    ]
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
