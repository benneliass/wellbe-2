from __future__ import annotations

import pytest

from wellbe_c4_processing.vital_registry import (
    VITAL_REGISTRY_VERSION,
    classify_vital,
)


class TestClassifyVital:
    @pytest.mark.parametrize(
        ("test_name", "expected_key"),
        [
            ("Blood pressure", "blood_pressure"),
            ("Systolic blood pressure", "blood_pressure"),
            ("Diastolic", "blood_pressure"),
            ("BP", "blood_pressure"),
            ("Heart rate", "heart_rate"),
            ("Pulse", "heart_rate"),
            ("Respiratory rate", "respiratory_rate"),
            ("Body temperature", "body_temperature"),
            ("Temperature", "body_temperature"),
            ("Oxygen saturation", "oxygen_saturation"),
            ("SpO2", "oxygen_saturation"),
            ("Body weight", "body_weight"),
            ("Weight", "body_weight"),
            ("Height", "body_height"),
            ("BMI", "body_mass_index"),
            ("Body Mass Index", "body_mass_index"),
        ],
    )
    def test_known_vitals_match(self, test_name: str, expected_key: str) -> None:
        concept = classify_vital(test_name)
        assert concept is not None
        assert concept.key == expected_key

    @pytest.mark.parametrize(
        "test_name",
        [
            "LDL cholesterol",
            "HDL cholesterol",
            "Hemoglobin A1c",
            "Vitamin D (25-OH)",
            "BNP",  # must NOT match blood_pressure via the "bp" token
            "Creatinine",
            "TSH",
            "",
            "   ",
        ],
    )
    def test_non_vitals_do_not_match(self, test_name: str) -> None:
        assert classify_vital(test_name) is None

    def test_registry_version_pinned(self) -> None:
        # Guards against an accidental reclassification without a version bump.
        assert VITAL_REGISTRY_VERSION == "vital-registry-v1"
