from __future__ import annotations

import enum

from pydantic import BaseModel, ConfigDict


class SourceTypeCode(str, enum.Enum):
    MANUAL_TEXT = "manual_text"
    PHOTO = "photo"
    PDF = "pdf"
    SMS = "sms"
    DEVICE = "device"
    FHIR = "fhir"
    ENVIRONMENTAL = "environmental"


class SourceTypeStatus(str, enum.Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class SourceTypeRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: SourceTypeCode
    display_name: str
    status: SourceTypeStatus
    requires_blob: bool
    default_mime_types: list[str]
