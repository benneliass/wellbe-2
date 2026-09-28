# Triage red-flag rule set: clinical-safety case note (C10)

> **Status: STARTER RULE SET, PENDING CLINICAL REVIEW.** The rules, qualifiers,
> same-day tier and guidance copy below were written by engineering from the
> sources cited in the approved decision. No clinician has signed them off yet.
> Do not describe this feature as clinically validated until the sign-off below
> is filled in.

- Rule set version: `2026.09-starter.1`
- Fingerprint: `5760881c90d92f9c78e6430c6aa6d8b07874d2c2a050b1db91486297f8f0eec2`
- Clinical review status: `pending_clinical_review`
- Sign-off owner (Clinical Safety Officer role): _unassigned_
- Sign-off date: _none_

**Governing decision:** [docs/decisions/triage-escalation-safety-rules.md](../decisions/triage-escalation-safety-rules.md)
(WEL-162, approved 2026-06-17): options 1a + 2c + 3b + 4b.
Also bound by [do_not_diagnose_rules.md](do_not_diagnose_rules.md),
[safety_model.md](safety_model.md), and
[health-adaptive-safety-language.md](../implementation/ui/health-adaptive-safety-language.md)
(red is reserved for C10 `route_urgent` only).

**Code:** `backend/packages/c10_safety/src/wellbe_c10_safety/triage/`
(`rules.py`, `negation.py`, `copy.py`, `sources.py`, `evaluator.py`).
**Endpoint:** `POST /v2/triage/evaluate` (`backend/apps/api/src/wellbe_api/routers/triage_v2.py`).
**Regression corpus:** `backend/packages/c10_safety/tests/test_triage_redflags.py` and the
Safety Gate CI harness `evals/safety/tests/test_triage_corpus.py`.

## Change control

Any change to a rule, a pattern, a qualifier, a template or the pregnancy mention
list changes the fingerprint. `test_ruleset_change_requires_safety_case_update`
then fails until you:

1. bump `RULESET_VERSION` in `rules.py`,
2. add a row to the change log below saying what changed and why,
3. set the review status back to `pending_clinical_review` if it was reviewed,
4. paste the new version and fingerprint at the top of this note.

This is the "wire a check so prompt/template/rule-set changes flag the safety
case for re-review" step from the decision's implementation notes.

## What the decision fixes vs. what this starter set adds

| Decision requirement | Where it is implemented |
|---|---|
| Triage without diagnosis: return "what to do next", never a condition, probability or treatment | Templates only; `copy_violations` blocks diagnosis, condition names, medication directives |
| Deterministic, source-linked routing, not the LLM | `rules.py` (regex + negation); every rule carries public `source_ids` |
| Four tiers + parallel crisis path | `route_urgent` (emergency now), `route_soon` (same-day clinician), `route_routine` (routine care / self-care with the watchful-waiting backstop); `crisis_support` flag + `crisis_support.v1` copy |
| Emergency-now categories: stroke (FAST), breathing difficulty, chest pain/pressure, confusion/unarousable, seizure, uncontrolled bleeding, anaphylaxis, overdose/poisoning, loss of consciousness, danger to self/others | `U-*` rules below, one or more per category |
| Pregnancy/postpartum as a first-class branch from launch | `P-*` rules (CDC HEAR HER), gated on `context.pregnant_or_postpartum` or a pregnancy mention in the answers |
| Template-first copy + deterministic banned-phrase filter | `copy.py` `TEMPLATES` + `BANNED_COPY_PATTERNS`; rendering fails closed on a violation |
| Locale-config emergency numbers, generalized default | `EMERGENCY_NUMBERS` / `CRISIS_LINES`; default "your local emergency number" |
| Conservative by default | Negation never crosses a comma/clause; pseudo-negations ignored; "never ... before/like this" counts as present; English sign phrases match without requiring severity words except where noted |

**Added by engineering (needs clinical review):** the concrete phrases, the
same-day (`S-*`) tier, the qualifiers on `U-BREATH-02` / `U-STROKE-BALANCE-01`,
the adult use of child-sourced rules (`U-FEVER-NECK-01`, `U-RASH-01`), all
guidance wording, and the negation behaviour.

## Rules

