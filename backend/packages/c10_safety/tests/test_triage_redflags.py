"""Unit tests for the deterministic triage red-flag evaluator (C10, WEL-162).

Covers: every emergency-now sign category from the approved decision, negation
("no chest pain"), clause boundaries, the pregnancy/postpartum branch, the
crisis path, same-day signs, the routine backstop, template-only copy passing
the never-alarm / do-not-diagnose filter for every locale, locale substitution,
and the pinned rule-set fingerprint that forces a safety-case re-review.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from wellbe_c10_safety.triage import (
    CLINICAL_REVIEW_STATUS,
    RULES,
    RULESET_VERSION,
    answers_sha256,
    copy_violations,
    evaluate_triage,
    ruleset_fingerprint,
)
from wellbe_c10_safety.triage.copy import (
    BANNED_COPY_PATTERNS,
    CRISIS_LINES,
    EMERGENCY_NUMBERS,
    TEMPLATES,
    render,
)
from wellbe_c10_safety.triage.negation import is_negated, segments_for
from wellbe_c10_safety.triage.sources import SOURCES
from wellbe_contracts.triage import TriageEvaluateRequestV2, TriageRoute

_SAFETY_CASE = Path(__file__).resolve().parents[4] / "docs/safety/triage-red-flag-ruleset.md"


def _eval(what: str, **extra: Any) -> Any:
    context = extra.pop("context", {})
    return evaluate_triage(
        TriageEvaluateRequestV2.model_validate(
            {"answers": {"what": what, **extra}, "context": context}
        )
    )


def _ids(result: Any) -> set[str]:
    return {r.rule_id for r in result.matched_rules}


# ------------------------------------------------------------------ emergency now

URGENT_CASES = [
    ("I have chest pain and I'm short of breath", "U-CHEST-01"),
    ("There's a crushing pressure in my chest", "U-CHEST-01"),
    ("My chest feels tight and heavy", "U-CHEST-01"),
    ("I can't breathe properly", "U-BREATH-01"),
    ("I'm struggling to breathe", "U-BREATH-01"),
    ("My lips look blue", "U-BREATH-01"),
    ("I haven't been able to catch my breath all morning", "U-BREATH-01"),
    ("Suddenly short of breath while sitting", "U-BREATH-02"),
    ("My face is drooping on one side", "U-STROKE-FACE-01"),
    ("Sudden weakness in my left arm", "U-STROKE-ARM-01"),
    ("I can't lift my right arm", "U-STROKE-ARM-01"),
    ("My speech is slurred", "U-STROKE-SPEECH-01"),
    ("I can't get my words out", "U-STROKE-SPEECH-01"),
    ("I lost my vision in one eye", "U-STROKE-VISION-01"),
    ("Suddenly dizzy and lost my balance", "U-STROKE-BALANCE-01"),
    ("The worst headache of my life", "U-HEAD-01"),
    ("A headache that came on suddenly like a thunderclap", "U-HEAD-01"),
    ("I passed out in the kitchen", "U-CONSC-01"),
    ("My dad is unresponsive and we can't wake him", "U-CONSC-01"),
    ("She seems confused and disoriented", "U-CONFUSION-01"),
    ("I had a seizure an hour ago", "U-SEIZURE-01"),
    ("There's heavy bleeding from the cut", "U-BLEED-01"),
    ("The bleeding won't stop", "U-BLEED-01"),
    ("I've been coughing up blood", "U-BLEED-01"),
    ("My throat is swelling after eating nuts", "U-ALLERGY-01"),
    ("I used my EpiPen", "U-ALLERGY-01"),
    ("I think I took too many pills", "U-OVERDOSE-01"),
    ("My toddler swallowed bleach", "U-OVERDOSE-01"),
    ("Severe stomach pain since this morning", "U-ABDO-01"),
    ("A sudden severe pain in my back", "U-PAIN-01"),
    ("I have a fever and a stiff neck", "U-FEVER-NECK-01"),
    ("There's a rash that doesn't fade when I press a glass on it", "U-RASH-01"),
    ("I think I'm having a heart attack", "U-DESCRIBED-01"),
    ("We need an ambulance", "U-DESCRIBED-01"),
    ("I've been having thoughts of ending my life", "U-HARM-SELF-01"),
    ("I feel suicidal", "U-HARM-SELF-01"),
    ("I've been hurting myself", "U-HARM-SELF-01"),
    ("I don't want to be alive anymore", "U-HARM-SELF-01"),
    ("I'm scared I might hurt someone", "U-HARM-OTHERS-01"),
]


@pytest.mark.parametrize(("text", "rule_id"), URGENT_CASES)
def test_emergency_signs_route_urgent(text: str, rule_id: str) -> None:
    result = _eval(text)
    assert rule_id in _ids(result), (text, _ids(result))
    assert result.route is TriageRoute.URGENT
    assert result.safety_gate_decision == "route_urgent"


def test_every_urgent_rule_has_a_positive_case() -> None:
    covered = {rule_id for _, rule_id in URGENT_CASES}
    general_urgent = {
        r.rule_id for r in RULES if r.route is TriageRoute.URGENT and r.population == "general"
    }
    assert general_urgent <= covered, general_urgent - covered


def test_signs_are_found_in_any_answer_field() -> None:
    result = _eval("Feeling off today", worry="Why does my chest hurt so much?")
    assert result.route is TriageRoute.URGENT
    assert result.matched_rules[0].answer_field == "worry"


# ----------------------------------------------------------------------- negation

NEGATED_CASES = [
    "no chest pain",
    "No chest pain or shortness of breath",
    "I don't have any chest pain",
    "I have no trouble breathing",
    "I'm not short of breath at all",
    "Denies chest pain",
    "Without any chest tightness",
    "chest pain: none",
    "I'm not suicidal, just tired",
    "I don't want to die, I just want answers",
    "No bleeding and no fever",
    "It isn't the worst headache of my life, just annoying",
    "I haven't passed out",
]


@pytest.mark.parametrize("text", NEGATED_CASES)
def test_negated_signs_do_not_match(text: str) -> None:
    result = _eval(text)
    assert result.route is TriageRoute.ROUTINE, (text, _ids(result))
    assert result.matched_rules == []


@pytest.mark.parametrize(
    ("text", "rule_id"),
    [
        # Negation never crosses a clause boundary.
        ("No fever, but chest pain since this morning", "U-CHEST-01"),
        ("no fever, chest pain since this morning", "U-CHEST-01"),
        ("No symptoms other than chest pain", "U-CHEST-01"),
        # Pseudo-negations are not negations.
        ("Not sure if it's chest pain or heartburn", "U-CHEST-01"),
        ("I don't know why my chest hurts", "U-CHEST-01"),
        # "never ... until/before/like this" describes a new sign.
        ("Never had chest pain until today", "U-CHEST-01"),
        ("I've never had chest pain like this before", "U-CHEST-01"),
        # "can't"/"couldn't" are part of the sign, not a negation.
        ("I couldn't stop the bleeding", "U-BLEED-01"),
        ("I can't breathe", "U-BREATH-01"),
    ],
)
def test_conservative_negation_edges_still_match(text: str, rule_id: str) -> None:
    assert rule_id in _ids(_eval(text)), text


def test_is_negated_window_is_bounded() -> None:
    clause = segments_for("what", "not really sure what started this whole thing with chest pain")[0]
    start = clause.text.index("chest pain")
    # The cue is part of a pseudo-negation ("not ... sure") far outside the window.
    assert not is_negated(clause.text, start, start + len("chest pain"))


# ------------------------------------------------------------ routine / same-day

ROUTINE_CASES = [
    "Dizzy when I stand up. It passes after a minute.",
    "I've been more tired than usual for a few weeks",
    "I'm confused about my lab results",
    "Food poisoning I think, some nausea since last night",
    "I can't talk to my doctor about this, it's embarrassing",
    "I keep fit and I'm sleeping badly",
    "My knee aches after running",
    "I sob when I think about my job",
]


@pytest.mark.parametrize("text", ROUTINE_CASES)
def test_everyday_concerns_route_routine_with_backstop(text: str) -> None:
    result = _eval(text)
    assert result.route is TriageRoute.ROUTINE, (text, _ids(result))
    assert result.safety_gate_decision == "allow_with_obligations"
    assert result.guidance.template_id == "routine.v1"
    assert "isn't complete" in result.guidance.backstop
    assert "your local emergency number" in result.guidance.backstop
    assert {s.source_id for s in result.sources} == {
        "medlineplus-emergencies",
        "cdc-flu-warning-signs",
    }


SOON_CASES = [
    ("Short of breath climbing stairs for months", "S-BREATH-01"),
    ("A severe headache for two days", "S-HEAD-01"),
    ("My vision is blurry", "S-VISION-01"),
    ("I feel like I'm going to pass out", "S-FAINT-01"),
    ("A very high fever", "S-FEVER-01"),
    ("My temperature is 39.8 and it keeps coming back", "S-FEVER-01"),
    ("I haven't been peeing much and can't keep fluids down", "S-FLUIDS-01"),
    ("Terrible back pain", "S-PAIN-01"),
    ("There's blood in my pee", "S-BLOOD-01"),
    ("It's getting worse quickly", "S-WORSE-01"),
    ("I'm worried it's a stroke", "S-CONCERN-01"),
    ("Is this an emergency?", "S-CONCERN-01"),
]


@pytest.mark.parametrize(("text", "rule_id"), SOON_CASES)
def test_same_day_signs_route_soon(text: str, rule_id: str) -> None:
    result = _eval(text)
    assert rule_id in _ids(result), (text, _ids(result))
    assert result.route is TriageRoute.SOON
    assert result.guidance.template_id == "same_day.v1"
    assert result.safety_gate_decision == "allow_with_obligations"


def test_structured_answers_route_soon_for_recent_loss_of_function() -> None:
    result = _eval("I feel off", onset="Today", impact="I can't do my usual things")
    assert _ids(result) == {"S-FUNCTION-01"}
    assert result.route is TriageRoute.SOON
    assert result.matched_rules[0].answer_field == "impact"
    older = _eval("I feel off", onset="Months ago or longer", impact="I can't do my usual things")
    assert older.route is TriageRoute.ROUTINE


def test_onset_today_upgrades_shortness_of_breath_to_urgent() -> None:
    assert _eval("I'm short of breath").route is TriageRoute.SOON
    today = _eval("I'm short of breath", onset="Today")
    assert "U-BREATH-02" in _ids(today)
    assert today.route is TriageRoute.URGENT


def test_the_most_urgent_route_wins() -> None:
    result = _eval("Terrible back pain and now my speech is slurred")
    assert {"S-PAIN-01", "U-STROKE-SPEECH-01"} <= _ids(result)
    assert result.route is TriageRoute.URGENT
    assert result.guidance.template_id == "emergency_now.v1"


# ------------------------------------------------------ pregnancy / postpartum


@pytest.mark.parametrize(
    ("text", "rule_id"),
    [
        ("I'm 30 weeks pregnant and have a headache", "P-HEADACHE-01"),
        ("I gave birth 3 weeks ago and I feel dizzy", "P-DIZZY-01"),
        ("Pregnant and seeing spots", "P-VISION-01"),
        ("Postpartum, running a temperature", "P-FEVER-01"),
        ("I'm pregnant and my hands and face are swollen", "P-SWELLING-01"),
        ("Pregnant and my heart is racing", "P-HEART-01"),
        ("Pregnant and I can't stop vomiting", "P-VOMIT-01"),
        ("I'm pregnant with belly pain", "P-BELLY-01"),
        ("The baby is moving less than usual, I'm 34 weeks pregnant", "P-MOVEMENT-01"),
        ("Pregnant and some spotting", "P-BLEED-01"),
        ("Had my baby last month and my calf is swollen and red", "P-LEG-01"),
        ("Since the birth I've had overwhelming tiredness", "P-TIRED-01"),
        ("Since the birth I have thoughts of harming my baby", "P-HARM-BABY-01"),
    ],
)
def test_pregnancy_branch_routes_urgent(text: str, rule_id: str) -> None:
    result = _eval(text)
    assert rule_id in _ids(result), (text, _ids(result))
    assert result.route is TriageRoute.URGENT


def test_every_pregnancy_rule_is_gated_on_pregnancy() -> None:
    assert _eval("I have a headache").route is TriageRoute.ROUTINE
    assert _eval("I'm not pregnant, I have a headache").route is TriageRoute.ROUTINE
    flagged = _eval("I have a headache", context={"pregnant_or_postpartum": True})
    assert _ids(flagged) == {"P-HEADACHE-01"}
    assert flagged.guidance.template_id == "pregnancy_urgent.v1"
    assert "maternity team" in flagged.guidance.action
    # An explicit "no" never hides a pregnancy mention in the answers.
    mentioned = _eval("Pregnant, bad headache", context={"pregnant_or_postpartum": False})
    assert "P-HEADACHE-01" in _ids(mentioned)


def test_general_emergency_copy_wins_over_pregnancy_copy() -> None:
    result = _eval("I'm pregnant and I have chest pain")
    assert {"U-CHEST-01"} <= _ids(result)
    assert result.guidance.template_id == "emergency_now.v1"


# ------------------------------------------------------------------- crisis path


def test_crisis_path_uses_crisis_copy_and_flags_support() -> None:
    result = _eval("I keep thinking about killing myself")
    assert result.route is TriageRoute.URGENT
    assert result.crisis_support is True
    assert result.guidance.template_id == "crisis_support.v1"
    assert "your local emergency number" in result.guidance.action
    assert "a local crisis line" in result.guidance.action
    assert {"nimh-suicide-warning-signs", "samhsa-in-crisis"} <= {
        s.source_id for s in result.sources
    }


def test_crisis_copy_wins_over_other_emergency_copy() -> None:
    result = _eval("Chest pain and I want to end my life")
    assert result.guidance.template_id == "crisis_support.v1"


# ------------------------------------------------------------ locale + copy rules


def test_generic_default_when_no_region() -> None:
    result = _eval("chest pain")
    assert result.jurisdiction == "generic"
    assert result.guidance.emergency_number is None
    assert "Call your local emergency number now" in result.guidance.action


@pytest.mark.parametrize(("region", "number"), [("US", "911"), ("gb", "999"), ("AU", "000"),
                                                ("DE", "112"), ("FR", "112")])
def test_region_substitutes_emergency_number(region: str, number: str) -> None:
    result = _eval("chest pain", context={"region": region})
    assert result.jurisdiction == region.upper()
    assert result.guidance.emergency_number == number
    assert f"Call {number} now" in result.guidance.action


def test_unknown_region_falls_back_to_generic_wording() -> None:
    result = _eval("chest pain", context={"region": "IL"})
    assert result.jurisdiction == "IL"
    assert result.guidance.emergency_number is None
    assert "your local emergency number" in result.guidance.action


def test_us_crisis_line_is_substituted() -> None:
    result = _eval("I feel suicidal", context={"region": "US"})
    assert result.guidance.crisis_line == "988"
    assert "988" in result.guidance.action
    assert _eval("chest pain", context={"region": "US"}).guidance.crisis_line is None


def test_default_region_applies_when_request_has_none() -> None:
    request = TriageEvaluateRequestV2.model_validate({"answers": {"what": "chest pain"}})
    assert evaluate_triage(request, default_region="GB").guidance.emergency_number == "999"


@pytest.mark.parametrize("template_id", sorted(TEMPLATES))
@pytest.mark.parametrize("region", [None, *sorted(EMERGENCY_NUMBERS), *sorted(CRISIS_LINES)])
def test_every_rendered_template_passes_the_never_alarm_filter(
    template_id: str, region: str | None
) -> None:
    guidance = render(template_id, region=region)
    for text in (guidance.headline, guidance.action, guidance.rationale, guidance.backstop):
        assert copy_violations(text) == [], (template_id, region, text)
        assert "{" not in text
    # Every route carries a concrete next step (urgency never without action).
    assert guidance.action.strip()


def test_every_template_states_it_is_not_a_diagnosis() -> None:
    for template_id in TEMPLATES:
        rationale = render(template_id, region=None).rationale.lower()
        assert "isn't a diagnosis" in rationale or "diagnosing" in rationale


@pytest.mark.parametrize(
    "bad",
    [
        "You have a serious condition.",
        "This is a stroke.",
        "You probably have an infection.",
        "Don't worry, it's not serious.",
        "You're fine.",
        "This rules everything out.",
        "This could be life-threatening!",
        "Act now",
        "Stop your medication.",
    ],
)
def test_filter_catches_banned_phrasing(bad: str) -> None:
    assert copy_violations(bad), bad


def test_rule_labels_never_name_a_condition() -> None:
    condition = BANNED_COPY_PATTERNS["condition_name"]
    for rule in RULES:
        assert not condition.search(rule.label), rule.rule_id


def test_rules_are_unique_and_source_linked() -> None:
    ids = [r.rule_id for r in RULES]
    assert len(ids) == len(set(ids))
    for rule in RULES:
        assert rule.source_ids, rule.rule_id
        assert all(s in SOURCES for s in rule.source_ids), rule.rule_id
        assert re.fullmatch(r"[UPS]-[A-Z-]+-\d{2}", rule.rule_id), rule.rule_id
        expected = TriageRoute.SOON if rule.rule_id.startswith("S-") else TriageRoute.URGENT
        assert rule.route is expected, rule.rule_id


def test_response_never_echoes_the_answers() -> None:
    secret = "zebra-marmalade chest pain"
    dumped = _eval(secret).model_dump_json()
    assert "zebra" not in dumped
    assert "not_diagnosis" in dumped


def test_response_metadata() -> None:
    result = _eval("chest pain")
    assert result.ruleset_version == RULESET_VERSION
    assert result.clinical_review_status == CLINICAL_REVIEW_STATUS == "pending_clinical_review"
    assert result.not_diagnosis is True
    assert result.matched_rules[0].source_ids


def test_answers_hash_is_stable_and_content_sensitive() -> None:
    a = TriageEvaluateRequestV2.model_validate({"answers": {"what": "a"}})
    b = TriageEvaluateRequestV2.model_validate({"answers": {"what": "b"}})
    assert answers_sha256(a) == answers_sha256(a)
    assert answers_sha256(a) != answers_sha256(b)


def test_ruleset_change_requires_safety_case_update() -> None:
    """Any rule/template change must bump the version and re-open the safety case.

    If this fails: bump RULESET_VERSION, record the change and re-review status in
    docs/safety/triage-red-flag-ruleset.md, and paste the new fingerprint there.
    """
    doc = _SAFETY_CASE.read_text()
    assert f"Rule set version: `{RULESET_VERSION}`" in doc
    assert f"Fingerprint: `{ruleset_fingerprint()}`" in doc
    for rule in RULES:
        assert f"`{rule.rule_id}`" in doc, f"{rule.rule_id} missing from the safety-case note"
