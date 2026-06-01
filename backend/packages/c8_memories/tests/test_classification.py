from __future__ import annotations

from wellbe_contracts.c8_memory import (
    DEFAULT_AUTHORSHIP,
    DERIVED_MEMORY_TYPES,
    AuthorshipMode,
    MemoryType,
)


def test_every_memory_type_has_default_authorship() -> None:
    for mt in MemoryType:
        assert mt in DEFAULT_AUTHORSHIP


def test_clinical_and_pattern_are_derived() -> None:
    assert MemoryType.CLINICAL in DERIVED_MEMORY_TYPES
    assert MemoryType.PATTERN in DERIVED_MEMORY_TYPES
    assert DEFAULT_AUTHORSHIP[MemoryType.CLINICAL] == AuthorshipMode.SYSTEM_DERIVED
    assert DEFAULT_AUTHORSHIP[MemoryType.PATTERN] == AuthorshipMode.SYSTEM_DERIVED


def test_story_and_equity_are_controller_sourced() -> None:
    assert DEFAULT_AUTHORSHIP[MemoryType.STORY] == AuthorshipMode.CONTROLLER_AUTHORED
    assert (
        DEFAULT_AUTHORSHIP[MemoryType.EQUITY_ACCESS]
        == AuthorshipMode.CONTROLLER_CONFIRMED
    )
    # Authored/confirmed memory types are not in the derived-evidence-gate set.
    assert MemoryType.STORY not in DERIVED_MEMORY_TYPES
    assert MemoryType.EQUITY_ACCESS not in DERIVED_MEMORY_TYPES


def test_decision_and_responsibility_are_hybrid() -> None:
    assert DEFAULT_AUTHORSHIP[MemoryType.DECISION] == AuthorshipMode.HYBRID
    assert DEFAULT_AUTHORSHIP[MemoryType.RESPONSIBILITY] == AuthorshipMode.HYBRID
