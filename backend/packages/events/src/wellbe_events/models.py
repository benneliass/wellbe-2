from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from wellbe_db import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OutboxEventRow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "outbox_events"
    __table_args__ = {"schema": "events"}

    event_type: Mapped[str] = mapped_column(String(255))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    correlation_id: Mapped[str] = mapped_column(Text)
    trace_id: Mapped[str] = mapped_column(Text)
    delivered_at: Mapped[datetime | None] = mapped_column(default=None)
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    last_error: Mapped[str | None] = mapped_column(Text, default=None)
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    dead_lettered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