| Rule | Route | Warning sign (shown to the user) | Conditions | Sources |
|---|---|---|---|---|
| `U-CHEST-01` | route_urgent | Chest pain, pressure or tightness | — | aha-warning-signs, medlineplus-emergencies, cdc-flu-warning-signs |
| `U-BREATH-01` | route_urgent | Serious difficulty breathing | — | medlineplus-emergencies, mayo-shortness-of-breath, cdc-flu-warning-signs |
| `U-BREATH-02` | route_urgent | Sudden or severe shortness of breath | needs a qualifier in the same clause (or onset = Today) | mayo-shortness-of-breath |
| `U-STROKE-FACE-01` | route_urgent | Face drooping or numb on one side | — | cdc-stroke-signs, aha-warning-signs |
| `U-STROKE-ARM-01` | route_urgent | Sudden weakness or numbness in an arm or leg, especially on one side | — | cdc-stroke-signs, aha-warning-signs, medlineplus-emergencies |
| `U-STROKE-SPEECH-01` | route_urgent | Sudden trouble speaking or understanding speech | — | cdc-stroke-signs, aha-warning-signs |
| `U-STROKE-VISION-01` | route_urgent | Sudden loss of vision or trouble seeing | — | cdc-stroke-signs, medlineplus-emergencies |
| `U-STROKE-BALANCE-01` | route_urgent | Sudden dizziness, loss of balance or trouble walking | needs a qualifier in the same clause ("sudden", "out of nowhere", "collapsed") | cdc-stroke-signs |
| `U-HEAD-01` | route_urgent | Sudden, severe headache | — | cdc-stroke-signs |
| `U-CONSC-01` | route_urgent | Fainting, passing out or being hard to wake | — | medlineplus-emergencies, cdc-flu-warning-signs |
| `U-CONFUSION-01` | route_urgent | New confusion or disorientation | — | medlineplus-emergencies, cdc-flu-warning-signs |
| `U-SEIZURE-01` | route_urgent | A seizure or fit | — | medlineplus-emergencies, cdc-flu-warning-signs |
| `U-BLEED-01` | route_urgent | Heavy bleeding, or bleeding that won't stop | — | medlineplus-emergencies, nhs-when-to-call-999 |
| `U-ALLERGY-01` | route_urgent | Signs of a severe allergic reaction | — | mayo-anaphylaxis, nhs-when-to-call-999 |
| `U-OVERDOSE-01` | route_urgent | Possible overdose or poisoning | — | medlineplus-emergencies, samhsa-in-crisis |
| `U-ABDO-01` | route_urgent | Severe or persistent belly pain | — | medlineplus-emergencies, cdc-flu-warning-signs |
| `U-PAIN-01` | route_urgent | Sudden, severe pain | — | medlineplus-emergencies |
| `U-FEVER-NECK-01` | route_urgent | Fever with a stiff neck | needs a fever mention anywhere | nice-ng143-traffic-light, nhs-serious-illness-children |
| `U-RASH-01` | route_urgent | A rash that doesn't fade when pressed | — | nhs-serious-illness-children, nice-ng143-traffic-light |
| `U-DESCRIBED-01` | route_urgent | You described what may be an emergency happening now | — | nhs-when-to-call-999, cdc-stroke-signs, aha-warning-signs |
| `U-HARM-SELF-01` | route_urgent | Thoughts of suicide or harming yourself | crisis path | nimh-suicide-warning-signs, samhsa-in-crisis |
| `U-HARM-OTHERS-01` | route_urgent | Thoughts of harming someone else | crisis path | medlineplus-emergencies, samhsa-in-crisis |
| `P-HEADACHE-01` | route_urgent | Headache during pregnancy or after giving birth | pregnant / postpartum only | cdc-hear-her |
| `P-DIZZY-01` | route_urgent | Dizziness or fainting during pregnancy or after giving birth | pregnant / postpartum only | cdc-hear-her |
| `P-VISION-01` | route_urgent | Changes in vision during pregnancy or after giving birth | pregnant / postpartum only | cdc-hear-her |
| `P-FEVER-01` | route_urgent | Fever during pregnancy or after giving birth | pregnant / postpartum only | cdc-hear-her |
| `P-SWELLING-01` | route_urgent | Swelling of the hands or face during pregnancy or after giving birth | pregnant / postpartum only | cdc-hear-her |
| `P-HEART-01` | route_urgent | A racing or pounding heartbeat during pregnancy or after giving birth | pregnant / postpartum only | cdc-hear-her |
| `P-VOMIT-01` | route_urgent | Severe nausea or vomiting during pregnancy or after giving birth | pregnant / postpartum only | cdc-hear-her |
| `P-BELLY-01` | route_urgent | Belly pain during pregnancy or after giving birth | pregnant / postpartum only | cdc-hear-her |
| `P-MOVEMENT-01` | route_urgent | The baby moving less, or not moving | pregnant / postpartum only | cdc-hear-her |
| `P-BLEED-01` | route_urgent | Bleeding or leaking fluid during pregnancy, or heavy bleeding after birth | pregnant / postpartum only | cdc-hear-her |
| `P-LEG-01` | route_urgent | Swelling, redness or pain in a leg or arm during pregnancy or after birth | pregnant / postpartum only | cdc-hear-her |
| `P-TIRED-01` | route_urgent | Overwhelming tiredness during pregnancy or after giving birth | pregnant / postpartum only | cdc-hear-her |
| `P-HARM-BABY-01` | route_urgent | Thoughts of harming yourself or your baby | pregnant / postpartum only; crisis path | cdc-hear-her, nimh-suicide-warning-signs |
| `S-BREATH-01` | route_soon | Shortness of breath | — | mayo-shortness-of-breath |
| `S-HEAD-01` | route_soon | A severe headache | — | cdc-stroke-signs, medlineplus-emergencies |
| `S-VISION-01` | route_soon | Blurred or double vision | — | cdc-stroke-signs |
| `S-FAINT-01` | route_soon | Feeling like you might faint | — | medlineplus-emergencies |
| `S-FEVER-01` | route_soon | A very high fever, or a fever that keeps coming back | — | cdc-flu-warning-signs |
| `S-FLUIDS-01` | route_soon | Not peeing, or not able to keep fluids down | — | cdc-flu-warning-signs |
| `S-PAIN-01` | route_soon | Severe pain | — | medlineplus-emergencies |
| `S-BLOOD-01` | route_soon | Blood in pee or poo, or black poo | — | medlineplus-emergencies |
| `S-WORSE-01` | route_soon | Getting worse quickly | — | cdc-flu-warning-signs |
| `S-CONCERN-01` | route_soon | You're worried it could be an emergency | — | nhs-when-to-call-999 |
| `S-FUNCTION-01` | route_soon | It started recently and you can't do your usual things | structured: onset Today / last few days + impact "I can't do my usual things" | medlineplus-emergencies |

