from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from wellbe_contracts.primitives import ActorId, AwareDatetime, PatientId


class AdapterInput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_type: str
    raw_data: bytes
    captured_at: AwareDatetime
    actor_id: ActorId
    patient_id: PatientId
    metadata: dict[str, Any] | None = None


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = []


class NormalizedPayload(BaseModel):
    data: bytes
    mime_type: str
    byte_size: int
    encoding: str | None = None
    language: str | None = None


class AdapterProvenance(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_type: str
    source_id: str | None = None
    external_source_id: str | None = None
    captured_at: AwareDatetime
    adapter_name: str
    adapter_version: str
    source_metadata: dict[str, Any] | None = None
    original_filename_hash: str | None = None
    mime_type: str
    encoding: str | None = None
    language: str | None = None
