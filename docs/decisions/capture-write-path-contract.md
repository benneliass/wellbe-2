# Decision: Capture write-path API contract (CaptureModal → C3 → C2)

**Status:** Approved  
**Date opened:** 2026-06-17  
**Date approved:** 2026-06-17  
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

> Agent-run LLM research (model: gpt-5.5, date: 2026-06-17, run id: resp_0d593a1595337e7b006a32fd8137e08191b5920ea875ec813e, web_search: on). Recorded verbatim per research-protocol.mdc Section I. Not synthesised by the agent.

## 1. External patterns to examine

### A. Request/response shape per capture type

- **Health-data resource modeling:** HL7 FHIR R4 uses separate resources for different clinical artifact types: `Observation` for observations and measured findings, `DiagnosticReport` for lab/imaging/pathology reports that may reference atomic `Observation` results, `DocumentReference` for document metadata and attached/referenced content, and `Composition` for organized clinical note-like documents. These are relevant external shapes for symptom, lab, document, and note capture, without implying the capture API must expose FHIR directly. ([hl7.org](https://hl7.org/fhir/R4/DiagnosticReport.html?utm_source=openai))  
- **HTTP success/error response conventions:** RFC 9110 defines `201 Created` for creation and `202 Accepted` for accepted-but-not-completed processing; RFC 9457 defines a standard `application/problem+json` error body for machine-readable HTTP API errors. ([httpwg.org](https://httpwg.org/specs/rfc9110.html?utm_source=openai))  
- **Asynchronous operation resources:** Azure’s asynchronous request-reply pattern and Google AIP-151 both describe returning an operation/status resource when work is too long-running to complete in the initial request. ([learn.microsoft.com](https://learn.microsoft.com/en-us/azure/architecture/patterns/asynchronous-request-reply?utm_source=openai))  

### B. Idempotency/dedupe for at-least-once write paths

- **Client-supplied idempotency key:** Stripe, AWS EC2/ECS, Google AIP-155, and the IETF `Idempotency-Key` draft/MDN documentation describe client-provided request identifiers for safe retries of mutating calls. ([docs.stripe.com](https://docs.stripe.com/api/idempotent_requests?++lang=node&utm_source=openai))  
- **Parameter/request fingerprint checking:** Stripe and AWS both document mismatch handling when a reused idempotency key is paired with different request parameters. ([docs.stripe.com](https://docs.stripe.com/api/idempotent_requests?++lang=node&utm_source=openai))  
- **Deterministic IDs from natural keys:** RFC 9562 defines UUIDv5 as a namespace/name-based UUID derived from a canonical name, which is relevant to deterministic ID generation from stable natural keys. ([ietf.org](https://www.ietf.org/rfc/rfc9562?utm_source=openai))  
- **Append-only/event-store idempotence:** EventStoreDB/Kurrent documents idempotent appends based on event ID plus stream, with stronger guarantees when optimistic concurrency / expected revision is used rather than `Any`. ([docs.kurrent.io](https://docs.kurrent.io/clients/tcp/dotnet/21.2/appending.html?utm_source=openai))  
- **At-least-once consumers:** The Idempotent Consumer pattern describes duplicate message handling as a normal requirement under at-least-once delivery. ([microservices.io](https://microservices.io/patterns/communication-style/idempotent-consumer.html?utm_source=openai))  

### C. Provenance metadata at ingest

- **General provenance model:** W3C PROV-O models provenance using entities, activities, agents, derivations, and responsibility relationships. ([w3.org](https://www.w3.org/TR/prov-o/?utm_source=openai))  
- **Health provenance model:** HL7 FHIR Provenance is based on W3C PROV and records provenance for FHIR resources; US Core describes provenance as supporting authenticity, trust, and reproducibility. ([hl7.org](https://hl7.org/fhir/R4/provenance.html?utm_source=openai))  
- **Attachment/document metadata:** FHIR `Attachment` includes content type, size, hash, creation date, and data or URL; `DocumentReference` includes document identifiers, status, type/category, subject, author, date, description, security labels, content attachment, and clinical context. ([hl7.org](https://hl7.org/fhir/R4/datatypes.html?utm_source=openai))  

### D. Sync vs. deferred C4 processing

- **Immediate validation vs. deferred execution:** Azure’s async request-reply pattern says the API should validate the request before starting long-running work, then return `202 Accepted` with a polling/status location for background processing. ([learn.microsoft.com](https://learn.microsoft.com/en-us/azure/architecture/patterns/asynchronous-request-reply?utm_source=openai))  
- **Long-running operation boundary:** Google AIP-151 says operations that take significant time should return an operation token/resource rather than blocking; it distinguishes errors that prevent the operation from starting from errors that occur during execution. ([google.aip.dev](https://google.aip.dev/151?utm_source=openai))  
- **HTTP limitation:** RFC 9110 notes there is no HTTP facility to later resend the final status code for an asynchronous operation, which is why status resources, polling, callbacks, or other async completion channels are used. ([httpwg.org](https://httpwg.org/specs/rfc9110.html?utm_source=openai))  

---

## 2. Evidence inventory

1. **HL7 FHIR R4 — Observation / DiagnosticReport / DocumentReference / Composition / Clinical Notes**  
   - **URL:** HL7 FHIR pages cited inline. ([hl7.org](https://hl7.org/fhir/R4/DiagnosticReport.html?utm_source=openai))  
   - **Covers:** Standard health-resource shapes for observations, lab reports, documents, and clinical notes.  
   - **Jurisdiction/context:** International health interoperability standard; US Core clinical-notes page is US implementation context.  
   - **Limitations:** FHIR is an interoperability model, not automatically a product API contract; many elements are optional or profile-dependent.

2. **HL7 FHIR R4 — Provenance and US Core Basic Provenance**  
   - **URL:** HL7 FHIR Provenance and US Core provenance pages. ([hl7.org](https://hl7.org/fhir/R4/provenance.html?utm_source=openai))  
   - **Covers:** Provenance target, generation/update context, relationship to W3C PROV, “last hop” and reproducibility concepts.  
   - **Jurisdiction/context:** FHIR R4 global; US Core is US implementation guidance.  
   - **Limitations:** FHIR Provenance is oriented around FHIR resources; a raw immutable vault may need an internal provenance schema that maps to, but is not identical to, FHIR.

3. **W3C PROV-O**  
   - **URL:** W3C Recommendation. ([w3.org](https://www.w3.org/TR/prov-o/?utm_source=openai))  
   - **Covers:** Entities, activities, agents, derivation chains, responsibility relationships.  
   - **Jurisdiction/context:** Web provenance standard; domain-neutral.  
   - **Limitations:** Conceptual ontology; does not prescribe API payloads, database layout, or healthcare-specific fields.

4. **FHIR R4 Datatypes — Attachment**  
   - **URL:** HL7 FHIR datatypes page. ([hl7.org](https://hl7.org/fhir/R4/datatypes.html?utm_source=openai))  
   - **Covers:** Attachment metadata such as `contentType`, `size`, `hash`, `creation`, data, and URL.  
   - **Jurisdiction/context:** FHIR R4.  
   - **Limitations:** FHIR R4 uses SHA-1 for `Attachment.hash`; systems with stronger integrity requirements often track additional hashes separately, but that specific practice is outside this source.

5. **Stripe API — Idempotent requests**  
   - **URL:** Stripe API docs. ([docs.stripe.com](https://docs.stripe.com/api/idempotent_requests?++lang=node&utm_source=openai))  
   - **Covers:** Idempotency keys for POST retries, storing first status/body, comparing later parameters, TTL pruning, random high-entropy keys.  
   - **Jurisdiction/context:** Payments API, production commercial API.  
   - **Limitations:** Stripe’s semantics are payment/API-provider-specific; not all choices transfer to append-only health capture.

6. **AWS EC2 — Ensuring idempotency in API requests**  
   - **URL:** AWS EC2 developer guide. ([docs.aws.amazon.com](https://docs.aws.amazon.com/ec2/latest/devguide/ec2-api-idempotency.html?utm_source=openai))  
   - **Covers:** Client tokens, parameter mismatch errors, idempotency scoping by region/zone.  
   - **Jurisdiction/context:** Cloud infrastructure APIs.  
   - **Limitations:** AWS scopes idempotency to cloud resources and regions/zones; health capture may need different scoping boundaries.

7. **Google AIP-155 — Request identification**  
   - **URL:** Google API Improvement Proposal. ([google.aip.dev](https://google.aip.dev/155?utm_source=openai))  
   - **Covers:** `request_id` for deduplication, retries, auditing, UUID4 guidance, stale success response handling.  
   - **Jurisdiction/context:** Google-style resource APIs.  
   - **Limitations:** AIP guidance is design guidance, not an internet standard.

8. **MDN / IETF draft — `Idempotency-Key` HTTP header**  
   - **URL:** MDN and IETF draft pages. ([developer.mozilla.org](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Idempotency-Key?utm_source=openai))  
   - **Covers:** Header use for POST/PATCH idempotency and retry safety.  
   - **Jurisdiction/context:** HTTP API design.  
   - **Limitations:** MDN marks the header experimental; the consulted IETF source is an Internet-Draft, not an RFC.

9. **RFC 9562 — UUIDs**  
   - **URL:** IETF RFC. ([ietf.org](https://www.ietf.org/rfc/rfc9562?utm_source=openai))  
   - **Covers:** UUIDv5 namespace/name-based deterministic ID generation.  
   - **Jurisdiction/context:** Internet standard.  
   - **Limitations:** Defines identifier generation, not dedupe policy, conflict handling, or health-data natural keys.

10. **EventStoreDB/Kurrent — Appending events and idempotence**  
    - **URL:** Kurrent/EventStoreDB documentation. ([docs.kurrent.io](https://docs.kurrent.io/clients/tcp/dotnet/21.2/appending.html?utm_source=openai))  
    - **Covers:** Event ID + stream idempotence, expected version checks, duplicate append behavior.  
    - **Jurisdiction/context:** Event store / append-only stream database.  
    - **Limitations:** Applies to EventStoreDB semantics; other vault implementations may not provide identical guarantees.

11. **Azure Architecture Center — Asynchronous Request-Reply pattern**  
    - **URL:** Microsoft Learn. ([learn.microsoft.com](https://learn.microsoft.com/en-us/azure/architecture/patterns/asynchronous-request-reply?utm_source=openai))  
    - **Covers:** `202 Accepted`, status endpoint, validation-before-start, polling, `Retry-After`, operation states.  
    - **Jurisdiction/context:** Distributed REST APIs and cloud architecture.  
    - **Limitations:** Pattern-level guidance; not health-specific and not tied to append-only storage.

12. **Google AIP-151 — Long-running operations**  
    - **URL:** Google AIP. ([google.aip.dev](https://google.aip.dev/151?utm_source=openai))  
    - **Covers:** Operation resources, metadata, progress/status, start-time vs execution-time errors, operation expiry.  
    - **Jurisdiction/context:** Google-style APIs.  
    - **Limitations:** gRPC/resource-oriented framing; HTTP APIs may express equivalent concepts differently.

13. **RFC 9110 — HTTP Semantics**  
    - **URL:** HTTP Semantics RFC. ([httpwg.org](https://httpwg.org/specs/rfc9110.html?utm_source=openai))  
    - **Covers:** HTTP status semantics, including `201 Created` and `202 Accepted`.  
    - **Jurisdiction/context:** Internet standard.  
    - **Limitations:** Does not define application-specific response bodies or workflow contracts.

14. **RFC 9457 — Problem Details for HTTP APIs**  
    - **URL:** RFC Editor. ([rfc-editor.org](https://www.rfc-editor.org/rfc/rfc9457.html?utm_source=openai))  
    - **Covers:** Standard machine-readable error body using `application/problem+json`.  
    - **Jurisdiction/context:** Internet standard.  
    - **Limitations:** Error format only; does not define success responses or domain validation rules.

15. **Microservices.io — Idempotent Consumer pattern**  
    - **URL:** Pattern catalog. ([microservices.io](https://microservices.io/patterns/communication-style/idempotent-consumer.html?utm_source=openai))  
    - **Covers:** Handling duplicate messages under at-least-once delivery.  
    - **Jurisdiction/context:** Microservice messaging pattern.  
    - **Limitations:** Pattern source, not a normative standard; focuses on consumers more than HTTP write endpoints.

---

## 3. Decision-neutral findings

### Q1. Request/response shape per capture type

**Relevant to C3 Ingestion Layer and C2 Raw Context Vault**

- FHIR separates clinical artifact categories rather than using one universal clinical payload. `Observation` is the common structure for measurements and observations; its fields include clinically relevant time, performer, value, interpretation, note, body site, method, and data-absent reason. ([fhirtruck.com](https://fhirtruck.com/fhirdocs/fhir/R4/Observation?utm_source=openai))  
- FHIR `DiagnosticReport` is used for lab, pathology, and imaging reports, and it can include atomic results by referencing `Observation` resources. This creates a distinction between a lab panel/report artifact and individual result observations. ([hl7.org](https://hl7.org/fhir/R4/DiagnosticReport.html?utm_source=openai))  
- FHIR `DocumentReference` is metadata for a document and includes identifiers, status, type/category, subject, authorship, date, description, security labels, content attachment, and clinical context. ([hl7.org](https://hl7.org/fhir/R4/DocumentReference.html?utm_source=openai))  
- FHIR `Composition` organizes clinical/administrative content into sections with narrative and references, and the US Core clinical-notes guidance notes that clinical notes may appear in several FHIR resources, including `Composition`, `ClinicalImpression`, `DocumentReference`, and `DiagnosticReport`. ([hl7.org](https://hl7.org/fhir/R4/composition.html?utm_source=openai))  
- RFC 9457 supplies an external pattern for validation and domain errors: a problem-detail object with machine-readable fields such as `type`, `title`, `status`, `detail`, and `instance`, plus extensions. ([rfc-editor.org](https://www.rfc-editor.org/rfc/rfc9457.html?utm_source=openai))  
- RFC 9110 distinguishes creation responses from accepted-for-processing responses: `201 Created` is associated with completed resource creation, while `202 Accepted` indicates that processing has been accepted but not completed. ([httpwg.org](https://httpwg.org/specs/rfc9110.html?utm_source=openai))  

**Affected component implications, factual only**

- C3 request schemas can be compared against external health artifact categories: symptom-like observation, lab report plus lab observations, document metadata plus attachment, and note-like document/composition.  
- C2 write records can be compared against source-artifact models that preserve both raw content and metadata.  
- C4 processing can consume raw artifacts with type-specific downstream expectations, but the consulted sources do not prescribe where this project must draw the internal type boundary.

---

### Q2. Idempotency for re-submitted/retried capture

**Relevant to C3 Ingestion Layer and C2 Raw Context Vault**

- Stripe’s pattern stores the first result for an idempotency key and returns the same status/body for subsequent requests with the same key; it also compares incoming parameters to the original request and errors if they differ. ([docs.stripe.com](https://docs.stripe.com/api/idempotent_requests?++lang=node&utm_source=openai))  
- AWS EC2 uses a client token for optional idempotency on many mutating APIs; retries with the same token and same parameters do not perform additional actions, while retries with the same token and different parameters fail with an idempotency mismatch error. ([docs.aws.amazon.com](https://docs.aws.amazon.com/ec2/latest/devguide/ec2-api-idempotency.html?utm_source=openai))  
- Google AIP-155 describes a `request_id` as a unique customer-provided identifier used for deduplication, retry safety, and auditing; it recommends random UUIDs and notes that duplicate creates may return a current resource state rather than an identical historical response in some cases. ([google.aip.dev](https://google.aip.dev/155?utm_source=openai))  
- MDN describes `Idempotency-Key` as an HTTP request header for making POST/PATCH retries safe; MDN marks the feature experimental. ([developer.mozilla.org](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Idempotency-Key?utm_source=openai))  
- RFC 9562 UUIDv5 provides a deterministic namespace/name-based UUID mechanism, where the same canonical namespace/name input yields the same UUIDv5 value. ([ietf.org](https://www.ietf.org/rfc/rfc9562?utm_source=openai))  
- EventStoreDB’s append model treats identical append operations as idempotent based on `EventId` plus stream, and documents stronger guarantees when expected revision is specified rather than `ExpectedVersion.Any`. ([docs.kurrent.io](https://docs.kurrent.io/clients/tcp/dotnet/21.2/appending.html?utm_source=openai))  
- At-least-once delivery patterns assume duplicates can occur; the Idempotent Consumer pattern frames duplicate handling as part of correct consumer behavior. ([microservices.io](https://microservices.io/patterns/communication-style/idempotent-consumer.html?utm_source=openai))  

**Affected component implications, factual only**

- C3 can be compared against client-supplied key patterns, deterministic natural-key ID patterns, or event-ID/stream-based append idempotence patterns.  
- C2 append-only behavior makes the first successful write materially important because later correction is an additional record, not mutation of the existing raw record.  
- C4 consumers may still need idempotent handling even if C3/C2 dedupe write retries, because downstream processing may be retried or replayed.

---

### Q3. Provenance metadata written at ingest

**Relevant to C3 Ingestion Layer, C2 Raw Context Vault, and C4 Processing**

- W3C PROV-O’s core provenance concepts are entities, activities, and agents, with relationships such as used, generated by, derived from, primary source, and responsibility attribution. ([w3.org](https://www.w3.org/TR/prov-o/?utm_source=openai))  
- FHIR Provenance is based on W3C PROV and is used to record creation/update provenance for FHIR-defined resources; FHIR notes that multiple provenance records may exist for a resource or version. ([hl7.org](https://hl7.org/fhir/R4/provenance.html?utm_source=openai))  
- US Core describes provenance as supporting authenticity, trust, and reproducibility, with “last hop” guidance for practical exchange. ([hl7.org](https://www.hl7.org/fhir/us/core/STU6.1/basic-provenance.html?utm_source=openai))  
- FHIR Provenance includes target references, recorded time, agents, and entities; the R4B page explicitly lists entity roles such as derivation, revision, quotation, source, and removal, and records middleware provenance use cases. ([hl7.org](https://hl7.org/fhir/R4B/provenance.html?utm_source=openai))  
- FHIR `DocumentReference` and `Attachment` expose document/attachment metadata relevant to provenance and integrity: identifiers, author/date/context, content attachment, content type, size, hash, creation time, and URL or data. ([hl7.org](https://hl7.org/fhir/R4/DocumentReference.html?utm_source=openai))  

**Affected component implications, factual only**

- C3 ingest metadata can be compared against provenance models that distinguish the user/source artifact, the ingest activity, software/system actor, and any source document/entity used as input.  
- C2 raw records can be compared against source-linked provenance models that preserve target/source relationships and recorded timestamps.  
- C4 derived facts can be compared against W3C/FHIR derivation models that link derived entities back to raw entities and processing activities.

---

### Q4. Which C4 processing is synchronous vs. deferred

**Relevant to C3 Ingestion Layer, C2 Raw Context Vault, and C4 Processing**

- Azure’s asynchronous request-reply pattern says the API should validate the request and requested action before starting long-running processing; invalid requests should return immediate errors, while accepted long-running work should return `202 Accepted` with a status location. ([learn.microsoft.com](https://learn.microsoft.com/en-us/azure/architecture/patterns/asynchronous-request-reply?utm_source=openai))  
- Azure’s pattern also identifies status payload fields such as status, created time, and last-updated time, and mentions `Retry-After` to reduce excessive polling. ([learn.microsoft.com](https://learn.microsoft.com/en-us/azure/architecture/patterns/asynchronous-request-reply?utm_source=openai))  
- Google AIP-151 frames long-running operations as returning an operation object instead of blocking for the ultimate response; it separates errors that prevent operation start from errors during operation execution, which are stored in the operation error field. ([google.aip.dev](https://google.aip.dev/151?utm_source=openai))  
- RFC 9110 notes that HTTP has no facility for later re-sending a final status code from an asynchronous operation, which makes explicit operation/status resources or callbacks relevant when work continues after the initial response. ([httpwg.org](https://httpwg.org/specs/rfc9110.html?utm_source=openai))  
- RFC 9457 provides a standard shape for immediate validation/start errors but does not define deferred operation error bodies. ([rfc-editor.org](https://www.rfc-editor.org/rfc/rfc9457.html?utm_source=openai))  

**Affected component implications, factual only**

- C3 synchronous behavior can be compared against external patterns for request syntax validation, authorization/permission checks, idempotency-key conflict detection, and acceptance/creation response formation.  
- C2 synchronous behavior can be compared against patterns where the durable write/append is the boundary before returning success or acceptance.  
- C4 extraction, normalization, entity linking, scoring, and other potentially long-running or replayable processing can be compared against long-running operation and background-processing patterns. The consulted sources do not define a health-specific threshold for which clinical extraction steps must be synchronous.

---

## 4. Tradeoffs and open questions

### Request/response shape

- **Single generic capture envelope vs. type-specific payloads**
  - Generic envelope risk: may under-specify required fields for labs, documents, notes, and observations.
  - Type-specific risk: more schema surface area and versioning work.
- **Internal-native schema vs. FHIR-shaped schema**
  - FHIR-shaped risk: may expose interoperability complexity to product clients.
  - Internal-native risk: later mappings to FHIR/US Core provenance or clinical-note conventions may require translation decisions.
- **Raw artifact plus metadata vs. pre-normalized clinical fields at capture**
  - Raw-first risk: C4 has more deferred interpretation work.
  - Pre-normalized risk: C3 may embed clinical interpretation or normalization too early.

### Idempotency/dedupe

- **Client-supplied idempotency key vs. deterministic natural key**
  - Client key risk: retries are safe only if the client reuses the same key for the same logical operation.
  - Natural key risk: stable, collision-resistant natural keys may not exist for all capture types, especially free-text notes or repeated symptoms.
- **Store first response vs. return current state**
  - First-response storage risk: requires response persistence and retention policy.
  - Current-state response risk: may differ from the original response if later layers or status change.
- **Permanent vs. TTL-bounded idempotency**
  - Permanent risk: unbounded key/index retention.
  - TTL risk: same retry after pruning may create a new append unless another dedupe mechanism catches it.
- **Dedupe at C3 vs. C2 vs. both**
  - C3-only risk: concurrent or alternate ingestion paths may bypass the check.
  - C2-only risk: API semantics may be harder to express if the vault only exposes append conflicts.
  - Both risk: duplicated logic and mismatched conflict semantics.

### Provenance metadata

- **Minimal provenance vs. rich provenance**
  - Minimal risk: derived facts may not have enough context to support source-linked traceability.
  - Rich risk: more fields to validate, store, protect, and keep stable.
- **User-visible provenance vs. internal audit provenance**
  - User-visible risk: may require careful wording and redaction of technical details.
  - Internal-only risk: may not satisfy product expectations for source-linked memory.
- **Attachment hash choices**
  - FHIR R4 defines SHA-1 for `Attachment.hash`; stronger or additional hashes would be an internal extension decision not settled by the FHIR source.

### Sync vs. deferred C4 processing

- **Return after validation only vs. return after durable C2 append vs. return after initial C4 extraction**
  - Validation-only risk: accepted captures may later fail to persist unless status handling is explicit.
  - Durable-append risk: user may see success before derived memory is available.
  - Initial-extraction risk: slower response path and possible coupling of capture reliability to C4 availability.
- **Operation/status resource vs. simple capture response**
  - Operation resource risk: more API and UI state management.
  - Simple response risk: less visibility into deferred processing failures or pending states.
- **Synchronous clinical normalization**
  - Sync normalization risk: latency and accidental diagnostic/interpretive behavior in the write path.
  - Deferred normalization risk: raw record exists before derived facts are available, requiring UI and processing-state clarity.

## Approaches considered

_Grounded only in the recorded research above (FHIR Observation/DiagnosticReport/DocumentReference/Composition, W3C PROV-O, FHIR Provenance/Attachment, Stripe/AWS/Google AIP-155 idempotency, RFC 9562 UUIDv5, EventStoreDB append idempotence, Azure async request-reply, Google AIP-151, RFC 9110/9457, Idempotent Consumer)._

**Q1 — Request/response shape**
- **A1a. Single generic envelope:** one capture payload for all types. Pro: minimal surface. Con: under-specifies labs/documents/notes (FHIR separates these for a reason).
- **A1b. Type-specific payloads, internal-native schema, behind a common envelope:** distinct shapes for symptom/observation, lab (report + results), document (metadata + attachment), note — modeled on FHIR categories but not exposing FHIR to clients. Pro: matches real artifact categories, keeps clients simple, raw-first. Con: more schema/versioning.
- **A1c. FHIR-shaped payloads exposed to clients.** Pro: interoperability later. Con: pushes FHIR complexity onto the UI prematurely.

**Q2 — Idempotency/dedupe**
- **A2a. Client `Idempotency-Key` header only:** safe if client reuses the key. Con: a different client/path can still double-write.
- **A2b. Deterministic vault id (UUIDv5 from natural key) + append `ON CONFLICT DO NOTHING` at C2:** the durable store is the dedupe boundary. Pro: idempotent by construction even across retries/paths; matches event-store append idempotence. Con: needs a stable natural key (hard for free-text/repeated symptoms).
- **A2c. Both: client key + deterministic C2 id:** key carries intent + first-response replay; C2 id is the hard guarantee. Pro: belt-and-suspenders, safe under at-least-once. Con: two mechanisms to keep coherent.

**Q3 — Provenance at ingest**
- **A3a. Minimal (actor + timestamp).** Con: too thin for C5 source-linking/no-orphan-claims.
- **A3b. Rich W3C-PROV/FHIR-Provenance-aligned record:** source artifact (entity), ingest activity, actor (user + software agent), timestamp, correlation id, content hash. Pro: supports authenticity/traceability and C5. Con: more fields to store/validate.

**Q4 — Sync vs deferred C4**
- **A4a. Return only after C4 extraction.** Con: couples capture reliability to C4; latency; risks interpretive work in the write path.
- **A4b. Validate synchronously → durable C2 append → return `201` with the raw record id → C4 runs asynchronously (existing ingestion-worker/outbox):** Pro: capture is reliable and fast; raw record exists immediately; derived memory appears when C4 completes. Con: UI must show a "processing" state for derived facts.
- **A4c. `202 Accepted` + operation/status resource.** Pro: explicit async. Con: more API/UI state than needed when the raw append itself is fast.

## Decision

_Approved by user 2026-06-17._

- **Q1:** Adopt **A1b** — type-specific, internal-native capture payloads (symptom/observation, lab report + results, document + attachment metadata, note) behind one common capture envelope; raw-first (store the raw artifact + metadata; defer normalization to C4). Do not expose FHIR to clients, but keep field choices mappable to FHIR categories.
- **Q2:** Adopt **A2c** — clients send an `Idempotency-Key`; C2 computes a **deterministic UUIDv5 vault record id** from a natural key (actor + patient + capture-type + content hash + client key) and appends with `ON CONFLICT DO NOTHING`, so re-delivery/retry is idempotent by construction at the durable boundary. C3 checks the key for a fast first-response replay; C2 is the hard guarantee. Idempotency-key→response mapping is TTL-bounded; the natural-key dedupe at C2 is permanent.
- **Q3:** Adopt **A3b** — write a rich provenance record at ingest (source artifact entity, ingest activity, user + software agent, timestamp, correlation id, content hash) aligned to W3C PROV / FHIR Provenance, so every raw record is source-linked for C5.
- **Q4:** Adopt **A4b** — validate synchronously, perform the durable C2 append, return `201 Created` with the raw record id; C4 extraction/normalization runs asynchronously via the existing ingestion-worker/outbox. The UI shows the capture immediately and a "processing" state until derived memory is ready.

## Trade-offs accepted

- **Two idempotency mechanisms.** Carrying both a client `Idempotency-Key` and a deterministic C2 vault id is more to keep coherent than either alone. We accept it because the Vault is append-only and a duplicate raw record is permanent — the hard C2 guarantee is non-negotiable, and the client key buys fast first-response replay.
- **Natural-key edge cases.** Free-text notes and repeated identical symptoms may not have a naturally unique key; the content hash + timestamp + client key disambiguates, at the cost of occasionally treating two genuinely identical captures as distinct. We accept that over silently dropping a real second capture.
- **Deferred derived memory.** Returning `201` before C4 finishes means the UI must show a "processing" state and derived facts arrive slightly later. We accept this for capture reliability and speed (capture must not depend on C4 availability).
- **Rich provenance cost.** More fields to store/validate/protect at ingest. Accepted because C5 "no orphan claims" depends on it.

## Implementation notes

- **Components/repos:** C3 ingestion (`backend/packages/c3_ingestion/`, `backend/apps/ingestion-worker/`), C2 vault (`backend/packages/c2_vault/`, `backend/apps/vault-writer/`), new C13 endpoint in `backend/apps/api/`. Builds on WEL-95 adapter pattern.
- **Endpoint:** `POST` capture with a common envelope `{ capture_type, payload, occurred_at?, source }` + `Idempotency-Key` header. `capture_type ∈ {symptom, lab, document, note}` with a type-specific `payload` schema. Returns `201` `{ id, status: "captured", processing: "pending" }`.
- **Idempotency:** vault record id = `uuid5(NAMESPACE, actor_id|patient_id|capture_type|sha256(canonical_payload)|idempotency_key)`; write with `INSERT ... ON CONFLICT (id) DO NOTHING`; if conflict, return the existing record (200/201 idempotent replay). Persist key→response for a bounded TTL; the C2 natural-key uniqueness is permanent.
- **Provenance:** on append, write a provenance row: entity (the raw artifact), activity (ingest), agents (user actor + software/version), `recorded_at`, `correlation_id`, `content_hash` (sha-256; note FHIR R4 `Attachment.hash` is SHA-1 — we store sha-256 internally).
- **Processing:** validate synchronously (schema, authz, idempotency-key conflict) before the durable append; enqueue C4 via the existing outbox/ingestion-worker (must itself be idempotent on re-delivery). 
- **Frontend:** `CaptureModal` calls the endpoint, generates the `Idempotency-Key` (e.g. `crypto.randomUUID()`), shows captured-immediately + a "processing" affordance for derived memory.
- **Unblocks:** WEL-155 (capture write API endpoint) and wiring `CaptureModal` "Add to memory".

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
