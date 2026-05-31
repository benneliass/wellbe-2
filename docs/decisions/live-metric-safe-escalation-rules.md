# Decision: Live Metrics Safety Monitor thresholds and safe-escalation rules

**Status:** Open  
**Date opened:** 2026-05-31  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-132  
**Blocks:** WEL-121 (Live Metrics Safety Monitor)

---

## Question

What baseline model, thresholds, and Safety & Governance Gate (C10) rules govern **Live-Metric escalation** so it suggests care without diagnosing, panicking, over-alerting, or silently handling urgent risk?

Specifically:
1. How is a personal baseline computed and what deviation + persistence + symptom-pairing conditions trigger a surfaced signal?
2. What user-configurable safety rules are allowed, and what hard floors/ceilings does the system enforce regardless of user config?
3. What C10 rules guarantee no disease prediction as a final output, no panic language, and no silent urgent handling?
4. How is device data distinguished from clinical data, and how is confidence + source shown on every signal?

## Context

Live metrics is the only engine that may proactively surface guidance, making it the highest alert-fatigue and missed-deterioration risk surface. It touches C10 (safety gate) and depends on wearable integration (F-WEAR) and continuity (C9). Wrong thresholds either cause harm (missed escalation) or erode trust (over-alerting). The escalation copy and routing are safety-critical and must be settled before implementation.

## Research provided

_Research results must be provided by the user. Agents may not self-research._

_Research received: YYYY-MM-DD_

## Approaches considered

<!-- Filled after research is provided. -->

## Decision

<!-- Proposed after research, approved by user. -->

## Trade-offs accepted

<!-- Filled after approval. -->

## Implementation notes

<!-- Filled after approval. -->

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
