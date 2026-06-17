# Decision: Pattern-detection semantics (non-diagnostic)

**Status:** Open  
**Date opened:** 2026-06-17  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-164  
**Blocks:** WEL-79 [Implement Pattern, Temporal, Confounder, Missing-Data, and Contradiction intelligence engines]

---

## Question

For the `pattern` pill ("Check my patterns"), what are the pattern-detection semantics over the knowledge graph?
1. **Temporal precedence** — how is the order between two co-occurring events determined: timestamp order, user-reported order, or a confidence-weighted combination?
2. **Co-occurrence/pattern definition** — what counts as a pattern worth surfacing.
3. **Confidence** — how is confidence scored and surfaced, read/annotate only, never diagnosis (`may_explain` is the strongest causal edge).

## Context

Touches C4 (Processing), C6 (Knowledge Graph), C8 (Six Memories) — see `docs/architecture/component-map.md` and `docs/system-design/intelligence_engines.md`. Wrong precedence or confidence semantics risk implying causation/diagnosis — a do-not-diagnose violation (`docs/safety/do_not_diagnose_rules.md`).

## Research provided

_Research received: YYYY-MM-DD_

<!-- Agent-run research (model, date) recorded verbatim here per research-protocol Section I. -->

## Approaches considered

<!-- Written by agent after research, grounded only in the recorded research. -->

## Decision

<!-- Proposed by agent, approved by user. -->

## Trade-offs accepted

<!-- Filled after approval. -->

## Implementation notes

<!-- Filled after approval. -->

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
