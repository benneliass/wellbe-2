# Decision: Triage check-in and safe-escalation rules behind C10

**Status:** Approved  
**Date opened:** 2026-06-17  
**Date approved:** 2026-06-17  
**Approved by:** User  
**Jira Spike:** WEL-162  
**Blocks:** WEL-47 [WB2-F019: Deterioration check-in and escalation guidance]

---

## Question

For the `triage` pill ("Something feels off"), what are the rules for a calm deterioration check-in and safe escalation behind the C10 gate?
1. **Do-not-diagnose boundaries** — what the check-in may and may not say.
2. **Never-alarm language constraints** — tone and phrasing rules for any escalation message.
3. **Escalation criteria** — what maps a check-in to an escalation tier (and the tiers themselves).
4. **Response routing** — self-care guidance vs. "seek care" vs. emergency, all non-diagnostic and source-aware.

## Context

Touches C10 (Safety & Governance Gate) — the single hardest architectural rule (`docs/architecture/component-map.md`, `docs/safety/safety_model.md`, `docs/safety/do_not_diagnose_rules.md`). A wrong escalation or never-alarm rule is a direct safety risk to the user. This is the most consequential spike in the build-out.

## Research provided

> Agent-run LLM research (model: gpt-5.5, date: 2026-06-17, run id: resp_099c63a6331bef4a006a32ff975f248191bbc9643e0dfadbf6, web_search: on). Recorded verbatim per research-protocol.mdc Section I. Not synthesised by the agent.

## 1. External patterns to examine

### A. Non-diagnostic digital triage pattern
- **NHS 111 online** describes itself as a digital triage service that asks a series of questions about a **main symptom**, says “you will not get a diagnosis,” and routes the user to what help they need. It also states it can triage **one symptom at a time** and cannot advise on conditions the user already knows they have. This is directly relevant to do-not-diagnose boundaries, check-in question scope, and response routing. ([nhs.uk](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/how-nhs-111-online-works/))
- **FDA clinical decision support / medical device boundary** uses intended use as a key regulatory concept: software intended for diagnosis, cure, mitigation, treatment, or prevention may meet the medical-device definition; FDA’s CDS guidance distinguishes non-device CDS from device software and notes policies still apply to patient/caregiver-facing functions that meet the device definition. This is relevant to boundaries around “what may be said” and whether the tool is framed as wellness support, triage, or medical decision support. ([fda.gov](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software))

