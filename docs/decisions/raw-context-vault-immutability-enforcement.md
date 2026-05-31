# Decision: Raw Context Vault append-only immutability enforcement

**Status:** Open  
**Date opened:** 2026-05-31  
**Date approved:** _(fill on approval)_  
**Approved by:** _(fill on approval)_  
**Jira Spike:** WEL-94  
**Blocks:** WEL-80 — Build immutable append-only Raw Context Event store with full provenance

---

## Question

How should the Raw Context Vault enforce append-only immutability — what Postgres-level constraints prevent mutation of existing rows, how is S3 object-lock configured for document storage, and what is the canonical provenance schema attached to every raw context event?

Specifically:
1. What Postgres constraints or triggers prevent UPDATE/DELETE on raw context rows after insert?
2. What is the schema of a `RawContextEvent` — what fields carry provenance (`source_type`, `source_id`, `actor_id`, `ingested_at`, `content_hash`)?
3. How are raw documents (PDFs, images) stored in S3 with object-lock — what bucket policy, retention mode, and key naming convention?
4. How is content-addressable deduplication handled — hash-based, at ingest time, before writing to the Vault?

## Context

C2 is the immutability guarantee the entire system depends on. It sits at layer L1 and is the first destination for all ingested data. The system principle "every output has provenance" and the safety rule "corrections never overwrite raw data" (C11 adds new layers, never mutates) both depend on C2 being truly append-only. If a raw event can be mutated or deleted, provenance breaks across all downstream components.

The `RawContextEvent` schema is also the shared contract between C3 (adapters that write it) and C4 (pipeline that reads it). Getting it wrong means cascading schema migrations across at least three components. The tech stack has committed to PostgreSQL 17 for structured metadata and S3-compatible object storage with object-lock for raw blobs.

**Key constraint:** Per-user envelope encryption keys (for crypto-shred deletion) interact with immutability — deleting the key destroys the user's PHI without mutating the raw records. This must be compatible with whatever immutability enforcement is chosen.

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
