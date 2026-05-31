from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from wellbe_db import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OutboxEventRow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "outbox_events"
    __table_args__ = {"schema": "events"}

    event_type: Mapped[str] = mapped_column(String(255))
    payload: Mapped[dict] = mapped_column(JSONB)
    correlation_id: Mapped[str] = mapped_column(Text)
    trace_id: Mapped[str] = mapped_column(Text)
    delivered_at: Mapped[datetime | None] = mapped_column(default=None)
