from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator, Field


def _ensure_tz_aware(v: datetime) -> datetime:
    if v.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return v


AwareDatetime = Annotated[datetime, AfterValidator(_ensure_tz_aware)]

CapturedAt = Annotated[
    AwareDatetime,
    Field(description="Timestamp when the data was originally captured at the source"),
]
ReceivedAt = Annotated[
    AwareDatetime,
    Field(description="Timestamp when the system first received the data"),
]
IngestedAt = Annotated[
    AwareDatetime,
    Field(description="Timestamp when the data was persisted in the vault"),
]
