"""Published-case concern keys stay scoped to one case. Real captures do not."""

from wellbe_c9_continuity.genesis import published_case_concept_id


def test_published_case_source_scopes_the_concept_id() -> None:
    assert published_case_concept_id("pain", "published-case:C001") == "pain|published-case:C001"
    assert published_case_concept_id("pain", "published-case:C002") == "pain|published-case:C002"


def test_real_captures_and_bad_ids_are_not_scoped() -> None:
    assert published_case_concept_id("pain", None) is None
    assert published_case_concept_id("pain", "manual") is None
    assert published_case_concept_id("pain", "published-case:") is None
    assert published_case_concept_id("pain", "published-case:C001 extra") is None
    assert published_case_concept_id("pain", "published-case: C001") is None
    assert published_case_concept_id("pain", 12) is None
