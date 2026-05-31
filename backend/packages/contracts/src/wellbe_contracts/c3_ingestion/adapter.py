from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict

from wellbe_contracts.primitives import ActorId, AwareDatetime, PatientId


class AdapterInput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_type: str
    raw_data: bytes
    captured_at: AwareDatetime
    actor_id: ActorId
    patient_id: PatientId
    metadata: Optional[dict] = None


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = []


class NormalizedPayload(BaseModel):
    data: bytes
    mime_type: str
    byte_size: int
    encoding: Optional[str] = None
    language: Optional[str] = None


class AdapterProvenance(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_type: str
    source_id: Optional[str] = None
    external_source_id: Optional[str] = None
    captured_at: AwareDatetime
    adapter_name: str
    adapter_version: str
    source_metadata: Optional[dict] = None
    original_filename_hash: Optional[str] = None
    mime_type: str
    encoding: Optional[str] = None
    language: Optional[str] = None
