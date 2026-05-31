# Intelligence Engines

Eight engines transform raw Health Thread data into insight. They run on the Knowledge Graph and power the **Investigate** step of the operating loop (Capture → Connect → **Investigate** → Clarify → Close → Correct), feeding the Clarify step.

They operate silently (except the Live-Metric Safety Monitor, which may surface low-alarm escalation guidance). Their outputs surface as thread annotations, investigation prompts, and missing-context checklists — not as proactive alerts that could cause alert fatigue.

## Engine risk tiers

Every engine carries a safety risk tier; higher tiers get stronger controls and always pass the Safety & Governance Gate (C10) before any user-facing output.

| Engine | Risk tier |
|---|---|
| Pattern Detection, Temporal Analysis, Missing Data | Lower |
| Confounder Detection, Contradiction Resolution | Medium |
| Theory Evaluator | Medium-high |
| External Research Relevance | High |
| Live-Metric Escalation | High |
| Cross-patient comparison (Research Sandbox) | Very high |

---

## 1. Pattern Detection Engine

**Purpose:** Find recurring structures in a user's data — co-occurrence, compound triggers, and repeating episode clusters.

**Inputs:** Health Thread entities, Knowledge Graph edges, timestamped symptom episodes, mood states, wearable metrics, environmental events.

**Outputs:** `Pattern` objects attached to threads: pattern type, frequency, confidence, contributing entities, date range, supporting source IDs.

**Trigger:** Runs after indexing completes for new data. Also on-demand when user enters investigation mode.

**Examples:**
- "Chest tightness episodes cluster within 4 hours of high-stress days."
- "Migraine episodes co-occur with low sleep + low activity days."
- "GI symptoms repeat on days following medication dose changes."

**Safety:** Patterns are surfaced as observations, not conclusions. Language: "this pattern appears in your data" — never "X causes Y."

---

## 2. Temporal Analysis Engine

**Purpose:** Determine the *order* of events, not just their co-occurrence. Time-lagged correlations and temporal precedence validation.

**Inputs:** Timestamped entities, Knowledge Graph `temporally_precedes` edges, Health Thread timelines.

**Outputs:** Temporal relationship annotations: "A consistently precedes B by N days/hours," confidence interval, source count.

**Trigger:** On-demand and after significant new data is added to a thread.

**Examples:**
- "Sleep quality drops 2–3 days before each migraine episode, not after."
- "Fatigue onset precedes the elevated inflammatory marker by approximately 5 days."

**Safety:** Temporal precedence is not causation. All outputs carry explicit "correlation only" framing. No clinical ordering claims.

---

## 3. Confounder Detection Engine

**Purpose:** When pattern A→B is detected, identify whether a third variable C explains both — preventing spurious causal claims.

**Inputs:** Detected patterns from Pattern Detection Engine, full entity graph, known confounders (menstrual cycle, seasonal patterns, medication cycles, life events).

**Outputs:** Confounder candidates attached to pattern objects: "Pattern X may be explained by C (confidence: N%)."

**Trigger:** Runs automatically after any pattern is created or updated.

**Examples:**
- "Low activity correlates with your headaches — but both may be driven by your menstrual cycle."
- "Sleep disruption correlates with joint pain — but both increase on high-air-pollution days."

**Safety:** Critical guard against the system presenting misleading patterns. Any pattern with an identified high-confidence confounder is marked `needs_context` and shown with the confounder candidate before the raw pattern.

---

## 4. Missing Data Engine

**Purpose:** Surface gaps in context that, if filled, would meaningfully clarify a thread or resolve a pattern ambiguity.

**Inputs:** Active Health Threads, Knowledge Graph, detected patterns, known data types (sleep, mood, labs, visits, medications).

**Outputs:** `DataGap` objects linked to threads: what is missing, why it matters, how to add it (log it, upload a document, import from a source).

**Trigger:** Runs when a pattern is inconclusive and after any thread reaches a "Clarify" step review.

**Examples:**
- "You have 6 months of headache logs but no sleep quality data from that period. Sleep data would clarify the sleep-headache connection."
- "Your abdominal pain thread has no record of what you ate during episodes. Food log data would help evaluate a dietary trigger."

**Safety:** Data gap prompts are framed as opportunities, not alarms. They never imply a diagnosis would be revealed by the missing data.

