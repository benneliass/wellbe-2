# Decision: Raw Context Vault append-only immutability enforcement

**Status:** Approved  
**Date opened:** 2026-05-31  
**Date approved:** 2026-05-31  
**Approved by:** User  
**Jira Spike:** WEL-94  
**Blocks:** WEL-80 — Build immutable append-only Raw Context Event store with full provenance

---

## Question

How should the Raw Context Vault enforce append-only immutability — what Postgres-level constraints prevent mutation of existing rows, how is S3 object-lock configured for document storage, and what is the canonical provenance schema attached to every raw context event?

Specifically:
1. What Postgres constraints or triggers prevent UPDATE/DELETE on raw context rows after insert?
2. What is the schema of a `RawContextEvent` — what fields carry provenance?
3. How are raw documents stored in S3 with object-lock — bucket policy, retention mode, key naming?
4. How is content-addressable deduplication handled?

## Context

C2 is the immutability guarantee the entire system depends on. It sits at layer L1 and is the first destination for all ingested data. The system principle "every output has provenance" and the safety rule "corrections never overwrite raw data" (C11 adds new layers, never mutates) both depend on C2 being truly append-only. If a raw event can be mutated or deleted, provenance breaks across all downstream components.

The `RawContextEvent` schema is the shared contract between C3 (adapters that write it) and C4 (pipeline that reads it). The tech stack has committed to PostgreSQL 17 for structured metadata and S3-compatible object storage with object-lock for raw blobs. Per-user envelope encryption keys support crypto-shred deletion — this must be compatible with the immutability enforcement.

## Research provided

### Executive summary (C2)

C2 must be append-only at four layers simultaneously: application service (no update/delete API), Postgres runtime role (INSERT/SELECT only), Postgres trigger (reject any mutation attempt), and object-lock storage (immutable raw blobs). GDPR/HIPAA erasure is handled through per-user envelope-key destruction plus append-only audit markers — never by deleting or mutating raw rows. RLS alone is insufficient because table owners and privileged roles can bypass it.

### Q1 — Postgres-level immutability enforcement

**Recommended approach:** four-layer defence.

1. Application service exposes no update/delete endpoint for raw events
2. Runtime app DB role has `INSERT`, `SELECT` only — no `UPDATE`, `DELETE`, `TRUNCATE` on `raw_context_events`
3. PostgreSQL Row Level Security enforces patient isolation (patient sees only their rows)
4. `BEFORE UPDATE OR DELETE` trigger raises an exception for any mutation attempt

For GDPR erasure or account deletion: destroy the user envelope key (or encrypted data key), append an erasure audit event (`raw_context.crypto_shredded`), mark `key_destroyed_at` / `erasure_requested_at`. Retain non-PHI metadata where legally justified. NIST SP 800-88 recognises cryptographic erase as a valid sanitization approach when designed from the start.

Separate migration/break-glass role exists for schema migrations but is not used by runtime services.

### Q2 — `RawContextEvent` schema

**Recommended fields:**
```
id, patient_id, tenant_id (nullable), actor_id,
source_type, source_id (nullable), external_source_id (nullable),
idempotency_key,
captured_at, received_at, ingested_at,
content_hash, hash_scope = patient,
blob_ref, blob_bucket, blob_key, blob_version_id,
byte_size, mime_type, encoding, language,
original_filename_hash (nullable),
source_metadata (jsonb),
adapter_name, adapter_version, ingestor_version,
consent_snapshot_id, share_grant_id (nullable),
encryption_key_id, encryption_key_version,
retention_policy_id,
correlation_id, trace_id,
duplicate_of_event_id (nullable),
schema_version, created_at
```

`source_type` should be a lookup table, not a PostgreSQL enum — source types will grow and a lookup table is easier to extend, add metadata to, and deprecate:
```
raw_context_source_types
  code (text primary key), display_name,
  status (active | deprecated),
  requires_blob (boolean),
  default_mime_types (text[])
```

### Q3 — S3 object-lock configuration

**Recommended approach:** versioned object storage with object-lock enabled. Use **GOVERNANCE mode** for MVP (allows override by privileged role for exceptional corrections). Use **COMPLIANCE mode** only when legal/regulatory requirements demand non-overridable retention — it is intentionally difficult to bypass.

