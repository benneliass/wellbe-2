"""Versioned, source-linked red-flag rule set for the triage check-in.

STARTER RULE SET — PENDING CLINICAL REVIEW. The approved decision
(docs/decisions/triage-escalation-safety-rules.md) fixes the tiers, the
emergency-now sign categories and the pregnancy/postpartum branch, but no
clinician has signed off the concrete phrases, qualifiers or the same-day tier
below. Any change here must bump ``RULESET_VERSION`` and update the safety-case
note in docs/safety/triage-red-flag-ruleset.md (a test pins the fingerprint).

Rules match symptom/sign phrases, never condition names as outputs. Matching is
English-only, deterministic, and conservative: when in doubt a rule matches.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from wellbe_contracts.triage import TriageRoute

RULESET_VERSION = "2026.09-starter.1"
CLINICAL_REVIEW_STATUS: Literal["pending_clinical_review"] = "pending_clinical_review"

Population = Literal["general", "pregnancy"]

ONSET_TODAY = "Today"
ONSET_RECENT = frozenset({"Today", "In the last few days"})
IMPACT_CANNOT = frozenset({"I can't do my usual things"})


def _p(*alternatives: str) -> re.Pattern[str]:
    return re.compile(r"\b(?:" + "|".join(alternatives) + r")\b", re.I)


_CANT = (
    r"(?:can't|cant|cannot|can not|couldn't|could not|unable to|not able to|"
    r"(?:haven't|have not|hasn't|has not) been able to)"
)
_SEVERE = (
    r"(?:severe|severely|extreme|extremely|excruciating|unbearable|agoni[sz]ing|intense|"
    r"terrible|awful|worst)"
)
_SUDDEN = r"(?:sudden|suddenly|all of a sudden|out of nowhere|abrupt|abruptly)"

# Signs reused by several rules.
_SHORT_OF_BREATH = _p(
    r"short(?:ness)? of breath",
    r"breathless(?:ness)?",
    r"out of breath",
    r"winded",
)
_HEADACHE = _p(r"headaches?", r"migraines?", r"head (?:hurts|is pounding|pain)")
_FEVER = _p(
    r"fever(?:s|ish)?",
    r"high temperature",
    r"temperature (?:of|is|was|has been)",
    r"running a temperature",
)
PREGNANCY_MENTION = _p(
    r"pregnan\w*",
    r"post-?partum",
    r"gave birth",
    r"given birth",
    r"had (?:a|my|the) baby",
    r"expecting a baby",
    r"since (?:the )?birth",
    r"after (?:the )?(?:delivery|birth)",
    r"c-?section",
    r"ca?esarean",
    r"breastfeeding",
    r"(?:weeks|months) pregnant",
)


@dataclass(frozen=True)
class RedFlagRule:
    rule_id: str
    route: TriageRoute
    # Plain description of the warning sign — never a condition name.
    label: str
    source_ids: tuple[str, ...]
    # Any affirmed (non-negated) match triggers, subject to the conditions below.
    patterns: tuple[re.Pattern[str], ...] = ()
    # When set, a qualifier must also be affirmed in the same clause as the sign,
    # unless the structured onset answer is in ``qualifier_onset``.
    qualifiers: tuple[re.Pattern[str], ...] = ()
    qualifier_onset: frozenset[str] = frozenset()
    # When set, one of these must also be affirmed somewhere in the answers.
    also_requires: tuple[re.Pattern[str], ...] = ()
    # Structured-answer rule (no text patterns): both sets must contain the answer.
    onset_in: frozenset[str] = frozenset()
    impact_in: frozenset[str] = frozenset()
    population: Population = "general"
    # Parallel mental-health crisis path.
    crisis: bool = False


_URGENT = TriageRoute.URGENT
_SOON = TriageRoute.SOON

RULES: tuple[RedFlagRule, ...] = (
    # ---------------------------------------------------------------- emergency now
    RedFlagRule(
        rule_id="U-CHEST-01",
        route=_URGENT,
        label="Chest pain, pressure or tightness",
        source_ids=("aha-warning-signs", "medlineplus-emergencies", "cdc-flu-warning-signs"),
        patterns=(
            _p(
                r"chest (?:pain|pains|pressure|tightness|discomfort|heaviness|ache|aching|"
                r"squeezing|hurt|hurts|hurting|is hurting|is sore)",
                r"(?:pain|pressure|tightness|discomfort|heaviness|squeezing|ache) "
                r"(?:in|on|across|around|behind) (?:my |the |his |her )?chest",
                r"chest (?:feels|is|was|felt|has been) (?:tight|heavy|painful|sore|crushed|"
                r"squeezed)",
                r"(?:tight|heavy|painful|crushing|sore) chest",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="U-BREATH-01",
        route=_URGENT,
        label="Serious difficulty breathing",
        source_ids=("medlineplus-emergencies", "mayo-shortness-of-breath", "cdc-flu-warning-signs"),
        patterns=(
            _p(
                _CANT + r" (?:breathe|catch (?:my|his|her|their) breath|get (?:enough )?air)",
                r"(?:struggling|struggle|fighting) (?:to breathe|for breath|for air)",
                r"(?:trouble|difficulty|difficult|problems?|hard time|hard) "
                r"(?:with )?(?:breathing|to breathe|catching (?:my|his|her) breath)",
                r"gasping",
                r"choking",
                r"(?:lips|face|fingertips|nails) (?:are |is |look |looks |turning |turned |went )?"
                r"(?:blue|grey|gray)",
                r"turning blue",
                r"(?:not|isn't|is not|stopped|has stopped|stops) breathing",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="U-BREATH-02",
        route=_URGENT,
        label="Sudden or severe shortness of breath",
        source_ids=("mayo-shortness-of-breath",),
        patterns=(_SHORT_OF_BREATH,),
        qualifiers=(
            _p(
                _SUDDEN,
                _SEVERE,
                r"very",
                r"really bad",
                r"at rest",
                r"resting",
                r"lying (?:down|still|flat)",
                r"sitting still",
                r"when talking",
            ),
        ),
        qualifier_onset=frozenset({ONSET_TODAY}),
    ),
    RedFlagRule(
        rule_id="U-STROKE-FACE-01",
        route=_URGENT,
        label="Face drooping or numb on one side",
        source_ids=("cdc-stroke-signs", "aha-warning-signs"),
        patterns=(
            _p(
                r"face (?:is |looks |feels |has |started |went )?(?:drooping|droopy|drooped|"
                r"numb|lopsided|uneven|weak|fallen)",
                r"(?:drooping|droopy|drooped|numb|lopsided|uneven) (?:face|mouth|smile|lip|eyelid)",
                r"(?:mouth|smile|lip) (?:is |looks )?(?:drooping|droopy|drooped|lopsided|crooked|"
                r"uneven)",
                r"one side of (?:my |his |her |their |the )?face",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="U-STROKE-ARM-01",
        route=_URGENT,
        label="Sudden weakness or numbness in an arm or leg, especially on one side",
        source_ids=("cdc-stroke-signs", "aha-warning-signs", "medlineplus-emergencies"),
        patterns=(
            _p(
                r"(?:weakness|numbness|paralysis|no feeling) (?:in|of|on|down) (?:my |one |the |"
                r"his |her |their )?(?:left |right )?(?:arm|leg|hand|foot|side)",
                r"(?:arm|leg|hand|foot|side) (?:suddenly )?(?:went|is|feels|felt|has gone|"
                r"has become|became|going) (?:very )?(?:weak|numb|dead|limp|paralysed|paralyzed)",
                _CANT + r" (?:lift|raise|move|feel|use) (?:my |his |her |their |the )?"
                r"(?:left |right )?(?:arm|leg|hand|foot)",
                r"(?:weak|numb) on one side",
                r"one side of (?:my |his |her |their |the )?body",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="U-STROKE-SPEECH-01",
        route=_URGENT,
        label="Sudden trouble speaking or understanding speech",
        source_ids=("cdc-stroke-signs", "aha-warning-signs"),
        patterns=(
            _p(
                r"slurred",
                r"slurring",
                r"(?:speech|words) (?:is |are |was |were |sound |sounds )?(?:slurred|jumbled|"
                r"garbled|muddled|coming out wrong|not making sense)",
                r"(?:can't|cannot|unable to|trouble|difficulty|struggling to|not able to) "
                r"(?:speak|talk|speaking|talking)(?! (?:to|with|about))",
                r"(?:can't|cannot|unable to|trouble|difficulty|struggling to) "
                r"(?:get (?:my |the |his |her )?words out|find (?:my |the )?words)",
                r"(?:can't|cannot|unable to|trouble|difficulty) understand(?:ing)? "
                r"(?:what )?(?:people|anyone|others|what people)",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="U-STROKE-VISION-01",
        route=_URGENT,
        label="Sudden loss of vision or trouble seeing",
        source_ids=("cdc-stroke-signs", "medlineplus-emergencies"),
        patterns=(
            _p(
                r"(?:lost|losing|loss of) (?:my |the |his |her )?(?:vision|sight|eyesight)",
                r"(?:went|gone|going) blind",
                _CANT + r" see (?:out of|in|with|from) (?:one|my (?:left|right)|the (?:left|right))"
                r" eye",
                _SUDDEN + r" (?:blurred|blurry|double|loss of|lost|dim|dark) (?:vision|sight)",
                r"(?:vision|sight) (?:suddenly )?(?:went|goes|going) (?:black|dark|blurry)",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="U-STROKE-BALANCE-01",
        route=_URGENT,
        label="Sudden dizziness, loss of balance or trouble walking",
        source_ids=("cdc-stroke-signs",),
        patterns=(
            _p(
                r"dizz\w*",
                r"vertigo",
                r"(?:lost|losing|loss of) (?:my )?(?:balance|coordination)",
                r"off balance",
                r"unsteady",
                _CANT + r" (?:walk|stand)",
                r"(?:trouble|difficulty) (?:walking|standing)",
                r"falling over",
            ),
        ),
        qualifiers=(_p(_SUDDEN, r"collapsed"),),
    ),
    RedFlagRule(
        rule_id="U-HEAD-01",
        route=_URGENT,
        label="Sudden, severe headache",
        source_ids=("cdc-stroke-signs",),
        patterns=(
            _p(
                r"worst headache",
                r"thunderclap",
                r"(?:sudden|suddenly|explosive|blinding) (?:[\w']+ )?headache",
                r"headache (?:that )?(?:came on|started|hit|began) (?:very )?(?:suddenly|all of a "
                r"sudden|out of nowhere|like a thunderclap)",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="U-CONSC-01",
        route=_URGENT,
        label="Fainting, passing out or being hard to wake",
        source_ids=("medlineplus-emergencies", "cdc-flu-warning-signs"),
        patterns=(
            _p(
                r"passed out",
                r"passing out",
                r"fainted",
                r"fainting",
                r"blacked out",
                r"blacking out",
                r"lost consciousness",
                r"loss of consciousness",
                r"unconscious",
                r"unresponsive",
                r"collapsed",
                r"(?:can't|cannot|couldn't|hard to|won't|will not) (?:wake|be woken|rouse)"
                r"(?: (?:him|her|them|up))?",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="U-CONFUSION-01",
        route=_URGENT,
        label="New confusion or disorientation",
        source_ids=("medlineplus-emergencies", "cdc-flu-warning-signs"),
        patterns=(
            _p(
                r"(?:confused|confusion|disoriented|disorientated|delirious)"
                r"(?! (?:about|by|why|whether|if|what|how|as to|over|with|when|which))",
                r"(?:doesn't|does not|don't|didn't) know where (?:i|he|she|they) (?:am|is|are|was)",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="U-SEIZURE-01",
        route=_URGENT,
        label="A seizure or fit",
        source_ids=("medlineplus-emergencies", "cdc-flu-warning-signs"),
        patterns=(_p(r"seizures?", r"seizing", r"convuls\w*", r"(?:having|had|has) a fit", r"fitting"),),
    ),
    RedFlagRule(
        rule_id="U-BLEED-01",
        route=_URGENT,
        label="Heavy bleeding, or bleeding that won't stop",
        source_ids=("medlineplus-emergencies", "nhs-when-to-call-999"),
        patterns=(
            _p(
                r"(?:heavy|heavily|severe|uncontrolled|uncontrollable|lots of|a lot of|profuse|"
                r"gushing|pouring|massive) bleed(?:ing)?",
                r"bleeding (?:very )?(?:heavily|a lot|profusely|badly)",
                r"(?:won't|will not|doesn't|does not|can't|cannot|couldn't|could not) stop "
                r"(?:the )?bleeding",
                r"bleeding (?:that |which )?(?:won't|will not|doesn't|does not|hasn't|has not|"
                r"isn't|is not|can't|cannot) stop",
                r"(?:coughing|vomiting|throwing|spitting) up blood",
                r"vomiting blood",
                r"(?:soaking|soaked) through",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="U-ALLERGY-01",
        route=_URGENT,
        label="Signs of a severe allergic reaction",
        source_ids=("mayo-anaphylaxis", "nhs-when-to-call-999"),
        patterns=(
            _p(
                r"anaphyla\w*",
                r"severe allergic reaction",
                r"(?:throat|tongue|lips?|mouth) (?:is |are |feels |felt |started |starting |"
                r"has |have )?(?:swelling|swollen|closing|closing up|tight|puffing up)",
                r"swelling (?:of|in) (?:my |the |his |her )?(?:throat|tongue|lips|mouth)",
                r"(?:swollen|swelling) (?:throat|tongue|lips)",
                r"used (?:my |an |the |his |her )?epi-?pen",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="U-OVERDOSE-01",
        route=_URGENT,
        label="Possible overdose or poisoning",
        source_ids=("medlineplus-emergencies", "samhsa-in-crisis"),
        patterns=(
            _p(
                r"overdos\w*",
                r"took too many (?:pills|tablets|of (?:my|the|his|her))",
                r"(?:swallowed|drank|ingested|ate) (?:some )?(?:bleach|poison|chemicals?|"
                r"antifreeze|cleaning (?:fluid|product)|batteries|a battery)",
                r"(?<!food )poison(?:ed|ing)",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="U-ABDO-01",
        route=_URGENT,
        label="Severe or persistent belly pain",
        source_ids=("medlineplus-emergencies", "cdc-flu-warning-signs"),
        patterns=(
            _p(
                _SEVERE + r" (?:abdominal|belly|stomach|tummy|abdomen) (?:pain|ache|cramps?)",
                r"(?:persistent|constant) (?:abdominal|belly|stomach|tummy) (?:pain|ache)",
                r"(?:abdominal|belly|stomach|tummy) (?:pain|ache) (?:is |that is |that's )?"
                r"(?:severe|unbearable|excruciating|constant|persistent|agoni[sz]ing)",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="U-PAIN-01",
        route=_URGENT,
        label="Sudden, severe pain",
        source_ids=("medlineplus-emergencies",),
        patterns=(
            _p(
                _SUDDEN + r" (?:and )?(?:severe|extreme|excruciating|intense|sharp|unbearable) "
                r"(?:pain|ache)",
                r"(?:severe|extreme|excruciating|intense|unbearable) (?:pain|ache) (?:that )?"
                r"(?:came on|started|began) (?:very )?(?:suddenly|all of a sudden|out of nowhere)",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="U-FEVER-NECK-01",
        route=_URGENT,
        label="Fever with a stiff neck",
        source_ids=("nice-ng143-traffic-light", "nhs-serious-illness-children"),
        patterns=(_p(r"stiff neck", r"neck (?:is |feels |felt |was )?(?:very )?stiff"),),
        also_requires=(_FEVER,),
    ),
    RedFlagRule(
        rule_id="U-RASH-01",
        route=_URGENT,
        label="A rash that doesn't fade when pressed",
        source_ids=("nhs-serious-illness-children", "nice-ng143-traffic-light"),
        patterns=(
            _p(
                r"rash (?:that |which )?(?:doesn't|does not|won't|will not|didn't|did not) fade",
                r"non-?blanching",
                r"glass test",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="U-DESCRIBED-01",
        route=_URGENT,
        label="You described what may be an emergency happening now",
        source_ids=("nhs-when-to-call-999", "cdc-stroke-signs", "aha-warning-signs"),
        patterns=(
            _p(
                r"(?:having|just had) a (?:stroke|heart attack|seizure)",
                r"(?:think|believe) (?:it's|it is|this is) a (?:stroke|heart attack)",
                r"(?:need|call|calling|called) (?:an |for an )?ambulance",
                r"(?:this|it) (?:is|feels like) an emergency",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="U-HARM-SELF-01",
        route=_URGENT,
        label="Thoughts of suicide or harming yourself",
        source_ids=("nimh-suicide-warning-signs", "samhsa-in-crisis"),
        crisis=True,
        patterns=(
            _p(
                r"suicid\w*",
                r"kill(?:ing)? myself",
                r"end(?:ing)? (?:my life|it all|my own life)",
                r"take my (?:own )?life",
                r"want(?:ed|ing)? to die",
                r"wish(?:ed)? i (?:was|were) dead",
                r"better off dead",
                r"(?:hurt|harm|cut|burn)(?:ing)? myself",
                r"self[- ]?harm\w*",
                r"no reason to (?:live|go on|keep going)",
                r"(?:don't|do not) want to (?:live|be alive|be here|wake up)(?: anymore)?",
                r"(?:can't|cannot) go on",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="U-HARM-OTHERS-01",
        route=_URGENT,
        label="Thoughts of harming someone else",
        source_ids=("medlineplus-emergencies", "samhsa-in-crisis"),
        crisis=True,
        patterns=(
            _p(
                r"(?:want|wanted|wanting|going|urge|urges|thoughts?|thinking|afraid|scared|"
                r"might|could) (?:to |of |about |that )?(?:i'll |i will |i might |i could )?"
                r"(?:hurt|harm|kill)(?:ing)? (?:someone|somebody|others|other people|people|him|"
                r"her|them|my (?:partner|wife|husband|child|children|kids?|son|daughter|baby|"
                r"mum|mom|dad|mother|father))",
            ),
        ),
    ),
    # ------------------------------------------------ pregnancy and 1 year postpartum
    # CDC HEAR HER: "seek medical care immediately" for these signs.
    RedFlagRule(
        rule_id="P-HEADACHE-01",
        route=_URGENT,
        label="Headache during pregnancy or after giving birth",
        source_ids=("cdc-hear-her",),
        population="pregnancy",
        patterns=(_HEADACHE,),
    ),
    RedFlagRule(
        rule_id="P-DIZZY-01",
        route=_URGENT,
        label="Dizziness or fainting during pregnancy or after giving birth",
        source_ids=("cdc-hear-her",),
        population="pregnancy",
        patterns=(_p(r"dizz\w*", r"faint\w*", r"light-?headed", r"passed out"),),
    ),
    RedFlagRule(
        rule_id="P-VISION-01",
        route=_URGENT,
        label="Changes in vision during pregnancy or after giving birth",
        source_ids=("cdc-hear-her",),
        population="pregnancy",
        patterns=(
            _p(
                r"vision",
                r"eyesight",
                r"blurr(?:y|ed)",
                r"seeing (?:spots|stars|flashes|flashing lights|lights)",
                r"flashing lights",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="P-FEVER-01",
        route=_URGENT,
        label="Fever during pregnancy or after giving birth",
        source_ids=("cdc-hear-her",),
        population="pregnancy",
        patterns=(_FEVER,),
    ),
    RedFlagRule(
        rule_id="P-SWELLING-01",
        route=_URGENT,
        label="Swelling of the hands or face during pregnancy or after giving birth",
        source_ids=("cdc-hear-her",),
        population="pregnancy",
        patterns=(
            _p(
                r"(?:swollen|swelling|puffy|puffiness) (?:[\w']+ ){0,2}(?:hands?|face|fingers)",
                r"(?:hands?|face|fingers) (?:are |is |look |looks |feel |feels |have |has )?"
                r"(?:very |really )?(?:swollen|swelling|puffy)",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="P-HEART-01",
        route=_URGENT,
        label="A racing or pounding heartbeat during pregnancy or after giving birth",
        source_ids=("cdc-hear-her",),
        population="pregnancy",
        patterns=(
            _p(
                r"(?:racing|pounding|fast|rapid) (?:heart|heartbeat|heart beat|pulse)",
                r"heart (?:is |was |keeps )?(?:racing|pounding)",
                r"palpitations?",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="P-VOMIT-01",
        route=_URGENT,
        label="Severe nausea or vomiting during pregnancy or after giving birth",
        source_ids=("cdc-hear-her",),
        population="pregnancy",
        patterns=(
            _p(
                r"(?:severe|constant|non-?stop|nonstop) (?:nausea|vomiting|throwing up|sickness)",
                r"(?:can't|cannot|won't) stop (?:vomiting|throwing up|being sick)",
                r"(?:can't|cannot) keep (?:anything|any food|fluids|water) down",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="P-BELLY-01",
        route=_URGENT,
        label="Belly pain during pregnancy or after giving birth",
        source_ids=("cdc-hear-her",),
        population="pregnancy",
        patterns=(
            _p(
                r"(?:abdominal|belly|stomach|tummy|abdomen|pelvic) (?:pain|ache|cramps?|cramping)",
                r"(?:pain|cramps?|cramping) in (?:my |the )?(?:belly|stomach|tummy|abdomen|pelvis)",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="P-MOVEMENT-01",
        route=_URGENT,
        label="The baby moving less, or not moving",
        source_ids=("cdc-hear-her",),
        population="pregnancy",
        patterns=(
            _p(
                r"baby (?:is |has been |has )?(?:moving|kicking) (?:much |a lot )?less",
                r"(?:stopped|reduced|fewer|less|decreased|no) (?:fetal |foetal |baby )?"
                r"(?:movements?|kicks|kicking)",
                r"baby (?:hasn't|has not|isn't|is not|hasnt|isnt|stopped) (?:moved|moving|kicking|"
                r"kicked)",
                r"(?:can't|cannot) feel (?:the |my )?baby (?:move|moving|kick|kicking)",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="P-BLEED-01",
        route=_URGENT,
        label="Bleeding or leaking fluid during pregnancy, or heavy bleeding after birth",
        source_ids=("cdc-hear-her",),
        population="pregnancy",
        patterns=(
            _p(
                r"bleeding",
                r"spotting",
                r"(?:fluid|waters?) (?:is |are |has been )?(?:leaking|broke|broken|breaking)",
                r"leaking (?:fluid|water)",
                r"blood clots?",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="P-LEG-01",
        route=_URGENT,
        label="Swelling, redness or pain in a leg or arm during pregnancy or after birth",
        source_ids=("cdc-hear-her",),
        population="pregnancy",
        patterns=(
            _p(
                r"(?:leg|calf|thigh|arm) (?:is |feels |looks |has been )?(?:very )?(?:swollen|red|"
                r"painful|sore|hot|warm|tender)",
                r"(?:swollen|swelling|red|painful|sore|hot|tender) (?:[\w']+ )?(?:leg|calf|thigh|arm)",
                r"(?:pain|swelling|redness) in (?:my |one |the )?(?:leg|calf|thigh|arm)",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="P-TIRED-01",
        route=_URGENT,
        label="Overwhelming tiredness during pregnancy or after giving birth",
        source_ids=("cdc-hear-her",),
        population="pregnancy",
        patterns=(
            _p(
                r"(?:overwhelming|extreme|extremely|exhausting|crushing) (?:tiredness|fatigue|"
                r"exhaustion|tired)",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="P-HARM-BABY-01",
        route=_URGENT,
        label="Thoughts of harming yourself or your baby",
        source_ids=("cdc-hear-her", "nimh-suicide-warning-signs"),
        population="pregnancy",
        crisis=True,
        patterns=(_p(r"(?:hurt|harm|hurting|harming) (?:my |the )?baby"),),
    ),
    # ---------------------------------------------------------- same-day clinician
    RedFlagRule(
        rule_id="S-BREATH-01",
        route=_SOON,
        label="Shortness of breath",
        source_ids=("mayo-shortness-of-breath",),
        patterns=(_SHORT_OF_BREATH,),
    ),
    RedFlagRule(
        rule_id="S-HEAD-01",
        route=_SOON,
        label="A severe headache",
        source_ids=("cdc-stroke-signs", "medlineplus-emergencies"),
        patterns=(
            _p(
                _SEVERE + r" (?:[\w']+ )?(?:headache|migraine)",
                r"(?:headache|migraine) (?:is |that is |that's )?(?:severe|unbearable|"
                r"excruciating|the worst)",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="S-VISION-01",
        route=_SOON,
        label="Blurred or double vision",
        source_ids=("cdc-stroke-signs",),
        patterns=(
            _p(
                r"blurr(?:ed|y) vision",
                r"double vision",
                r"seeing double",
                r"vision (?:is |has been |has gone |keeps going )?(?:blurry|blurred|fuzzy)",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="S-FAINT-01",
        route=_SOON,
        label="Feeling like you might faint",
        source_ids=("medlineplus-emergencies",),
        patterns=(
            _p(
                r"(?:feel|feels|feeling|felt) (?:very |really )?faint",
                r"(?:going to|about to|might|nearly|almost) (?:pass out|faint|black out)",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="S-FEVER-01",
        route=_SOON,
        label="A very high fever, or a fever that keeps coming back",
        source_ids=("cdc-flu-warning-signs",),
        patterns=(
            _p(
                r"(?:very |really )?high (?:fever|temperature)",
                r"(?:fever|temperature) (?:[\w']+ ){0,4}(?:came back|coming back|returned|keeps "
                r"coming back|won't go|won't come down|not going down|isn't going down)",
                r"(?:fever|temperature)[^0-9]{0,12}(?:39\.[5-9]|4[0-2](?:\.\d)?|10[3-9](?:\.\d)?)",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="S-FLUIDS-01",
        route=_SOON,
        label="Not peeing, or not able to keep fluids down",
        source_ids=("cdc-flu-warning-signs",),
        patterns=(
            _p(
                r"(?:not|haven't|hasn't|have not|has not|havent|hasnt) (?:been )?(?:peeing|"
                r"urinating|passing urine|weeing|peed)",
                r"(?:no|haven't had a|hasn't had a) (?:pee|wee|urine)",
                _CANT + r" keep (?:any )?(?:fluids|water|anything|liquids|food|drinks) down",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="S-PAIN-01",
        route=_SOON,
        label="Severe pain",
        source_ids=("medlineplus-emergencies",),
        patterns=(
            _p(
                r"(?:severe|extreme|excruciating|unbearable|agoni[sz]ing|intense|terrible) "
                r"(?:[\w']+ )?(?:pain|ache|cramps?)",
                r"(?:pain|ache) (?:is |that is |that's )?(?:severe|unbearable|excruciating|"
                r"agoni[sz]ing)",
                r"worst pain",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="S-BLOOD-01",
        route=_SOON,
        label="Blood in pee or poo, or black poo",
        source_ids=("medlineplus-emergencies",),
        patterns=(
            _p(
                r"blood in (?:my |the |his |her )?(?:urine|pee|wee|stool|stools|poo|poop|"
                r"bowel movements?)",
                r"(?:bloody|black|tarry) (?:stool|stools|poo|poop|urine|pee)",
                r"(?:peeing|pooping|passing) blood",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="S-WORSE-01",
        route=_SOON,
        label="Getting worse quickly",
        source_ids=("cdc-flu-warning-signs",),
        patterns=(
            _p(
                r"(?:getting|got|gets|going|become|becoming) (?:much |a lot )?worse (?:very )?"
                r"(?:quickly|fast|rapidly|by the hour|every hour)",
                r"(?:rapidly|quickly) (?:getting )?worse",
                r"(?:getting|got) worse and worse",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="S-CONCERN-01",
        route=_SOON,
        label="You're worried it could be an emergency",
        source_ids=("nhs-when-to-call-999",),
        patterns=(
            _p(
                r"emergency",
                r"ambulance",
                r"a&e",
                r"(?:worried|scared|afraid|frightened|fear|wonder|wondering|could|might|think) "
                r"(?:[\w']+ ){0,4}(?:stroke|heart attack|blood clot|sepsis|meningitis)",
            ),
        ),
    ),
    RedFlagRule(
        rule_id="S-FUNCTION-01",
        route=_SOON,
        label="It started recently and you can't do your usual things",
        source_ids=("medlineplus-emergencies",),
        onset_in=ONSET_RECENT,
        impact_in=IMPACT_CANNOT,
    ),
)