---

## 5. Contradiction Resolution Engine

**Purpose:** Find conflicting signals in the user's data and surface them as preserved contradictions rather than silently discarding one side.

**Inputs:** Derived facts, clinical summaries, user-entered data, patient corrections, document-extracted facts.

**Outputs:** `Contradiction` objects: the two conflicting claims, their sources, confidence levels, and a resolution status (unresolved / user-explained / updated-by-new-data).

**Trigger:** Runs after any new document is ingested or any clinical summary is processed. Also on-demand.

**Examples:**
- "Your GP's note says symptoms started in March. Your own logs show entries from January. This is unresolved — you can add a correction."
- "Your discharge summary says the scan was normal. Your own record shows a finding was noted and follow-up was recommended. These conflict."

**Resolution rule:** User-authored accounts of subjective symptoms rank higher than institutional summaries. Clinical objective findings rank higher than inferred system outputs. Contradictions are never auto-resolved — they require user action or new evidence.

**Safety:** Contradictions are presented neutrally. The engine does not determine which side is "true" — it preserves both until the user or new evidence resolves them.

---

## 6. Theory Evaluator (C15)

**Purpose:** Evaluate a user- or clinician-proposed Theory against the user's own data and external evidence — without diagnosing.

**Inputs:** Theory text + type, linked Investigation, personal evidence, External Evidence Graph relevance links.

**Outputs:** Theory status (unreviewed / needs_more_data / partially_supported / not_supported_by_current_data / contradicted_by_current_data / discuss_with_clinician), with evidence-for, evidence-against, missing-data, and what to discuss with a clinician.

**Trigger:** On-demand when a user or clinician enters a theory.

**Examples:**
- "Your data shows fatigue increased after the medication change, but sleep disruption also increased in the same period — the medication theory is possible but not isolated. Useful next context: exact dose dates and whether symptoms improve on non-work days."

**Safety (medium-high tier):** Never outputs true/false diagnosis or a ranked differential. Risky claims route to "discuss with clinician". Blocked if it would assert a diagnostic conclusion. See `../safety/do_not_diagnose_rules.md`.

---

## 7. External Research Relevance Engine (C16)

**Purpose:** Match curated external evidence (guidelines, papers, sources) to a thread by relevance, graded by source-quality tier — context, never a fact about the user.

**Inputs:** Thread summary, symptom clusters, labs, medications, search scope; External Evidence Graph.

**Outputs:** Relevance links: "this source discusses a similar pattern" with tier, confidence, and a possible question to ask; "new relevant source found"; "guideline changed".

**Trigger:** On-demand (Research/Theory) and via Research Watch on a user-defined schedule.

**Safety (high tier):** Source-quality tier shown on every result. No direct medical conclusion. External claims never enter the personal graph. Phrasing: "low-certainty and not specific to you".

---

## 8. Live-Metric Escalation Engine (F-LIVE)

**Purpose:** Watch wearable/device trends against personal baselines and suggest safe escalation when thresholds are crossed alongside concerning symptoms.

**Inputs:** Heart rate, HRV, sleep, SpO2, steps/activity, CGM, temperature, blood pressure, menstrual data, user-reported symptoms, medication changes; user-configured safety rules.

**Outputs:** "This changed from your baseline"; "this pattern persisted N days"; "this happened near a medication/sleep/activity change"; "based on your configured safety rules, consider seeking care".

**Trigger:** Continuous baseline-deviation evaluation; surfaces only when deviation persists and pairs with a concerning symptom.

**Safety (high tier):** No disease prediction as final output. No panic language. No silent urgent-risk handling. No over-alerting. Always distinguishes device data from clinical data and shows confidence + source. See `../safety/do_not_diagnose_rules.md` (Live-metric signal).

---

## Engine coordination

Engines run in sequence when triggered together:

```
Pattern Detection
    ↓
Confounder Detection  (runs on each pattern)
    ↓
Temporal Analysis     (runs on patterns with temporal components)
    ↓
Missing Data          (runs on inconclusive patterns)
    ↓
Contradiction         (runs independently on new document/summary ingestion)
```

All engine outputs are stored as first-class objects (not just UI annotations) and are source-linked, correctable, and auditable.
