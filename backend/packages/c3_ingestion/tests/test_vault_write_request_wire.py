"""The ingestion -> vault-writer JSON hop must carry arbitrary binary payloads."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from wellbe_contracts.c2_vault import VaultWriteRequest
from wellbe_contracts.c3_ingestion.adapter import AdapterProvenance

# PNG signature: not valid utf-8, like any scanned PDF or photo.
_BINARY = b"\x89PNG\r\n\x1a\n\x00\xff\xfe" + bytes(range(256))


def _request(payload: bytes) -> VaultWriteRequest:
    return VaultWriteRequest(
        patient_id=uuid.uuid4(),
        actor_id=uuid.uuid4(),
        normalized_payload=payload,
        adapter_provenance=AdapterProvenance(
            source_type="document",
            captured_at=datetime.now(UTC),
            adapter_name="test",
            adapter_version="1",
            mime_type="image/png",
        ),
        idempotency_key="k",
        consent_snapshot_id=uuid.uuid4(),
        correlation_id="c",
        trace_id="t",
        mime_type="image/png",
    )


def test_binary_payload_round_trips_through_json() -> None:
    wire = _request(_BINARY).model_dump_json()
    assert VaultWriteRequest.model_validate_json(wire).normalized_payload == _BINARY


def test_text_payload_round_trips_through_json() -> None:
    text = "héllo, ferritin 12 ng/mL".encode()
    wire = _request(text).model_dump_json()
    assert VaultWriteRequest.model_validate_json(wire).normalized_payload == text


def test_parsed_json_body_decodes_like_fastapi() -> None:
    # FastAPI validates the already-parsed JSON dict (python mode), not the raw JSON.
    import json

    body = json.loads(_request(_BINARY).model_dump_json())
    assert VaultWriteRequest.model_validate(body).normalized_payload == _BINARY