Route = most urgent matched rule. Template priority: crisis > general emergency >
pregnancy emergency > same-day > routine.

## Guidance copy (template ids)

`emergency_now.v1`, `crisis_support.v1`, `pregnancy_urgent.v1`, `same_day.v1`,
`routine.v1`. The only slots are the emergency number and crisis line. Every
rendered string, for every configured region, is tested against the banned-phrase
classes: diagnosis assertion, diagnostic conclusion, probabilistic diagnosis,
condition names, medication directives, unsupported reassurance, false closure,
catastrophic and panic/pressure phrasing (including `!`).

Locale numbers are limited to those named in the decision's sources: 911 (US, CA),
999 (GB), 000 (AU), 112 (EU member states), and the 988 crisis line (US). Every
other region, and requests without a region, get "your local emergency number" and
"a local crisis line". The web client does not send a region (browser language is
not a location); a deployment can set `WELLBE_TRIAGE_DEFAULT_REGION`.

## Hazard log (this component)

| Hazard | Cause | Mitigation in this build | Residual risk / open item |
|---|---|---|---|
| H-TRI-01 Under-triage of an emergency | Sign phrased in words the rules don't know; non-English text; sign mentioned only in a skipped answer | Broad phrase lists; negation deliberately narrow; routine route always carries the "not complete / if severe call" backstop; the web backstop is always visible | English-only; paraphrase coverage untested against clinical vignettes. **Needs clinical vignette testing** |
| H-TRI-02 Wrongly negated sign | NegEx-style scope errors | Negation limited to the same clause, 6-word window; pseudo-negations ignored; "until/before/like this" cancels; regression corpus | Complex sentences ("I wouldn't say it's not chest pain") may still mis-negate |
| H-TRI-03 Over-triage / alarm | Conservative matching (e.g. any chest pain, historical mentions such as "had a seizure as a child") | Calm template copy; red only for `route_urgent`; the user can still save their check-in | Accepted trade-off per the decision; monitor rate once real usage exists |
| H-TRI-04 Diagnostic or alarming wording | Copy drift | Template-only copy + banned-phrase filter at render time (fails closed) + tests for every template × region | Filter is lexical; paraphrased diagnosis in future templates needs review |
| H-TRI-05 Wrong emergency number | Region guessed wrongly | No guessing: explicit region only, generic default | Israel and most non-listed regions get generic wording |
| H-TRI-06 Evaluation unavailable | API/network failure | Web falls back to `needs_attention` tone with the generic backstop and still saves; never shows urgent styling without a C10 `route_urgent` | — |
| H-TRI-07 Crisis path mishandled | Keyword-only detection; negated mention ("not suicidal but hopeless") not routed | Crisis copy gives both emergency and crisis-line routes | Decision leaves open whether self-harm screening is asked in every check-in (follow-up) |

## Known gaps (for the clinical reviewer)

- No explicit pregnancy / postpartum question in the web check-in yet; the branch
  triggers from the answers text or an API `context` flag.
- No pediatric, older-adult, immunocompromised or chronic-condition branches
  (the decision allows these to phase in).
- `U-FEVER-NECK-01` and `U-RASH-01` are sourced from child-focused guidance and
  applied to all ages.
- The same-day tier (`S-*`) has no dedicated source-backed threshold set; it
  maps CDC "seek care" signs and severity words to same-day contact.
- No LLM gate, tone classifier or render token for this output yet: the decision
  orders deterministic rules first, then the LLM gate; only the deterministic
  layer exists.

## Change log

| Version | Change | Review |
|---|---|---|
| `2026.09-starter.1` | Initial starter rule set, templates and locale table | pending clinical review |
