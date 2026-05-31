# WellBe feature backlog

|feature_id|feature_name|phase|primary_user|problem_solved|evidence_strength|risk_level|status|
|---|---|---|---|---|---|---|---|
|WB2-F001|Health Thread core|MVP|patient|Symptoms, visits, tests and questions are scattered instead of one unresolved concern.|strong|high|core build|
|WB2-F002|Story Memory intake|MVP|patient|Patient concern, fear, timeline, and daily impact are lost in short visits or single-symptom forms.|strong|medium|core build|
|WB2-F003|Baseline change and function impact capture|MVP|patient|Clinical records often miss 'what changed from normal for me'.|strong|medium|core build|
|WB2-F004|Evidence traceability layer 2.0|MVP|patient|AI summaries lose trust when they cannot show sources.|strong|medium|core build|
|WB2-F005|Health Thread timeline and evidence graph|MVP|patient|People cannot easily show the sequence of symptoms, tests, visits and changes.|strong|medium|core build|
|WB2-F006|Normal-test safety net|MVP|patient|Normal results are treated as closure while symptoms persist.|strong|high|core build|
|WB2-F007|Personal pending result tracker|MVP|patient|Users do not know what test is pending, when to expect it, or whom to contact.|strong|high|core build|
|WB2-F008|Referral lifecycle tracker|MVP|patient|Referral placed is confused with referral completed.|strong|high|core build|
|WB2-F009|Post-visit plan checker|MVP|patient|Uncertainty, pending tests, unresolved symptoms and return precautions disappear after the visit.|strong/some|medium-high|core build|
|WB2-F010|Patient correction loop|MVP|patient|Wrong, missing, or unaddressed concerns persist and compound.|strong|medium|core build|
|WB2-F011|User-controlled clinician visit packet|MVP|patient|Clinicians need concise relevant history earlier, but cannot read a giant notebook.|strong|high|core build|
|WB2-F012|Repeat-visit and persistence view|Near-term|patient|Return visits are treated as isolated rather than one unresolved issue.|strong|high|near-term|
|WB2-F013|Missing context checklist|Near-term|patient|Family history, medication access, prior tests, out-of-system care and patient theory are often absent.|some/strong|medium|near-term|
|WB2-F014|Patient-held record import|Near-term|patient|Out-of-system care, old records, photos, PDFs, SMS, and low-resource records do not travel.|regional/strong|medium-high|near-term|
|WB2-F015|Access and equity memory|Near-term|patient|Language, transport, cost, disability, trust and cultural safety barriers are omitted though they affect identification.|strong/regional|high|near-term|
|WB2-F016|Lab trend and personal baseline explorer|Near-term|patient|Slow changes and personal baselines get missed when values are reviewed one at a time.|some|high|near-term with caution|
|WB2-F017|Medication and access clue capture|Near-term|patient|Medication interruption, affordability and access can explain deterioration or diagnostic confusion.|some|medium-high|near-term|
|WB2-F018|Note/document delta view|Near-term/Later|patient|Copied-forward notes and unchanged summaries hide evolving symptoms or plan gaps.|some|medium-high|later|
|WB2-F019|Deterioration check-in and escalation guidance|Near-term|patient|Patient/family concern about worsening can be hard to communicate and escalate.|strong/regional|high|near-term|
|WB2-F020|Personal Responsibility Memory ledger|MVP/Near-term|patient|Open loops have no personal memory: who to call, by when, and what remains unresolved.|strong|high|core build|
|WB2-F021|Safe research and explanation mode|Near-term|patient|Users research symptoms anyway, but need source-linked, non-diagnostic education tied to their thread.|internal + safety supported|medium-high|near-term|
|WB2-F022|Personal experiment guardrails|Later|patient|Users test lifestyle theories but may make unsafe changes without structure.|needs more evidence|medium-high|later|
|WB2-F023|Trend-over-noise PGHD summarizer|Near-term|patient|Wearable and self-tracking data can overwhelm rather than clarify.|some|medium|near-term|
|WB2-F024|Scoped share link / export|MVP|patient|The user needs to share the right context without handing over everything.|strong product identity|high|core build|
|WB2-F025|Care-team comment mode|Later|patient|Clinician feedback can improve memory accuracy, but clinician workflow integration creates risk.|some|high|later|
|WB2-F026|Low-resource / CHW / SMS mode|Regional|patient|Low-resource and rural systems need offline, paper/SMS, referral-backup-aware workflows.|regional|high|regional adaptation|
|WB2-F027|Bias/misattribution reflection prompt|Caution/Later|patient|Symptoms can be minimized due to age, gender, weight, mental-health label, race, language, or disability.|strong problem / cautious product|high|defer until safety review|
|WB2-F028|Workload-aware alert/worklist mode|Defer|clinician|Clinicians need prioritized action, not more alerts.|problem strong / feature caution|high|defer|
|WB2-F029|Cross-specialty pattern map|Later|patient|Specialists see one slice and unresolved patterns across specialties are lost.|some|high|later|
|WB2-F030|Decision and uncertainty memory|Later|patient|What was considered, ruled out, uncertain, and what should trigger reassessment is not remembered.|strong concept / implementation caution|high|later|
|WB2-F031|Doctor discovery as pathway support|Later|patient|Users may need the right specialty/pathway after a referral gap or wrong specialty loop.|some|medium-high|later|
|WB2-F032|Cross-patient comparison sandbox|Avoid for MVP|patient|Users may ask how their recovery compares to similar cases.|needs more evidence|very high|avoid for MVP|
|WB2-F033|Knowledge graph + visualization|Post-MVP|patient|Health entities (symptoms, tests, visits, referrals) exist in isolation — no structural view of how they connect.|strong|medium|post-mvp build|
|WB2-F034|Mood and energy logging|MVP|patient|Emotional and energy state are early signals of unresolved physical issues and are dismissed as subjective.|strong|medium|core build|
|WB2-F035|Myth Buster — personal theory evaluator|Post-MVP|patient|Patient theories about their own health are dismissed without structured evaluation against their own data and evidence.|strong|medium-high|post-mvp build|
|WB2-F036|Research Agent — external evidence lookup|Post-MVP|patient|Users research symptoms with ungrounded sources; they need source-linked evidence-graded external context tied to their thread.|product supported|medium-high|post-mvp build|
|WB2-F037|Environmental context ingestion|Post-MVP|patient|Environmental factors (weather, air quality, allergens, public health events, conflict proximity) affect health but are absent from the record.|strong for weather/AQ; opt-in for conflict|medium|post-mvp build|
|WB2-F038|Cross-device intelligence|Post-MVP|patient|Paired wearable devices can reveal asymmetric signals and drift patterns that single-device monitoring misses.|product supported|medium-high|post-mvp build|
|WB2-F039|Wearable integration|Post-MVP|patient|Longitudinal biometric data from devices is not connected to symptom threads preventing baseline-aware pattern analysis.|product supported|medium|post-mvp build|
|WB2-F040|Health-adaptive UI|Post-MVP|patient|UI provides no ambient signal about current health state; triage level is buried in a list rather than reflected in the experience.|product supported|low|post-mvp build|
|WB2-F041|Medical institution integration (user-pull FHIR)|Deferred|patient|Clinical records held by institutions are disconnected from the patient's personal health memory.|strong problem / complex solution|very high|deferred — compliance review required|
|WB2-F042|Intelligence engines (pattern temporal confounder contradiction missing data)|Post-MVP|patient|Patterns in health data go undetected because no system connects signals across time domains and sources for the individual patient.|strong|high|post-mvp build|
|WB2-F043|Live Metrics Safety Monitor|Post-MVP|patient|Wearable/device trends crossing personal baselines alongside concerning symptoms are not turned into safe, low-alarm escalation guidance.|product supported|high|post-mvp build (gated)|
|WB2-F044|Clinician Case Investigation Workspace|Post-MVP|patient + clinician (grant-scoped)|Clinicians cannot efficiently investigate an unresolved case longitudinally; the individual benefits from a better-prepared, consent-scoped clinician view.|product supported|high|post-mvp build (gated)|
|WB2-F045|Shared Health Thread workspace|Post-MVP|patient + caregiver/clinician (grant-scoped)|Patient and clinician views are stronger together; a patient-controlled collaboration space around one thread is missing.|product supported|high|post-mvp build (gated)|
|WB2-F046|Institution Continuity Intelligence|Deferred|patient (aggregate, consented)|Care loops break at the system level; institutions need continuity intelligence without default access to individual data.|product supported|very high|deferred — governance review required|
|WB2-F047|Research Sandbox / cohort comparison|Deferred|patient (opt-in) + researcher|Cross-patient/cohort comparison can help individuals but is high-risk; needs explicit opt-in and protocol governance.|needs more evidence|very high|deferred — supersedes F032 framing|
|WB2-F048|Full Health Context Summary|Post-MVP|patient|A user-owned summary across all data (not only clinician notes) is missing; expands the visit packet into the complete personal story.|strong|medium-high|post-mvp build|

