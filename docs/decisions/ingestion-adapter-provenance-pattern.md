# Decision: Ingestion Layer adapter interface and provenance pattern

**Status:** Approved  
**Date opened:** 2026-05-31  
**Date approved:** 2026-05-31  
**Approved by:** User  
**Jira Spike:** WEL-95  
**Blocks:** WEL-81 — Build pluggable Ingestion Layer with unified adapter protocol

---

## Question

What adapter interface pattern should the Ingestion Layer (C3) use so that new source types (manual text, photo/PDF, SMS, device, FHIR, environmental) can be added without modifying core ingestion logic, and how should provenance metadata be attached uniformly at the adapter boundary before writing to C2?

Specifically:
1. What is the minimal contract an adapter must implement — validate, extract, and metadata methods?
2. How does the adapter delegate to the C2 Vault Writer — pass a normalized object, or call a service directly?
3. How are long-running imports (e.g. FHIR bulk, document OCR) handled — synchronous, Dramatiq worker, or Temporal workflow?
4. How does provenance metadata flow from adapter to C2 raw event?

## Context

C3 is the only authorised path into C2. If any component writes to the Vault outside of C3, the provenance chain breaks and the "no orphan claims" guarantee cannot be held downstream. C3 sits at layer L1 and is the boundary between external input (in all its formats) and the system's internal immutable store.

The system will need to ingest: user-typed text, photos and PDFs (require OCR), SMS (requires parsing), wearable device data (structured metrics), FHIR records (clinical standards), and environmental context (weather, AQ). Each source type is structurally different but must produce the same `RawContextEvent` provenance schema defined by C2. Getting the adapter boundary wrong means either brittle one-off adapters or an ingestion layer that cannot be extended.

FHIR Provenance (R4) is a useful conceptual model: it links targets, entities used, and the agents and activities involved in their creation.

## Research provided

### Executive summary (C3)

