# Decision: Evidence & Provenance link schema and no-orphan-claims enforcement

**Status:** Open  
**Date opened:** 2026-05-31  
**Date approved:** _(fill on approval)_  
**Approved by:** _(fill on approval)_  
**Jira Spike:** WEL-97  
**Blocks:** WEL-83 — Build evidence-link service enforcing no-orphan-claims provenance

---

## Question

What is the evidence link schema between a derived fact and its raw source event(s), how is the "no orphan claims" rule enforced at write time, and how are multi-source facts (a single fact derived from multiple raw events) represented?

Specifically:
1. What are the tables/fields that link a derived fact back to its raw source — a many-to-many join table, an embedded array on the fact row, or a separate evidence graph?
2. How is "no orphan claims" enforced — at the application layer (service raises an error), at the DB layer (foreign key constraint), or both?
3. How is a fact derived from multiple raw sources represented — multiple rows in an `evidence_links` table, an array of `source_refs` on the fact, or a provenance chain object?
4. What is the confidence/weight model on each evidence link — a float, a categorical score, or a derivation from the source event's quality score in C4?

## Context

C5 is the provenance backbone that makes the system's core principle "every output has provenance" enforceable in code. It sits at layer L2, between C4 (which produces facts) and C6/C7/C10 (which consume facts). C10 (Safety Gate) queries C5 provenance when evaluating whether an AI output can be shown to a user. C7 (Health Thread Engine) queries it when linking thread context to source evidence. C11 (Correction Service) adds new source-linked correction layers by writing through C5.

The "no orphan claims" invariant means: no `ExtractedFact`, `HealthSignal`, memory entry, or AI-generated claim may exist in the system without at least one traceable link back to a `RawContextEvent` in C2. If this invariant is not enforced at write time, the system can accumulate unsourced claims that the safety gate cannot verify.

**Key constraint:** Evidence links are immutable — corrections (C11) add new links, they never modify existing ones. This means the link schema must be append-only-compatible from the start.

## Research provided

_Awaiting user research._

_Research received: —_

## Approaches considered

_To be written after research is received._

## Decision

_To be written after research is received and approved._

## Trade-offs accepted

_To be written after research is received and approved._

## Implementation notes

_To be written after approval._

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
