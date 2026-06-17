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


## Re-run research (user-provided, 2026-06-18)

> Recorded per research-protocol.mdc Section D. The approved decision above is unchanged. This independent re-run research was reviewed and is consistent with the approved decision; no supersede. Source file: `track-c-triage-research-result.md`.

# Track C triage research result: deterioration check-in and safe-escalation rules behind the safety gate

Scope: Decision-neutral research brief for WellBe's unbuilt "Something feels off" check-in and C10 Safety & Governance Gate. This brief is an evidence inventory and option-space map, not medical advice, legal advice, or a recommended product policy. Findings are limited to the sources linked below.

## External patterns to examine

### 1. Non-diagnostic digital triage and disposition routing

Public digital triage services commonly draw a hard line between symptom triage and diagnosis. [NHS 111 online](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/how-nhs-111-online-works/) says users answer a series of questions, that the service will not give a diagnosis, and that the user will instead find out what help they need. The live [NHS 111 online entry page](https://111.nhs.uk/) repeats that it will direct users to the best place to get help rather than diagnose. Australia's [healthdirect Symptom Checker](https://www.healthdirect.gov.au/symptom-checker) similarly says it can advise whether to see a doctor or care for oneself, but cannot provide a diagnosis and is not a substitute for professional care. Ontario's Health811 public listings describe symptom assessment and nurse access while stating that the service does not provide diagnoses and is not a substitute for in-person care for emergencies ([211 Ontario Health811](https://211ontario.ca/service/97619356/ontario-ministry-of-health-health811/), [Ontario seniors guide](https://www.ontario.ca/document/guide-programs-and-services-seniors/health-and-well-being)).

The routing pattern in these services is disposition-based rather than disease-label-based. NHS 111 online routes users toward self-care, pharmacist, dentist or optician, GP, nurse callback, urgent treatment centre, mental health support, A&E, or other urgent services depending on the pathway result ([NHS 111 online](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/how-nhs-111-online-works/)). Australia's government description of healthdirect frames outcomes as self-care, doctor, hospital, or ambulance/emergency routing ([Australian Government: healthdirect Symptom Checker](https://www.health.gov.au/resources/apps-and-tools/healthdirect-symptom-checker)). Ontario's service describes self-care suggestions, recommendation to contact a health practitioner, or referral to community resources, with 911 reserved for medical emergencies ([Ontario seniors guide](https://www.ontario.ca/document/guide-programs-and-services-seniors/health-and-well-being)).

### 2. Clinically governed triage pathways and provenance

A separate pattern is governance of the question flow and disposition logic. [NHS Pathways](https://digital.nhs.uk/services/nhs-pathways) describes itself as a clinical decision support system used across NHS 111, 999, urgent care, and emergency care settings. It states that its clinical authoring team is made up of registered, licensed practitioners with urgent and emergency care backgrounds, and that the tool is used to assess, triage, and direct the public to appropriate care. This does not establish a specific model for WellBe, but it is evidence that high-consequence triage logic is commonly treated as governed clinical content rather than ordinary conversational copy.

### 3. Regulatory and do-not-diagnose boundary framing

Regulatory sources examine software by intended use, user type, claims, function, and reliance. The [FDA Clinical Decision Support Software guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software) explains FDA's interpretation of when certain CDS functions are excluded from the medical-device definition under the 21st Century Cures Act, and when device software functions remain subject to FDA oversight. The [FDA CDS FAQ](https://www.fda.gov/medical-devices/software-medical-device-samd/clinical-decision-support-software-frequently-asked-questions-faqs) describes four criteria for non-device CDS, including that the software provide recommendations or options to a health care professional rather than a specific output or directive, and that the user can independently review the basis for the recommendation. The FAQ also notes that failure to meet all four non-device CDS criteria does not automatically mean the product is a regulated device.

FDA's broader [Device Software Functions Including Mobile Medical Applications](https://www.fda.gov/medical-devices/digital-health-center-excellence/device-software-functions-including-mobile-medical-applications) page describes a function-specific, risk-based approach. It gives examples of functions for which FDA intends enforcement discretion, including some functions that help patients self-manage a disease or condition without providing specific treatment suggestions. UK and EU sources use related but distinct frameworks: the MHRA [Software and AI as a Medical Device](https://www.gov.uk/government/publications/software-and-artificial-intelligence-ai-as-a-medical-device/software-and-artificial-intelligence-ai-as-a-medical-device) guidance discusses when software is a medical device in the UK, the MHRA [intended-purpose guidance](https://www.gov.uk/government/publications/crafting-an-intended-purpose-in-the-context-of-software-as-a-medical-device-samd) highlights safety and compliance risks from poorly framed intended-purpose statements, and EU [MDCG 2019-11 Rev.1](https://health.ec.europa.eu/document/download/b45335c5-1679-4c71-a91c-fc7a4d37f12b_en?filename=mdcg_2019_11_en.pdf) provides non-binding guidance on qualification and classification of software under MDR/IVDR. The [IMDRF SaMD key definitions](https://www.imdrf.org/documents/software-medical-device-samd-key-definitions) provide the international terminology baseline for "software as a medical device."

### 4. Safety-netting as the clinical communication pattern for uncertainty

Safety-netting literature addresses a problem close to the WellBe check-in: communicating uncertainty, what to watch for, and when/how to seek more help. A British Journal of General Practice review describes safety netting as including communication of uncertainty, explanation of red-flag symptoms, advice about future appointments, and timely reassessment ([BJGP literature review](https://bjgp.org/content/69/678/e70)). BMJ Quality & Safety work on safety-netting communication emphasizes tailoring, practical self-care and reconsultation information, checking understanding, considering personal circumstances, and documenting advice for continuity ([BMJ Quality & Safety / PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9234415/)). NIHR Evidence summarizes safety-netting as a way to manage uncertain diagnoses and reduce missed deterioration through clear advice and timely follow-up ([NIHR Evidence](https://evidence.nihr.ac.uk/alert/safety-netting-in-general-practice-manage-uncertain-diagnoses/)).

### 5. Red-flag and warning-sign frameworks

Authoritative public health and clinical sources publish warning-sign lists that can inform escalation criteria without requiring the product to diagnose a condition. General adult emergency signs are summarized by MedlinePlus from the American College of Emergency Physicians, including trouble breathing, chest pain, confusion or trouble waking, fainting, severe pain, severe abdominal pain, sudden weakness or vision change, uncontrolled bleeding, poisoning, suicidal or homicidal feelings, and other urgent signs ([MedlinePlus: recognizing medical emergencies](https://medlineplus.gov/ency/article/001927.htm)). Emergency-number guidance from the NHS frames 999 as appropriate for life-threatening emergencies, including major accidents, strokes, and heart attacks, and directs uncertainty to NHS 111 where available ([NHS: when to call 999](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-call-999/)).

Condition-specific warning-sign sources include stroke signs and BE FAST from the CDC and American Heart Association ([CDC stroke signs](https://www.cdc.gov/stroke/signs-symptoms/index.html), [American Heart Association symptoms](https://www.heart.org/en/about-us/heart-attack-and-stroke-symptoms)), heart attack warning signs from the American Heart Association ([AHA](https://www.heart.org/en/about-us/heart-attack-and-stroke-symptoms)), sepsis warning signs from CDC ([CDC sepsis](https://www.cdc.gov/sepsis/about/index.html)), and anaphylaxis signs and emergency action from Mayo Clinic ([Mayo Clinic anaphylaxis](https://www.mayoclinic.org/diseases-conditions/anaphylaxis/symptoms-causes/syc-20351468)).

Special-population frameworks include pregnancy and postpartum warning signs from CDC's HEAR HER campaign, which applies during pregnancy and up to one year after delivery ([CDC urgent maternal warning signs](https://www.cdc.gov/hearher/maternal-warning-signs/index.html), [CDC pregnant and postpartum guidance](https://www.cdc.gov/hearher/pregnant-postpartum/index.html)); early pregnancy bleeding and pain escalation signs from the Royal College of Obstetricians and Gynaecologists ([RCOG](https://www.rcog.org.uk/for-the-public/browse-our-patient-information/bleeding-andor-pain-in-early-pregnancy/)); pediatric fever traffic-light criteria from NICE ([NICE NG143](https://www.nice.org.uk/guidance/NG143), [NICE traffic-light table](https://www.nice.org.uk/guidance/ng143/resources/support-for-education-and-learning-educational-resource-traffic-light-table-pdf-6960664333)); and public child-serious-illness warning signs from NHS and healthdirect ([NHS baby/toddler serious illness](https://www.nhs.uk/baby/health/is-your-baby-or-toddler-seriously-ill/), [healthdirect serious illness in babies and children](https://www.healthdirect.gov.au/symptoms-of-serious-illness-in-babies-and-children)).

### 6. Crisis-safe and calm communication

Crisis and risk communication sources emphasize clarity, empathy, credibility, and action rather than alarm. CDC's [Crisis and Emergency Risk Communication manual](https://www.cdc.gov/cerc/php/cerc-manual/index.html) describes an evidence-based framework for communication during emergencies; CDC CERC materials summarize core principles as being right, credible, empathetic, action-oriented, and respectful. CDC's [Clear Communication Index](https://www.cdc.gov/ccindex/index.html) and [user guide](https://www.cdc.gov/ccindex/tool/index.html) provide criteria such as one main message, common words, active voice, specific action, clear risk explanation, and explicit statements of what is known and not known.

Mental-health crisis sources add constraints for non-alarming but direct language. The [988 Lifeline](https://988lifeline.org/) frames help as free, confidential, and available 24/7 for mental health struggles, emotional distress, substance or alcohol concerns, and needing someone to talk to. Its [Help Someone Else](https://988lifeline.org/help-someone-else/) guidance encourages direct, matter-of-fact, nonjudgmental conversation, listening, avoiding shock, connecting to help, and taking practical safety steps. [NIMH warning signs of suicide](https://www.nimh.nih.gov/health/publications/warning-signs-of-suicide) lists warning signs and directs people to 988 or emergency help. NICE self-harm guidance and NHS England suicide-prevention implementation guidance emphasize psychosocial assessment and safety planning and caution against using risk tools or global low/medium/high risk stratification to predict future suicide or self-harm ([NICE NG225](https://www.nice.org.uk/guidance/ng225), [NHS England: Staying safe from suicide](https://www.england.nhs.uk/long-read/staying-safe-from-suicide/)). WHO's suicide communication resource describes how communications about suicide can either increase harm or support prevention depending on framing ([WHO suicide-prevention media resource](https://www.who.int/publications/i/item/9789240076846)).

### 7. Digital symptom-checker safety evidence

Multiple reviews find that symptom checkers and online triage systems vary substantially in diagnostic and triage accuracy. The BMJ audit by Semigran et al. evaluated 23 symptom checkers against standardized vignettes and found variable diagnostic and triage performance, with triage more accurate for emergency cases than for non-urgent or self-care cases ([BMJ 2015](https://www.bmj.com/content/351/bmj.h3480)). A BMJ Open systematic review found little evidence on patient safety, adverse events, and user adherence, and described overall evidence quality as limited ([BMJ Open 2019](https://bmjopen.bmj.com/content/9/8/e027743)). An npj Digital Medicine systematic review reported generally low and highly variable diagnostic and triage accuracy across symptom checkers ([npj Digital Medicine 2022](https://www.nature.com/articles/s41746-022-00667-w)). A later review comparing symptom assessment applications, large language models, and laypeople found moderate but highly variable self-triage accuracy across applications, with no universal conclusion that such tools should be adopted or rejected in all settings ([NPJ Digital Medicine / PMC review](https://pmc.ncbi.nlm.nih.gov/articles/PMC11937345/)).

## Evidence inventory

| Source | URL | What it covers | Jurisdiction/context | Limitations |
|---|---|---|---|---|
| FDA Clinical Decision Support Software guidance | [Link](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software) | Interpretation of non-device CDS under the 21st Century Cures Act and when device software remains under FDA oversight. | United States; FDA-regulated device software. | Regulatory guidance, not product-specific legal advice; US-specific. |
| FDA CDS FAQ | [Link](https://www.fda.gov/medical-devices/software-medical-device-samd/clinical-decision-support-software-frequently-asked-questions-faqs) | Four non-device CDS criteria; role of recommendations/options, user review of basis, and HCP reliance. | United States; CDS and device software. | Criteria are framed around health care professionals; patient/caregiver consumer surfaces require separate analysis. |
| FDA Device Software Functions Including Mobile Medical Applications | [Link](https://www.fda.gov/medical-devices/digital-health-center-excellence/device-software-functions-including-mobile-medical-applications) | Function-specific risk-based device software policy; enforcement discretion examples, including some patient self-management functions without specific treatment suggestions. | United States; mobile apps and device software functions. | Enforcement-discretion examples do not automatically define a safe product boundary. |
| MHRA Software and AI as a Medical Device | [Link](https://www.gov.uk/government/publications/software-and-artificial-intelligence-ai-as-a-medical-device/software-and-artificial-intelligence-ai-as-a-medical-device) | UK framework for deciding when software, including AI, is a medical device; vigilance and safety concerns. | United Kingdom. | UK-specific; classification depends on intended purpose and detailed claims. |
| MHRA intended-purpose guidance | [Link](https://www.gov.uk/government/publications/crafting-an-intended-purpose-in-the-context-of-software-as-a-medical-device-samd) | How to craft intended-purpose statements for SaMD and why inaccurate statements create compliance and safety risk. | United Kingdom; SaMD. | Intended-purpose guidance does not by itself classify the WellBe feature. |
| EU MDCG 2019-11 Rev.1 | [Link](https://health.ec.europa.eu/document/download/b45335c5-1679-4c71-a91c-fc7a4d37f12b_en?filename=mdcg_2019_11_en.pdf) | Qualification and classification of software under MDR/IVDR. | European Union; medical device and IVD regulations. | MDCG guidance is non-binding; authoritative interpretation ultimately rests with courts and regulators. |
| IMDRF SaMD key definitions | [Link](https://www.imdrf.org/documents/software-medical-device-samd-key-definitions) | International terminology for software as a medical device. | International regulatory harmonization context. | Definitions alone do not answer classification or intended-use questions. |
| NHS 111 online: how it works | [Link](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/how-nhs-111-online-works/) | Non-diagnostic digital triage flow; one symptom at a time; possible dispositions including self-care, clinician callback, urgent services, A&E, mental health support. | England; national urgent and emergency care access. | Service-specific algorithm and outcomes are not fully public; age/location constraints apply. |
| NHS 111 online entry page | [Link](https://111.nhs.uk/) | Public-facing non-diagnosis statement and broad categories of help. | England. | Public landing page, not a complete triage protocol. |
| NHS Pathways | [Link](https://digital.nhs.uk/services/nhs-pathways) | Governed clinical decision support system used by NHS 111, 999, urgent care, and emergency care; clinical authoring governance. | England; licensed NHS triage system. | Full pathway logic is not publicly exposed; not directly portable without governance/licensing. |
| healthdirect Symptom Checker | [Link](https://www.healthdirect.gov.au/symptom-checker) | Consumer symptom checker that states it is not diagnostic and not a substitute for professional care. | Australia; government-funded public health service. | Powered by a third-party triage engine; pathway logic not fully visible. |
| Australian Government: healthdirect Symptom Checker | [Link](https://www.health.gov.au/resources/apps-and-tools/healthdirect-symptom-checker) | Outcome categories: self-care, see doctor, hospital, ambulance/emergency; local service finding. | Australia. | Australian emergency number and care system; not directly global. |
| Ontario Health811 listing | [Link](https://211ontario.ca/service/97619356/ontario-ministry-of-health-health811/) | Nurse access, symptom assessment, non-diagnosis and non-emergency framing. | Ontario, Canada. | Public listing; not a full clinical protocol. |
| Ontario Health811 government guide | [Link](https://www.ontario.ca/document/guide-programs-and-services-seniors/health-and-well-being) | Emergency call 911; Health811 can provide self-care suggestions, practitioner recommendation, or community-resource referral. | Ontario, Canada. | Part of a seniors guide; broader service details appear elsewhere. |
| MedlinePlus: recognizing medical emergencies | [Link](https://medlineplus.gov/ency/article/001927.htm) | General adult and pediatric warning signs for emergency medical help. | United States; consumer health information citing American College of Emergency Physicians. | Broad list; does not encode exact digital triage thresholds. |
| NHS: when to call 999 | [Link](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-call-999/) | Life-threatening emergency framing and call-handler routing expectations. | United Kingdom/England; NHS urgent and emergency care. | UK emergency number and NHS context; examples not exhaustive. |
| CDC stroke signs | [Link](https://www.cdc.gov/stroke/signs-symptoms/index.html) | Sudden stroke warning signs, BE FAST, and emergency action. | United States public health source. | Condition-specific; uses disease label as public warning sign, not as patient diagnosis. |
| American Heart Association symptoms | [Link](https://www.heart.org/en/about-us/heart-attack-and-stroke-symptoms) | Heart attack, stroke, and cardiac arrest warning signs. | United States nonprofit clinical/public health education. | Condition-specific; not a complete general triage system. |
| CDC sepsis | [Link](https://www.cdc.gov/sepsis/about/index.html) | Sepsis as life-threatening emergency; signs such as confusion, extreme pain, shortness of breath, high heart rate, fever/shivering/very cold. | United States public health source. | Diagnosis and treatment are clinician-dependent; signs are not specific. |
| Mayo Clinic anaphylaxis | [Link](https://www.mayoclinic.org/diseases-conditions/anaphylaxis/symptoms-causes/syc-20351468) | Severe allergic reaction symptoms and emergency help after epinephrine. | Consumer clinical education; United States. | Institution source rather than national public-health body; condition-specific. |
| CDC HEAR HER urgent maternal warning signs | [Link](https://www.cdc.gov/hearher/maternal-warning-signs/index.html) | Warning signs during pregnancy and up to one year postpartum that need immediate medical care. | United States public health; maternal health. | Warning signs are broad; local obstetric routes vary. |
| CDC HEAR HER pregnant/postpartum guidance | [Link](https://www.cdc.gov/hearher/pregnant-postpartum/index.html) | Urges care for maternal warning signs and telling providers about current/recent pregnancy. | United States public health; pregnancy/postpartum. | Does not provide a digital triage algorithm. |
| RCOG early pregnancy bleeding/pain | [Link](https://www.rcog.org.uk/for-the-public/browse-our-patient-information/bleeding-andor-pain-in-early-pregnancy/) | Escalation signs for bleeding or pain in early pregnancy, including heavy bleeding, severe abdominal pain, shoulder pain, dizziness, fainting. | United Kingdom; obstetric patient information. | Specific to early pregnancy bleeding/pain. |
| NICE fever in under 5s NG143 | [Link](https://www.nice.org.uk/guidance/NG143) | Clinical guideline for assessing feverish illness in children under 5. | United Kingdom; clinical guideline. | Designed for clinical assessment, not direct-to-consumer AI messaging. |
| NICE traffic-light table | [Link](https://www.nice.org.uk/guidance/ng143/resources/support-for-education-and-learning-educational-resource-traffic-light-table-pdf-6960664333) | Green/amber/red risk features for fever in under-5 children. | United Kingdom; NICE educational resource. | Pediatric fever-specific; some signs require clinical observation or measurement. |
| NHS serious illness in baby/toddler | [Link](https://www.nhs.uk/baby/health/is-your-baby-or-toddler-seriously-ill/) | Public warning signs and routing for serious illness in babies and toddlers. | United Kingdom/NHS public guidance. | UK care routes; age-specific. |
| healthdirect serious illness in babies and children | [Link](https://www.healthdirect.gov.au/symptoms-of-serious-illness-in-babies-and-children) | Child warning signs and emergency triggers, including drowsiness, breathing difficulty, blue/pale skin, seizure, non-fading rash, fever in under 3 months. | Australia. | Australian emergency number and health system; pediatric focus. |
| 988 Lifeline | [Link](https://988lifeline.org/) | 24/7 mental health crisis and emotional distress support by call, text, or chat. | United States; national crisis line. | US-specific number; international equivalents vary. |
| 988 Lifeline: Help Someone Else | [Link](https://988lifeline.org/help-someone-else/) | Warning signs, direct/nonjudgmental conversation, connection to help, and practical safety steps. | United States; crisis support. | Written for people helping someone else, not an AI product specification. |
| NIMH suicide warning signs | [Link](https://www.nimh.nih.gov/health/publications/warning-signs-of-suicide) | Warning signs and instruction to seek help quickly, including 988. | United States public health research agency. | US route; signs are not a predictive algorithm. |
| NICE self-harm NG225 | [Link](https://www.nice.org.uk/guidance/ng225) | Self-harm assessment, management, prevention of recurrence, and cautions around risk tools. | United Kingdom; clinical guideline. | Clinical guideline; not written as consumer self-triage copy. |
| NHS England: Staying safe from suicide | [Link](https://www.england.nhs.uk/long-read/staying-safe-from-suicide/) | Implementation guidance emphasizing psychosocial assessment, safety formulation/planning, and not using global low/medium/high suicide risk stratification to predict future harm. | England; clinical service implementation. | Service-provider oriented; not a direct app design standard. |
| WHO suicide-prevention media resource | [Link](https://www.who.int/publications/i/item/9789240076846) | Responsible communication about suicide; harmful and protective effects of framing. | Global; WHO communication guidance. | Media-focused, not digital triage-specific. |
| CDC CERC manual | [Link](https://www.cdc.gov/cerc/php/cerc-manual/index.html) | Evidence-based crisis and emergency risk communication framework. | United States public health, broadly applicable communication framework. | Designed for organizational public communication, not individualized AI triage. |
| CDC Clear Communication Index | [Link](https://www.cdc.gov/ccindex/index.html) | Research-based criteria for understandable public communication materials. | United States public health communication. | Scores materials, not triage accuracy. |
| CDC Clear Communication Index user guide | [Link](https://www.cdc.gov/ccindex/tool/index.html) | Practical scoring guidance: main message, common words, active voice, action steps, knowns/unknowns, risk explanation. | United States public health communication. | Communication quality tool, not clinical escalation framework. |
| BJGP safety-netting literature review | [Link](https://bjgp.org/content/69/678/e70) | Safety-netting definition and components: uncertainty, red flags, future appointments, timely reassessment. | Primary care; United Kingdom literature context. | Clinical consultation literature; translation to consumer AI requires design decisions. |
| BMJ Quality & Safety safety-netting communication | [Link](https://pmc.ncbi.nlm.nih.gov/articles/PMC9234415/) | Tailored advice, practical self-care/reconsultation information, checking understanding, documentation. | Primary care; qualitative/communication research. | Focuses on GP consultations, not automated check-ins. |
| NIHR Evidence: safety-netting | [Link](https://evidence.nihr.ac.uk/alert/safety-netting-in-general-practice-manage-uncertain-diagnoses/) | Safety-netting for uncertain diagnoses and timely follow-up. | United Kingdom evidence summary. | Secondary summary; not a full protocol. |
| BMJ 2015 symptom checker evaluation | [Link](https://www.bmj.com/content/351/bmj.h3480) | Diagnostic and triage performance of 23 symptom checkers using clinical vignettes. | International online symptom-checker market at time of study. | Vignette-based; older market snapshot; not specific to LLM-based interfaces. |
| BMJ Open 2019 systematic review | [Link](https://bmjopen.bmj.com/content/9/8/e027743) | Evidence on diagnostic accuracy, triage accuracy, patient safety, and user adherence for symptom checkers. | Systematic review of digital/online symptom checkers. | Finds limited evidence; heterogeneous studies. |
| npj Digital Medicine 2022 systematic review | [Link](https://www.nature.com/articles/s41746-022-00667-w) | Diagnostic and triage accuracy of symptom checkers; variation across tools. | Systematic review. | Accuracy estimates depend on study design and vignettes. |
| Review of symptom assessment applications, LLMs, and laypeople | [Link](https://pmc.ncbi.nlm.nih.gov/articles/PMC11937345/) | Comparative self-triage accuracy across symptom assessment applications, LLMs, and laypeople. | Recent systematic review including newer AI context. | Literature remains heterogeneous; conclusions are not product-specific. |

## Decision-neutral findings

### Decision question 1: Do-not-diagnose boundaries

**Affected components:** C10 Safety & Governance Gate; check-in response generator; provenance/source-linking layer; response-routing contract.

Public digital triage services provide a directly relevant boundary pattern: they ask symptom questions and route users to an appropriate care setting while explicitly stating that they do not diagnose. NHS 111 online says it uses a question flow and that users will not receive a diagnosis, but will find out what help they need ([NHS 111 online](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/how-nhs-111-online-works/)). healthdirect says its Symptom Checker can advise whether to see a doctor or care for oneself, but cannot provide a diagnosis and is not a substitute for professional care ([healthdirect Symptom Checker](https://www.healthdirect.gov.au/symptom-checker)). Ontario's Health811 listings distinguish symptom assessment and nurse advice from diagnosis, medication renewal, emergency care, and in-person assessment ([211 Ontario Health811](https://211ontario.ca/service/97619356/ontario-ministry-of-health-health811/)).

The sources therefore support a factual distinction between **disposition statements** and **diagnostic conclusions**. Disposition statements include routing language such as self-care, pharmacist, clinician, urgent care, emergency department, or emergency number; diagnostic conclusions include statements that the user has a named condition, a probability of disease, or a condition-specific treatment plan. That distinction appears in NHS 111, healthdirect, and Health811 service descriptions, but none of those public pages expose all internal thresholds or governance logic ([NHS 111 online](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/how-nhs-111-online-works/), [Australian Government: healthdirect Symptom Checker](https://www.health.gov.au/resources/apps-and-tools/healthdirect-symptom-checker), [Ontario seniors guide](https://www.ontario.ca/document/guide-programs-and-services-seniors/health-and-well-being)).

Regulatory sources do not create one universal product boundary, but they identify factors that matter: intended use, medical purpose, specificity of output, user type, reliance, transparency of basis, and whether the function gives treatment suggestions. FDA's CDS guidance and FAQ describe criteria for non-device CDS, including recommendation/option framing and the user's ability to review the basis for a recommendation, while noting that failing the criteria does not automatically settle device status ([FDA CDS guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software), [FDA CDS FAQ](https://www.fda.gov/medical-devices/software-medical-device-samd/clinical-decision-support-software-frequently-asked-questions-faqs)). FDA's device software page describes enforcement discretion for some patient self-management functions that do not provide specific treatment suggestions ([FDA device software functions](https://www.fda.gov/medical-devices/digital-health-center-excellence/device-software-functions-including-mobile-medical-applications)). MHRA and EU sources similarly turn on intended purpose, medical-device qualification, and classification ([MHRA Software and AI as a Medical Device](https://www.gov.uk/government/publications/software-and-artificial-intelligence-ai-as-a-medical-device/software-and-artificial-intelligence-ai-as-a-medical-device), [MHRA intended-purpose guidance](https://www.gov.uk/government/publications/crafting-an-intended-purpose-in-the-context-of-software-as-a-medical-device-samd), [EU MDCG 2019-11 Rev.1](https://health.ec.europa.eu/document/download/b45335c5-1679-4c71-a91c-fc7a4d37f12b_en?filename=mdcg_2019_11_en.pdf)).

For C10, the evidence points to boundary dimensions the gate would have to police if the product remains non-diagnostic: no assertion that the user has a disease, no disease probability, no instruction to start/stop/change medication, no substitution for clinician judgment, no hidden basis for an escalation, and no unsupported certainty. The same evidence leaves open legal and product choices about whether condition names may be mentioned as public-health warning-sign labels, such as "stroke warning signs" or "heart attack symptoms," when the message is still framed as urgent routing rather than a diagnosis of the user ([CDC stroke signs](https://www.cdc.gov/stroke/signs-symptoms/index.html), [American Heart Association symptoms](https://www.heart.org/en/about-us/heart-attack-and-stroke-symptoms)).

### Decision question 2: Never-alarm language constraints

**Affected components:** C10 language controls; response templates; escalation copy; mental-health crisis copy; source-linking and uncertainty statements.

Crisis communication sources frame effective escalation language as accurate, credible, empathetic, respectful, and action-oriented. CDC's CERC manual describes crisis and emergency risk communication as an evidence-based framework for emergency communication ([CDC CERC manual](https://www.cdc.gov/cerc/php/cerc-manual/index.html)). CDC's Clear Communication Index emphasizes one main message, common words, active voice, a specific call to action, risk explanation, and explicit communication about what is known and not known ([CDC Clear Communication Index](https://www.cdc.gov/ccindex/index.html), [CDC user guide](https://www.cdc.gov/ccindex/tool/index.html)). These sources are not product-specific, but they are directly relevant to C10 tone and phrasing constraints.

Safety-netting literature adds that uncertainty should be communicated with a plan, not with vague reassurance. The BJGP review describes safety netting as communication of uncertainty, red flags, future appointments, and timely reassessment ([BJGP](https://bjgp.org/content/69/678/e70)). BMJ Quality & Safety work emphasizes practical self-care and reconsultation advice, checking understanding, and tailoring to personal circumstances ([BMJ Quality & Safety / PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9234415/)). NIHR Evidence describes safety-netting as particularly relevant when diagnoses are uncertain and when patients need to know when to recontact services ([NIHR Evidence](https://evidence.nihr.ac.uk/alert/safety-netting-in-general-practice-manage-uncertain-diagnoses/)).

Mental-health crisis sources distinguish calmness from vagueness. The 988 Lifeline states that help is available 24/7 by call, text, or chat for mental health struggles, emotional distress, substance or alcohol concerns, and needing someone to talk to ([988 Lifeline](https://988lifeline.org/)). Its Help Someone Else guidance encourages direct, matter-of-fact, nonjudgmental communication; listening; avoiding shock; and connecting the person to help ([988 Help Someone Else](https://988lifeline.org/help-someone-else/)). WHO's suicide communication resource states that suicide-related communication can either increase harm or support prevention depending on framing, and emphasizes prevention, help, and recovery framing ([WHO](https://www.who.int/publications/i/item/9789240076846)). NICE and NHS England caution against prediction-style suicide risk stratification and emphasize psychosocial assessment, safety planning, and clear communication ([NICE NG225](https://www.nice.org.uk/guidance/ng225), [NHS England](https://www.england.nhs.uk/long-read/staying-safe-from-suicide/)).

As a decision-neutral option space, the evidence identifies language dimensions rather than a single mandated script: whether messages use one main action or multiple alternatives; whether uncertainty is stated as "I cannot tell what is causing this from here" versus stronger language; whether escalation messages name public warning signs; whether the message includes a source link inline or after the action; and how firm the action verb becomes at emergency thresholds. The evidence consistently treats catastrophic language, unsupported certainty, hidden rationale, false reassurance, and vague "monitor it" language without a recontact plan as risky communication patterns, but it does not define one universal copy rule for a consumer AI check-in.

### Decision question 3: Escalation criteria and tiers

**Affected components:** check-in question model; escalation-tier criteria; C10 red-flag detection; special-population handling; mental-health crisis branch; routing contract.

Existing public services use tiered dispositions, but the number of tiers varies. NHS 111 online includes outcomes such as self-care, pharmacist, dentist or optician, GP, nurse callback, urgent treatment centre, mental health support, and A&E or urgent referral ([NHS 111 online](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/how-nhs-111-online-works/)). healthdirect frames outcomes as self-care, doctor, hospital, or ambulance/emergency ([Australian Government: healthdirect Symptom Checker](https://www.health.gov.au/resources/apps-and-tools/healthdirect-symptom-checker)). NICE's pediatric fever guidance uses a green/amber/red traffic-light structure to separate lower, intermediate, and high-risk features in children under 5 ([NICE traffic-light table](https://www.nice.org.uk/guidance/ng143/resources/support-for-education-and-learning-educational-resource-traffic-light-table-pdf-6960664333)).

General emergency criteria in the consulted sources include trouble breathing, chest pain, confusion or trouble waking, fainting, severe or sudden pain, severe abdominal pain, uncontrolled bleeding, poisoning, severe injury, sudden weakness or vision change, and suicidal or homicidal feelings ([MedlinePlus](https://medlineplus.gov/ency/article/001927.htm)). NHS 999 guidance groups life-threatening emergencies around major accidents, suspected stroke, heart attack, and other situations where immediate emergency response is needed ([NHS 999](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-call-999/)). These are broad warning-sign frameworks, not precise automated thresholds.

Condition-specific warning signs create candidate red-flag inputs for C10 without making the product diagnostic. Stroke warning signs include sudden face drooping, arm weakness, speech trouble, vision trouble, dizziness or loss of balance, confusion, and sudden severe headache, with CDC advising emergency action and note of symptom onset time ([CDC stroke signs](https://www.cdc.gov/stroke/signs-symptoms/index.html)). Heart attack warning signs include chest discomfort lasting more than a few minutes or coming and going, upper body discomfort, shortness of breath, cold sweat, nausea, and lightheadedness ([American Heart Association](https://www.heart.org/en/about-us/heart-attack-and-stroke-symptoms)). Sepsis warning signs include confusion or disorientation, shortness of breath, high heart rate or weak pulse, fever/shivering/feeling very cold, clammy or sweaty skin, and extreme pain or discomfort ([CDC sepsis](https://www.cdc.gov/sepsis/about/index.html)). Severe allergic reaction/anaphylaxis signs include airway swelling or trouble breathing, wheeze, weak or rapid pulse, low blood pressure, dizziness or fainting, and widespread skin symptoms; Mayo Clinic directs emergency medical help for a severe allergic reaction even after epinephrine use ([Mayo Clinic](https://www.mayoclinic.org/diseases-conditions/anaphylaxis/symptoms-causes/syc-20351468)).

Special populations use different thresholds. CDC's HEAR HER campaign treats pregnancy and the year after delivery as a special period for urgent maternal warning signs and advises immediate medical care for warning signs such as persistent or worsening headache, dizziness or fainting, vision changes, fever, extreme swelling of hands or face, and thoughts of harming self or baby ([CDC maternal warning signs](https://www.cdc.gov/hearher/maternal-warning-signs/index.html)). CDC also advises telling the provider about current or recent pregnancy when seeking care ([CDC pregnant/postpartum guidance](https://www.cdc.gov/hearher/pregnant-postpartum/index.html)). RCOG identifies heavy bleeding, severe abdominal pain, shoulder pain, dizziness, and fainting in early pregnancy bleeding/pain as escalation signs ([RCOG](https://www.rcog.org.uk/for-the-public/browse-our-patient-information/bleeding-andor-pain-in-early-pregnancy/)).

Pediatric criteria differ from adult criteria. NICE's traffic-light table for feverish illness in children under 5 includes red high-risk features such as pale/mottled/ashen/blue skin, no response to social cues, inability to wake or stay awake, weak/high-pitched/continuous cry, grunting, severe breathing signs, reduced skin turgor, fever of 38 C or more in infants under 3 months, non-blanching rash, neck stiffness, bulging fontanelle, status epilepticus, focal neurological signs, and focal seizures ([NICE traffic-light table](https://www.nice.org.uk/guidance/ng143/resources/support-for-education-and-learning-educational-resource-traffic-light-table-pdf-6960664333)). NHS public guidance for babies and toddlers tells caregivers to trust instincts and lists serious illness warning signs including very high or very low temperature, listlessness, breathing difficulty, blue/pale/blotchy/ashen skin, difficulty waking, inconsolable crying, green vomit, poor feeding, and dry nappies; it lists 999 triggers such as stopping breathing, not waking, a non-fading rash, serious injury, and anaphylaxis ([NHS baby/toddler serious illness](https://www.nhs.uk/baby/health/is-your-baby-or-toddler-seriously-ill/)). healthdirect gives similar emergency triggers for children, including drowsiness, breathing difficulty, pale/blotchy/blue skin, seizure, non-fading rash, and fever in babies under 3 months ([healthdirect children](https://www.healthdirect.gov.au/symptoms-of-serious-illness-in-babies-and-children)).

Mental-health crisis criteria are not reducible to a predictive score in the consulted NICE/NHS England sources. NIMH lists suicide warning signs such as talking about wanting to die, feeling trapped or like a burden, making a plan or researching ways to die, withdrawing, saying goodbye, giving away possessions, dangerous risk-taking, mood swings, and changes in sleep, eating, or substance use, with immediate help-seeking especially when signs are new or increased ([NIMH](https://www.nimh.nih.gov/health/publications/warning-signs-of-suicide)). NICE and NHS England caution against using risk tools or global low/medium/high risk stratification to predict future suicide or self-harm or to decide treatment/discharge, emphasizing psychosocial assessment and safety planning instead ([NICE NG225](https://www.nice.org.uk/guidance/ng225), [NHS England](https://www.england.nhs.uk/long-read/staying-safe-from-suicide/)).

The check-in question model is implicated by these criteria because several red flags require knowing time course, suddenness, severity, age, pregnancy/postpartum status, child age, mental safety, breathing, consciousness, chest discomfort, neurological change, bleeding, rash behavior, and whether symptoms are worsening. Public digital triage services show one-question-at-a-time flows and sometimes one-main-symptom constraints, but the full internal logic is not public ([NHS 111 online](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/how-nhs-111-online-works/), [healthdirect Symptom Checker](https://www.healthdirect.gov.au/symptom-checker)).

### Decision question 4: Response routing

**Affected components:** response-routing contract; emergency branch; seek-care branch; self-care branch; special-population branch; source-linking layer; localization/location handling.

The consulted services use at least three broad route classes: self-care, contact or see a clinician/service, and emergency now. NHS 111 online says safe self-care outcomes include home-care advice; other outcomes include GP, pharmacy, nurse callback, urgent treatment centre, A&E, mental health support, and other services ([NHS 111 online](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/how-nhs-111-online-works/)). healthdirect's government page describes outcomes as self-care, seeing a doctor, going to hospital, or calling an ambulance, with local service finding ([Australian Government](https://www.health.gov.au/resources/apps-and-tools/healthdirect-symptom-checker)). Ontario describes Health811 as non-emergency access to nurses and health information, while emergency situations route to 911 ([Ontario Health811](https://211ontario.ca/service/97619356/ontario-ministry-of-health-health811/), [Ontario seniors guide](https://www.ontario.ca/document/guide-programs-and-services-seniors/health-and-well-being)).

Emergency-now routing is consistently tied to life-threatening warning signs and local emergency systems. NHS uses 999 in the UK context ([NHS 999](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-call-999/)); CDC stroke guidance uses 911 in the US context and advises not driving oneself to the hospital ([CDC stroke signs](https://www.cdc.gov/stroke/signs-symptoms/index.html)); healthdirect and Australian government pages use 000 in Australia ([Australian Government](https://www.health.gov.au/resources/apps-and-tools/healthdirect-symptom-checker), [healthdirect children](https://www.healthdirect.gov.au/symptoms-of-serious-illness-in-babies-and-children)); and 988 crisis sources use call/text/chat 988 for mental health crisis and emotional distress in the US ([988 Lifeline](https://988lifeline.org/)). These differences make localization part of the routing contract rather than a copy-only problem.

Seek-care routing in public services includes both urgent and routine clinician contact. NHS 111 online can route to nurse callback with a specified timeframe, GP, urgent treatment centre, mental health support, or A&E depending on answers ([NHS 111 online](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/how-nhs-111-online-works/)). healthdirect routes to doctor, hospital, or ambulance/emergency and helps find local services ([Australian Government](https://www.health.gov.au/resources/apps-and-tools/healthdirect-symptom-checker)). Ontario Health811 routes to nurse advice, self-care, health practitioner recommendation, or community resources ([Ontario seniors guide](https://www.ontario.ca/document/guide-programs-and-services-seniors/health-and-well-being)). These sources show a route taxonomy, but not a single shared set of timeframes.

Self-care routing is presented by these sources as bounded by safety-netting. NHS 111 says it will give home-care advice where it is safe to look after oneself ([NHS 111 online](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/how-nhs-111-online-works/)). Safety-netting literature describes self-care and reconsultation advice as needing red flags, expected course or uncertainty, when and how to seek further help, and attention to personal circumstances ([BJGP](https://bjgp.org/content/69/678/e70), [BMJ Quality & Safety / PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9234415/), [NIHR Evidence](https://evidence.nihr.ac.uk/alert/safety-netting-in-general-practice-manage-uncertain-diagnoses/)).

Special-population routing is a separate contract issue because ordinary adult self-care thresholds may not apply. CDC applies maternal warning-sign guidance during pregnancy and for one year postpartum and says to tell the provider about current or recent pregnancy ([CDC maternal warning signs](https://www.cdc.gov/hearher/maternal-warning-signs/index.html), [CDC pregnant/postpartum](https://www.cdc.gov/hearher/pregnant-postpartum/index.html)). NICE, NHS, and healthdirect pediatric sources distinguish infants and children, including specific thresholds for infants under 3 months with fever and warning signs that require emergency help ([NICE traffic-light table](https://www.nice.org.uk/guidance/ng143/resources/support-for-education-and-learning-educational-resource-traffic-light-table-pdf-6960664333), [NHS baby/toddler serious illness](https://www.nhs.uk/baby/health/is-your-baby-or-toddler-seriously-ill/), [healthdirect children](https://www.healthdirect.gov.au/symptoms-of-serious-illness-in-babies-and-children)). Mental-health crisis routing includes 988 in the US and emergency services when there is imminent danger; NICE/NHS England emphasize psychosocial assessment and safety planning rather than global risk prediction ([988 Lifeline](https://988lifeline.org/), [NICE NG225](https://www.nice.org.uk/guidance/ng225), [NHS England](https://www.england.nhs.uk/long-read/staying-safe-from-suicide/)).

Evidence on symptom checkers introduces a safety constraint for any routing contract. The BMJ 2015 audit, BMJ Open 2019 systematic review, npj Digital Medicine 2022 review, and more recent review of symptom assessment applications and LLMs all report variable performance and limited real-world safety evidence ([BMJ 2015](https://www.bmj.com/content/351/bmj.h3480), [BMJ Open 2019](https://bmjopen.bmj.com/content/9/8/e027743), [npj Digital Medicine 2022](https://www.nature.com/articles/s41746-022-00667-w), [PMC review](https://pmc.ncbi.nlm.nih.gov/articles/PMC11937345/)). This evidence does not determine the correct WellBe routing thresholds, but it makes under-triage, over-triage, and post-routing user adherence material design questions for C10 and the check-in model.

## Tradeoffs and open questions

### 1. Tier granularity

A three-part taxonomy such as self-care, seek care, and emergency now is simpler to explain and gate. A more granular taxonomy such as self-care, pharmacist, primary care, urgent care, nurse callback, emergency department, emergency number, and mental-health crisis line is closer to NHS 111-style disposition routing ([NHS 111 online](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/how-nhs-111-online-works/)). Simpler tiers reduce user and implementation complexity but may blur clinically meaningful distinctions. Granular tiers may provide more precise next steps but require more localization, governance, and maintenance.

### 2. Conservative escalation versus specificity

A conservative threshold may reduce under-triage risk for serious deterioration but can increase over-triage, unnecessary urgent-care use, and user anxiety. A more specific threshold may reduce unnecessary escalation but raises the risk of missing atypical or under-described emergencies. Symptom-checker evidence shows substantial variability in triage accuracy, and reviews emphasize limited real-world safety evidence ([BMJ 2015](https://www.bmj.com/content/351/bmj.h3480), [BMJ Open 2019](https://bmjopen.bmj.com/content/9/8/e027743), [npj Digital Medicine 2022](https://www.nature.com/articles/s41746-022-00667-w)).

### 3. Question depth and user burden

A short check-in supports low-friction capture but may miss information needed to detect red flags: age, suddenness, severity, pregnancy/postpartum status, pediatric age, breathing, consciousness, neurological changes, chest discomfort, bleeding, fever, rash behavior, and self-harm thoughts. A deeper flow can gather more safety-critical context, as public triage services do through question flows, but deeper flows introduce abandonment risk and may feel less personal-first ([NHS 111 online](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-use-111/how-nhs-111-online-works/), [healthdirect Symptom Checker](https://www.healthdirect.gov.au/symptom-checker)).

### 4. Jurisdiction and localization

Emergency and crisis routes differ by jurisdiction: 999 in the UK, 911 in the US and Canada, 000 in Australia, and 988 for US mental-health crisis support ([NHS 999](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-call-999/), [CDC stroke signs](https://www.cdc.gov/stroke/signs-symptoms/index.html), [Australian Government](https://www.health.gov.au/resources/apps-and-tools/healthdirect-symptom-checker), [988 Lifeline](https://988lifeline.org/)). Localized routing can make escalation more actionable, but it requires reliable location handling, emergency-number mapping, service availability, and maintenance. Generic routing avoids some localization risk but can be less useful during a crisis.

### 5. Use of condition names in a non-diagnostic product

Public warning-sign sources often use condition labels such as stroke, heart attack, sepsis, anaphylaxis, and suicide warning signs ([CDC stroke signs](https://www.cdc.gov/stroke/signs-symptoms/index.html), [American Heart Association](https://www.heart.org/en/about-us/heart-attack-and-stroke-symptoms), [CDC sepsis](https://www.cdc.gov/sepsis/about/index.html), [Mayo Clinic anaphylaxis](https://www.mayoclinic.org/diseases-conditions/anaphylaxis/symptoms-causes/syc-20351468), [NIMH](https://www.nimh.nih.gov/health/publications/warning-signs-of-suicide)). WellBe's non-diagnostic identity creates an open boundary question: whether the safety gate permits source-linked public warning-sign labels, prohibits all condition labels in user-specific responses, or permits condition labels only as non-user-specific source context. The tradeoff is between clarity and regulatory/product-boundary risk.

### 6. Calm language versus urgency

CERC, clear-communication, and safety-netting sources all support clear action, empathy, and uncertainty with a plan ([CDC CERC](https://www.cdc.gov/cerc/php/cerc-manual/index.html), [CDC Clear Communication Index](https://www.cdc.gov/ccindex/index.html), [BJGP](https://bjgp.org/content/69/678/e70)). Emergency red-flag sources sometimes require firm action language, such as calling emergency services immediately ([CDC stroke signs](https://www.cdc.gov/stroke/signs-symptoms/index.html), [NHS 999](https://www.nhs.uk/nhs-services/urgent-and-emergency-care-services/when-to-call-999/)). The open design problem is how firm an escalation can be while remaining calm, non-alarming, and user-controlled.

### 7. Mental-health crisis handling

Keyword-triggered crisis routing may capture explicit self-harm intent quickly, but mental-health sources caution against over-reliance on risk scoring and global low/medium/high stratification to predict future suicide or self-harm ([NICE NG225](https://www.nice.org.uk/guidance/ng225), [NHS England](https://www.england.nhs.uk/long-read/staying-safe-from-suicide/)). A more conversational safety branch may better reflect psychosocial assessment and safety-planning principles, but it increases complexity and risk of mishandling imminent danger. The routing contract also has to separate emotional distress support, self-harm thoughts, imminent danger, substance-related crisis, and local emergency routes ([988 Lifeline](https://988lifeline.org/), [NIMH](https://www.nimh.nih.gov/health/publications/warning-signs-of-suicide)).

### 8. Special-population detection and data minimization

Pregnancy/postpartum status and child age materially change escalation thresholds, as shown by CDC HEAR HER, RCOG, NICE, NHS, and healthdirect pediatric sources ([CDC maternal warning signs](https://www.cdc.gov/hearher/maternal-warning-signs/index.html), [RCOG](https://www.rcog.org.uk/for-the-public/browse-our-patient-information/bleeding-andor-pain-in-early-pregnancy/), [NICE traffic-light table](https://www.nice.org.uk/guidance/ng143/resources/support-for-education-and-learning-educational-resource-traffic-light-table-pdf-6960664333), [NHS baby/toddler serious illness](https://www.nhs.uk/baby/health/is-your-baby-or-toddler-seriously-ill/)). Asking for these details can improve escalation sensitivity but collects sensitive information and increases cognitive load. Not asking may preserve simplicity and privacy but can under-detect higher-risk contexts.

### 9. Source-linked public guidance versus licensed clinical pathways

Public sources are transparent and linkable, but many are warning-sign lists rather than complete triage algorithms. Licensed or clinically governed pathways, such as NHS Pathways, offer a stronger governance pattern but are not fully public and may carry licensing, localization, clinical-safety, and regulatory obligations ([NHS Pathways](https://digital.nhs.uk/services/nhs-pathways)). The maintainers have to decide how much routing logic can rest on public warning-sign sources versus governed clinical content.

### 10. Generative AI personalization versus deterministic safety templates

Generative language can personalize the check-in response to the user's words and WellBe memory context, but it creates risks around diagnosis leakage, tone drift, missing citations, and variable escalation phrasing. Deterministic templates and ruled routing can make C10 enforcement easier but may feel less responsive and may not capture nuanced user context. The regulatory and symptom-checker evidence does not resolve this architecture choice; it identifies why provenance, intended-use control, and routing validation matter ([FDA CDS guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software), [BMJ Open 2019](https://bmjopen.bmj.com/content/9/8/e027743), [PMC review](https://pmc.ncbi.nlm.nih.gov/articles/PMC11937345/)).

### 11. Validation, monitoring, and decision records

The consulted accuracy literature is heterogeneous and often vignette-based, while safety-netting literature is mainly clinical-consultation oriented. This leaves open what validation evidence is sufficient before release: vignette testing, clinician review, retrospective simulations, adversarial prompt testing, special-population test suites, localization tests, post-release monitoring, and documentation of false-negative and false-positive incidents. These choices affect both safety governance and the product's non-diagnostic positioning ([BMJ 2015](https://www.bmj.com/content/351/bmj.h3480), [BMJ Open 2019](https://bmjopen.bmj.com/content/9/8/e027743), [npj Digital Medicine 2022](https://www.nature.com/articles/s41746-022-00667-w), [BJGP](https://bjgp.org/content/69/678/e70)).

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
