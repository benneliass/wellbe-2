from __future__ import annotations

import pytest

# Import the mapping from the processing-worker tasks module
# We test it in isolation here since it's a critical safety contract
import sys
import os

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "..",
    "apps", "processing-worker", "src",
))

from wellbe_processing_worker.tasks import FACT_TYPE_TO_NODE_TYPE


class TestNodeTypeMapping:
    def test_dx_mention_maps_to_condition_hypothesis(self):
        """dx_mention must NEVER map to 'Condition' — always 'ConditionHypothesis'.
        This is a safety requirement: WellBe investigates, never diagnoses."""
        assert FACT_TYPE_TO_NODE_TYPE["dx_mention"] == "ConditionHypothesis"

    def test_finding_maps_to_condition_hypothesis(self):
        assert FACT_TYPE_TO_NODE_TYPE["finding"] == "ConditionHypothesis"

    def test_symptom_maps_to_symptom(self):
        assert FACT_TYPE_TO_NODE_TYPE["symptom"] == "Symptom"

    def test_medication_maps_to_medication(self):
        assert FACT_TYPE_TO_NODE_TYPE["medication"] == "Medication"

    def test_lab_result_maps_to_lab_result(self):
        assert FACT_TYPE_TO_NODE_TYPE["lab_result"] == "LabResult"

    def test_vital_sign_maps_to_vital_sign(self):
        assert FACT_TYPE_TO_NODE_TYPE["vital_sign"] == "VitalSign"

    def test_allergy_maps_to_allergy(self):
        assert FACT_TYPE_TO_NODE_TYPE["allergy"] == "Allergy"

    def test_other_maps_to_other(self):
        assert FACT_TYPE_TO_NODE_TYPE["other"] == "Other"

    def test_no_condition_node_type_exists(self):
        """There must never be a 'Condition' node type — only ConditionHypothesis."""
        for node_type in FACT_TYPE_TO_NODE_TYPE.values():
            assert node_type != "Condition"

    def test_all_fact_types_have_mapping(self):
        from wellbe_contracts.c4_processing import FactType
        for ft in FactType:
            assert ft.value in FACT_TYPE_TO_NODE_TYPE, f"Missing mapping for {ft.value}"
