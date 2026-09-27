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

import pytest
from wellbe_api.signals.engine import build_summary, gate_summary
from wellbe_contracts.c10_safety import C10Decision
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
    assert s.areas_total == 7
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
    assert s.areas_total == 7
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
    assert s.coverage_label == f"Recent data for {s.areas_with_data} of 7 areas"


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


# --- Blood & nutrition area (2026-09-27 amendment) ---


def _areas_for(label: str, node_type: str = "LabResult") -> set[str]:
    s = build_summary([_Node(node_type, label, NOW - timedelta(days=1))], now=NOW)
    return {a.id for a in s.areas if a.status is SignalStatus.RECENT}


def test_area_set_includes_blood_nutrition():
    s = build_summary([], now=NOW)
    ids = [a.id for a in s.areas]
    assert "blood_nutrition" in ids
    assert len(ids) == len(set(ids)) == 7
    assert _by_id(s, "blood_nutrition").label == "Blood & nutrition"


@pytest.mark.parametrize(
    "label",
    [
        "Hemoglobin 13.5 g/dL",
        "Haemoglobin 135 g/L",
        "Hb 13.2",
        "HGB 14.1",
        "Hematocrit 41%",
        "MCV 88 fL",
        "RBC 4.6",
        "Platelets 250",
        "Ferritin 45 ng/mL",
        "Serum iron 90",
        "Transferrin saturation 30%",
        "TIBC 320",
        "Vitamin B12 450 pg/mL",
        "Cobalamin 400",
        "Folate 12",
        "Folic acid",
        "Vitamin D 32 ng/mL",
        "Vitamin D3 (25-OH) 28",
        "25-OH vitamin D 30",
        "Zinc 85",
        "Magnesium 2.0",
    ],
)
def test_blood_nutrition_keywords_match(label):
    assert "blood_nutrition" in _areas_for(label)


@pytest.mark.parametrize(
    "label",
    ["HbA1c 5.4%", "Hb A1c 5.6", "Hemoglobin A1c 5.4%", "Glycated haemoglobin 36"],
)
def test_hba1c_is_metabolic_not_blood(label):
    areas = _areas_for(label)
    assert "blood_nutrition" not in areas
    assert "metabolic" in areas


@pytest.mark.parametrize(
    "label", ["Shbg 40", "Chromium 1.2", "Rhubarb intake", "Ironman training", "Thyroid TSH"]
)
def test_blood_nutrition_ignores_substring_lookalikes(label):
    assert "blood_nutrition" not in _areas_for(label)


def test_blood_nutrition_requires_lab_result():
    # A symptom mentioning iron is not a blood/nutrition measurement.
    assert "blood_nutrition" not in _areas_for("Iron deficiency worry", node_type="Symptom")


def test_ferritin_counts_toward_inflammation_and_blood_nutrition():
    assert {"inflammation", "blood_nutrition"} <= _areas_for("Ferritin 45")


def test_word_boundary_keeps_existing_prefix_matches():
    assert "inflammation" in _areas_for("Inflammatory markers panel")
    assert "sleep" in _areas_for("Sleeping 6h", node_type="VitalSign")
    assert "activity" in _areas_for("Walking 30 min", node_type="SocialFactor")
    # Short abbreviations no longer match inside other words.
    assert "sleep" not in _areas_for("Premature beats", node_type="Symptom")
    assert "cardiovascular" not in _areas_for("Three hours of chores", node_type="VitalSign")


def test_blood_nutrition_summary_counts():
    nodes = [
        _Node("LabResult", "Hemoglobin 13.5", NOW - timedelta(days=5)),
        _Node("LabResult", "Ferritin 45", NOW - timedelta(days=5)),
        _Node("LabResult", "Vitamin D 32", NOW - timedelta(days=5)),
    ]
    s = build_summary(nodes, now=NOW)
    blood = _by_id(s, "blood_nutrition")
    assert blood.status is SignalStatus.RECENT
    assert blood.source_count == 3
    assert blood.confidence is ConfidenceLabel.GOOD
    # Ferritin also informs inflammation; both are fresh -> 2 of 7 areas.
    assert _by_id(s, "inflammation").source_count == 1
    assert s.areas_with_data == 2
    assert s.areas_total == 7
    assert s.coverage_label == "Recent data for 2 of 7 areas"


def test_blood_nutrition_stale_is_not_counted():
    nodes = [_Node("LabResult", "Vitamin B12 450", NOW - timedelta(days=200))]
    s = build_summary(nodes, now=NOW)
    assert _by_id(s, "blood_nutrition").status is SignalStatus.STALE
    assert s.areas_with_data == 0
    assert s.suppressed is True


@pytest.mark.parametrize("with_data", [True, False])
def test_c10_gate_allows_seven_area_copy(with_data):
    nodes = (
        [
            _Node("LabResult", "Hemoglobin 13.5", NOW - timedelta(days=2)),
            _Node("LabResult", "Ferritin 45", NOW - timedelta(days=2)),
            _Node("VitalSign", "Blood pressure 118/76", NOW - timedelta(days=2)),
        ]
        if with_data
        else []
    )
    s = build_summary(nodes, now=NOW)
    decision = gate_summary(summary=s, patient_id=uuid.uuid4(), correlation_id="test-corr")
    assert decision in {C10Decision.ALLOW, C10Decision.ALLOW_WITH_OBLIGATIONS}
