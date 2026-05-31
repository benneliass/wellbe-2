# Decision: Theory object evaluation model and non-diagnostic safety routing

**Status:** Open  
**Date opened:** 2026-05-31  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-XXX (pending creation)  
**Blocks:** Theory Service (C15) story; Theory Evaluator engine story

---

## Question

How should the **Theory** object (C15) be evaluated against personal data and external evidence to produce evidence-for / evidence-against / missing-data and a status — without ever crossing into diagnosis — and how does that output route through the Safety & Governance Gate (C10)?

Specifically:
1. What is the authoritative theory status taxonomy (unreviewed / needs_more_data / partially_supported / not_supported_by_current_data / contradicted_by_current_data / discuss_with_clinician / clinician_reviewed) and what transitions are permitted?
2. Where is a Theory stored relative to Six Memories (C8) — is it a Pattern Memory entry, a first-class object, or both?
3. What C10 rules block a theory output from asserting a diagnosis or a ranked differential, and what triggers the `discuss_with_clinician` / urgent routing?
4. How are external sources (C16) attached as evidence without importing their claims as facts about the user?

## Context

The Theory object is the safe vehicle for user/clinician hypotheses and is the single most diagnosis-adjacent surface in the product. Getting the status taxonomy and the C10 routing wrong risks the system implying a diagnosis — the hardest safety line in `docs/safety/do_not_diagnose_rules.md`. C8 (Six Memories) and C10 (Safety Gate) are both touched, and the theory-evidence contract is consumed by the Theory Evaluator engine and the clinician workspace.

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