### B. Safety-governance pattern for health software
- **NHS clinical safety standards DCB0129/DCB0160** frame clinical safety as identifying hazards and mitigations, with DCB0129 applying to builders of healthcare software and DCB0160 to deploying care organizations. NHS developer guidance states that software builders should nominate a Clinical Safety Officer and maintain clinical risk-management artifacts. ([digital.nhs.uk](https://digital.nhs.uk/developer/guides-and-documentation/introduction-to-healthcare-technology/clinical-safety))
- NHS provides clinical safety templates including a **clinical safety case report**, **clinical risk management plan**, and **clinical safety hazard log**; these are relevant to C10 as a pre-output gate and to documenting under-escalation, over-escalation, provenance, and language hazards. ([digital.nhs.uk](https://digital.nhs.uk/services/clinical-safety/documentation))

### C. Escalation / disposition taxonomy pattern
- Public-facing urgent-care systems commonly separate:
  - **emergency / life-threatening** routing,
  - **urgent clinical callback or contact a healthcare service**,
  - **primary care / GP-type routing**,
  - **self-care or information-only routing**.
- NHS 111 online describes multiple outcome types, including nurse callback with a timeframe, contacting GP surgery, dentist/optician routing, and other service routing. ([nhs.uk](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/how-nhs-111-online-works/))
- NHS emergency guidance separates 999 for life-threatening emergencies from NHS 111 when the user is unsure whether emergency help is needed. ([nhs.uk](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-call-999/))
- U.S. crisis routing distinguishes 911/emergency room for danger or medical emergency from 988 for mental health, suicide, substance-use, or emotional crisis support. ([samhsa.gov](https://www.samhsa.gov/find-support/in-crisis))

### D. Red-flag / deterioration trigger pattern
- Sources use **specific symptom clusters** rather than diagnostic labels for urgent routing: trouble breathing, persistent chest pain/pressure, confusion, inability to arouse, seizures, not urinating, sudden severe weakness, stroke signs, severe allergic reaction, uncontrolled bleeding, overdose, loss of consciousness, and thoughts of harming self or others. ([cdc.gov](https://www.cdc.gov/flu/signs-symptoms/index.html))
- Condition-specific sources add specialized red flags, for example pregnancy/postpartum warning signs such as severe headache, vision changes, fever, extreme swelling, thoughts of harming self or baby, trouble breathing, chest pain, severe belly pain, heavy bleeding, reduced fetal movement, and severe limb swelling/pain. ([cdc.gov](https://www.cdc.gov/hearher/maternal-warning-signs/index.html))

### E. Never-alarm / crisis-safe communication pattern
- CDC’s Crisis and Emergency Risk Communication framework emphasizes being first, right, credible, empathetic, action-oriented, and respectful. It also states that meaningful action steps can calm anxiety and help restore a sense of control. ([cdc.gov](https://www.cdc.gov/cerc/media/pdfs/CERC_Introduction.pdf))
- CDC’s psychology-of-crisis guidance says that under stress, people may misinterpret confusing action messages; messages should be simple, credible, consistent, and repeated. It also warns against overconfidence and says communicators should state what is known, what is not known, and the process being used to get answers. ([cdc.gov](https://www.cdc.gov/cerc/media/pdfs/CERC_Psychology_of_a_Crisis.pdf))
- WHO plain-language guidance says health messages should get to the point quickly, use familiar words, organize the most important information first, and make the desired action clear. ([who.int](https://www.who.int/communicating-for-health/principles/understandable/plain-language/en/?utm_source=openai))

---

## 2. Evidence inventory

| Source | URL / source link | What it covers | Jurisdiction / context | Limitations |
|---|---|---|---|---|
| NHS — “How NHS 111 online works” | ([nhs.uk](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/how-nhs-111-online-works/)) | Digital triage model; no diagnosis; one main symptom; outcome types including nurse callback and GP/contact routing | England, NHS 111 online | NHS-specific service design and 999/111 ecosystem; not directly U.S. law or clinical policy |
| NHS — “When to call 999” | ([nhs.uk](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-call-999/)) | Emergency routing; 999 for life-threatening emergencies; 111 when unsure | UK / NHS | Emergency number and care pathways differ from U.S.; useful as taxonomy pattern |
| FDA — Clinical Decision Support Software guidance page | ([fda.gov](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software)) | Non-device CDS criteria; distinction between CDS exclusions and device software; patient/caregiver-facing caveat | U.S. FDA | Regulatory guidance, not a UX or triage algorithm; legal interpretation may require counsel |
| FDA — “How to Determine if Your Product is a Medical Device” | ([fda.gov](https://www.fda.gov/medical-devices/classify-your-medical-device/how-determine-if-your-product-medical-device)) | Medical-device definition tied to intended use for diagnosis, treatment, mitigation, prevention; SaMD concept | U.S. FDA | High-level classification guidance; does not decide status for a specific product |
| FDA — Examples of software functions that are not medical devices | ([fda.gov](https://www.fda.gov/medical-devices/device-software-functions-including-mobile-medical-applications/examples-software-functions-are-not-medical-devices)) | Examples where software provides source-basis to HCPs and does not require primary reliance | U.S. FDA | HCP-focused examples; direct-to-consumer triage may be treated differently |
| NHS England Digital — Clinical safety for developers | ([digital.nhs.uk](https://digital.nhs.uk/developer/guides-and-documentation/introduction-to-healthcare-technology/clinical-safety)) | DCB0129/DCB0160; clinical risk management; hazards, mitigations, Clinical Safety Officer | NHS / health IT builders | UK standard; not binding in U.S. but useful as mature health-software safety pattern |
| NHS England Digital — Clinical safety documentation | ([digital.nhs.uk](https://digital.nhs.uk/services/clinical-safety/documentation)) | Templates for safety case, clinical risk management plan, hazard log | NHS / health IT safety documentation | Templates are generic; source says generic hazard log is not definitive |
| npj Digital Medicine — Systematic review of symptom checker diagnostic and triage accuracy | ([nature.com](https://www.nature.com/articles/s41746-022-00667-w)) | Accuracy ranges; low/variable diagnostic accuracy; triage accuracy generally higher but variable; under- and over-triage harms | International literature review | Review includes heterogeneous tools and study designs; not a validation of any particular implementation |
| CDC — Crisis & Emergency Risk Communication Manual | ([cdc.gov](https://www.cdc.gov/cerc/php/cerc-manual/index.html)) | Emergency communication principles; empathy, credibility, action, respect; proportional risk messaging | U.S. public-health communication | Designed for public-health emergencies, not specifically app triage UX |
| CDC — Psychology of a Crisis | ([cdc.gov](https://www.cdc.gov/cerc/media/pdfs/CERC_Psychology_of_a_Crisis.pdf)) | Stress effects on comprehension; simple messages; uncertainty handling; avoid unsupported promises; action messages | U.S. public-health communication | Population-level crisis communication; must be adapted carefully to individual check-ins |
| WHO — Plain language guidance | ([who.int](https://www.who.int/communicating-for-health/principles/understandable/plain-language/en/?utm_source=openai)) | Plain-language principles for health communication | Global health communication | General communications guidance; not triage-specific |
| CDC — Flu emergency warning signs | ([cdc.gov](https://www.cdc.gov/flu/signs-symptoms/index.html)) | Adult and child warning signs: breathing difficulty, chest/abdominal pressure, confusion, seizures, no urination, worsening chronic conditions | U.S.; influenza-specific | Disease-specific; not exhaustive for all “something feels off” states |
| Mayo Clinic — Shortness of breath, when to see a doctor | ([mayoclinic.org](https://www.mayoclinic.org/symptoms/shortness-of-breath/basics/when-to-see-doctor/sym-20050890)) | Emergency and appointment-level routing for shortness of breath | U.S. clinical education | Symptom-specific; not a full triage framework |
| Johns Hopkins Medicine — “When to Call For Help” | ([hopkinsmedicine.org](https://www.hopkinsmedicine.org/health/wellness-and-prevention/when-to-call-for-help)) | Broad emergency symptoms: breathing, chest pain, fainting, confusion, severe pain, bleeding, self/other harm, stroke-like signs | U.S. patient education; cites ACEP | General list; not exhaustive and not a validated algorithm |
| CDC — Urgent maternal warning signs | ([cdc.gov](https://www.cdc.gov/hearher/maternal-warning-signs/index.html)) | Pregnancy/postpartum red flags and “seek medical care immediately” framing | U.S.; pregnancy and up to one year postpartum | Population-specific; may require user state/context to apply safely |
| CDC — Stroke signs and symptoms | ([cdc.gov](https://www.cdc.gov/stroke/signs-symptoms/?linkId=802504228&utm_source=openai)) | Sudden face/arm/leg weakness, confusion/speech trouble, vision trouble, walking trouble, severe headache; call 911 | U.S.; stroke education | Stroke-specific; should not be generalized beyond stroke-like symptoms |
| SAMHSA — Crisis help / 988 | ([samhsa.gov](https://www.samhsa.gov/find-support/in-crisis)) | 911/ER for danger or medical emergency; 988 for mental health, substance use, suicide crisis support | U.S. crisis system | Resource availability and user experience vary by location and modality |
| NIMH — Warning signs of suicide | ([nimh.nih.gov](https://www.nimh.nih.gov/health/publications/warning-signs-of-suicide)) | Warning signs: wanting to die, hopelessness, plan/researching ways to die, withdrawal, risky behavior, increased substance use; get help as soon as possible; 988 | U.S. mental-health education | Warning signs are not diagnostic and do not replace crisis assessment |

---

## 3. Decision-neutral findings

### DQ1 — Do-not-diagnose boundaries for the check-in

**Observed boundary pattern: triage without diagnosis.** NHS 111 online explicitly separates triage from diagnosis: users answer questions about a main symptom and are told what help they need, while the service states they “will not get a diagnosis.” It also narrows scope by triaging one symptom at a time and excluding advice on already-known conditions. This pattern maps to the triage pill’s Capture → Clarify role and to C10’s do-not-diagnose gate. ([nhs.uk](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/how-nhs-111-online-works/))

**Observed regulatory boundary: intended use matters.** FDA materials define medical-device status in part by whether the product is intended for diagnosis, cure, mitigation, treatment, or prevention, and FDA’s CDS guidance distinguishes non-device CDS from device software while noting that patient/caregiver-facing functions that meet the device definition remain subject to digital-health policies. This is relevant to wording choices such as “this may be X,” “you likely have X,” “treat X by doing Y,” versus “these answers match warning signs that public sources say should be checked urgently.” ([fda.gov](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software))

**Observed source-basis pattern.** FDA examples for non-device software emphasize that the basis for recommendations should be reviewable and that clinicians should not rely primarily on the software output. Although those examples are HCP-facing, the pattern is relevant to provenance: source-linked routing statements are materially different from unsupported clinical assertions. ([fda.gov](https://www.fda.gov/medical-devices/device-software-functions-including-mobile-medical-applications/examples-software-functions-are-not-medical-devices))

**Evidence limitation.** Symptom-checker research shows diagnostic accuracy is generally low and variable; a systematic review found primary diagnostic accuracy ranges of 19–38% and triage accuracy ranges of about 49–90%, with patient-safety hazards from reliance on symptom checkers. This supports treating diagnosis generation as a distinct risk class from routing guidance. ([nature.com](https://www.nature.com/articles/s41746-022-00667-w))

**Affected components.**
- **Triage question model:** sources favor symptom/status questions rather than diagnostic labeling.
- **C10 safety gate:** needs to detect diagnostic claims, treatment claims, and unsupported probabilistic disease assertions.
- **Response contract:** source-linked “what to do next” language is distinct from “what condition you have” language.

---

### DQ2 — Never-alarm language constraints for escalation messages

**Observed language pattern: simple, action-oriented, proportionate.** CDC CERC principles emphasize accuracy, credibility, empathy, respect, and meaningful action steps. CDC states that giving people meaningful things to do can calm anxiety and restore some sense of control. ([cdc.gov](https://www.cdc.gov/cerc/media/pdfs/CERC_Introduction.pdf))

**Observed stress-comprehension pattern.** CDC psychology-of-crisis guidance says people under stress may not fully hear information, may remember less, and may misinterpret confusing action messages; it therefore calls for simple, credible, consistent messaging. ([cdc.gov](https://www.cdc.gov/cerc/media/pdfs/CERC_Psychology_of_a_Crisis.pdf))

**Observed uncertainty pattern.** CDC advises communicators to acknowledge uncertainty, distinguish what is known from what is not known, and avoid unsupported promises; it also warns that overconfidence can backfire and that the goal is appropriate vigilance rather than over-reassurance. ([cdc.gov](https://www.cdc.gov/cerc/media/pdfs/CERC_Psychology_of_a_Crisis.pdf))

**Observed plain-language pattern.** WHO plain-language guidance says public health messages should get to the point quickly, use familiar words, put the most important information first, and make the desired action clear. ([who.int](https://www.who.int/communicating-for-health/principles/understandable/plain-language/en/?utm_source=openai))

**Implications for option space, without choosing policy.**
- Sources support language that is:
  - direct about the next action,
  - calm and non-graphic,
  - clear about uncertainty,
  - free of unsupported reassurance,
  - free of catastrophic speculation,
  - respectful and non-stigmatizing.
- Sources do not supply a product-ready “never-alarm” lexicon; maintainers must define the exact banned phrases, required phrases, and tone tests.

**Affected components.**
- **C10 panic-language filter:** can be mapped against catastrophic, speculative, or overconfident phrasing.
- **Response templates:** can separate “why this route appears” from “what to do next.”
- **Provenance layer:** can state source basis without turning warnings into diagnoses.

---

### DQ3 — Criteria mapping a check-in to escalation tier, and tier patterns

**Observed emergency criteria.** Multiple public health and clinical education sources use symptom-based red flags for emergency escalation. Examples include difficulty breathing, persistent chest or abdominal pain/pressure, confusion or inability to arouse, seizures, not urinating, severe weakness/unsteadiness, sudden severe pain, uncontrolled bleeding, overdose/poisoning, loss of consciousness, severe allergic reaction, and feelings about harming self or others. ([cdc.gov](https://www.cdc.gov/flu/signs-symptoms/index.html))

**Observed stroke-specific criteria.** CDC stroke guidance identifies sudden numbness or weakness in the face, arm, or leg—especially on one side—sudden confusion or trouble speaking/understanding speech, sudden vision trouble, sudden walking trouble/dizziness/loss of balance, and sudden severe headache, with instruction to call 911 right away. ([cdc.gov](https://www.cdc.gov/stroke/signs-symptoms/?linkId=802504228&utm_source=openai))

**Observed breathing-specific routing.** Mayo Clinic distinguishes emergency shortness-of-breath presentations—sudden severe shortness of breath, shortness of breath with chest pain, fainting, blue lips/nails, or mental-status change—from appointment-level presentations such as swelling, trouble breathing lying flat, fever/chills/cough, wheezing, or worsening long-term shortness of breath. ([mayoclinic.org](https://www.mayoclinic.org/symptoms/shortness-of-breath/basics/when-to-see-doctor/sym-20050890))

**Observed pregnancy/postpartum special-case criteria.** CDC’s maternal warning signs include severe or worsening headache, vision changes, fever, extreme swelling, thoughts of harming self or baby, trouble breathing, chest pain or fast heartbeat, severe nausea/vomiting, severe belly pain, reduced fetal movement, vaginal bleeding/fluid leakage, heavy postpartum bleeding, and severe limb swelling/redness/pain. CDC states to seek medical care immediately for listed signs and that the symptoms can indicate life-threatening conditions. ([cdc.gov](https://www.cdc.gov/hearher/maternal-warning-signs/index.html))

**Observed mental-health crisis criteria.** NIMH lists warning signs such as talking about wanting to die, hopelessness, unbearable pain, making a plan or researching ways to die, withdrawal/goodbyes, dangerous risks, mood swings, altered eating/sleeping, and increased drug/alcohol use; it says to get help as soon as possible, especially if new or increased. SAMHSA separates 911/ER for danger or medical emergency from 988 for crisis support. ([nimh.nih.gov](https://www.nimh.nih.gov/health/publications/warning-signs-of-suicide))

**Observed tier pattern.** The sources collectively show at least four external routing categories:
1. **Emergency now** — life-threatening, danger, major red flags, stroke/heart/breathing/severe injury/overdose/self-harm risk patterns. ([nhs.uk](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-call-999/))  
2. **Urgent clinical contact / callback / same-day service** — symptom severity or warning signs that require prompt clinician review but are not always framed as immediate emergency dispatch. NHS 111 nurse callback and Mayo appointment/escalation examples illustrate this middle layer. ([nhs.uk](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/how-nhs-111-online-works/))  
3. **Primary care / known care team / condition-specific service** — NHS 111 includes GP, dentist, optician, and other-service routing; Mayo includes doctor appointment routing for non-emergency shortness-of-breath patterns. ([nhs.uk](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/how-nhs-111-online-works/))  
4. **Self-care / information with watchful waiting triggers** — NHS 111 includes outcome types below urgent callback, and CDC sources often add “not all inclusive” clauses and clinician contact for symptoms that are severe or concerning. ([nhs.uk](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/how-nhs-111-online-works/))

**Affected components.**
- **Question model:** needs to elicit red-flag presence/absence, onset, severity, pregnancy/postpartum status, self/other-harm risk, and uncertainty.
- **Escalation tiering:** external sources supply tier patterns but not one universal validated tier schema.
- **C10 gate:** must handle special populations and “severe or concerning” fallback language.

---

### DQ4 — Response routing: self-care vs. seek care vs. emergency, non-diagnostic and source-aware

**Observed routing language avoids diagnosis in mature triage services.** NHS 111 online says it tells users “what to do next” rather than diagnosing them. That distinction is a concrete external pattern for non-diagnostic routing. ([nhs.uk](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/how-nhs-111-online-works/))

**Observed emergency routing language is directive but symptom-based.** NHS says 999 is for life-threatening emergencies such as serious accidents, strokes, and heart attacks; CDC stroke guidance says call 911 right away if stroke signs appear; SAMHSA says call 911 or go to the nearest ER if someone is in danger or having a medical emergency. These are action routes tied to warning signs or emergency categories, not individualized diagnoses. ([nhs.uk](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-call-999/))

**Observed “seek care” routing varies by system.** NHS 111 may route to nurse callback with a timeframe, GP surgery, dentists/opticians, or other services. Mayo shortness-of-breath guidance routes some presentations to immediate emergency care and others to a doctor appointment. ([nhs.uk](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/how-nhs-111-online-works/))

**Observed self-care routing requires escalation backstops.** CDC’s flu warning-sign page lists emergency warning signs and then says the list is not all-inclusive and to consult a medical provider for any other severe or concerning symptom. This pattern leaves room for user concern and unlisted deterioration rather than treating the checklist as exhaustive. ([cdc.gov](https://www.cdc.gov/flu/signs-symptoms/index.html))

**Observed crisis routing distinguishes immediate danger from crisis support.** SAMHSA frames 988 as 24/7 trained crisis-counselor support for people struggling or in crisis, while reserving 911/ER for danger or medical emergency. NIMH warning signs point to 988 and getting help as soon as possible, especially when behaviors are new or increasing. ([samhsa.gov](https://www.samhsa.gov/find-support/in-crisis))

**Affected components.**
- **Response-routing contract:** needs to encode source, jurisdiction, action route, urgency wording, and non-diagnostic rationale.
- **C10 provenance control:** source-aware routing depends on linking each route to a trusted source or clinical governance rule.
- **UI:** must distinguish informational self-care from “contact a clinician” and “emergency now” without implying certainty about a disease.

---

## 4. Tradeoffs and open questions

### A. How narrow should the triage scope be?
- **Narrow scope pattern:** One main symptom, no known-condition advice, no diagnosis, as in NHS 111 online. This reduces ambiguity and diagnostic drift but may frustrate users with multi-symptom deterioration. ([nhs.uk](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/how-nhs-111-online-works/))
- **Broader “something feels off” scope:** Captures vague deterioration and user intuition but increases ambiguity, red-flag false negatives, and the need for robust fallback routing.

### B. How should the system balance under-triage and over-triage?
- Symptom-checker evidence identifies both under-triage harms and over-triage burdens; the systematic review notes variable accuracy and potential patient-safety hazards from reliance on symptom checkers. ([nature.com](https://www.nature.com/articles/s41746-022-00667-w))
- A more conservative policy may increase emergency/urgent routing and user alarm or service burden.
- A less conservative policy may reduce alarm but increases risk of missed deterioration.

### C. What counts as “emergency” in the product’s jurisdiction?
- U.S. sources route danger, medical emergency, stroke signs, and many acute red flags to 911/ER. ([samhsa.gov](https://www.samhsa.gov/find-support/in-crisis))
- UK NHS sources use 999/111 and NHS-specific service pathways. ([nhs.uk](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-call-999/))
- The product must decide whether routing text is location-specific, user-configured, or generalized with local-emergency-number substitution.

### D. How much uncertainty should escalation messages expose?
- CDC guidance supports stating what is known, what is not known, and what action to take, while avoiding unsupported promises or overconfidence. ([cdc.gov](https://www.cdc.gov/cerc/media/pdfs/CERC_Psychology_of_a_Crisis.pdf))
- Too much uncertainty may reduce action.
- Too little uncertainty may imply diagnosis or false precision.

### E. Should special populations be first-class triage branches?
- Pregnancy/postpartum warning signs differ materially from general adult warning signs, and CDC covers pregnancy through one year after delivery. ([cdc.gov](https://www.cdc.gov/hearher/maternal-warning-signs/index.html))
- Pediatric, older adult, immunocompromised, chronic-condition, and disability contexts may require separate question paths.
- Collecting these attributes improves routing relevance but raises UX, privacy, and bias-control questions.

### F. How should mental-health crisis routing be integrated?
- SAMHSA and NIMH distinguish crisis support through 988 from 911/ER when there is danger or medical emergency. ([samhsa.gov](https://www.samhsa.gov/find-support/in-crisis))
- Over-triggering crisis resources can feel alarming or irrelevant; under-triggering can miss imminent risk.
- Open design choice: whether self-harm screening appears in every check-in, only when indicated, or via a separate parallel safety gate.

### G. What safety artifacts are required for C10?
- NHS clinical safety practice uses hazard logs, safety cases, risk-management plans, and Clinical Safety Officer responsibility. ([digital.nhs.uk](https://digital.nhs.uk/developer/guides-and-documentation/introduction-to-healthcare-technology/clinical-safety))
- Open product question: which artifacts are mandatory internally for this component, who signs them off, and how changes to prompts/routing rules re-open the safety case.

### H. What is the exact “never-alarm” enforcement mechanism?
- CERC and WHO provide principles—plain language, empathy, actionability, credibility, proportionality—but not a ready-made banned-phrase list. ([cdc.gov](https://www.cdc.gov/cerc/media/pdfs/CERC_Introduction.pdf))
- Open implementation choices include template-only messages, classifier-based tone checks, rule-based banned phrases, human-reviewed escalation copy, or a hybrid.

## Approaches considered

_Grounded only in the recorded research above._

**DQ1 — Do-not-diagnose boundary.**
- **(1a) Triage-without-diagnosis (NHS 111 pattern):** ask about a main symptom/status, return "what to do next," never name a condition or probability. Lowest diagnostic-drift risk; cleanest C10 gate; may frustrate multi-symptom users.
- **(1b) Soft-differential:** surface "this may relate to X" with hedging. Higher perceived usefulness but crosses the FDA intended-use line toward device/diagnosis and contradicts `do_not_diagnose_rules.md`.

**DQ2 — Never-alarm enforcement.**
- **(2a) Template-only copy:** every escalation message is a pre-written, reviewed template; the model only selects a route, never authors prose. Maximum control, lowest expressiveness.
- **(2b) Free-form + classifier tone check:** model writes, a classifier scores tone. Expressive but weakest guarantee.
- **(2c) Template-first + deterministic banned-phrase filter + classifier as defense-in-depth:** templates carry the copy; a rule-based filter blocks catastrophic/speculative/overconfident/unsupported-reassurance phrasing; a classifier is a second net. Strong guarantee, still maintainable.

**DQ3 — Escalation tiers.**
- **(3a) Binary (emergency / not):** simple but collapses the urgent-vs-routine distinction the sources clearly separate.
- **(3b) Four-tier disposition** (Emergency now / Urgent same-day clinical contact / Routine care / Self-care with watchful-waiting triggers) **+ a parallel mental-health crisis path** (988 vs 911/ER split). Matches the NHS 111 / SAMHSA / NIMH pattern across all consulted sources.

**DQ4 — Routing rule source + jurisdiction.**
- **(4a) LLM-derived routing:** model decides the tier. Rejected — symptom-checker evidence shows low/variable accuracy and patient-safety hazards.
- **(4b) Deterministic, source-linked red-flag rule set** (curated symptom clusters from CDC/Mayo/NIMH/SAMHSA) drives the tier; LLM only phrases the chosen route. Jurisdiction handled by locale-config emergency-number substitution with a generalized default.

## Decision

_Approved by user on 2026-06-17._

For the `triage` "Something feels off" check-in behind C10, adopt **1a + 2c + 3b + 4b**:

1. **Triage-without-diagnosis.** The check-in elicits symptom/status (presence/absence of red flags, onset, severity, special-population status, self/other-harm risk, uncertainty) and returns **"what to do next," never a condition name, probability, or treatment instruction.** Every response is framed as non-diagnostic and source-linked.
2. **Deterministic, source-linked routing into four tiers + a parallel mental-health crisis path.** A curated, version-controlled red-flag rule set (not the LLM) selects the tier:
   - **Emergency now** — stroke (FAST), breathing difficulty, chest pain/pressure, confusion/unarousable, seizure, uncontrolled bleeding, anaphylaxis, overdose/poisoning, loss of consciousness, danger to self/others.
   - **Urgent same-day clinical contact** — warning signs needing prompt clinician review but not immediate dispatch.
   - **Routine primary care / known care team.**
   - **Self-care with watchful-waiting triggers** — always carrying a CDC-style "this list is not all-inclusive; if it feels severe or concerning, contact a clinician" backstop.
   - **Mental-health crisis path** (parallel): 988-style crisis support vs 911/ER when there is danger or medical emergency.
3. **Special populations are first-class branches.** Pregnancy/postpartum (through one year) is a distinct red-flag branch from launch; pediatric / older-adult / immunocompromised / chronic-condition branches are designed-for but may phase in.
4. **Never-alarm enforcement = template-first + deterministic banned-phrase filter + classifier (defense-in-depth).** Escalation copy is pre-written, reviewed, plain-language, action-first, calm, and uncertainty-honest. The LLM selects a route and fills approved slots; it never free-authors escalation prose. A rule-based filter blocks catastrophic, speculative, overconfident, and unsupported-reassurance phrasing; a tone classifier is a second net.
5. **Jurisdiction is locale-config.** Routing text uses a generalized default ("call your local emergency number") with locale substitution (911 / 999 / 112, 988); never hard-coded to one country.
6. **C10 ordering:** deterministic rules engine (red-flag tiering + banned-phrase + do-not-diagnose + source-provenance) runs **first**, then the LLM gate, then output routing. Any change to prompts, templates, or the red-flag rule set re-opens the clinical-safety artifacts (hazard log entry + safety-case note).

## Trade-offs accepted

- **Conservative-by-default** (route up when ambiguous) accepts more urgent/self-care escalations and some over-triage burden, in exchange for fewer missed-deterioration false negatives — the safer error class for a safety gate.
- **Template-first copy** sacrifices conversational expressiveness for an auditable never-alarm guarantee.
- **Single main concern at a time** (NHS 111 scope) may frustrate multi-symptom users; mitigated by the always-present "severe or concerning" backstop and the ability to run another check-in.
- **Deterministic routing** trades adaptive coverage for predictability and source-traceability; the rule set must be curated and maintained, and re-opens the safety case on every change.
- **Locale-config emergency numbers** add configuration surface but avoid unsafe country-hard-coding.

## Implementation notes

- **C10 (rules engine):** add a triage red-flag rule set (versioned, source-linked) + banned-phrase/never-alarm filter + do-not-diagnose detector; enforce deterministic-first ordering ahead of the LLM gate.
- **Triage question model:** symptom/status elicitation including onset, severity, special-population status, self/other-harm screen, and an explicit uncertainty capture.
- **Response-routing contract:** each route carries `{source, jurisdiction, action_route, urgency_wording, non_diagnostic_rationale}`; UI distinguishes informational self-care from "contact a clinician" from "emergency now" without implying disease certainty.
- **Safety artifacts:** create a hazard log entry + clinical-safety-case note for this component; define sign-off owner; wire a check so prompt/template/rule-set changes flag the safety case for re-review.
- **Crisis path:** 988/911 split surfaced via a parallel screen; decide (separate follow-up) whether self-harm screening appears in every check-in or only when indicated.
- Honors guardrails: personal-first, user-controlled, source-linked, **non-diagnostic**, **never-alarm/calm**, grant-scoped; empowers the user within the clinical system rather than replacing it.

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