**Object key pattern:**
```
raw/patient/{patient_id_hash}/event/{raw_context_event_id}/blob
```
No PHI, filenames, dates of birth, or source text in S3 keys. Encrypt each object with a data key; encrypt the data key with a per-user key-encryption key (KEK). Crypto-shred by destroying or disabling the user KEK — the object remains but is unreadable.

### Q4 — Deduplication

**Recommended approach:** per-patient hash namespaces; always append the event even when the blob is a duplicate.

```
content_hash = hash(raw_bytes)
dedup_key = (patient_id, content_hash)

On duplicate detected:
  1. Create a new RawContextEvent row
  2. Set duplicate_of_event_id = existing event id
  3. Optionally reuse the existing S3 object version for this patient
  4. Preserve captured_at and ingested_at as a separate user action
```

Do not use a global cross-user hash namespace — it leaks whether two users share the same document or content. Accept the storage cost of duplicate event rows: repeated user submission is itself health context.

### References

- PostgreSQL 17 Row Security Policies — https://www.postgresql.org/docs/17/ddl-rowsecurity.html
- PostgreSQL 17 CREATE TRIGGER — https://www.postgresql.org/docs/17/sql-createtrigger.html
- NIST SP 800-88 Rev. 2, Guidelines for Media Sanitization — https://csrc.nist.gov/pubs/sp/800/88/r2/final
- AWS S3 Object Lock — https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html
- AWS S3 Object Lock retention modes — https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock-configure.html

_Research received: 2026-05-31_

---

## Approaches considered

| Approach | Decision | Reason |
|---|---|---|
| Application-layer enforcement only | Rejected | Privileged roles and direct DB access can bypass it |
| RLS only | Rejected | Table owners and superusers can bypass RLS; not sufficient alone |
| Postgres trigger only | Rejected | Triggers can be disabled by superuser; not sufficient alone |
| Four-layer defence (app service + role + RLS + trigger) | **Accepted** | Defence-in-depth; each layer catches what the others miss |
| PostgreSQL enum for `source_type` | Rejected | Enums are hard to extend without migrations; lookup table is additive |
| Lookup table for `source_type` | **Accepted** | Extensible, deprecatable, supports metadata per type |
| GDPR erasure via row deletion | Rejected | Breaks immutability and provenance chain |
| GDPR erasure via crypto-shred (key destruction) | **Accepted** | Immutability preserved; NIST SP 800-88 recognises cryptographic erase |
| Global cross-user hash namespace for deduplication | Rejected | Leaks content correlation between users |
| Per-patient hash namespace with duplicate event row | **Accepted** | Privacy-safe; preserves repeated submission as health context |
| S3 COMPLIANCE mode for MVP | Rejected | Too rigid for MVP — GOVERNANCE mode allows corrections with a privileged role |
| S3 GOVERNANCE mode for MVP | **Accepted** | Immutability for normal operations; override possible for legitimate corrections |

## Decision

C2 will be immutable by design: the runtime app role has INSERT/SELECT only, a `BEFORE UPDATE OR DELETE` Postgres trigger rejects any mutation attempt, RLS enforces patient isolation, and raw blobs are stored in versioned S3 object-lock storage (GOVERNANCE mode at MVP). `source_type` is a lookup table, not an enum. Deduplication uses per-patient hash namespaces; duplicate submissions create a new event row with `duplicate_of_event_id` set. User erasure is implemented by destroying the per-user envelope encryption key plus appending a `raw_context.crypto_shredded` audit event — raw rows are never deleted or mutated in normal operation.

## Trade-offs accepted

- Four-layer immutability enforcement is redundant by design — accept the maintenance overhead as the cost of the safety guarantee.
- Duplicate event rows cost storage — accepted because repeated user submission is health context.
- GOVERNANCE mode means a break-glass role can technically override immutability — accepted for MVP practicality; move to COMPLIANCE when regulated.

## Implementation notes

- Runtime app DB user must be granted `INSERT, SELECT` only on `raw_context_events`. `UPDATE`, `DELETE`, `TRUNCATE` are never granted.
- The migration/break-glass role is separate, requires MFA, and every use is logged.
- `encryption_key_id` + `encryption_key_version` on every event row is required from day 1 — retrofitting per-user encryption later is prohibitively expensive.
- Events emitted via outbox: `raw_context.received` (on every successful insert), `raw_context.crypto_shredded` (on key destruction).

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
