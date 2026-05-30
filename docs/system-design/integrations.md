# Integrations

External integrations extend the Personal Data Factory with data from devices, institutions, and the environment. All integrations are user-initiated, user-controlled, and user-revocable. The system never pulls data automatically without consent.

---

## 1. Wearable Integration

**Purpose:** Connect wearable devices (watches, rings, phones) to import health metrics as longitudinal context for the Data Factory and Intelligence Engines.

**Supported metric types:** heart rate, HRV, sleep stages and duration, SpO2, steps, activity, skin temperature, respiratory rate, blood glucose (CGM), stress index.

**How it works:**
1. User connects device or service (OAuth / vendor API)
2. WellBe imports historical data within the user-defined consent scope
3. New data syncs on schedule or on-demand
4. Metrics are stored as `RawContextEvent` objects with device provenance
5. Processing pipeline extracts structured metrics, computes personal baselines
6. Intelligence engines can query metric history for pattern detection

**Privacy:** Location stored at city-level only. Raw biometric streams are not shared with any third party. User can revoke device access and delete imported data at any time.

**Prerequisite for:** Cross-device intelligence, Lab trend / personal baseline explorer (WB2-F016), Pattern detection.

---

## 2. Cross-Device Intelligence

**Purpose:** Detect health signals from paired devices on different body sides or contexts — baseline learning, drift detection, asymmetry alerts, and cross-device validation.

**How it works:**
1. User registers multiple devices and their placement (left wrist, right wrist, ring, phone)
2. Baseline period runs (minimum: 14 days) before any intelligence is surfaced
3. After baseline: drift detection compares device readings over time
4. Asymmetry detection flags persistent differences between paired-side devices
5. Cross-device validation uses agreement between devices to increase or decrease confidence in a signal

**Safety constraints:**
- Asymmetry detection never implies diagnosis — framed as "persistent difference detected"
- Device malfunction is distinguished from health signal using consistency and metadata checks
- No insight surfaces until baseline period completes
- All asymmetry alerts carry confidence level and "discuss with provider" prompt if sustained

**Depends on:** Wearable integration.

---

## 3. Medical Institution Integration

**Purpose:** Allow the user to pull their own records from hospitals, clinics, labs, and patient portals directly into their WellBe context — user-initiated, not institution-initiated.

**Design principle (from vision guardrails):** The user is the data controller. Institutions are sources, not systems of record for WellBe. WellBe is never a node in an institutional workflow.

**How it works (FHIR patient access):**
1. User selects a supported institution or patient portal
2. WellBe initiates a FHIR R4 patient-access OAuth flow — the user authenticates with the institution directly
3. WellBe receives a scoped access token for that user's records only
4. User reviews and approves which resource types to import (conditions, medications, lab results, immunizations, clinical notes, imaging reports)
5. Imported records are stored as `RawContextEvent` objects with institution provenance
6. Processing pipeline extracts structured facts and links them to Health Threads

**What is never done:**
- WellBe never receives access to other patients' data
- Institutions cannot see WellBe data without explicit user share
- WellBe does not write back to institutional EHR systems
- Institutional access tokens are stored encrypted and scoped to user-approved resource types only

**Supported standards:** HL7 FHIR R4, SMART on FHIR patient-access profile.

**Phase:** Deferred — requires jurisdiction-specific compliance review, FHIR vendor integration work, and user consent model validation before implementation.

---

## 4. Environmental Context Ingestion

**Purpose:** Capture external environmental and social context that affects health — correlating it with thread data to reveal non-obvious influences.

**Context types:**

| Type | Source | Privacy |
|---|---|---|
| Weather | Open-Meteo or equivalent public API | City-level location only |
| Air quality & pollution | OpenAQ or equivalent | City-level |
| Pollen / allergen index | Public weather APIs | City-level |
| UV index | Weather API | City-level |
| Public health alerts | WHO / national health agency RSS | No personal location needed |
| Conflict / civil unrest proximity | Opt-in only — ACLED or equivalent public dataset | User explicitly enables; city-level resolution |
| Major news events affecting health | Opt-in only — curated public health news feeds | User explicitly enables |

**How it works:**
1. User enables environmental context (off by default)
2. User selects which context types to include (each independently toggled)
3. WellBe fetches data at city-level granularity on a daily schedule
4. Environmental events stored as `environmental_event` graph nodes
5. Pattern Detection Engine correlates environmental signals with thread entities

**Privacy hard rules:**
- Precise coordinates are never stored
- City-level location is used for API queries only — not stored as a persistent field
- Conflict/news context is explicitly opt-in with a clear explanation of the data source before enabling

**Examples of correlations this enables:**
- High-pollen days correlated with respiratory symptom episodes
- Air quality index spikes correlated with headache onset
- Conflict-period sleep disruption visible alongside mood and energy logs

---

## Integration architecture

All integrations write through the same ingestion path:

```
External source
    ↓
Ingestion Layer (source-type-specific adapter)
    ↓
Raw Context Vault (immutable RawContextEvent with source provenance)
    ↓
Processing Pipeline (entity extraction, quality scoring)
    ↓
Multi-index + Knowledge Graph
    ↓
Health Thread Engine + Intelligence Engines
```

No integration bypasses the Data Factory. Every external fact is traceable to its source, timestamped at ingestion, and carries a verification status (official / user-confirmed / unverified).
