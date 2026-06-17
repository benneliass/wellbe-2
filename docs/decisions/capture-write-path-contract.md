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


## Re-run research (user-provided, 2026-06-18)

> Recorded per research-protocol.mdc Section D. The approved decision above is unchanged. This independent re-run research was reviewed and is consistent with the approved decision; no supersede. Source file: `track-b-capture-research-result.md`.

# Track B: Capture write-path API contract research brief

Research date: 2026-06-17

Scope note: This brief is decision-neutral. It surveys external patterns for a capture write path from UI to ingestion adapter to an append-only raw vault. It does not select an architecture, contract, endpoint, schema, status-code policy, idempotency policy, or processing boundary. The WellBe product constraints supplied in the research packet are treated as local requirements: personal-first, source-linked, non-diagnostic, and raw inputs are append-only and never mutated.

## External patterns to examine

### 1. Request and response shape patterns for symptom, lab, document, and note capture

External health-data standards split the option space by the type of thing being captured rather than by a single generic payload.

- **Symptom or patient-reported observation shapes.** HL7 FHIR describes `Observation` as a resource for measurements, assertions, and simple observations, and notes that symptoms may be represented as either `Observation` or `Condition` depending on use; it also states that `Observation` is not intended to represent a diagnosis by itself ([FHIR Observation](https://fhir.hl7.org/fhir/observation.html)). FHIR `QuestionnaireResponse` is a different pattern: it records answers to a form or questionnaire and preserves the exact questions, order, and answers, while `Observation` focuses on the meaning of an answer ([FHIR QuestionnaireResponse](https://fhir.hl7.org/fhir/questionnaireresponse.html)). A newer HL7 symptoms implementation guide is specifically about patient-reported symptoms, but the cited build identifies itself as a continuous integration build that changes regularly, so it is useful context rather than a stable normative source ([HL7 FHIR Symptoms IG continuous build](https://build.fhir.org/ig/HL7/fhir-symptoms-ig/)).

- **Lab-result and diagnostic-report shapes.** FHIR separates atomic result values from report-level context. `Observation` is the atomic result pattern, while `DiagnosticReport` groups observations, specimen/request context, conclusions, images, and attached formatted reports for lab, imaging, pathology, and other diagnostic services ([FHIR Observation](https://fhir.hl7.org/fhir/observation.html), [FHIR DiagnosticReport](https://fhir.hl7.org/fhir/diagnosticreport.html)). This creates an external distinction between a structured lab value capture, a report capture, and a document scan of a report.

- **Document and binary-object shapes.** FHIR `DocumentReference` is an index and metadata resource for documents and serialized objects. It can reference or contain PDFs, scanned paper, images, video, audio, CSV, Word documents, clinical notes, and other binary or text artifacts; it also distinguishes document provenance from provenance of the reference record itself ([FHIR DocumentReference](https://fhir.hl7.org/fhir/documentreference.html)). This is relevant to capture flows that accept a file, photo, scan, imported PDF, or user-entered source document.

- **Free-text note shapes.** US Core clinical-note guidance describes the variability of clinical note exposure and identifies `DocumentReference` and `DiagnosticReport` as indexing mechanisms for clinical notes and reports ([US Core Clinical Notes](https://build.fhir.org/ig/HL7/US-Core/clinical-notes.html)). For WellBe-style personal notes, the external pattern space includes storing a note as a source document-like artifact, storing structured fields plus raw text, or recording form answers through a questionnaire-style shape; the cited sources define those categories but do not prescribe a WellBe-specific contract.

- **Response and error-shape patterns.** HTTP `201 Created` is the standard response when a request has been fulfilled and a new resource has been created, while `202 Accepted` is used when the request has been accepted but processing is not complete and may or may not ultimately be acted upon ([RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)). For errors, IETF `Problem Details` defines machine-readable HTTP error bodies using the `application/problem+json` media type ([RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html)); FHIR `OperationOutcome` is the FHIR-native pattern for conveying error, warning, or informational results from an operation ([FHIR OperationOutcome](https://fhir.hl7.org/fhir/operationoutcome.html)).

### 2. Idempotency patterns for append-only write paths

The sources show several distinct idempotency patterns, each with different assumptions.

- **Client-supplied idempotency key.** The IETF Idempotency-Key draft defines a request header whose value is a unique client-generated string used by a resource server to recognize retries of non-idempotent requests such as `POST` or `PATCH`; it also discusses key uniqueness, key expiry, request fingerprinting, replaying the original response, mismatch handling, concurrent-request conflict handling, and low-entropy-key risks ([IETF Idempotency-Key draft](https://www.ietf.org/archive/id/draft-ietf-httpapi-idempotency-key-header-07.html)). The current datatracker entry marks the document as an expired Internet-Draft as of the research date, so it is a work-in-progress source rather than an RFC ([IETF Datatracker entry](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/)). Stripe's API docs are a production example of this pattern: Stripe stores the first result for a key and returns the same status code and body on later requests with that key; it compares later parameters to the original request and suggests random UUID-style keys with sufficient entropy ([Stripe idempotent requests](https://docs.stripe.com/api/idempotent_requests)).

- **Caller request token rather than synthetic parameter hash.** Amazon's Builders' Library explains that hashing request parameters can conflate two intentionally separate operations with identical payloads; AWS APIs therefore often use a caller-supplied client request identifier, and they treat reuse of the same token with different parameters as an error ([AWS Builders' Library, Making retries safe with idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)).

- **Deterministic or name-based IDs.** RFC 9562 defines UUID version 5 as a deterministic UUID produced from a namespace identifier and a name using SHA-1, and notes that if SHA-1 is disallowed, name-based UUIDs can be constructed using UUID version 8 with a modern hash such as SHA-256 ([RFC 9562](https://www.rfc-editor.org/rfc/rfc9562.html)). The same RFC cautions that name-based UUIDs are not generally recommended as database primary keys when they depend on identifiers that are assumed to be stable but may later change ([RFC 9562](https://www.rfc-editor.org/rfc/rfc9562.html)).

- **Event ID plus stream/expected-version dedupe.** Event-store implementations expose another pattern. Kurrent/EventStoreDB documentation states that append operations can be made idempotent when duplicate appends use the same event ID and expected stream version, but it also states that idempotency is not guaranteed with the unconstrained `Any` expected version ([Kurrent/EventStoreDB appending documentation](https://docs.kurrent.io/clients/tcp/dotnet/21.2/appending)).

- **Server-side dedupe and fingerprints.** The IETF draft discusses an idempotency fingerprint derived from request payload, selected request parts, checksum, or signature; AWS's article warns that parameter-derived hashes can be the wrong semantic signal for caller intent in some APIs ([IETF Idempotency-Key draft](https://www.ietf.org/archive/id/draft-ietf-httpapi-idempotency-key-header-07.html), [AWS Builders' Library](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)).

### 3. Provenance and audit metadata patterns

External standards distinguish several provenance and audit roles that are relevant at ingest time.

- **Domain-neutral provenance graph.** W3C PROV defines provenance as records about the people, institutions, entities, and activities involved in producing, influencing, or delivering data. Its core model includes entities, activities, agents, times, derivations, responsibility, bundles, and collections ([W3C PROV-DM](https://www.w3.org/TR/prov-dm/), [W3C PROV overview](https://www.w3.org/TR/prov-overview/)).

- **FHIR Provenance.** FHIR `Provenance` is based on W3C provenance and is scoped to generation of FHIR resources. It identifies target resources generated by an activity, entities used, agents associated with the activity, activity timing, recorded time, policies, location, authorizations, patient, and agent roles ([FHIR Provenance](https://fhir.hl7.org/fhir/provenance.html)).

- **FHIR AuditEvent.** FHIR `AuditEvent` is oriented toward security/audit logging and can record who did what, when, why, against which patient/entity/source, and with what authorization/purpose of use. FHIR guidance notes that the patient affected by an auditable event should generally be included for accounting and access-log use cases ([FHIR AuditEvent](https://fhir.hl7.org/fhir/auditevent.html)).

- **Document-specific provenance distinction.** FHIR `DocumentReference` states that document provenance and the provenance of the reference/index record are distinct: one concerns the original document and its authorship or custody, the other concerns creation and maintenance of the metadata record ([FHIR DocumentReference](https://fhir.hl7.org/fhir/documentreference.html)).

- **Event-envelope metadata.** CloudEvents defines a common event envelope with required attributes including `id`, `source`, `specversion`, and `type`, optional attributes including `subject` and `time`, and extension attributes for additional metadata; it separates event context from domain-specific event data ([CloudEvents specification](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md)).

### 4. Synchronous versus deferred processing patterns for write APIs feeding append-only stores

The external sources draw a boundary between accepting or creating the durable source record and running downstream processing.

- **HTTP creation versus accepted-for-processing.** RFC 9110 defines `201 Created` for completed creation and `202 Accepted` for accepted but incomplete processing. It explicitly describes `202` as noncommittal and says there is no HTTP facility for later resending the final status code, which means APIs using `202` often need a separate status resource or polling pattern ([RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)).

- **Asynchronous request-reply.** Azure Architecture Center's asynchronous request-reply pattern validates the request before starting processing, returns `400` for invalid requests, returns `202 Accepted` with a `Location` header for a status endpoint when work is asynchronous, optionally includes `Retry-After`, and offloads work to a queue or another component. It also notes that idempotency on the initiating request can return the existing status resource rather than enqueueing duplicate work ([Azure Architecture Center, Asynchronous Request-Reply pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/asynchronous-request-reply)).

- **Long-running-operation APIs.** Microsoft Azure API Guidelines state that cloud APIs should embrace failure, that operations including `POST` should be idempotent, that synchronous create responses use `201 Created`, and that asynchronous operations return `202 Accepted` and expose operation-status resources. The guidelines also describe request validation at initiation, `operation-location`, `Retry-After`, status monitor resources, and conflict behavior when the same operation ID is reused with a different request body ([Microsoft Azure API Guidelines](https://github.com/microsoft/api-guidelines/blob/vNext/azure/Guidelines.md)).

- **Event sourcing and append-only processing.** Azure's event-sourcing pattern describes storing each state-changing event in an append-only event store, deriving current state by replaying the event stream, updating materialized views asynchronously, using compensating events instead of mutating prior events, and making event handlers idempotent because consumers may receive events more than once ([Azure Architecture Center, Event Sourcing pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)). Martin Fowler's event-sourcing article similarly describes recording every state change as an event sequence, rebuilding state from the log, and being careful about replayed events that would otherwise cause external side effects ([Martin Fowler, Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)).

## Evidence inventory

| Source | URL | What it covers | Context for WellBe decision | Limitations |
|---|---|---|---|---|
| IETF Idempotency-Key Internet-Draft | [URL](https://www.ietf.org/archive/id/draft-ietf-httpapi-idempotency-key-header-07.html) | Header syntax and responsibilities for retry-safe non-idempotent HTTP operations, including uniqueness, expiry, fingerprinting, replay, and error cases. | Directly relevant to capture retries from UI to ingestion adapter before an append-only vault write. | Expired Internet-Draft as of 2026-06-17, not an RFC; useful as an emerging pattern, not a stable standard. |
| IETF Datatracker entry for Idempotency-Key | [URL](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/) | Current datatracker metadata for the draft. | Establishes source status and recency. | Metadata source only; it does not define the contract itself. |
| Stripe idempotent requests | [URL](https://docs.stripe.com/api/idempotent_requests) | Production API behavior for idempotency keys: first-result replay, parameter comparison, key entropy, and pruning. | Concrete production precedent for create/update retries and response replay semantics. | Stripe-specific commercial API; not health-domain specific. |
| AWS Builders' Library: Making retries safe with idempotent APIs | [URL](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/) | Retry-safe API design, client request identifiers, late-arriving requests, token reuse with different parameters, and complexity tradeoffs. | Relevant to deciding whether idempotency expresses caller intent, payload identity, or server dedupe. | AWS service-design perspective; examples are not append-only health vaults. |
| RFC 9562: UUIDs | [URL](https://www.rfc-editor.org/rfc/rfc9562.html) | UUID versions including name-based deterministic UUIDv5 and UUIDv8 guidance; caveats about name-based IDs. | Relevant to deterministic ID strategies based on natural keys or namespaces. | Defines identifiers, not HTTP idempotency behavior or health provenance. |
| RFC 9110: HTTP Semantics | [URL](https://www.rfc-editor.org/rfc/rfc9110.html) | Semantics for `201 Created`, `202 Accepted`, `409 Conflict`, `422 Unprocessable Content`, `503 Retry-After`, and other HTTP behavior. | Baseline for synchronous create versus accepted-for-processing response semantics. | Generic HTTP standard; does not define WellBe-specific payloads. |
| RFC 9457: Problem Details for HTTP APIs | [URL](https://www.rfc-editor.org/rfc/rfc9457.html) | Machine-readable HTTP error response format using problem detail objects. | Candidate external error-shape pattern for non-FHIR endpoints. | Generic HTTP API standard; not health-specific. |
| FHIR Observation | [URL](https://fhir.hl7.org/fhir/observation.html) | Atomic observations, measurements, assertions, and relationship to DiagnosticReport and Condition. | Relevant to symptom captures, lab values, device readings, and derived observations. | FHIR resource semantics do not by themselves define a raw vault contract or UI payload. |
| FHIR QuestionnaireResponse | [URL](https://fhir.hl7.org/fhir/questionnaireresponse.html) | Captures exact questions, order, and answers from a questionnaire. | Relevant when symptom capture is form-like and exact prompt wording matters. | Not a general replacement for observations; dependent on questionnaire definitions. |
| HL7 FHIR Symptoms IG continuous build | [URL](https://build.fhir.org/ig/HL7/fhir-symptoms-ig/) | Patient-reported symptom modeling context. | Useful context for subjective symptom capture. | Continuous integration build, explicitly subject to change; not treated here as a stable normative source. |
| FHIR DiagnosticReport | [URL](https://fhir.hl7.org/fhir/diagnosticreport.html) | Diagnostic report-level context, atomic observations, specimens, images, conclusions, and attachments. | Relevant to lab report captures and the distinction between individual lab values and reports. | FHIR-specific resource; WellBe may store raw inputs before mapping to FHIR. |
| FHIR DocumentReference | [URL](https://fhir.hl7.org/fhir/documentreference.html) | Metadata and indexing for documents, scans, media, clinical notes, and binary objects; document provenance versus reference provenance. | Relevant to document/photo/PDF capture and provenance requirements at ingest. | Does not specify binary storage architecture or immutable vault behavior. |
| US Core Clinical Notes | [URL](https://build.fhir.org/ig/HL7/US-Core/clinical-notes.html) | Clinical note access patterns using DocumentReference and DiagnosticReport. | Relevant to note-like capture and document-index patterns. | US implementation guide context; not specifically for personal health memory notes. |
| FHIR OperationOutcome | [URL](https://fhir.hl7.org/fhir/operationoutcome.html) | FHIR-native operation result, warning, and error messages. | Candidate error-shape pattern if capture APIs use FHIR-style errors. | FHIR-specific; the resource itself is not designed as a persisted workflow object. |
| W3C PROV-DM | [URL](https://www.w3.org/TR/prov-dm/) | Domain-neutral provenance model: entities, activities, agents, derivation, responsibility, bundles, and timing. | Foundation for provenance concepts independent of FHIR. | Abstract model; implementation profiles are needed for concrete API fields. |
| W3C PROV overview | [URL](https://www.w3.org/TR/prov-overview/) | Overview of provenance use cases including trust, quality assessment, derivation, attribution, and reproducibility. | Supports the source-linked and no-orphan-claims product principle at a conceptual level. | Overview rather than detailed API contract. |
| FHIR Provenance | [URL](https://fhir.hl7.org/fhir/provenance.html) | Provenance for generated FHIR resources: target, entity, activity, agent, timing, policies, location, authorization, patient. | Relevant to ingest provenance and later derived facts that trace to raw sources. | Scoped to FHIR resources; WellBe may need non-FHIR raw-source provenance. |
| FHIR AuditEvent | [URL](https://fhir.hl7.org/fhir/auditevent.html) | Security and access audit events with agents, source, patient, entity, purpose, authorization, and outcome. | Relevant to capture auditing, source access, actor accountability, and purpose-of-use metadata. | Audit logging is distinct from provenance of the captured source itself. |
| CloudEvents specification | [URL](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md) | Common event envelope with required `id`, `source`, `type`, and optional `subject`, `time`, extensions, and data content attributes. | Relevant if ingestion emits events from C3/C2 to C4 workers. | Event-envelope standard, not a health-data content model. |
| Azure Architecture Center: Asynchronous Request-Reply | [URL](https://learn.microsoft.com/en-us/azure/architecture/patterns/asynchronous-request-reply) | `202 Accepted`, status endpoint, queue offload, `Retry-After`, validation before async work, idempotent initial requests. | Relevant to deciding whether capture returns after raw write or after downstream processing. | Cloud architecture pattern, not a formal internet standard. |
| Microsoft Azure API Guidelines | [URL](https://github.com/microsoft/api-guidelines/blob/vNext/azure/Guidelines.md) | REST API patterns for idempotent operations, synchronous create, long-running operations, operation status resources, and retry behavior. | Concrete API-style guidance for status resources and operation identifiers. | Vendor guideline; implementation style may not match WellBe constraints. |
| Azure Architecture Center: Event Sourcing | [URL](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing) | Append-only event store, immutable events, replay, materialized views, compensating events, event-handler idempotency. | Directly relevant to an immutable raw vault and downstream processing pipeline. | General architecture pattern; not specific to health data or personal data controller models. |
| Kurrent/EventStoreDB appending documentation | [URL](https://docs.kurrent.io/clients/tcp/dotnet/21.2/appending) | Append semantics, expected stream version, duplicate event IDs, idempotent append behavior, and limitations with unconstrained expected version. | Concrete append-only store behavior relevant to preventing duplicate raw writes. | Product-specific and versioned; not a universal event-store standard. |
| Martin Fowler: Event Sourcing | [URL](https://martinfowler.com/eaaDev/EventSourcing.html) | Event log as state-change record, rebuilding state, temporal queries, replay, and side-effect hazards. | Useful background on event-sourced append-only systems and replay boundaries. | Explanatory article, not a standard or API specification. |

## Decision-neutral findings

### Decision question 1: Request and response shape per capture type

**General observation across capture types.** The sources distinguish between raw source material, structured clinical statements, grouped reports, and documents. FHIR `Observation`, `DiagnosticReport`, `DocumentReference`, and `QuestionnaireResponse` each cover different semantics, and none of the sources says that a raw ingest API must use those resources verbatim. For WellBe, this means the external evidence can inform field categories and later mappings, while the C3-to-C2 contract still has to define what is raw input, what is metadata, and what is derived later ([FHIR Observation](https://fhir.hl7.org/fhir/observation.html), [FHIR DiagnosticReport](https://fhir.hl7.org/fhir/diagnosticreport.html), [FHIR DocumentReference](https://fhir.hl7.org/fhir/documentreference.html), [FHIR QuestionnaireResponse](https://fhir.hl7.org/fhir/questionnaireresponse.html)).

**Symptom capture.** External patterns split symptom capture into at least three representational modes:

- A symptom can be treated as an observation or assertion about the person. FHIR states that symptoms may be represented as `Observation` or `Condition` depending on context, and that `Observation` is not itself a diagnosis ([FHIR Observation](https://fhir.hl7.org/fhir/observation.html)).
- If the UI asks structured questions, `QuestionnaireResponse` preserves the exact questions, ordering, and answers, which is different from converting answers into observations ([FHIR QuestionnaireResponse](https://fhir.hl7.org/fhir/questionnaireresponse.html)).
- A symptom-specific HL7 guide exists, but the cited page is a changing continuous build, so it is evidence of an active modeling direction rather than a stable contract source ([HL7 FHIR Symptoms IG continuous build](https://build.fhir.org/ig/HL7/fhir-symptoms-ig/)).

Applied to components, C3 can be viewed as the place where a manual symptom submission arrives with source and actor context; C2 is the place where the original user input and metadata remain immutable; C4 is the place where symptom terms, body location, timing, severity, quality, and confidence could later be extracted or normalized. The sources support this division only at the level of pattern; they do not define WellBe's exact fields.

**Lab capture.** FHIR distinguishes a single atomic lab result from the report that groups results and context. `Observation` covers atomic values and assertions, and `DiagnosticReport` covers a diagnostic report that can include observations, specimen details, request details, conclusions, images, and attached formatted reports ([FHIR Observation](https://fhir.hl7.org/fhir/observation.html), [FHIR DiagnosticReport](https://fhir.hl7.org/fhir/diagnosticreport.html)). This supports an option space in which a lab capture could be raw structured values, a full report, an attachment, or some combination. A design decision remains about whether C3 accepts structured lab fields at write time, raw document/file evidence, or both, and whether C4 later extracts atomic facts from the stored raw source.

**Document capture.** `DocumentReference` is the closest consulted health standard for representing a captured PDF, photo, scan, image, audio file, CSV, or other document-like source. It provides metadata about the document and can include or point to the content; it also calls out the distinction between provenance of the underlying document and provenance of the reference/index record ([FHIR DocumentReference](https://fhir.hl7.org/fhir/documentreference.html)). For WellBe's C3/C2 boundary, the source suggests metadata categories such as document type, date, author/custodian when known, content format, and integrity metadata; it does not prescribe whether the immutable vault stores bytes inline, stores object-storage pointers plus hashes, or stores both.

**Free-text note capture.** US Core clinical-note guidance describes notes as variable artifacts exposed through `DocumentReference` and `DiagnosticReport` indexing patterns ([US Core Clinical Notes](https://build.fhir.org/ig/HL7/US-Core/clinical-notes.html)). FHIR `DocumentReference` also covers clinical notes and other text artifacts ([FHIR DocumentReference](https://fhir.hl7.org/fhir/documentreference.html)). For a personal WellBe note, the external evidence supports treating the note as source material that can be linked to later derived facts; it does not require the note to be classified as a clinical note, diagnostic report, questionnaire response, or observation at ingest.

**Response shapes.** The consulted HTTP sources separate completed creation from accepted asynchronous work. `201 Created` means a new resource has been created, and the primary resource is identified by `Location` or the target URI; `202 Accepted` means processing has not completed and may need a status monitor ([RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)). The Azure asynchronous pattern adds an operational shape for `202`: return a status endpoint in `Location`, optionally `Retry-After`, and a status resource that can later show progress, errors, or completion ([Azure Architecture Center, Asynchronous Request-Reply](https://learn.microsoft.com/en-us/azure/architecture/patterns/asynchronous-request-reply)). Error bodies have at least two external pattern families: generic `Problem Details` for HTTP APIs and FHIR `OperationOutcome` for FHIR-style APIs ([RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html), [FHIR OperationOutcome](https://fhir.hl7.org/fhir/operationoutcome.html)).

**Affected components.** C3 is affected because it owns adapter-specific request validation, source-type classification, idempotency evaluation, and creation of the raw ingest record. C2 is affected because the response has to identify the immutable raw record or accepted write operation without implying later mutation. C4 is affected if the response also exposes an extraction/enrichment job status, but the consulted sources distinguish raw creation from downstream asynchronous work rather than treating derived processing as part of the same raw write.

### Decision question 2: Idempotency against an append-only vault

**Client-supplied key pattern.** The IETF draft, Stripe docs, AWS article, and Azure API guidelines all discuss some form of caller-supplied idempotency or repeatability identifier for retrying non-idempotent writes ([IETF Idempotency-Key draft](https://www.ietf.org/archive/id/draft-ietf-httpapi-idempotency-key-header-07.html), [Stripe idempotent requests](https://docs.stripe.com/api/idempotent_requests), [AWS Builders' Library](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/), [Microsoft Azure API Guidelines](https://github.com/microsoft/api-guidelines/blob/vNext/azure/Guidelines.md)). The common mechanics in these sources are: the client supplies a unique value, the server records enough state to recognize retries, a repeated matching request gets a semantically equivalent or replayed response, and reuse of the same key with a different payload is treated as an error or conflict.

**Fingerprint and payload-comparison pattern.** The IETF draft describes an idempotency fingerprint derived from the request payload, selected request fields, checksum, or signature; Stripe compares later request parameters against the original request and errors if they differ ([IETF Idempotency-Key draft](https://www.ietf.org/archive/id/draft-ietf-httpapi-idempotency-key-header-07.html), [Stripe idempotent requests](https://docs.stripe.com/api/idempotent_requests)). This pattern is distinct from using a payload hash as the sole semantic identifier. AWS explicitly warns that two requests with identical parameters can represent distinct caller intent in some APIs, so a caller request identifier can be more expressive than a synthetic parameter hash ([AWS Builders' Library](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)).

**Key expiry and retry horizon.** The IETF draft states that servers may define time-based expiry for idempotency keys and should publish the expiry policy; Stripe says keys may be removed after they are at least 24 hours old; AWS discusses retaining enough request history to handle late-arriving requests and ties some retention decisions to resource lifetimes or expected retry windows ([IETF Idempotency-Key draft](https://www.ietf.org/archive/id/draft-ietf-httpapi-idempotency-key-header-07.html), [Stripe idempotent requests](https://docs.stripe.com/api/idempotent_requests), [AWS Builders' Library](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)). For an append-only C2 vault, the unresolved design choice is how long C3 must remember idempotency state to prevent duplicate permanent raw records from delayed retries.

**Deterministic ID pattern.** RFC 9562 provides a standards-based way to generate name-based deterministic UUIDs, including UUIDv5 and UUIDv8 approaches, but the RFC also cautions that name-based UUIDs can be problematic as database primary keys if the chosen natural keys are less stable than expected ([RFC 9562](https://www.rfc-editor.org/rfc/rfc9562.html)). This leaves an option space for deterministic vault source IDs based on a namespace plus natural key, but it also exposes the risk that the natural key must have stable semantics and must not collapse distinct captures into one identity.

**Append-store concurrency pattern.** EventStoreDB/Kurrent documentation describes idempotent append behavior when an append retries with the same event ID and expected stream version; it also notes that idempotency guarantees are lower when appending with an unconstrained expected version ([Kurrent/EventStoreDB appending documentation](https://docs.kurrent.io/clients/tcp/dotnet/21.2/appending)). Azure's event-sourcing pattern also notes that duplicate entity or event IDs should be rejected and that event handlers should be idempotent because consumers may receive events more than once ([Azure Architecture Center, Event Sourcing pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)).

**Error and conflict semantics.** The IETF draft gives specific examples for idempotency errors: missing required key, key reused with a different payload, and retry while the original request is still outstanding; these map to client-visible failures such as `400`, `422`, and `409` in the draft ([IETF Idempotency-Key draft](https://www.ietf.org/archive/id/draft-ietf-httpapi-idempotency-key-header-07.html)). RFC 9110 defines `422 Unprocessable Content` as a case where the server understands the content type and syntax but cannot process the instructions, and defines conflict semantics for `409` ([RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)). The sources do not require one exact status mapping for WellBe, but they do show that mismatch and concurrent retry cases are normally specified explicitly.

**Affected components.** C3 is the natural boundary where idempotency state, request fingerprints, key scope, and mismatch rules can be enforced before a C2 append. C2 is affected because a duplicate append cannot be repaired by mutation under the WellBe raw-immutability constraint. C4 is affected because downstream workers should also be idempotent; event-sourcing guidance assumes consumers can see duplicate events and should not create duplicate projections or orphan derived facts ([Azure Architecture Center, Event Sourcing pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)).

### Decision question 3: Provenance metadata written at ingest

**Common provenance dimensions.** W3C PROV identifies entities, activities, agents, derivations, responsibility, and timing as core provenance concepts ([W3C PROV-DM](https://www.w3.org/TR/prov-dm/)). FHIR `Provenance` maps similar concepts to health data by identifying targets, entities used, agents, activity, occurred time, recorded time, policies, location, authorizations, patient, and agent roles ([FHIR Provenance](https://fhir.hl7.org/fhir/provenance.html)). FHIR `AuditEvent` covers audit-style metadata such as agent, source, patient, entity, authorization/purpose, outcome, and time ([FHIR AuditEvent](https://fhir.hl7.org/fhir/auditevent.html)). Together, the sources identify a provenance field space rather than a single mandatory WellBe ingest schema.

**Source-linked raw and derived records.** W3C PROV's concepts of entity, activity, derivation, and agent provide a generic way to represent that a later fact or signal was derived from a raw source by a processing activity ([W3C PROV-DM](https://www.w3.org/TR/prov-dm/)). FHIR `Provenance` similarly represents target resources generated by an activity and entities used by that activity ([FHIR Provenance](https://fhir.hl7.org/fhir/provenance.html)). This is relevant to WellBe's no-orphan-claims guardrail: the raw record in C2 can be the source entity, and C4 outputs can carry derivation links back to that entity. The sources do not dictate the exact identifier names or storage layout.

**Actor and agency.** FHIR `Provenance` includes agents and agent roles, including who acted and on whose behalf an action occurred ([FHIR Provenance](https://fhir.hl7.org/fhir/provenance.html)). W3C PROV distinguishes agents from activities and entities ([W3C PROV-DM](https://www.w3.org/TR/prov-dm/)). For a personal-first product, the field space implied by these standards includes the data controller/person, the submitting actor, any caregiver or delegated actor, the adapter or system agent, and any device or source system involved. The standards provide concepts; they do not decide which WellBe actors must be required on every capture type.

**Time fields.** W3C PROV includes activity and entity timing concepts ([W3C PROV-DM](https://www.w3.org/TR/prov-dm/)). FHIR `Provenance` distinguishes occurred time from recorded time, while CloudEvents distinguishes event occurrence time from transport/envelope context ([FHIR Provenance](https://fhir.hl7.org/fhir/provenance.html), [CloudEvents specification](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md)). For capture, this creates an external distinction between when the user says the health event occurred, when the user entered it, when the ingestion adapter received it, and when C2 committed it. The sources do not collapse those timestamps into one field.

**Document provenance versus index provenance.** FHIR `DocumentReference` explicitly separates the provenance of the original document from the provenance of the `DocumentReference` resource that indexes it ([FHIR DocumentReference](https://fhir.hl7.org/fhir/documentreference.html)). For document capture, this distinction maps to open questions such as: who authored or issued the document, who uploaded it, when the file was received, what adapter wrote the reference, what binary hash proves content integrity, and whether later OCR/extraction provenance should be represented separately.

**Audit versus provenance.** FHIR `AuditEvent` and `Provenance` overlap but have different purposes: audit events focus on security/accounting of system actions, while provenance focuses on how a resource was generated and what inputs and agents were involved ([FHIR AuditEvent](https://fhir.hl7.org/fhir/auditevent.html), [FHIR Provenance](https://fhir.hl7.org/fhir/provenance.html)). This leaves a design choice about whether WellBe writes one combined ingest metadata record, separate provenance and audit records, or a raw vault record plus separate audit log entries.

**Event-envelope provenance.** If C3 or C2 emits a message to C4, CloudEvents offers an event-envelope pattern with stable `id`, `source`, `type`, optional `subject`, `time`, content type, schema, and extensions ([CloudEvents specification](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md)). This evidence is about event interoperability and routing; it does not replace health-specific provenance or raw-source metadata.

**Affected components.** C3 is affected because it observes the submitter, source adapter, request metadata, idempotency key, content type, client context, and adapter version. C2 is affected because provenance captured at append time becomes part of the immutable raw source record or an immutable linked metadata record. C4 is affected because its derived facts, signals, quality scores, and confidence scores need source links back to C2 and may need their own processing-activity provenance.

### Decision question 4: Synchronous versus deferred processing boundary

**What external HTTP patterns put before the response.** The Azure asynchronous request-reply pattern validates the request before starting asynchronous work and returns `400` for invalid requests; the Azure API Guidelines similarly say long-running operations should do as much validation as practical at initiation ([Azure Architecture Center, Asynchronous Request-Reply](https://learn.microsoft.com/en-us/azure/architecture/patterns/asynchronous-request-reply), [Microsoft Azure API Guidelines](https://github.com/microsoft/api-guidelines/blob/vNext/azure/Guidelines.md)). In a capture context, the source-backed pattern space includes synchronous authentication/authorization, shape validation, content-type and size checks, idempotency-key validation, required provenance presence, and the durable raw append itself. The sources do not specify exactly which WellBe validations are mandatory before C2 append.

**What external patterns defer.** Azure's event-sourcing pattern describes continuing after appending events while background tasks handle materialized views, integration, and other event handlers; it also emphasizes eventual consistency and idempotent event handlers ([Azure Architecture Center, Event Sourcing pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)). The asynchronous request-reply pattern offloads long work to queues and exposes progress through a status endpoint ([Azure Architecture Center, Asynchronous Request-Reply](https://learn.microsoft.com/en-us/azure/architecture/patterns/asynchronous-request-reply)). For WellBe, this maps to C4 activities such as OCR, entity extraction, normalization, confidence scoring, quality scoring, dedupe analysis beyond the write contract, and derived-fact generation as candidates for deferred processing. This is a mapping from external patterns to WellBe components, not a source-mandated boundary.

**Response status and observability.** RFC 9110's `202 Accepted` is explicitly noncommittal, so a client cannot infer final success from `202` alone ([RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)). Azure's asynchronous pattern therefore uses a `Location` status endpoint and optionally `Retry-After`, and the Azure API Guidelines use status monitor resources for long-running operations ([Azure Architecture Center, Asynchronous Request-Reply](https://learn.microsoft.com/en-us/azure/architecture/patterns/asynchronous-request-reply), [Microsoft Azure API Guidelines](https://github.com/microsoft/api-guidelines/blob/vNext/azure/Guidelines.md)). If WellBe separates raw capture from C4 processing, the external pattern space includes returning the raw C2 source identifier, returning a C4 job/status identifier, or returning both; the sources do not choose one.

**Write first, derive later.** Event-sourcing sources treat immutable events as the system of record and derive current state or materialized views by replaying or consuming events ([Azure Architecture Center, Event Sourcing pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing), [Martin Fowler, Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)). This aligns with the supplied WellBe constraint that raw inputs are never overwritten and corrections layer on as new records, but it also exposes a risk: malformed events are permanent, and later schema evolution needs versioning, tolerant readers, upcasting, or compensating events rather than in-place mutation ([Azure Architecture Center, Event Sourcing pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)).

**At least once delivery and worker idempotency.** Event-sourcing guidance states that event consumers may be called more than once and should be idempotent ([Azure Architecture Center, Event Sourcing pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)). Martin Fowler also notes that replaying events can accidentally repeat external side effects if handlers do not distinguish replay from live processing ([Martin Fowler, Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)). This affects C4 worker contracts independently of the UI-to-C3 idempotency contract: even if C3 prevents duplicate raw records, C4 still needs dedupe or idempotent projection behavior for retries and replays.

## Tradeoffs and open questions

| Decision area | Option space visible in the sources | Potential benefit | Risk or unresolved question |
|---|---|---|---|
| Endpoint granularity | One polymorphic capture endpoint, per-type endpoints for symptom/lab/document/note, or a common envelope plus type-specific body. | A common envelope can standardize idempotency and provenance; type-specific bodies can make validation clearer. | A common endpoint can under-specify capture-type semantics; per-type endpoints can duplicate cross-cutting provenance and idempotency logic. |
| Payload basis | WellBe-native raw capture schema, FHIR-shaped input, or FHIR-inspired field categories with raw source preserved separately. | FHIR-inspired shapes align with external health semantics for observations, reports, documents, and questionnaire answers. | FHIR resources may imply clinical semantics or derived normalization at ingest that WellBe may want to defer; a native schema needs explicit mapping rules. |
| Symptom representation | Observation-like assertion, questionnaire answer set, note-like raw text, or later C4-derived fact from a raw note. | Supports either semantic capture or exact user-question capture. | Observation-like fields may over-structure subjective user input; questionnaire responses preserve form wording but may not directly represent the symptom as a normalized fact. |
| Lab representation | Atomic lab value, full diagnostic report, document/photo/PDF source, or combined structured-plus-document capture. | Separates raw evidence from later normalized lab facts. | If structured values are accepted at ingest, the contract must decide how they remain source-linked to the original lab source and whether user-entered values are raw claims or derived facts. |
| Document storage | Store bytes in the vault, store object-storage pointer plus hash, store both, or store a metadata record that references immutable content elsewhere. | DocumentReference-like patterns expose content metadata and integrity concepts. | Pointer-only designs need guarantees that the referenced bytes remain immutable and retrievable; byte storage raises size, privacy, and retention questions. |
| Response semantics | `201 Created` after durable C2 append, `202 Accepted` with a status resource, or a mixed response that includes raw source and processing status. | `201` is clear for completed raw creation; `202` fits deferred C4 work. | `202` is noncommittal unless status semantics are precise; `201` can be misleading if the UI expects extraction or indexing to be complete. |
| Error format | RFC 9457 Problem Details, FHIR OperationOutcome, or a WellBe-native error object. | Problem Details is generic and HTTP-native; OperationOutcome aligns with FHIR-style clients. | Multiple error formats complicate clients; a single format may not satisfy both FHIR and non-FHIR consumers. |
| Idempotency key placement | HTTP `Idempotency-Key` header, body field, operation ID, or capture-source ID. | A header follows the emerging IETF/Stripe-style pattern; a body field can be included in signed/enveloped requests. | Header-only keys may be dropped by intermediaries or clients; body-only keys may be less reusable across API infrastructure. |
| Idempotency key scope | Global key, per-user key, per-actor key, per-adapter key, per-capture-type key, or per-target-stream key. | Narrow scope can reduce accidental collisions; broad scope can simplify lookup. | The wrong scope can either collapse distinct captures or fail to dedupe real retries. The sources do not define a health-vault-specific scope. |
| Idempotency retention | Short TTL such as 24 hours, longer retry horizon, or retention tied to raw source lifetime. | Short TTL limits storage and privacy exposure; longer retention protects against late retries. | In an append-only vault, retries after expiry can create permanent duplicates unless another dedupe mechanism exists. |
| Key reuse with changed payload | Reject as conflict/error, replay original response, create a new raw record, or require a new key. | Explicit mismatch rules make client behavior predictable. | Replaying a prior response for changed input can hide client bugs; creating a new record with reused key breaks idempotency semantics. |
| Deterministic natural-key IDs | UUIDv5/UUIDv8 from namespace plus natural key, event ID from content hash, or server-issued random IDs plus idempotency index. | Deterministic IDs can remove the need to persist every retry key separately. | Natural keys may be unstable or semantically ambiguous; identical payloads can be distinct user intent. RFC 9562 and AWS both expose these concerns. |
| Server-side dedupe | Dedupe by exact payload hash, normalized fingerprint, client token plus fingerprint, or event-store expected version. | Can catch some duplicates even when clients retry poorly. | Server dedupe can become a clinical or semantic judgment if normalization is aggressive; weak dedupe can allow permanent duplicates. |
| Append concurrency | Use expected stream/version checks, unique event IDs, database uniqueness constraints, or adapter-level locks. | Event-store patterns show how duplicate appends can be rejected before persistence. | Unconstrained appends can reduce idempotency guarantees; strict concurrency can increase conflict cases the UI must handle. |
| Provenance minimum | Minimal actor/source/time metadata, W3C PROV-like entity/activity/agent graph, FHIR Provenance-like fields, separate AuditEvent, or all of these in linked records. | Rich provenance supports traceability and source-linked derived facts. | Too little provenance creates orphan claims; too much required metadata can block capture when the user only has partial context. |
| Document provenance split | One provenance record for the upload event, separate provenance for the original document, or a combined record. | FHIR DocumentReference explicitly identifies this distinction. | Combining them can blur who created the document versus who uploaded it; separating them increases contract complexity. |
| Synchronous validation depth | Validate only syntax/auth/idempotency, validate domain fields too, or run extraction/normalization before returning. | Shallow validation preserves capture speed; deeper validation catches permanent bad writes earlier. | Running C4-like processing synchronously can make the write path slow and brittle; shallow validation can admit malformed but immutable raw records. |
| C4 processing trigger | Emit CloudEvents-style event from C2 append, enqueue adapter-specific job, poll vault for new records, or return no job status. | Event envelopes standardize routing metadata and downstream processing. | Event delivery is at least once in many systems, so C4 consumers still need idempotency and replay controls. |
| Derived-fact source linkage | Store links from every C4 output to raw C2 source IDs, store a PROV-style derivation graph, or embed provenance in each derived object. | Maintains the no-orphan-claims invariant. | Link-only models may omit processing context; full provenance graphs can be heavier to query and maintain. |
| Correction model | Append a new correction record, append a compensating event, append supersession metadata, or append a new source with explicit relationship to the old one. | Event-sourcing patterns support correction without mutating old events. | The contract must define how clients discover current interpretation without treating the raw source as deleted or changed. |
| Schema evolution | Version the raw capture envelope, use data schema links, maintain tolerant readers/upcasters, or migrate with new immutable records. | Event-sourcing and CloudEvents patterns expose ways to handle schema drift. | In-place mutation conflicts with raw immutability; unversioned schemas make later C4 replay risky. |
| Personal-data retention | Keep raw append-only records forever, separate personal data from event metadata, encrypt per user/source, or use crypto-shredding for erasure scenarios. | Event-sourcing guidance notes that separating sensitive personal data from append-only events can reduce deletion conflict. | Health data may create legal and product obligations that conflict with indefinite append-only raw storage; this brief does not resolve those obligations. |
| Replay and side effects | Treat C4 as pure projection, mark replay mode, or isolate external side effects behind replay-aware gateways. | Fowler's event-sourcing article identifies replay side effects as a known hazard. | Without replay boundaries, reprocessing raw records can duplicate notifications, derived facts, or external writes. |

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
