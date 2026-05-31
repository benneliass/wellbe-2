from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from wellbe_contracts.primitives import AwareDatetime


class OutboxEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    event_type: str
    payload: dict
    created_at: AwareDatetime
    delivered_at: Optional[AwareDatetime] = None
    correlation_id: str
    trace_id: str
