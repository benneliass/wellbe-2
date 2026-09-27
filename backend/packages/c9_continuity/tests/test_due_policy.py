"""C9 due-date policy: owner-decided windows, env overrides, overdue grace."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from wellbe_c9_continuity.policy import ContinuityPolicySettings, DuePolicy
from wellbe_contracts.c9_continuity import PendingItemType

_OPENED = datetime(2026, 9, 1, 10, 0, tzinfo=UTC)


def test_default_windows_are_owner_decisions() -> None:
    policy = DuePolicy()
    assert policy.due_at(PendingItemType.RESULT_PENDING, _OPENED) == _OPENED + timedelta(days=7)
    assert policy.due_at(PendingItemType.REFERRAL_PENDING, _OPENED) == _OPENED + timedelta(
        weeks=4
    )
    assert policy.overdue_at(_OPENED) == _OPENED + timedelta(days=2)


def test_from_settings_defaults_match_dataclass_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("RESULT_WINDOW_DAYS", "REFERRAL_WINDOW_DAYS", "OVERDUE_GRACE_DAYS"):
        monkeypatch.delenv(f"WELLBE_C9_{var}", raising=False)
    assert DuePolicy.from_settings() == DuePolicy()


def test_windows_are_configurable_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WELLBE_C9_RESULT_WINDOW_DAYS", "3")
    monkeypatch.setenv("WELLBE_C9_REFERRAL_WINDOW_DAYS", "14")
    monkeypatch.setenv("WELLBE_C9_OVERDUE_GRACE_DAYS", "0")
    policy = DuePolicy.from_settings()
    assert policy.window_for(PendingItemType.RESULT_PENDING) == timedelta(days=3)
    assert policy.window_for(PendingItemType.REFERRAL_PENDING) == timedelta(days=14)
    assert policy.overdue_at(_OPENED) == _OPENED


def test_items_without_a_policy_window_stay_undated() -> None:
    policy = DuePolicy()
    for item_type in (
        PendingItemType.NORMAL_TEST_SAFETY_NET,
        PendingItemType.FOLLOW_UP_DUE,
        PendingItemType.USER_NEXT_STEP,
    ):
        assert policy.due_at(item_type, _OPENED) is None


def test_non_positive_windows_are_rejected() -> None:
    with pytest.raises(ValueError):
        ContinuityPolicySettings(result_window_days=0)
