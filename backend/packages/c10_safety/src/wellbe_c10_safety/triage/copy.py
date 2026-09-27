"""Pre-written triage guidance templates + never-alarm / do-not-diagnose filter.

Template-first copy (approved decision, point 4): the rules select a template,
the only slots are the locale emergency number and crisis line. Every rendered
string must pass ``copy_violations`` — a deterministic filter for diagnostic,
speculative, catastrophic, overconfident and unsupported-reassurance phrasing.

DRAFT COPY — PENDING CLINICAL REVIEW (see docs/safety/triage-red-flag-ruleset.md).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from wellbe_contracts.triage import TriageGuidanceV2

# Locale configuration: only numbers named in the approved decision's sources.
# Anything else falls back to the generalized "your local emergency number".
_EU_112 = frozenset(
    "AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE".split()
)
EMERGENCY_NUMBERS: dict[str, str] = {
    "US": "911",
    "CA": "911",
    "GB": "999",
    "AU": "000",
    **dict.fromkeys(_EU_112, "112"),
}
CRISIS_LINES: dict[str, tuple[str, str]] = {
    # region -> (number, how to refer to it in copy)
    "US": ("988", "the 988 Suicide & Crisis Lifeline (call or text 988)"),
}

GENERIC_EMERGENCY = "your local emergency number"
GENERIC_CRISIS = "a local crisis line"


@dataclass(frozen=True)
class GuidanceTemplate:
    template_id: str
    headline: str
    action: str
    rationale: str
    backstop: str


_SAVE_WHEN_SAFE = "Your answers are still here. You can save your check-in afterwards."

TEMPLATES: dict[str, GuidanceTemplate] = {
    t.template_id: t
    for t in (
        GuidanceTemplate(
            template_id="emergency_now.v1",
            headline="Please get emergency help now",
            action=(
                "Call {emergency} now, or ask someone nearby to call for you. "
                "If you can, don't drive yourself."
            ),
            rationale=(
                "Something you described matches a warning sign that public health "
                "sources say should be checked straight away. WellBe can't tell what "
                "is causing it, and this isn't a diagnosis. Getting checked now is the "
                "safe next step."
            ),
            backstop=_SAVE_WHEN_SAFE,
        ),
        GuidanceTemplate(
            template_id="crisis_support.v1",
            headline="Support is available right now",
            action=(
                "If you might act on these thoughts, or anyone is in danger, call "
                "{emergency} now. You can also reach {crisis} at any time to talk "
                "with someone."
            ),
            rationale=(
                "You mentioned thoughts of harming yourself or someone else. You don't "
                "have to handle this alone. WellBe isn't judging or diagnosing "
                "anything; the aim is to connect you with people who can help now."
            ),
            backstop=(
                "Your answers are still here. You can save your check-in whenever "
                "you're ready."
            ),
        ),
        GuidanceTemplate(
            template_id="pregnancy_urgent.v1",
            headline="Please get medical care now",
            action=(
                "Contact your maternity team or an urgent care service now, and tell "
                "them you're pregnant or recently gave birth. If it feels severe or "
                "you can't reach anyone, call {emergency}."
            ),
            rationale=(
                "Something you described matches a warning sign that public health "
                "sources say needs medical care straight away during pregnancy and in "
                "the year after birth. WellBe can't tell what is causing it, and this "
                "isn't a diagnosis."
            ),
            backstop=_SAVE_WHEN_SAFE,
        ),
        GuidanceTemplate(
            template_id="same_day.v1",
            headline="It's worth speaking to a clinician today",
            action=(
                "Contact your doctor, a nurse advice line, or an urgent care service "
                "today rather than waiting for a routine appointment. If it gets worse, "
                "or you feel it's an emergency, call {emergency}."
            ),
            rationale=(
                "Something you described matches a sign that public health sources "
                "suggest having checked promptly. WellBe can't tell what is causing "
                "it, and this isn't a diagnosis. A clinician can look at it properly."
            ),
            backstop=(
                "This list isn't complete. If anything feels severe or concerning, "
                "contact a clinician sooner."
            ),
        ),
        GuidanceTemplate(
            template_id="routine.v1",
            headline="None of the warning signs WellBe checks for came up",
            action=(
                "Keep noting how it changes. If it doesn't improve, or you're unsure, "
                "contact your doctor or care team."
            ),
            rationale=(
                "WellBe compares your answers with a short list of warning signs from "
                "public health sources. It can't rule anything out, and this isn't a "
                "diagnosis."
            ),
            backstop=(
                "This list isn't complete. If it feels severe or concerning, contact a "
                "clinician. If you think it's an emergency, call {emergency}."
            ),
        ),
    )
}


def _c(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.I)


# Deterministic never-alarm + do-not-diagnose filter over rendered copy.
BANNED_COPY_PATTERNS: dict[str, re.Pattern[str]] = {
    # Diagnosis / probabilistic diagnosis (docs/safety/do_not_diagnose_rules.md §1).
    "diagnosis_assertion": _c(r"\byou\s+(?:definitely\s+|certainly\s+)?have\s+[a-z]"),
    "diagnostic_conclusion": _c(r"\bthis\s+is\s+(?:definitely\s+|certainly\s+)?[a-z]"),
    "probabilistic_diagnosis": _c(
        r"\b(?:you\s+(?:probably|likely|may|might|could)\s+have|almost\s+certainly|"
        r"most\s+likely|sounds\s+like)\b"
    ),
    "condition_name": _c(
        r"\b(?:stroke|heart attack|cardiac|sepsis|meningitis|anaphyla\w*|cancer|tumou?r|"
        r"infection|pre-?eclampsia|blood clot|embolism|thrombosis|appendicitis|"
        r"depression|psychosis)\b"
    ),
    # Medication directive.
    "medication_directive": _c(r"\b(?:stop|start|change|take|increase|decrease)\s+(?:your\s+)?"
                               r"(?:medication|medicine|dose|pills|tablets)\b"),
    # Unsupported reassurance / false closure.
    "unsupported_reassurance": _c(
        r"\b(?:don't|do not)\s+worry\b|\bnothing\s+to\s+worry\b|\bnot\s+serious\b|"
        r"\byou(?:'re|\s+are)\s+(?:fine|ok|okay|safe|healthy)\b|\ball\s+clear\b|"
        r"\bsafe\s+to\s+wait\b"
    ),
    "false_closure": _c(r"\b(?:this|it|that|which)\s+(?:rules|ruled)\s+(?:\w+\s+){0,2}out\b"),
    # Catastrophic / panic phrasing.
    "catastrophic": _c(
        r"\b(?:life[- ]threatening|fatal|deadly|die|dying|death|critical\s+condition)\b"
    ),
    "panic_pressure": _c(r"!|\bact\s+now\b|\bpanic\b|\bhurry\b|\basap\b|\burgent(?:ly)?!"),
}


def copy_violations(text: str) -> list[str]:
    """Names of every banned-phrase class present in ``text`` (empty = clean)."""
    return [name for name, pattern in BANNED_COPY_PATTERNS.items() if pattern.search(text)]


class TriageCopyViolationError(RuntimeError):
    """A rendered template failed the never-alarm filter — fail closed."""


def render(template_id: str, *, region: str | None) -> TriageGuidanceV2:
    template = TEMPLATES[template_id]
    region = region.upper() if region else None
    emergency_number = EMERGENCY_NUMBERS.get(region) if region else None
    crisis = CRISIS_LINES.get(region) if region else None
    slots = {
        "emergency": emergency_number or GENERIC_EMERGENCY,
        "crisis": crisis[1] if crisis else GENERIC_CRISIS,
    }
    guidance = TriageGuidanceV2(
        template_id=template.template_id,
        headline=template.headline.format(**slots),
        action=template.action.format(**slots),
        rationale=template.rationale.format(**slots),
        backstop=template.backstop.format(**slots),
        emergency_number=emergency_number,
        crisis_line=crisis[0] if crisis and template_id.startswith("crisis") else None,
    )
    for text in (guidance.headline, guidance.action, guidance.rationale, guidance.backstop):
        violations = copy_violations(text)
        if violations:
            raise TriageCopyViolationError(f"{template_id}: {violations}")
    return guidance