## Product modules (P1–P10) → feature mapping

The expanded vision groups capabilities into product modules. The personal core (P1) stays MVP and unchanged; all new workspaces/objects are Post-MVP or Deferred behind governance gates.

| Module | Description | Maps to |
|---|---|---|
| P1 Individual Health Memory Workspace | Personal timeline, symptoms, documents, theories, visit prep | F001–F011 (MVP, unchanged) |
| P2 Self Ongoing Investigation | Track one concern over time as an Investigation | NEW — Investigation object (C14) |
| P3 Clinician Case Investigation Workspace | Consent-scoped longitudinal case view + evidence/theory board | F044 |
| P4 Shared Patient–Clinician Thread | Patient-controlled shared investigation space | F045 (extends F024, F025) |
| P5 Theory Evaluator | Evaluate a theory against own data + evidence | F035 + Theory object (C15) |
| P6 External Evidence Watch | Monitor trusted external sources by relevance | F036 + External Evidence Graph (C16) |
| P7 Live Metrics Safety Monitor | Safe escalation from baseline deviations | F043 (pulls F039/F038/F019) |
| P8 Institution Continuity Intelligence | Aggregate, consented care-loop analytics | F046 (reframes F028) |
| P9 Cohort / Research Sandbox | Opt-in cross-patient comparison under governance | F047 (supersedes F032 framing) |
| P10 Visit Packet / Full Health Context Summary | Provenance-backed summary across all data | F048 (expands F011) |
