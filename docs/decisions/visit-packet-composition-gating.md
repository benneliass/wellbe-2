# Decision: Visit Packet composition, source-linking, scoped-share/revocation, and C10 gating

**Status:** Proposed  
**Date opened:** 2026-06-17  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-160  
**Blocks:** WEL-68 [Build Visit Packet generator with source-linked summary and scoped share/export]

---

## Question

For the user-controlled clinician Visit Packet (Home pill `prep`):
1. **Composition** — what is included in a packet, and how is every claim source-linked back to its evidence (C5) so there are no orphan claims?
2. **Scoped share/export + revocation** (C1) — what is the grant model for sharing/exporting a packet (audience, purpose, duration), and what are the exact revocation semantics?
3. **C10 gating** — how does the generated summary pass the Safety & Governance Gate (do-not-diagnose, panic-language, provenance, bias) before it can be shared?

## Context

Touches C7 (Health Thread Engine), C5 (Evidence & Provenance), C10 (Safety & Governance Gate), C1 (Trust & Consent) — see `docs/architecture/component-map.md`. The packet is the first WellBe output that leaves the personal core for a third party, so a wrong decision on share scoping, revocation, or C10 gating is a safety/privacy regression that is expensive or impossible to reverse once a packet has been shared externally. Personal-first and grant-scoped guardrails apply (`.cursor/rules/wellbe-vision-guardrails.mdc`).

## Research provided

> Agent-run LLM research (model: gpt-5.5, date: 2026-06-17, run id: resp_0110518a1803a6e1006a32f9f38eb8819c933353f2df932123, web_search: on). Recorded verbatim per research-protocol.mdc Section I. Not synthesised by the agent.

## 1. External patterns to examine

### A. Packet content / source-linked claims — C7 + C5

