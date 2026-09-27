from __future__ import annotations

import uuid

import pytest
from wellbe_c4_processing.extractor import TextFactExtractor, parse_lab_lines
from wellbe_contracts.c4_processing import FactType

_PID = uuid.uuid4()


async def _keys(text: str) -> dict[str, bool]:
    results = await TextFactExtractor().extract(text, _PID)
    return {r.normalized_key: r.is_negated for r in results}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("text", "key"),
    [
        ("Feeling very tired and low energy all week.", "fatigue"),
        ("So exhausted lately", "fatigue"),
        ("I get lightheaded when I stand up", "dizziness"),
        ("Migraine again", "headache"),
        ("Feeling nauseous after meals", "nausea"),
    ],
)
async def test_synonyms_map_to_canonical_concepts(text: str, key: str) -> None:
    assert key in await _keys(text)


@pytest.mark.asyncio
async def test_one_fact_per_concept_even_with_several_surface_forms() -> None:
    results = await TextFactExtractor().extract("Tired, exhausted, low energy.", _PID)
    assert [r.normalized_key for r in results] == ["fatigue"]


@pytest.mark.asyncio
async def test_specific_pain_does_not_also_yield_generic_pain() -> None:
    assert await _keys("Chest pain since yesterday") == {"chest_pain": False}


@pytest.mark.asyncio
async def test_body_site_pain_keeps_the_site() -> None:
    results = await TextFactExtractor().extract("My knee pain is worse on stairs", _PID)
    assert [(r.normalized_key, r.entity_label) for r in results] == [("pain:knee", "knee pain")]


@pytest.mark.asyncio
async def test_word_boundaries_prevent_substring_matches() -> None:
    # "coughing" is a cough; "painting" is not pain.
    assert await _keys("Went painting, kept coughing") == {"cough": False}


@pytest.mark.asyncio
async def test_negation_does_not_cross_sentences() -> None:
    assert await _keys("Dry cough at night. No fever.") == {"cough": False, "fever": True}
    assert await _keys("No fever. Cough at night.") == {"fever": True, "cough": False}


@pytest.mark.asyncio
async def test_medication_is_extracted_but_never_negated() -> None:
    results = await TextFactExtractor().extract(
        "Started iron supplements. Dizziness when standing up quickly.", _PID
    )
    by_key = {r.normalized_key: r for r in results}
    assert by_key["iron_supplement"].fact_type is FactType.MEDICATION
    assert by_key["dizziness"].is_negated is False


def test_parse_lab_lines_reads_value_unit_and_reference() -> None:
    labs = parse_lab_lines("Vitamin B12: 180 pg/mL (ref 200-900)\nFerritin = 9 ng/mL")
    assert labs == [
        {"test_name": "Vitamin B12", "value": "180", "unit": "pg/mL",
         "reference_range": "200-900"},
        {"test_name": "Ferritin", "value": "9", "unit": "ng/mL", "reference_range": None},
    ]


def test_parse_lab_lines_ignores_prose_without_unit_or_range() -> None:
    assert parse_lab_lines("Pain: 7\nMood: 3") == []
