from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from wellbe_contracts.primitives import AwareDatetime


class OutboxEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    event_type: str
    payload: dict[str, Any]
    created_at: AwareDatetime
    delivered_at: AwareDatetime | None = None
    correlation_id: str
    trace_id: str
