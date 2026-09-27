"""C9 due-date policy: the single table of follow-up windows.

When C9 opens a waiting item it has no known due date from a source document, so
the due date is policy-relative (``due_precision = relative_policy``): the moment
the thread entered the waiting state plus the window for that item type. After
the item comes due it gets a grace period before it is marked overdue.

Windows are owner-configurable through settings (defaults: result 7 days,
referral 4 weeks, overdue grace 2 days). Migration 024 backfills existing items
with the same defaults; keep them in sync if the defaults change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from wellbe_contracts.c9_continuity import PendingItemType

DEFAULT_RESULT_WINDOW_DAYS = 7
DEFAULT_REFERRAL_WINDOW_DAYS = 28
DEFAULT_OVERDUE_GRACE_DAYS = 2


class ContinuityPolicySettings(BaseSettings):
    """``WELLBE_C9_RESULT_WINDOW_DAYS`` / ``WELLBE_C9_REFERRAL_WINDOW_DAYS`` / ..."""

    model_config = SettingsConfigDict(env_prefix="WELLBE_C9_", extra="ignore")

    result_window_days: int = Field(default=DEFAULT_RESULT_WINDOW_DAYS, ge=1)
    referral_window_days: int = Field(default=DEFAULT_REFERRAL_WINDOW_DAYS, ge=1)
    overdue_grace_days: int = Field(default=DEFAULT_OVERDUE_GRACE_DAYS, ge=0)


@dataclass(frozen=True)
class DuePolicy:
    windows: dict[PendingItemType, timedelta] = field(
        default_factory=lambda: {
            PendingItemType.RESULT_PENDING: timedelta(days=DEFAULT_RESULT_WINDOW_DAYS),
            PendingItemType.REFERRAL_PENDING: timedelta(days=DEFAULT_REFERRAL_WINDOW_DAYS),
        }
    )
    overdue_grace: timedelta = timedelta(days=DEFAULT_OVERDUE_GRACE_DAYS)

    @classmethod
    def from_settings(cls, settings: ContinuityPolicySettings | None = None) -> DuePolicy:
        s = settings or ContinuityPolicySettings()
        return cls(
            windows={
                PendingItemType.RESULT_PENDING: timedelta(days=s.result_window_days),
                PendingItemType.REFERRAL_PENDING: timedelta(days=s.referral_window_days),
            },
            overdue_grace=timedelta(days=s.overdue_grace_days),
        )

    def window_for(self, item_type: PendingItemType) -> timedelta | None:
        return self.windows.get(item_type)

    def due_at(self, item_type: PendingItemType, opened_at: datetime) -> datetime | None:
        """Due date for an item opened at ``opened_at``; None if no policy window."""
        window = self.window_for(item_type)
        return opened_at + window if window is not None else None

    def overdue_at(self, due_at: datetime) -> datetime:
        return due_at + self.overdue_grace


@lru_cache(maxsize=1)
def default_policy() -> DuePolicy:
    return DuePolicy.from_settings()