C3 exposes a stable adapter protocol with three steps: validate, extract, metadata. Adapters validate and normalize inputs — they do not write directly to tables, make global deduplication decisions, or manage encryption. The Vault Writer (C2's write path) owns persistence, hashing, deduplication, encryption metadata, and event emission. Long-running imports are Temporal workflows that orchestrate standard adapter activities; simple ingestion is synchronous to the point of writing the raw event safely to C2 (then async from there).

### Q1 — Adapter protocol contract

**Recommended approach:** every adapter implements three methods.

```python
class BaseAdapter:
    async def validate(self, raw_input: AdapterInput) -> ValidationResult:
        """Validate the raw input is well-formed and complete enough to ingest."""

    async def extract(self, raw_input: AdapterInput) -> NormalizedPayload:
        """Normalize the raw input into a format the Vault Writer can hash and store."""

    async def metadata(self, raw_input: AdapterInput, payload: NormalizedPayload) -> AdapterProvenance:
        """Produce the provenance fields: adapter_name, adapter_version, source_type, source_metadata."""
```

Adapters do not decide whether something is a duplicate. They do not write to `raw_context_events`. They do not manage encryption keys. They emit `AdapterProvenance` — the Vault Writer merges it with system-level provenance (ingestor version, consent snapshot, encryption key, idempotency key) before writing the `RawContextEvent`.

### Q2 — Delegation to the C2 Vault Writer

**Recommended approach:** adapter calls the Vault Writer service with a typed write request; the Vault Writer owns the database write.

```python
class VaultWriteRequest:
    patient_id: UUID
    actor_id: UUID
    normalized_payload: NormalizedPayload
    adapter_provenance: AdapterProvenance
    idempotency_key: str
    consent_snapshot_id: UUID
    share_grant_id: UUID | None
    correlation_id: str
    trace_id: str
```

The Vault Writer resolves: `content_hash`, `dedup_key`, `encryption_key_id/version`, `blob_ref`, and outbox event. No adapter touches these.

### Q3 — Long-running import orchestration

**Recommended approach:** two paths — synchronous for simple ingestion, Temporal for long-running work.

| Ingestion type | Orchestration |
|---|---|
| Manual text, simple photo/PDF | Synchronous call through adapter → Vault Writer → return |
| OCR on large/complex documents | Temporal workflow (`DocumentOCRWorkflow`) — adapter runs as an activity |
| FHIR bulk import | Temporal workflow (`FHIRBulkImportWorkflow`) — polls FHIR endpoint, processes pages, retries |
| Degraded image (fallback to vision) | Temporal workflow — tries OCR activity, then vision-model activity on failure |
| Device data batch | Dramatiq worker for lightweight batches; Temporal for retryable device sync |

The key rule: synchronous ingestion ends the moment the `RawContextEvent` is safely written. Processing (C4) begins asynchronously from that point. An adapter must never hold a synchronous HTTP connection open while waiting for OCR or FHIR pagination.

### Q4 — Provenance metadata flow

**Recommended approach:** provenance is attached by the adapter and sealed by the Vault Writer.

```
adapter produces:
  source_type, source_id, external_source_id, captured_at,
  adapter_name, adapter_version, source_metadata (jsonb),
  original_filename_hash (nullable), mime_type, encoding, language

Vault Writer adds:
  ingestor_version, received_at, ingested_at,
  content_hash, hash_scope, encryption_key_id/version,
  consent_snapshot_id, idempotency_key, correlation_id, trace_id,
  duplicate_of_event_id (if dedup match found)
```

FHIR Provenance R4 model maps directly: `target` = `raw_context_event_id`, `entity.what` = source FHIR resource, `agent` = actor (user, system, clinician), `activity` = ingestion activity code.

### References

- FHIR R4 Provenance — https://r4.fhir.space/provenance.html
- Temporal workflow definition and determinism — https://docs.temporal.io/workflow-definition
- Temporal Python activity timeouts — https://docs.temporal.io/develop/python/activities/timeouts
- Dramatiq guide — https://dramatiq.io/guide.html

_Research received: 2026-05-31_

---

## Approaches considered

| Approach | Decision | Reason |
|---|---|---|
| Adapters write directly to `raw_context_events` | Rejected | Breaks the single-ingress guarantee; provenance fields and encryption managed inconsistently |
| Adapters manage deduplication | Rejected | Global dedup decisions belong to Vault Writer; adapters should not know about other patients' hashes |
| Adapter + Vault Writer in one monolithic service | Rejected | Cannot add new source types without modifying core ingestion logic |
| Three-method adapter protocol (validate / extract / metadata) | **Accepted** | Minimal stable contract; new source types add a new class, not a new code path |
| Synchronous-only ingestion | Rejected | FHIR bulk and large document OCR cannot hold an HTTP connection open |
| Temporal for all ingestion | Rejected | Overkill for simple text and short documents; adds durability overhead where none is needed |
| Synchronous for simple + Temporal for long-running | **Accepted** | Right tool for each case; consistent adapter protocol across both |
| Dramatiq workers for all async work | Partially accepted | Appropriate for lightweight device batches; insufficient for multi-step OCR or FHIR pagination |

## Decision

C3 is the only ingress path into C2. Every adapter implements a stable `validate / extract / metadata` protocol and delegates persistence, hashing, deduplication, encryption metadata, and event emission to the Vault Writer. The Vault Writer is the only component that writes `RawContextEvent` rows. Long-running imports (OCR, FHIR bulk, degraded image fallback) are orchestrated as Temporal workflows; simple ingestion is synchronous to the point of the raw event being safely stored. Provenance metadata is produced by the adapter and sealed (with system-level fields) by the Vault Writer before the DB write.

## Trade-offs accepted

- Adapter protocol adds an indirection layer — accepted for extensibility and testability.
- Two ingestion paths (synchronous + Temporal) add operational complexity — accepted because a single path cannot satisfy both latency requirements.
- Temporal workflows add durability overhead for long-running imports — accepted; the retry and checkpointing semantics are required for FHIR/OCR reliability.

## Implementation notes

- Every adapter must be tested with a `FakeVaultWriter` that verifies provenance fields are complete before the real Vault Writer writes them.
- The `source_type` lookup table (defined in the C2 decision record) must exist before any adapter is registered.
- The `DocumentOCRWorkflow` Temporal workflow should be a separate activity from the `validate/extract` steps so that OCR timeouts do not affect provenance writing.
- Events emitted via outbox: `ingestion.batch_started`, `ingestion.batch_completed`, `ingestion.item_failed`.

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
