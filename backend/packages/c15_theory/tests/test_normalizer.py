from __future__ import annotations

import pytest
from wellbe_c15_theory.normalizer import (
    normalize_theory_text,
    strip_question_frame,
    theory_display_label,
)
from wellbe_contracts.c15_theory import TheorySafetyLevel


@pytest.mark.parametrize(
    "text",
    [
        "I have lupus",
        "I am diagnosed with diabetes",
        "This is definitely an autoimmune disease",
        "My rash is most likely caused by the new medication",
        "The blood test confirms anemia",
        "This rules out cancer",
    ],
)
def test_diagnostic_assertions_are_blocked(text: str) -> None:
    result = normalize_theory_text(text)
    assert result.blocked is True
    assert result.normalized_question is None
    assert result.safety_level is TheorySafetyLevel.BLOCKED_DUE_TO_DIAGNOSTIC_CLAIM
    assert result.blocked_reason is not None


@pytest.mark.parametrize(
    "text",
    [
        "Could my fatigue be related to my sleep?",
        "Does coffee affect my heart rate",
        "my headaches and screen time",
    ],
)
def test_non_diagnostic_text_is_reframed_as_question(text: str) -> None:
    result = normalize_theory_text(text)
    assert result.blocked is False
    assert result.safety_level is TheorySafetyLevel.LOW
    assert result.normalized_question is not None
    assert result.normalized_question.endswith("?")


def test_existing_question_is_preserved() -> None:
    result = normalize_theory_text("Is my fatigue linked to low iron?")
    assert result.blocked is False
    assert result.normalized_question == "Is my fatigue linked to low iron?"


def test_reframing_is_idempotent() -> None:
    once = normalize_theory_text("my headaches and screen time")
    assert once.normalized_question == "Could my data be related to: my headaches and screen time?"
    twice = normalize_theory_text(once.normalized_question or "")
    assert twice.normalized_question == once.normalized_question


@pytest.mark.parametrize(
    ("stored", "clean"),
    [
        ("Could my data be related to: screen time?", "screen time"),
        (
            "Could my data be related to: Could my data be related to: screen time?",
            "screen time",
        ),
        ("could my data be related to screen time?", "screen time"),
        ("Is my fatigue linked to low iron?", "Is my fatigue linked to low iron?"),
        ("Could my data be related tomatoes?", "Could my data be related tomatoes?"),
        ("Could my data be related to:", "Could my data be related to:"),
    ],
)
def test_strip_question_frame(stored: str, clean: str) -> None:
    assert strip_question_frame(stored) == clean


def test_display_label_has_no_frame_and_is_bounded() -> None:
    assert theory_display_label("Could my data be related to: sleep?", "sleep") == "sleep"
    assert theory_display_label(None, "x" * 500) == "x" * 200
