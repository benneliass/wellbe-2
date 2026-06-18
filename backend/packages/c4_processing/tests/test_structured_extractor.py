from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from wellbe_c4_processing.extractor import (
    STRUCTURED_CONTRACT_VERSION,
    StructuredObservationExtractor,
)
from wellbe_c4_processing.vital_registry import VITAL_REGISTRY_VERSION
from wellbe_contracts.c4_processing import FactType, QualityFlag

OCCURRENCE = date(2026, 6, 18)


@pytest.fixture
def extractor() -> StructuredObservationExtractor:
    return StructuredObservationExtractor()


class TestLabTyping:
    def test_ldl_is_lab_result(self, extractor: StructuredObservationExtractor) -> None:
        (fact,) = extractor.extract_lab(
            test_name="LDL cholesterol",
            value="160",
            unit="mg/dL",
            reference_range="<100",
            occurrence=OCCURRENCE,
        )
        assert fact.fact_type is FactType.LAB_RESULT
        assert fact.entity_label == "LDL cholesterol"
        assert fact.normalized_key == "lab:ldl_cholesterol:2026-06-18"
        assert fact.quality_flag is QualityFlag.CLEAN
        assert fact.extraction_confidence == 0.97
        assert fact.code is None and fact.code_system is None
        meta = fact.quality_metadata
        assert meta["normalization_status"] == "raw_only"
        assert meta["raw_value"] == "160"
        assert meta["raw_unit"] == "mg/dL"
        assert meta["reference_range"] == "<100"
        assert meta["contract_version"] == STRUCTURED_CONTRACT_VERSION

    def test_hba1c_is_lab_result(
        self, extractor: StructuredObservationExtractor
    ) -> None:
        (fact,) = extractor.extract_lab(
            test_name="Hemoglobin A1c", value="6.1", unit="%", occurrence=OCCURRENCE
        )
        assert fact.fact_type is FactType.LAB_RESULT
        assert fact.normalized_key == "lab:hemoglobin_a1c:2026-06-18"

    def test_vitamin_d_is_lab_result(
        self, extractor: StructuredObservationExtractor
    ) -> None:
        (fact,) = extractor.extract_lab(
            test_name="Vitamin D (25-OH)",
            value="22",
            unit="ng/mL",
            occurrence=OCCURRENCE,
        )
        assert fact.fact_type is FactType.LAB_RESULT
        assert fact.normalized_key == "lab:vitamin_d_25_oh:2026-06-18"


class TestVitalTyping:
    def test_blood_pressure_is_vital_with_components(
        self, extractor: StructuredObservationExtractor
    ) -> None:
        (fact,) = extractor.extract_lab(
            test_name="Blood pressure",
            value="128/82",
            unit="mmHg",
            occurrence=OCCURRENCE,
        )
        assert fact.fact_type is FactType.VITAL_SIGN
        assert fact.normalized_key == "vital:blood_pressure:2026-06-18"
        meta = fact.quality_metadata
        assert meta["vital_registry_version"] == VITAL_REGISTRY_VERSION
        assert meta["vital_concept"] == "blood_pressure"
        assert meta["components"] == {"systolic": 128.0, "diastolic": 82.0}

    def test_blood_pressure_unparseable_value_still_typed(
        self, extractor: StructuredObservationExtractor
    ) -> None:
        (fact,) = extractor.extract_lab(
            test_name="Blood pressure", value="normal", occurrence=OCCURRENCE
        )
        assert fact.fact_type is FactType.VITAL_SIGN
        assert "components" not in fact.quality_metadata

    def test_heart_rate_is_vital(
        self, extractor: StructuredObservationExtractor
    ) -> None:
        (fact,) = extractor.extract_lab(
            test_name="Heart rate", value="72", unit="bpm", occurrence=OCCURRENCE
        )
        assert fact.fact_type is FactType.VITAL_SIGN
        assert fact.normalized_key == "vital:heart_rate:2026-06-18"


class TestIdempotencyAndOccurrence:
    def test_same_concept_same_day_is_stable_key(
        self, extractor: StructuredObservationExtractor
    ) -> None:
        (a,) = extractor.extract_lab(
            test_name="LDL cholesterol", value="160", occurrence=OCCURRENCE
        )
        (b,) = extractor.extract_lab(
            test_name="LDL cholesterol", value="158", occurrence=OCCURRENCE
        )
        assert a.normalized_key == b.normalized_key

    def test_different_day_is_distinct_key(
        self, extractor: StructuredObservationExtractor
    ) -> None:
        (a,) = extractor.extract_lab(
            test_name="LDL cholesterol", value="160", occurrence=date(2026, 6, 18)
        )
        (b,) = extractor.extract_lab(
            test_name="LDL cholesterol", value="160", occurrence=date(2026, 7, 1)
        )
        assert a.normalized_key != b.normalized_key

    def test_datetime_occurrence_uses_calendar_day(
        self, extractor: StructuredObservationExtractor
    ) -> None:
        (fact,) = extractor.extract_lab(
            test_name="LDL cholesterol",
            value="160",
            occurrence=datetime(2026, 6, 18, 23, 30, tzinfo=timezone.utc),
        )
        assert fact.normalized_key == "lab:ldl_cholesterol:2026-06-18"

    def test_missing_occurrence_is_unknown_token(
        self, extractor: StructuredObservationExtractor
    ) -> None:
        (fact,) = extractor.extract_lab(test_name="LDL cholesterol", value="160")
        assert fact.normalized_key == "lab:ldl_cholesterol:unknown"


class TestSafetyAndMalformed:
    def test_no_clinical_interpretation_computed(
        self, extractor: StructuredObservationExtractor
    ) -> None:
        # An out-of-range value must NOT be flagged abnormal by WellBe.
        (fact,) = extractor.extract_lab(
            test_name="LDL cholesterol",
            value="300",
            reference_range="<100",
            occurrence=OCCURRENCE,
        )
        assert "source_provided_flag" not in fact.quality_metadata
        assert "interpretation" not in fact.quality_metadata

    def test_source_flag_stored_as_provenance_only(
        self, extractor: StructuredObservationExtractor
    ) -> None:
        (fact,) = extractor.extract_lab(
            test_name="LDL cholesterol",
            value="300",
            occurrence=OCCURRENCE,
            abnormal_flag="H",
        )
        assert fact.quality_metadata["source_provided_flag"] == "H"

    def test_missing_value_is_other_for_review(
        self, extractor: StructuredObservationExtractor
    ) -> None:
        (fact,) = extractor.extract_lab(
            test_name="LDL cholesterol", value="", occurrence=OCCURRENCE
        )
        assert fact.fact_type is FactType.OTHER
        assert fact.quality_flag is QualityFlag.REQUIRES_REVIEW
        assert fact.quality_metadata["reason"] == "missing_observation_identity"

    def test_missing_test_name_is_other_for_review(
        self, extractor: StructuredObservationExtractor
    ) -> None:
        (fact,) = extractor.extract_lab(
            test_name="", value="160", occurrence=OCCURRENCE
        )
        assert fact.fact_type is FactType.OTHER

    def test_model_metadata(
        self, extractor: StructuredObservationExtractor
    ) -> None:
        assert extractor.model_name == "wellbe-structured-observation-extractor"
        assert extractor.model_version == "0.1.0"
