"""Deterministic Vault-id idempotency for the capture write path (WEL-155).

The decision (docs/decisions/capture-write-path-contract.md, Q2=A2c) requires the
durable Vault id to be a uuid5 of the capture natural key, so a retried/redelivered
capture collapses onto the same row. These tests pin that determinism contract.
"""

from __future__ import annotations

import uuid

from wellbe_c3_ingestion.service import deterministic_event_id

_ACTOR = uuid.UUID("11111111-1111-1111-1111-111111111111")
_PATIENT = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _id(**overrides: object) -> uuid.UUID:
    kwargs: dict[str, object] = {
        "actor_id": _ACTOR,
        "patient_id": _PATIENT,
        "capture_type": "symptom",
        "payload_sha256": "abc123",
        "client_idempotency_key": "key-1",
    }
    kwargs.update(overrides)
    return deterministic_event_id(**kwargs)  # type: ignore[arg-type]


def test_same_inputs_yield_same_id() -> None:
    assert _id() == _id()


def test_is_uuid5() -> None:
    assert _id().version == 5


def test_different_client_key_yields_different_id() -> None:
    assert _id() != _id(client_idempotency_key="key-2")


def test_different_payload_yields_different_id() -> None:
    assert _id() != _id(payload_sha256="def456")


def test_different_capture_type_yields_different_id() -> None:
    assert _id() != _id(capture_type="note")


def test_different_actor_yields_different_id() -> None:
    other = uuid.UUID("33333333-3333-3333-3333-333333333333")
    assert _id() != _id(actor_id=other)
