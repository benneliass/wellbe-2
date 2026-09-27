"""Clause segmentation and negation detection for the triage red-flag rules.

A small NegEx-style detector, tuned to be conservative (the approved decision
accepts over-triage in exchange for fewer missed warning signs):

- Text is split into clauses on sentence punctuation, commas, semicolons and
  contrast words ("but", "however", "except", "other than", ...). Negation never
  carries across a clause boundary, so "no fever, chest pain since this morning"
  still counts the chest pain.
- A sign is negated only when a negation cue ("no", "not", "don't have",
  "without", "denies", ...) appears in the same clause within the few words
  before it, or a post-negation ("chest pain: none") follows it.
- Pseudo-negations ("not sure", "no idea", "not only") are not cues, so
  "not sure if it's chest pain" still counts.
- "until"/"till" after the sign cancels the negation ("never had chest pain
  until today").
- "can't"/"cannot"/"couldn't" are deliberately NOT cues: "can't breathe" and
  "couldn't stop the bleeding" are warning signs, not negations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

NEGATION_WINDOW_WORDS = 6

_CLAUSE_SPLIT = re.compile(
    r"(?:[!?;,\n]|(?<!\d)\.|\.(?!\d))+|\b(?:but|however|although|though|except|yet|whereas|"
    r"apart from|aside from|other than)\b",
    re.I,
)

_NEGATION_CUE = re.compile(
    r"\b(?:no|not|never|without|denies|deny|denied|none|nor|neither|free of|"
    r"absence of|negative for|no longer|zero|"
    r"don't|dont|do not|doesn't|doesnt|does not|didn't|didnt|did not|"
    r"haven't|havent|have not|hasn't|hasnt|has not|hadn't|hadnt|had not|"
    r"isn't|isnt|is not|wasn't|wasnt|was not|aren't|arent|are not|"
    r"weren't|werent|were not|am not|i'm not|im not)\b",
    re.I,
)

_PSEUDO_NEGATION = re.compile(
    r"\b(?:not sure|not certain|not only|not just|not necessarily|no doubt|"
    r"no idea|no clue|not clear|unsure|"
    r"(?:don't|dont|do not|doesn't|does not|didn't|did not) (?:know|understand|get)|"
    r"not know|not understand)\b",
    re.I,
)

_POST_NEGATION = re.compile(r"^\s*[:\-–—?]\s*(?:no|none|denies|nope)\b", re.I)

# "never had chest pain until today / before / like this" describes a new sign.
_NEGATION_CANCEL = re.compile(
    r"\b(?:until|till|til|before|like this|like that|this bad|so bad)\b", re.I
)


@dataclass(frozen=True)
class Segment:
    """One clause of one check-in answer."""

    answer_field: str
    text: str


def normalize(text: str) -> str:
    """Lower-case and fold typographic apostrophes/dashes so patterns stay simple."""
    return (
        text.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u02bc", "'")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .lower()
    )


def segments_for(answer_field: str, text: str) -> list[Segment]:
    clauses = (c.strip() for c in _CLAUSE_SPLIT.split(normalize(text)))
    return [Segment(answer_field, c) for c in clauses if c]


def is_negated(clause: str, start: int, end: int) -> bool:
    """Whether the sign at ``clause[start:end]`` is negated within its clause."""
    after = clause[end:]
    if _POST_NEGATION.match(after):
        return True
    words = clause[:start].split()
    window = " ".join(words[-NEGATION_WINDOW_WORDS:])
    if not window:
        return False
    pseudo_spans = [m.span() for m in _PSEUDO_NEGATION.finditer(window)]
    for cue in _NEGATION_CUE.finditer(window):
        if any(ps <= cue.start() < pe for ps, pe in pseudo_spans):
            continue
        return not _NEGATION_CANCEL.search(after)
    return False


def affirmed(pattern: re.Pattern[str], segment: Segment) -> bool:
    """True when ``pattern`` matches ``segment`` at least once without negation."""
    return any(
        not is_negated(segment.text, m.start(), m.end()) for m in pattern.finditer(segment.text)
    )
