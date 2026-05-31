# Decision: Ingestion Layer adapter interface and provenance pattern

**Status:** Open  
**Date opened:** 2026-05-31  
**Date approved:** _(fill on approval)_  
**Approved by:** _(fill on approval)_  
**Jira Spike:** WEL-95  
**Blocks:** WEL-81 — Build ingestion adapter framework and entity/fact/signal extraction pipeline

---

## Question

What adapter interface pattern should the Ingestion Layer (C3) use so that new source types (manual text, photo/PDF, SMS, device, FHIR, environmental) can be added without modifying core ingestion logic, and how should provenance metadata be attached uniformly at the adapter boundary before writing to C2?

Specifically:
1. What is the adapter interface contract — what methods must every source-type adapter implement?
2. How does an adapter attach provenance to its output — what fields are required before the event is written to the Vault (`source_type`, `source_id`, `actor_id`, `raw_payload`, `content_hash`, `ingested_at`)?
3. How are durable ingestion workflows (e.g. FHIR import, bulk wearable backfill) handled — as Temporal workflow activities wrapping the adapter, or as a different pattern?
4. How is partial ingestion failure handled — does the adapter write a partial event, write nothing, or write a failed-ingest event?

## Context

C3 is the only path into C2. Every data capture feature — mood logging, document upload, wearable sync, FHIR pull, SMS — is an adapter on C3. The system principle "no institutional overreach" and the architecture rule "no feature bypasses the Data Factory" mean every adapter must write through the same Vault interface, with the same provenance fields. If the adapter interface is not stable and provenance-enforcing at the boundary, individual adapters will attach inconsistent provenance metadata, creating orphan claims downstream in C5.

The tech stack has committed to Temporal for durable workflows (FHIR import, bulk backfill) and Dramatiq for lightweight fire-and-forget jobs. The adapter framework decision determines whether new source types are purely additive (new adapter class, no core changes) or require touching shared code.

**Key constraint from `docs/system-design/integrations.md`:** Every integration writes only through C3 into C2. No feature component is permitted to write directly to the Vault, bypassing the adapter layer.

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
