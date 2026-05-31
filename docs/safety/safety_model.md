# Safety model

## Core safety posture

WellBe is a memory and investigation support system, not a diagnostic authority. This holds across every workspace (individual, clinician, institution, research): clinician outputs may be more technical but remain source-linked and uncertainty-preserving, and the safety gate runs before every user-facing AI output in every workspace.

## Safety layers

1. **Scope safety** — Does the feature serve the individual, with any non-individual access grant-scoped?
2. **Data safety** — Is each claim source-linked and labeled by type and source-quality tier (Tier 1 guidelines … Tier 5 anecdote)?
3. **Language safety** — Does the output avoid diagnosis, blame, panic, and certainty?
4. **Urgency safety** — Does urgent content route to appropriate care advice without delaying care?
5. **Privacy safety** — Is sharing grant-based, user-scoped, revocable, and minimal?
6. **Bias safety** — Does the feature avoid stigmatizing labels and demographic shortcuts?
7. **Workflow safety** — Could it overload clinicians or imply false ownership?
8. **Monitoring safety** — Are false positives, false negatives, ignored alerts, and user outcomes reviewed?
9. **Engine risk-tier safety** — Is the feature's engine assigned a risk tier (lower: timeline/missing-context; higher: theory evaluation, external research relevance, live-metric escalation, cross-patient comparison) with tier-appropriate controls?
10. **Clinical-review marker safety** — Is every output labeled with its review state (patient-entered / AI-summarized / not-clinician-reviewed / clinician-reviewed / clinician-annotated / ready-for-visit / needs-urgent-care-consideration)?

## Non-bypass rule

The Safety Engine must evaluate every user-facing AI output. No assistant, agent, summary generator, or research mode can bypass it.
