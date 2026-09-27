"""Theory-text normalization and diagnostic-claim detection (C15 validator).

This is C15's own deterministic guardrail layer — it does NOT replace C10. It
either reframes free text into a non-diagnostic question, or blocks it when the
text asserts a diagnosis (status blocked_due_to_diagnostic_claim, withheld).

Per the decision's open risk: do not rely on C10 as the sole guardrail — also
enforce via validators (this module), schema constraints, and prohibited edges.
"""

from __future__ import annotations

import re

from wellbe_contracts.c15_theory import TheorySafetyLevel, TheoryTextNormalization

# Hard diagnostic-assertion patterns. If any match, the text is blocked.
_DIAGNOSTIC_ASSERTION_PATTERNS = (
    re.compile(r"\bI\s+(?:definitely\s+|certainly\s+)?have\s+[a-z]", re.I),
    re.compile(r"\b(?:I'm|I am)\s+diagnosed\s+with\b", re.I),
    re.compile(r"\bdiagnosed\s+with\b", re.I),
    re.compile(r"\bthis\s+is\s+(?:definitely\s+|certainly\s+)?(?:a\s+)?[a-z]", re.I),
    re.compile(r"\b(?:it'?s|its)\s+(?:definitely|certainly|most\s+likely)\b", re.I),
    re.compile(r"\bmost\s+likely\b", re.I),
    re.compile(r"\brules?\s+out\b", re.I),
    re.compile(r"\bconfirms?\b", re.I),
    re.compile(r"\bproves?\b", re.I),
    re.compile(r"\bcaused\s+by\b", re.I),
    re.compile(r"\bdefinitely\s+have\b", re.I),
)


QUESTION_FRAME = "Could my data be related to:"

# Matches the frame this module adds (with or without the colon), repeated.
_FRAME_RE = re.compile(r"^(?:\s*could\s+my\s+data\s+be\s+related\s+to\b\s*:?\s*)+", re.I)


def strip_question_frame(text: str) -> str:
    """Remove the 'Could my data be related to:' frame from a stored label.

    The frame is a UI concern; labels persisted before it moved to the UI still
    carry it (sometimes twice), so readers strip it. Text the user phrased as
    their own question is left untouched.
    """
    stripped = text.strip()
    core = _FRAME_RE.sub("", stripped)
    if core == stripped:
        return stripped
    return core.rstrip("?").strip() or stripped


def theory_display_label(normalized_question: str | None, theory_text: str) -> str:
    """The clean label stored on a theory's graph node (no question frame)."""
    return strip_question_frame(normalized_question or theory_text)[:200]


def _matched_pattern(text: str) -> str | None:
    for pattern in _DIAGNOSTIC_ASSERTION_PATTERNS:
        if pattern.search(text):
            return pattern.pattern
    return None


def normalize_theory_text(text: str) -> TheoryTextNormalization:
    """Reframe free text into a safe question, or block a diagnostic assertion."""
    stripped = strip_question_frame(text)
    matched = _matched_pattern(stripped)
    if matched is not None:
        return TheoryTextNormalization(
            blocked=True,
            normalized_question=None,
            safety_level=TheorySafetyLevel.BLOCKED_DUE_TO_DIAGNOSTIC_CLAIM,
            blocked_reason=f"diagnostic_assertion:{matched}",
        )

    # Reframe into a question form ("...?") without asserting truth.
    if stripped.endswith("?"):
        question = stripped
    else:
        core = stripped.rstrip(".")
        question = f"{QUESTION_FRAME} {core}?"

    return TheoryTextNormalization(
        blocked=False,
        normalized_question=question,
        safety_level=TheorySafetyLevel.LOW,
    )
