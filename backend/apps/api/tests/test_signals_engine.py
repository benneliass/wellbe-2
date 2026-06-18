"""Unit tests for the coverage-aware Home signals engine (WEL-91).

Guards the never-alarm / honesty rules from
docs/decisions/signals-summary-semantics.md: missing data is never green, the
denominator counts only fresh areas, no "all clear"/"in range" wording, and a
sparse account is suppressed into a calm learning state.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from wellbe_api.signals.engine import build_summary
from wellbe_contracts.signals import ConfidenceLabel, SignalStatus

NOW = datetime(2026, 6, 1, tzinfo=UTC)
_BANNED = ("all clear", "in range", "all good", "steady", "you're healthy", "no concern")


@dataclass
class _Node:
    node_type: str
    display_label: str
    last_seen_at: datetime
    id: uuid.UUID = uuid.uuid4()


def _by_id(summary, area_id):
    return next(a for a in summary.areas if a.id == area_id)


def test_no_data_is_suppressed_and_never_reassures():
    s = build_summary([], now=NOW)
    assert s.suppressed is True
    assert s.areas_with_data == 0
    assert s.areas_total == 6
    assert s.not_diagnosis is True
    text = (s.headline + s.coverage_label + s.note).lower()
    assert not any(b in text for b in _BANNED)
    # Every area is an explicit unknown, never green.
    for a in s.areas:
        assert a.status is SignalStatus.NO_DATA
        assert a.confidence is ConfidenceLabel.NONE
        assert a.last_updated is None


def test_recent_data_counts_toward_coverage_only_when_fresh():
    nodes = [
        _Node("VitalSign", "Blood pressure 118/76", NOW - timedelta(days=2)),
        _Node("VitalSign", "Resting heart rate 62", NOW - timedelta(days=2)),
        # Stale lab: exists but older than the freshness window -> not counted.
        _Node("LabResult", "CRP 1.1", NOW - timedelta(days=200)),
    ]
    s = build_summary(nodes, now=NOW)
    assert s.suppressed is False
    assert s.areas_total == 6
    # vitals + cardiovascular are fresh; inflammation is stale.
    vitals = _by_id(s, "vitals")
    assert vitals.status is SignalStatus.RECENT
    assert vitals.confidence is ConfidenceLabel.GOOD  # 2 sources
    inflammation = _by_id(s, "inflammation")
    assert inflammation.status is SignalStatus.STALE
    assert inflammation.confidence is ConfidenceLabel.LIMITED
    # Denominator counts ONLY fresh areas; stale is excluded.
    assert s.areas_with_data == sum(
        1 for a in s.areas if a.status is SignalStatus.RECENT
    )
    assert inflammation.id not in {a.id for a in s.areas if a.status is SignalStatus.RECENT}
    assert s.coverage_label == f"Recent data for {s.areas_with_data} of 6 areas"


def test_single_source_recent_is_limited_confidence():
    nodes = [_Node("VitalSign", "Blood pressure 120/80", NOW - timedelta(days=1))]
    s = build_summary(nodes, now=NOW)
    vitals = _by_id(s, "vitals")
    assert vitals.status is SignalStatus.RECENT
    assert vitals.confidence is ConfidenceLabel.LIMITED  # only 1 source
    assert vitals.source_count == 1


def test_missing_areas_show_explicit_unknown_not_green():
    nodes = [_Node("VitalSign", "Blood pressure 118/76", NOW - timedelta(days=1))]
    s = build_summary(nodes, now=NOW)
    sleep = _by_id(s, "sleep")
    assert sleep.status is SignalStatus.NO_DATA
    assert "not enough current data" in sleep.status_label.lower()


def test_no_aggregate_health_verdict_language():
    nodes = [
        _Node("VitalSign", "Blood pressure 118/76", NOW - timedelta(days=1)),
        _Node("LabResult", "Glucose 92", NOW - timedelta(days=3)),
    ]
    s = build_summary(nodes, now=NOW)
    blob = " ".join(
        [s.headline, s.coverage_label, s.note]
        + [a.status_label for a in s.areas]
    ).lower()
    assert not any(b in blob for b in _BANNED)