- **Patient-summary document pattern:** HL7’s International Patient Summary (IPS) frames a patient summary as a **minimal, non-exhaustive, clinically relevant snapshot** of essential health information, originally for unplanned cross-border care but also usable for planned/local care. IPS explicitly treats the summary as a FHIR **Bundle** organized through a **Composition** resource. ([hl7.org](https://www.hl7.org/fhir/uv/ips/))  
- **Minimum clinical sections pattern:** IPS identifies current **allergies/intolerances, medications, and problems** as the minimum structural expectation for all IPS documents, while allowing other sections when relevant. It also recognizes that not all lifetime data is relevant at summary-generation time. ([hl7.org](https://www.hl7.org/fhir/uv/ips/Generation-and-Data-Inclusion.html))  
- **Empty / unavailable data pattern:** IPS distinguishes between omitted optional sections and required sections where data is missing. For required sections, it uses `Composition.section.emptyReason` or explicit “known absence” statements rather than leaving ambiguity. ([hl7.org](https://www.hl7.org/fhir/uv/ips/Empty-Sections-and-Missing-Data.html))  
- **Narrative plus structured-entry pattern:** IPS requires human-readable section text for populated sections and uses `Composition.section.entry` references to structured resources where available. FHIR Composition also permits narrative-only sections, but the IPS pattern favors entries where data exists. ([hl7.org](https://www.hl7.org/fhir/uv/ips/Empty-Sections-and-Missing-Data.html))  
- **Provenance / no-orphan-claim pattern:** FHIR Provenance records the “who, what, when” behind resources and the entities/processes involved in producing them; it supports assessments of authenticity, trust, reliability, and reproducibility. The Provenance resource can point to any generated or updated resource and can reference source entities using roles such as `source`, `derivation`, `quotation`, or `revision`. ([hl7.org](https://hl7.org/fhir/R4/provenance.html))  
- **Document metadata pattern:** FHIR DocumentReference separates metadata about a document from the document itself and explicitly notes that there can be two provenance layers: provenance of the referenced document and provenance of the DocumentReference record. ([hl7.org](https://hl7.org/fhir/R4/DocumentReference.html))  
- **Patient-generated data pattern:** HL7’s draft Personal Health Record / PGHD guidance describes patient-generated health data as data created, recorded, or gathered by patients or caregivers outside clinical settings, and maps such data to FHIR resources such as Observation and related resources. It is a continuous build, so its stability is lower than published normative/stable standards. ([build.fhir.org](https://build.fhir.org/ig/HL7/personal-health-record-format-ig/en/pghd.html?utm_source=openai))  

### B. Scoped share/export + revocation — C1 + C5

- **Consent-grant structure pattern:** FHIR Consent models healthcare consent directives with policy context, grantor/grantee concepts, provisions, actors, purposes of use, data objects, date ranges, and references back to the source consent directive. It also states that enforcement is outside the Consent resource and typically depends on access-control mechanisms such as OAuth, UMA, XACML, RBAC, or ABAC. ([hl7.org](https://hl7.org/fhir/r4/Consent.html))  
- **HIPAA authorization-element pattern:** U.S. HIPAA authorization rules require, among other elements, a specific description of information disclosed, who may disclose, who may receive, purpose, expiration date/event, signature/date, revocation notice, and a redisclosure warning; the authorization must be in plain language. ([law.cornell.edu](https://www.law.cornell.edu/cfr/text/45/164.508))  
- **Revocation semantics pattern:** HIPAA permits revocation of an authorization in writing, except to the extent the covered entity has already acted in reliance on it. This establishes a common legal pattern: revocation can stop future reliance/disclosure, but it does not automatically unwind prior disclosures. ([law.cornell.edu](https://www.law.cornell.edu/cfr/text/45/164.508))  
- **Defective / inactive grant pattern:** HIPAA treats authorizations as invalid if the expiration date/event has passed, required elements are incomplete, the authorization is known to have been revoked, or material information is false. ([law.cornell.edu](https://www.law.cornell.edu/cfr/text/45/164.508))  
- **FHIR security-label / purpose-of-use pattern:** FHIR security labels can express confidentiality, sensitivity, purpose of use, and handling caveats on resources or bundles. The specification states that labels derive meaning from a broader policy/consent framework and that recipient enforcement depends on the applicable trust framework. ([hl7.org](https://www.hl7.org/fhir/R4/security-labels.html?utm_source=openai))  
- **SMART scoped-token pattern:** SMART App Launch uses OAuth scopes to request specific FHIR resource permissions; the specification cautions that wildcard scopes can expose more data than needed and encourages clients to request only the permissions they need. ([hl7.org](https://hl7.org/fhir/smart-app-launch/1.0.0/scopes-and-launch-context/index.html?utm_source=openai))  
- **SMART Health Links pattern:** SMART Health Links lets a sharing user choose what to share, whether to require a passcode, and whether the link expires. The protocol supports FHIR JSON payloads, passcode-protected links, expiration hints, encrypted files, short-lived file URLs, and a server response of `404` when a link is no longer active. ([docs.smarthealthit.org](https://docs.smarthealthit.org/smart-health-links/spec/?utm_source=openai))  
- **Export-boundary pattern:** HHS guidance on patient access, apps, and APIs says that once health information is transmitted to a third-party app at the individual’s direction, the covered entity is generally not liable under HIPAA for the app’s subsequent use/disclosure; HHS also notes that health information entered into a non-HIPAA-regulated mobile app is generally not PHI under HIPAA. ([hhs.gov](https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/access-right-health-apps-apis/index.html?utm_source=openai))  

### C. Safety gate for generated summaries — C10 + C5 + C7

- **Non-diagnostic / no-directive pattern:** FDA’s CDS guidance distinguishes software that provides information/options from software that gives specific preventive, diagnostic, or treatment outputs or directives. It also flags specific follow-up directives, time-critical alarms, treatment plans, and risk scores as examples that do not satisfy the “recommendations rather than directives” criterion. ([fda.gov](https://www.fda.gov/medical-devices/digital-health-center-excellence/step-6-software-function-intended-provide-clinical-decision-support))  
- **Basis-for-review pattern:** FDA’s CDS guidance says software intended to let healthcare professionals independently review the basis of recommendations should identify intended use, required inputs, relevance/data-quality requirements, algorithm logic/methods, data relied upon, validation information, and patient-specific knowns/unknowns. ([fda.gov](https://www.fda.gov/medical-devices/digital-health-center-excellence/step-6-software-function-intended-provide-clinical-decision-support))  
- **AI governance pattern:** WHO’s AI-for-health principles include human autonomy, safety, transparency/explainability/intelligibility, accountability, inclusiveness/equity, and responsive/sustainable use. WHO specifically warns about bias, patient-safety risks, cybersecurity risks, and overestimating AI benefits. ([who.int](https://www.who.int/news/item/28-06-2021-who-issues-first-global-report-on-ai-in-health-and-six-guiding-principles-for-its-design-and-use))  
- **AI trustworthiness pattern:** NIST’s AI RMF frames trustworthy AI characteristics as valid/reliable, safe, secure/resilient, accountable/transparent, explainable/interpretable, privacy-enhanced, and fair with harmful bias managed. NIST also notes that tradeoffs among trustworthiness characteristics are common. ([nist.gov](https://www.nist.gov/node/1674681))  
- **Plain-language / calm communication pattern:** CDC health-literacy guidance says health information should be accurate, accessible, and actionable, and that plain-language practices are not “dumbing down” or distorting the science. ([cdc.gov](https://www.cdc.gov/health-literacy/php/develop-materials/develop-test-materials.html))  
- **Patient appointment-prep pattern:** AHRQ’s QuestionBuilder helps patients and caregivers prepare questions for medical visits, organize appointment-specific concerns, and keep data under user control; its FAQ notes that data entered in the app stays on the user’s device unless the user uses email/calendar features, in which case those providers may store copies. ([ahrq.gov](https://www.ahrq.gov/questions/question-builder/index.html?utm_source=openai))  
- **Patient-authored pre-visit narrative pattern:** OpenNotes’ OurNotes asks patients to compose interval history, goals, and questions before a visit, using the “subjective” component of SOAP as a familiar clinical-communication pattern while keeping the patient contribution distinct from clinician-authored documentation. ([opennotes.org](https://www.opennotes.org/ournotes/?utm_source=openai))  

---

## 2. Evidence inventory

1. **HL7 FHIR IPS Implementation Guide v2.0.0** — URL via citation. Covers IPS purpose, scope, minimal/non-exhaustive summary framing, FHIR Bundle/Composition organization, current published version context. Jurisdiction/context: international HL7 standard, trial-use. Limitation: designed around IPS use cases, not specifically a patient-controlled AI-generated visit-prep packet. ([hl7.org](https://www.hl7.org/fhir/uv/ips/))  

2. **HL7 IPS “Generation and Data Inclusion”** — URL via citation. Covers `$summary`, `$docref`, Bundle/Composition generation, data inclusion, relevance filtering, minimum structural expectation for allergies/medications/problems. Context: HL7 IPS STU2. Limitation: does not define exact relevance rules for all implementations. ([hl7.org](https://www.hl7.org/fhir/uv/ips/Generation-and-Data-Inclusion.html))  

3. **HL7 IPS “Empty Sections and Missing Data”** — URL via citation. Covers required-section `emptyReason`, known absence, unavailable/not-asked/masked cases, human-readable section text. Context: HL7 IPS STU2. Limitation: focuses on IPS documents, not consumer-facing AI prose. ([hl7.org](https://www.hl7.org/fhir/uv/ips/Empty-Sections-and-Missing-Data.html))  

4. **FHIR Provenance R4** — URL via citation. Covers provenance target, agent, entity, activity, source/derivation/quotation/revision roles, trust/reproducibility rationale, W3C PROV alignment. Context: HL7 FHIR R4. Limitation: resource-level provenance; claim-level citation granularity is implementation-specific. ([hl7.org](https://hl7.org/fhir/R4/provenance.html))  

5. **US Core Basic Provenance** — URL via citation. Covers “last hop” provenance display and the idea that full provenance requires original creator plus intermediary actors. Context: U.S. FHIR implementation guidance. Limitation: focused on US Core exchange, not all source-chain details. ([hl7.org](https://www.hl7.org/fhir/us/core/STU6.1/basic-provenance.html))  

6. **FHIR DocumentReference R4** — URL via citation. Covers document metadata, document discovery/management, and distinction between provenance of the document and provenance of its reference. Context: HL7 FHIR R4. Limitation: metadata container; not a full share-policy model. ([hl7.org](https://hl7.org/fhir/R4/DocumentReference.html))  

7. **FHIR Composition R5** — URL via citation. Covers document author, attester, custodian, narrative-only allowance, subject/focus semantics. Context: HL7 FHIR R5. Limitation: R5 version may differ from R4 details used by IPS; useful mainly for document-composition concepts. ([fhir.hl7.org](https://fhir.hl7.org/fhir/composition.html))  

8. **FHIR Consent R4** — URL via citation. Covers consent directives, policy context, source consent references, partial consent representations, provisions, purpose-of-use, recipients, date range, and enforcement boundaries. Context: HL7 FHIR R4. Limitation: FHIR states enforcement is not included in the resource itself. ([hl7.org](https://hl7.org/fhir/r4/Consent.html))  

9. **45 CFR § 164.508 / HIPAA authorization rule** — URL via citation. Covers required authorization elements, revocation, expiration, redisclosure warning, plain-language requirement, invalid/defective authorization cases. Context: U.S. HIPAA covered-entity authorization law. Limitation: WellBe packet sharing may involve consumer-directed exports and non-covered-entity contexts; legal applicability depends on role and facts. ([law.cornell.edu](https://www.law.cornell.edu/cfr/text/45/164.508))  

10. **FHIR Security Labels R4/R5** — URL via citation. Covers purpose-of-use labels, confidentiality labels, handling caveats such as delete-after-use, and the dependence of labels on a broader trust framework. Context: HL7 FHIR security model. Limitation: labels do not enforce policy by themselves. ([hl7.org](https://www.hl7.org/fhir/R4/security-labels.html?utm_source=openai))  

11. **SMART App Launch Scopes** — URL via citation. Covers OAuth resource-level scopes, patient context, wildcard-scope overbreadth, and least-permission pattern. Context: SMART on FHIR. Limitation: app authorization pattern, not document-link export semantics. ([hl7.org](https://hl7.org/fhir/smart-app-launch/1.0.0/scopes-and-launch-context/index.html?utm_source=openai))  

12. **SMART Health Links specification** — URL via citation. Covers shareable links/QRs, manifest URL, encryption key, passcode flag, expiration hint, FHIR JSON files, short-lived file URLs, invalid/passcode handling, and inactive-link `404`. Context: SMART/HL7 ecosystem. Limitation: does not determine the policy meaning of already-downloaded copies. ([docs.smarthealthit.org](https://docs.smarthealthit.org/smart-health-links/spec/?utm_source=openai))  

13. **HHS HIPAA right-of-access / apps / APIs guidance** — URL via citation. Covers patient-directed transmission to apps and limits on covered-entity liability after transmission; distinguishes non-HIPAA-regulated apps. Context: U.S. HIPAA guidance. Limitation: does not define WellBe’s contractual or product duties outside HIPAA. ([hhs.gov](https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/access-right-health-apps-apis/index.html?utm_source=openai))  

14. **AHRQ QuestionBuilder and FAQ** — URL via citation. Covers patient appointment-prep workflow, question organization, optional email/calendar sharing, and local/user-controlled storage caveats. Context: U.S. patient-safety / health-communication resource. Limitation: question list, not a comprehensive clinical data packet. ([ahrq.gov](https://www.ahrq.gov/questions/question-builder/index.html?utm_source=openai))  

15. **OpenNotes OurNotes** — URL via citation. Covers patient-authored pre-visit interval history, goals, and questions, mapped to the subjective component of SOAP. Context: patient-clinician communication research initiative. Limitation: designed around portal/EHR submission, not sovereign personal-core export. ([opennotes.org](https://www.opennotes.org/ournotes/?utm_source=openai))  

16. **CDC health-literacy material-development guidance** — URL via citation. Covers accurate, accessible, actionable health information and plain-language framing. Context: U.S. public-health communication. Limitation: broad content guidance, not AI-specific. ([cdc.gov](https://www.cdc.gov/health-literacy/php/develop-materials/develop-test-materials.html))  

17. **WHO AI for health principles** — URL via citation. Covers autonomy, safety, transparency, accountability, inclusiveness/equity, bias, and patient-safety risks. Context: global AI health governance. Limitation: principles-level guidance, not implementation contract. ([who.int](https://www.who.int/news/item/28-06-2021-who-issues-first-global-report-on-ai-in-health-and-six-guiding-principles-for-its-design-and-use))  

18. **NIST AI Risk Management Framework FAQ** — URL via citation. Covers trustworthy AI characteristics and tradeoffs among trustworthiness properties. Context: U.S. voluntary AI risk framework. Limitation: not healthcare-specific and not a compliance safe harbor by itself. ([nist.gov](https://www.nist.gov/node/1674681))  

19. **FDA Clinical Decision Support digital-health guidance page** — URL via citation. Covers medical-information display, recommendations vs directives, patient/caregiver distinction, independent review of basis, and examples such as patient data summaries. Context: U.S. FDA digital-health policy. Limitation: regulatory classification depends on intended use and exact product behavior. ([fda.gov](https://www.fda.gov/medical-devices/digital-health-center-excellence/step-6-software-function-intended-provide-clinical-decision-support))  

20. **HL7 draft Personal Health Record / PGHD guidance** — URL via citation. Covers PGHD definition and FHIR mapping principles for patient-generated data. Context: HL7 continuous build / ballot content. Limitation: not an authorized final publication and subject to change. ([build.fhir.org](https://build.fhir.org/ig/HL7/personal-health-record-format-ig/en/pghd.html?utm_source=openai))  

---

## 3. Decision-neutral findings mapped to the decision questions and affected components

### Decision question 1: What is included in a packet and how is each claim source-linked so there are no orphan claims?

**Affected components:** C7 Health Thread Engine, C5 Evidence & Provenance, C10 Safety & Governance Gate.

- **External patient-summary standards separate “minimum core” from “relevant additional data.”** IPS treats the patient summary as minimal and non-exhaustive, with allergies/intolerances, medications, and problems as minimum structural expectations; it allows additional clinically relevant sections and recognizes that summary-generation may filter lifetime records for relevance. This maps to C7’s thread-to-packet composition question because the packet can be compared against established “core + relevant extras” summary patterns without treating IPS as a required product shape. ([hl7.org](https://www.hl7.org/fhir/uv/ips/))  

- **Clinical-summary standards preserve absence semantics rather than silently omitting required concepts.** IPS uses `emptyReason`, data-absent-reason extensions, and “known absence” patterns when data is unavailable, not asked, masked, or known absent. This maps to C5 because “no orphan claims” also includes avoiding implied claims from missing sections, such as implying “no allergy” when the real state is “not asked” or “unavailable.” ([hl7.org](https://www.hl7.org/fhir/uv/ips/Empty-Sections-and-Missing-Data.html))  

- **FHIR Composition supports sectioned documents with authorship, attestation, custodian, subject, and section entries.** Composition can contain narrative-only text, but IPS adds expectations for section text and structured entries where populated. This creates an external distinction between a human-readable summary and the underlying referenced structured resources. ([hl7.org](https://www.hl7.org/fhir/uv/ips/Empty-Sections-and-Missing-Data.html))  

- **FHIR Provenance supports resource-level source chains but does not by itself define claim-level citation UX.** Provenance can identify targets, agents, entities used, activity, timestamps, and roles such as `source`, `quotation`, `derivation`, and `revision`. The standard provides the machinery for traceability, while the claim-level rule “every generated sentence/claim must map to raw source” remains an implementation-level contract above base FHIR. ([hl7.org](https://hl7.org/fhir/R4/provenance.html))  

- **DocumentReference introduces a separate provenance layer for the packet artifact.** A generated packet may have provenance for the source data used inside it and separate provenance for the packet document/reference itself. This matters to C5 because a packet can be “generated from” raw sources while its exported PDF/link/document also has authorship, creation time, status, and custodian metadata. ([hl7.org](https://hl7.org/fhir/R4/DocumentReference.html))  

- **Patient-generated data is recognized as a distinct source class.** HL7 PGHD guidance defines PGHD as patient/caregiver-created or gathered data outside clinical settings, including logs, self-measured vitals, diet records, and symptom diaries. This maps to WellBe’s personal-first model because source labels may need to distinguish patient-authored statements, device readings, imported clinical records, AI-derived summaries, and transformed/normalized records. ([build.fhir.org](https://build.fhir.org/ig/HL7/personal-health-record-format-ig/en/pghd.html?utm_source=openai))  

- **Appointment-prep prior art emphasizes user questions, goals, symptoms, medicines, and concerns.** AHRQ’s patient-prep materials and QuestionBuilder focus on questions for the visit, symptoms/health history, medications, tests, procedures, and user-controlled sharing; OpenNotes OurNotes focuses on interval history, goals, and visit questions. These patterns are narrower than a clinical patient summary but relevant to a visit packet’s non-diagnostic, patient-to-clinician handoff role. ([ahrq.gov](https://www.ahrq.gov/questions/question-builder/index.html?utm_source=openai))  

### Decision question 2: What is the scoped share/export + revocation model?

**Affected components:** C1 Trust & Consent, C5 Evidence & Provenance, C10 Safety & Governance Gate.

- **External consent models commonly encode audience/recipient, purpose, duration, data scope, and source consent reference.** HIPAA authorization requires recipient, purpose, information scope, expiration, revocation notice, redisclosure warning, and plain language; FHIR Consent supports provisions for recipients/actors, purpose-of-use, data references, date ranges, and source-consent references. These map directly to C1 grant-shape fields. ([law.cornell.edu](https://www.law.cornell.edu/cfr/text/45/164.508))  

- **Revocation has two separate external meanings: access revocation and copy recall.** HIPAA’s authorization revocation stops future reliance except where the covered entity has already acted in reliance, which indicates that legal revocation does not necessarily invalidate prior disclosures. SMART Health Links can make a link inactive so future manifest requests fail, but the protocol does not by itself erase data already fetched or copied by a recipient. ([law.cornell.edu](https://www.law.cornell.edu/cfr/text/45/164.508))  

- **FHIR Consent explicitly separates consent representation from enforcement.** The FHIR Consent resource can express consent directives or metadata, but its text says enforcement is expected through other access-control methodologies. For C1, this means the grant object and the enforcement mechanism are externally recognized as separable layers. ([hl7.org](https://hl7.org/fhir/r4/Consent.html))  

- **SMART Health Links provide a concrete external pattern for time-boxed, passcode-protected link sharing.** The SHL payload includes a manifest URL, decryption key, optional expiration hint, passcode-required flag, label, and version; manifest responses can include FHIR JSON, and file locations are short-lived and may be one-time-use. If the SHLink is no longer active, the resource server returns `404`. ([docs.smarthealthit.org](https://docs.smarthealthit.org/smart-health-links/spec/?utm_source=openai))  

- **FHIR security labels and purpose-of-use codes can carry handling context but rely on downstream agreement.** FHIR labels can express purpose-of-use, confidentiality, and handling caveats; the specification says labels enable policy fragments to accompany data but are meaningful only within a wider security/trust framework. This maps to C1/C5 as metadata that can travel with the packet but not guarantee recipient behavior after export. ([hl7.org](https://www.hl7.org/fhir/R4/security-labels.html?utm_source=openai))  

- **SMART scopes show a least-permission pattern for API grants.** SMART warns that broad wildcard scopes can authorize more future data than the user expects and encourages requesting only needed scopes. This maps to packet-generation/export grants as an external analogue for exact scope boundaries. ([hl7.org](https://hl7.org/fhir/smart-app-launch/1.0.0/scopes-and-launch-context/index.html?utm_source=openai))  

- **User-controlled sharing prior art includes explicit copy-boundary warnings.** AHRQ’s QuestionBuilder FAQ says user-entered data remains on-device unless the user uses email/calendar features, in which case those account providers may store copies. HHS guidance similarly distinguishes a covered entity’s responsibilities from third-party app behavior after patient-directed transmission. These sources support treating “share within controlled link” and “export/copy into third-party systems” as distinct states. ([ahrq.gov](https://www.ahrq.gov/questions/question-builder/faqs.html?utm_source=openai))  

### Decision question 3: How does generated summary text pass C10 before it can be shared?

**Affected components:** C10 Safety & Governance Gate, C5 Evidence & Provenance, C7 Health Thread Engine, C1 Trust & Consent.

- **External CDS guidance distinguishes summaries/options from diagnostic or treatment directives.** FDA’s CDS materials include patient data reports/summaries as examples in the CDS context, but distinguish these from specific preventive, diagnostic, or treatment outputs/directives, time-critical alarms, treatment plans, follow-up directives, and disease risk scores. This maps to C10’s do-not-diagnose and never-alarm checks. ([fda.gov](https://www.fda.gov/medical-devices/digital-health-center-excellence/step-6-software-function-intended-provide-clinical-decision-support))  

- **FDA’s “basis for independent review” pattern aligns with source-linked summaries.** FDA describes independent review support as including input information, data quality requirements, algorithm logic/methods, data relied upon, validation information, and patient-specific knowns/unknowns. For C10/C5, this is external support for gating generated text against the evidence it relied on, rather than presenting unsupported conclusions. ([fda.gov](https://www.fda.gov/medical-devices/digital-health-center-excellence/step-6-software-function-intended-provide-clinical-decision-support))  

- **WHO and NIST both identify transparency, safety, accountability, bias/fairness, and human control as AI health risk controls.** WHO emphasizes human control of health-care systems and medical decisions, transparency/explainability, accountability, inclusiveness/equity, and patient-safety risks; NIST lists trustworthy AI characteristics including validity/reliability, safety, transparency/accountability, explainability, privacy, and harmful-bias management. These map to C10 categories for safety, provenance, and bias. ([who.int](https://www.who.int/news/item/28-06-2021-who-issues-first-global-report-on-ai-in-health-and-six-guiding-principles-for-its-design-and-use))  

- **CDC health-literacy guidance supports calm, plain, non-distorting language.** CDC frames effective health information as accurate, accessible, and actionable, and states that plain language should preserve scientific accuracy rather than distort it. This maps to C10 checks for calm language, non-alarmism, and comprehensibility. ([cdc.gov](https://www.cdc.gov/health-literacy/php/develop-materials/develop-test-materials.html))  

- **Patient-prep patterns keep the patient contribution distinct from clinician diagnosis.** AHRQ QuestionBuilder focuses on patient questions and preparation, while OurNotes asks patients to provide interval history, goals, and questions. Neither pattern turns patient-authored prep material into a clinician diagnosis. This supports a safety distinction between “what I noticed / what I want to ask / what sources show” and “what condition I have / what treatment I need.” ([ahrq.gov](https://www.ahrq.gov/questions/question-builder/index.html?utm_source=openai))  

- **Provenance gating has both raw-source and generated-artifact layers.** FHIR Provenance can record source entities and generating agents for resources, while DocumentReference can represent the generated packet document and its metadata. For C10, this means gate results could be associated with the generated packet artifact, while C5 claim links can remain attached to underlying source records. ([hl7.org](https://hl7.org/fhir/R4/provenance.html))  

---

## 4. Tradeoffs and open questions

### A. Packet inclusion scope

- **Option space:** A packet could mirror IPS-like core sections; focus narrowly on visit-prep questions/goals/symptoms; or combine a patient-prep layer with a source-backed health-summary layer. External standards show all three ingredients exist, but they do not define the exact WellBe packet boundary. ([hl7.org](https://www.hl7.org/fhir/uv/ips/))  
- **Risk if too broad:** Larger packets may include stale, irrelevant, or overly sensitive data; IPS notes that not all lifetime data is relevant at summary-generation time. ([hl7.org](https://www.hl7.org/fhir/uv/ips/Generation-and-Data-Inclusion.html))  
- **Risk if too narrow:** A packet that omits medications, allergies, or problems may diverge from common patient-summary expectations, even if it remains useful as a visit-prep artifact. ([hl7.org](https://www.hl7.org/fhir/uv/ips/Generation-and-Data-Inclusion.html))  
- **Open question:** Whether “required” packet fields mean “must include if known,” “must include with absence reason,” or “must be user-selectable but visibly omitted if deselected.” IPS provides missing-data mechanics but not this product policy. ([hl7.org](https://www.hl7.org/fhir/uv/ips/Empty-Sections-and-Missing-Data.html))  

### B. Claim-level provenance granularity

- **Option space:** Provenance can be tracked at packet level, section level, claim/sentence level, or source-resource level. FHIR Provenance supports resource-level provenance and source entities, but claim-level citation is an application-layer choice. ([hl7.org](https://hl7.org/fhir/R4/provenance.html))  
- **Risk if provenance is only packet-level:** A clinician or user may not be able to tell which raw source supports a specific generated statement. This would weaken the “no orphan claims” guardrail even if the packet has document-level provenance. ([hl7.org](https://hl7.org/fhir/R4/provenance.html))  
- **Risk if provenance is claim-level everywhere:** Fine-grained citation can increase implementation complexity, UI density, and failure modes when sources conflict or when one sentence summarizes many sources. FHIR does not prescribe a claim-level UX. ([hl7.org](https://hl7.org/fhir/R4/provenance.html))  
- **Open question:** How to represent generated inferences versus direct quotations, since FHIR Provenance has entity roles such as `quotation`, `source`, and `derivation` but does not decide product semantics for “AI-derived from source.” ([hl7.org](https://hl7.org/fhir/R4/provenance.html))  

### C. Missing data and known absence

- **Option space:** Missing data can be omitted, marked unavailable/not asked/masked, or represented as a known-absence clinical statement. IPS uses different mechanisms depending on requiredness, coding, and data type. ([hl7.org](https://www.hl7.org/fhir/uv/ips/Empty-Sections-and-Missing-Data.html))  
- **Risk if omitted silently:** The packet may imply that no issue exists when the source state is actually unknown or unavailable. ([hl7.org](https://www.hl7.org/fhir/uv/ips/Empty-Sections-and-Missing-Data.html))  
- **Risk if every unknown is surfaced:** The packet may become noisy or anxiety-producing, especially if many sections contain no relevant data. CDC’s health-literacy guidance emphasizes accessibility and actionability, which can conflict with exhaustive uncertainty display. ([cdc.gov](https://www.cdc.gov/health-literacy/php/develop-materials/develop-test-materials.html))  
- **Open question:** Which packet sections require explicit absence reasons, and which can be omitted without implying “none.”  

### D. Revocation semantics

- **Option space:** Revocation can invalidate future link access, revoke future API/token access, mark a grant inactive, log revocation, or attempt downstream copy recall by notice/request. SMART Health Links covers inactive links and short-lived URLs; HIPAA demonstrates that revocation generally does not undo prior reliance/disclosure. ([docs.smarthealthit.org](https://docs.smarthealthit.org/smart-health-links/spec/?utm_source=openai))  
- **Risk if revoke is presented as copy recall:** Users may believe already-exported PDFs, emails, screenshots, EHR uploads, or downloaded files are technically invalidated when external sources show that prior disclosures/copies commonly cannot be unwound automatically. ([law.cornell.edu](https://www.law.cornell.edu/cfr/text/45/164.508))  
- **Risk if revoke is presented only as link shutdown:** Users may underestimate that revocation can still be meaningful for future access, long-lived links, passcodes, dynamic manifests, and audit history. SMART Health Links explicitly supports no-longer-active link behavior. ([docs.smarthealthit.org](https://docs.smarthealthit.org/smart-health-links/spec/?utm_source=openai))  
- **Open question:** Whether WellBe’s grant model distinguishes “controlled link share,” “download/export,” “recipient copied,” and “recipient acknowledged handling caveats.”  

### E. Audience and purpose limitation

- **Option space:** Audience can be a named clinician, clinic, care team, any holder of a link, or a user-selected recipient class; purpose can be appointment preparation, treatment discussion, second opinion, caregiver review, or personal archive. HIPAA and FHIR Consent both include recipient and purpose concepts, while SMART Health Links may be link-holder based unless layered with app policy. ([law.cornell.edu](https://www.law.cornell.edu/cfr/text/45/164.508))  
- **Risk if audience is broad link-holder access:** A link model can be convenient but may not express a named audience unless the sharing application adds recipient controls. ([docs.smarthealthit.org](https://docs.smarthealthit.org/smart-health-links/spec/?utm_source=openai))  
- **Risk if audience is strictly named:** Strict recipient binding may reduce practical shareability in clinical workflows where front-desk staff, nurses, or covering clinicians need access. FHIR Consent supports actors/classes, but enforcement depends on the access-control layer. ([hl7.org](https://hl7.org/fhir/r4/Consent.html))  
- **Open question:** Whether “audience” is enforced cryptographically, by authenticated access, by link possession/passcode, by policy labels, or by user-visible intent only.  

### F. C10 gate strictness

- **Option space:** The gate can block any diagnostic/treatment wording; allow neutral restatement of source diagnoses already present in records; allow patient-authored concerns/questions; or allow clinician-facing summaries with clear basis and limitations. FDA’s CDS guidance distinguishes summaries/options from directives and emphasizes independent review of basis. ([fda.gov](https://www.fda.gov/medical-devices/digital-health-center-excellence/step-6-software-function-intended-provide-clinical-decision-support))  
- **Risk if too permissive:** Generated text may drift into diagnosis, treatment direction, risk scoring, urgency escalation, or time-critical alarm language. FDA’s examples identify these as sensitive categories. ([fda.gov](https://www.fda.gov/medical-devices/digital-health-center-excellence/step-6-software-function-intended-provide-clinical-decision-support))  
- **Risk if too restrictive:** The packet may fail to communicate clinically useful, source-backed facts such as “source record lists asthma” or “patient reports chest tightness after exertion,” even when those are not new diagnoses. ([fda.gov](https://www.fda.gov/medical-devices/digital-health-center-excellence/step-6-software-function-intended-provide-clinical-decision-support))  
- **Open question:** How C10 distinguishes: direct source fact, patient-reported observation, generated synthesis, generated inference, diagnostic label from source record, and new diagnostic label generated by AI.  

### G. Bias and equity review

- **Option space:** Bias checks can focus on language, source coverage, missing-data warnings, differential uncertainty, or model-output evaluation. WHO and NIST both identify bias/fairness, inclusiveness, transparency, and safety as AI-health governance concerns. ([who.int](https://www.who.int/news/item/28-06-2021-who-issues-first-global-report-on-ai-in-health-and-six-guiding-principles-for-its-design-and-use))  
- **Risk if limited to banned words:** Bias can arise from missing data, overconfidence, inappropriate inference, or unequal source quality, not only from wording. WHO specifically notes that systems trained primarily on high-income-country data may not perform well in other settings. ([who.int](https://www.who.int/news/item/28-06-2021-who-issues-first-global-report-on-ai-in-health-and-six-guiding-principles-for-its-design-and-use))  
- **Risk if bias review is too broad for MVP:** A broad fairness program can delay packet generation if not scoped to the concrete output risks at share time. NIST notes that AI trustworthiness characteristics involve tradeoffs and may vary by setting. ([nist.gov](https://www.nist.gov/node/1674681))  
- **Open question:** Which bias checks are mandatory pre-share gates versus post-hoc monitoring/audit signals.

---

## Approaches considered

_Grounded only in the recorded research above (IPS, FHIR Provenance/Consent/Composition/DocumentReference, SMART Health Links, HIPAA §164.508, FDA CDS, WHO, NIST, CDC, AHRQ, OpenNotes)._

**Q1 — Packet composition + source-linking**
- **A1a. IPS-style core summary:** mirror IPS minimum sections (allergies, medications, problems) + relevant extras. Pro: aligns with an established cross-care summary expectation. Con: skews toward a clinical record rather than a patient-prep artifact; risks stale/over-broad inclusion (IPS notes not all lifetime data is relevant).
- **A1b. Visit-prep-only artifact:** questions, goals, symptoms, current meds (AHRQ QuestionBuilder / OpenNotes OurNotes pattern). Pro: clearly patient-authored, non-diagnostic, low blast radius. Con: may omit allergies/meds/problems a clinician expects.
- **A1c. Two-layer packet:** a patient-prep layer (questions/goals/observations) + an optional source-backed summary layer, with claim-level provenance and explicit absence semantics (IPS `emptyReason`/known-absence). Pro: combines both patterns; preserves "no orphan claims" including no implied "none" from missing data. Con: highest implementation complexity (claim-level citation UX).

**Q2 — Scoped share/export + revocation**
- **A2a. Link-holder share (SMART Health Links pattern):** time-boxed, passcode-protected link; inactive link returns 404. Pro: concrete, proven, convenient. Con: audience is link-holder, not a named recipient, unless layered with recipient controls.
- **A2b. Named-audience grant (FHIR Consent / HIPAA §164.508 fields):** recipient, purpose, info scope, expiration, revocation notice, redisclosure warning. Pro: explicit, least-permission, maps cleanly to C1 grant fields. Con: strict recipient binding can reduce real-world shareability (front-desk/covering clinician).
- **A2c. Two-state model:** distinguish "controlled link share" (revocable future access) from "export/copy" (cannot be unwound), with revocation honestly scoped to future access + audit, never presented as copy-recall (HIPAA reliance exception; SHL inactive-link). Pro: honest, calm, matches legal reality. Con: requires clear UI to convey that exported copies persist.

**Q3 — C10 gating of generated text**
- **A3a. Banned-word/diagnosis blocklist:** simplest gate. Pro: cheap. Con: WHO/NIST note bias/overconfidence/missing-data harms aren't only wording; too weak alone.
- **A3b. Source-provenance gate (FDA "basis for independent review"):** every shareable claim must map to source evidence; block unsupported conclusions; classify each statement (direct source fact / patient-reported observation / generated synthesis / generated inference / source-record diagnosis / new AI diagnostic label) and block the last category. Pro: enforces "no orphan claims" + do-not-diagnose precisely; supports independent review. Con: needs the claim-classification + provenance plumbing from Q1c.
- **A3c. Layered gate:** A3b + calm/plain-language check (CDC) + a bias/equity pre-share subset (WHO/NIST) with the rest as post-hoc audit. Pro: most complete; scopes bias work to share-time risk. Con: largest gate to build for MVP.

## Decision

_Proposed by agent; awaiting user approval._

**Q1:** Adopt **A1c (two-layer packet)** — a patient-prep layer plus an optional, user-selectable source-backed summary layer, with **claim-level** source links and **explicit absence semantics** (no silent omission that implies "none"). Required fields mean "include if known, else show an explicit absence reason"; user may deselect, but deselection is visibly marked, not silently dropped.

**Q2:** Adopt **A2b + A2c** — the grant object carries named recipient, purpose, info scope, and expiration (HIPAA/FHIR-Consent field set), shared via a time-boxed, passcode-protected, revocable link (SHL pattern). Revocation invalidates **future** link access and is audit-logged; the UI states plainly that already-exported/downloaded copies cannot be recalled. "Export/copy" is a distinct, clearly-warned state from "controlled link share."

**Q3:** Adopt **A3b for MVP, with A3c as the target** — C10 blocks any shareable claim not mapped to source evidence and any new AI-generated diagnostic/treatment/risk/alarm language, using a per-statement classification; a calm/plain-language check is included at share time; broader bias/equity checks start as post-hoc audit and graduate to pre-share gates over time.

## Trade-offs accepted

<!-- Filled after approval. -->

## Implementation notes

<!-- Filled after approval. -->

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
