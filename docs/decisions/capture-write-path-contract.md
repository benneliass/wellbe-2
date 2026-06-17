# Decision: Capture write-path API contract (CaptureModal → C3 → C2)

**Status:** Open  
**Date opened:** 2026-06-17  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-161  
**Blocks:** WEL-155 [Capture write API endpoint (ingestion adapter to Vault) for Log something]

---

## Question

For the `log` pill / `CaptureModal`, what is the capture write-path API contract from the UI through the C3 ingestion adapter into the immutable C2 Vault?
1. **Request/response shape** per capture type (symptom, lab, document, note).
2. **Idempotency/dedupe** — how is a re-submitted or retried capture made safe against the append-only Vault?
3. **Provenance metadata** written at ingest (source, actor, timestamp, correlation).
4. **Sync vs deferred** — which derived processing (C4) happens inline vs. asynchronously after the write returns.

## Context

Touches C3 (Ingestion Layer) and C2 (Raw Context Vault, immutable/append-only), plus C4 (Processing) — see `docs/architecture/component-map.md`. The Vault cannot be mutated to fix a bad write, so a non-idempotent or under-specified contract creates orphaned or duplicated raw context that is permanent. Builds on the already-approved ingestion-adapter spike (WEL-95, Done).

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
