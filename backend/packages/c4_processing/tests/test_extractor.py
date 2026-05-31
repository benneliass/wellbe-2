from __future__ import annotations

import uuid

import pytest

from wellbe_c4_processing.extractor import (
    ExtractionResult,
    TextFactExtractor,
    compute_quality_flag,
)
from wellbe_contracts.c4_processing import FactType, QualityFlag


class TestComputeQualityFlag:
    def test_clean_above_085(self):
        assert compute_quality_flag(0.90) == QualityFlag.CLEAN
        assert compute_quality_flag(0.85) == QualityFlag.CLEAN
        assert compute_quality_flag(1.0) == QualityFlag.CLEAN

    def test_low_confidence_060_to_085(self):
        assert compute_quality_flag(0.60) == QualityFlag.LOW_CONFIDENCE
        assert compute_quality_flag(0.75) == QualityFlag.LOW_CONFIDENCE
        assert compute_quality_flag(0.84) == QualityFlag.LOW_CONFIDENCE

    def test_requires_review_below_060(self):
        assert compute_quality_flag(0.59) == QualityFlag.REQUIRES_REVIEW
        assert compute_quality_flag(0.0) == QualityFlag.REQUIRES_REVIEW
        assert compute_quality_flag(0.30) == QualityFlag.REQUIRES_REVIEW

    def test_partial_overrides_confidence(self):
        assert compute_quality_flag(0.99, is_partial=True) == QualityFlag.PARTIAL
        assert compute_quality_flag(0.10, is_partial=True) == QualityFlag.PARTIAL


class TestTextFactExtractor:
    @pytest.fixture
    def extractor(self) -> TextFactExtractor:
        return TextFactExtractor()

    @pytest.mark.asyncio
    async def test_extracts_symptom_keyword(self, extractor: TextFactExtractor):
        results = await extractor.extract("I have a headache today", uuid.uuid4())
        assert len(results) >= 1
        headache_result = next(r for r in results if r.normalized_key == "headache")
        assert headache_result.fact_type == FactType.SYMPTOM
        assert headache_result.entity_label == "headache"
        assert headache_result.extraction_confidence == 0.90
        assert headache_result.quality_flag == QualityFlag.CLEAN
        assert headache_result.text_span_start is not None
        assert headache_result.text_span_end is not None

    @pytest.mark.asyncio
    async def test_extracts_medication_keyword(self, extractor: TextFactExtractor):
        results = await extractor.extract("Taking ibuprofen for pain", uuid.uuid4())
        med_results = [r for r in results if r.fact_type == FactType.MEDICATION]
        assert len(med_results) >= 1
        assert med_results[0].normalized_key == "ibuprofen"

    @pytest.mark.asyncio
    async def test_detects_negation(self, extractor: TextFactExtractor):
        results = await extractor.extract("I don't have headache", uuid.uuid4())
        headache = next(r for r in results if r.normalized_key == "headache")
        assert headache.is_negated is True

    @pytest.mark.asyncio
    async def test_no_keywords_returns_fallback(self, extractor: TextFactExtractor):
        results = await extractor.extract("Just a general note", uuid.uuid4())
        assert len(results) == 1
        assert results[0].fact_type == FactType.OTHER
        assert results[0].extraction_confidence == 0.50
        assert results[0].quality_flag == QualityFlag.REQUIRES_REVIEW

    @pytest.mark.asyncio
    async def test_multiple_keywords_extracted(self, extractor: TextFactExtractor):
        results = await extractor.extract(
            "I have headache and nausea, taking ibuprofen", uuid.uuid4()
        )
        types = {r.normalized_key for r in results}
        assert "headache" in types
        assert "nausea" in types
        assert "ibuprofen" in types

    @pytest.mark.asyncio
    async def test_model_metadata(self, extractor: TextFactExtractor):
        assert extractor.model_name == "wellbe-text-extractor"
        assert extractor.model_version == "0.1.0"
