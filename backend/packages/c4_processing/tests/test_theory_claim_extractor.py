from __future__ import annotations

from wellbe_c4_processing.investigation_extractor import (
    ExternalClaimExtractor,
    TheoryClaimExtractor,
)


async def test_theory_claim_extractor_marks_hypotheses_as_theories_not_facts():
    results = await TheoryClaimExtractor().extract(
        "Possible migraine may explain the headache pattern."
    )

    assert len(results) == 1
    assert results[0].object_type == "theory"
    assert results[0].claim_text == "Possible migraine may explain the headache pattern."
    assert results[0].diagnostic_assertion is False


async def test_external_claim_extractor_keeps_external_scope_and_quality_tier():
    result = await ExternalClaimExtractor().extract(
        source_id="source-1",
        source_quality_tier=2,
        text="Guidelines say sleep disruption can worsen migraine frequency.",
    )

    assert result.source_id == "source-1"
    assert result.source_scope == "external"
    assert result.source_quality_tier == 2
    assert result.personal_evidence is False
