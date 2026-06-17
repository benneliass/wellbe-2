# Research Brief — Track B: Capture write-path API contract (UI → ingestion adapter → append-only Vault)

> **How to use this file:** copy everything below the line into your research tool
> (ChatGPT/Gemini/Claude/Perplexity, web search on). It is fully self-contained — no
> access to our codebase is required. Paste the result back and it will be recorded
> verbatim into the decision record `docs/decisions/capture-write-path-contract.md` (Spike WEL-161).

---

## YOUR TASK (read first)

You are a research assistant producing a **DECISION-NEUTRAL research brief** for a software design decision. Everything below is context. Your job is to **actually perform research** (use web search to find real, citable sources) and **return findings — not to restate this packet, not to describe how you would research, and not to ask whether to proceed.**

Produce a brief with these sections, grounded only in sources you actually consulted:

1. **External patterns to examine** — established patterns/standards relevant to each decision question.
2. **Evidence inventory** — a table of concrete sources (name, URL, what it covers, context, limitations).
3. **Decision-neutral findings** — what the sources say, mapped to the decision questions and the affected components. Factual only.
4. **Tradeoffs and open questions** — the unresolved choices the maintainers must make, and the risks of each direction.

**HARD CONSTRAINT:** do **not** propose, recommend, or choose a final answer/architecture/contract for any decision question. Present the option space and the evidence; the human decides. Honor the product's identity guardrails (personal-first, source-linked, non-diagnostic; **raw immutability — the store is append-only and never mutated**). Cite sources inline.

**OUTPUT FORMAT — deliver as a downloadable file:** write the complete brief to a **downloadable Markdown (`.md`) file** named **`track-b-capture-research-result.md`** and give me a download link/button. Do not put the brief only in the chat body — I need the file to download. Use the four section headings above as `##` Markdown headings, and keep all source citations as inline Markdown links.

---

## PRODUCT CONTEXT — what WellBe is

WellBe is a **Patient-Centered Health Investigation OS**. Its core is a **Personal Shared Health Memory OS**: a user-controlled memory layer for an individual's health context. **The individual is always the data controller.** It is **not** a diagnosis engine or EHR.

**Operating loop:** Capture → Connect → Investigate → Clarify → Close → Correct. This feature is the **Capture** step — the entry point of WellBe's "Data Factory."

**Non-negotiable design principles relevant here:**
- **Raw data immutability** — original inputs are never overwritten; the raw store is **append-only**.
- **Source-linked** — every derived fact traces back to a raw source ("no orphan claims").
- **Correct, don't hide** — corrections layer on top as new records; they never mutate or delete the original.

## THE FEATURE — the capture write-path

When a user logs something (a symptom, a lab result, a document, a free-text note) via the capture UI ("Log something" / "Add to memory"), that input must be **durably persisted into the append-only Raw Context Vault** through an ingestion adapter, with full provenance. Today the capture modal collects input but does **not** persist it. This research informs the **write-path API contract**: request/response shapes, idempotency, provenance, and what processing happens synchronously vs. later.

## ARCHITECTURE CONTEXT — the components this touches

The capture write-path runs through three core components:

- **C3 — Ingestion Layer.** Source-type adapters (manual, document, SMS, device, FHIR, environmental) that write into the Vault. Everything that enters WellBe goes through here; no feature bypasses it.
- **C2 — Raw Context Vault.** The **immutable, append-only** store of every raw input with full provenance. **Never mutated.**
- **C4 — Processing Pipeline.** Extracts entities, facts, and signals from raw context and computes quality/confidence scores. Runs *after* the raw input is captured.

**Blast radius:** writes into an append-only store are **permanent**. A non-idempotent or under-specified write contract produces permanent duplicated/orphaned raw context and **cannot be repaired by mutation after the fact**.

**Already exists in the system:** a vault-writer service and an ingestion-worker service run in the cluster; an ingestion-adapter pattern is already decided. The capture UI exists but does not yet persist.

**Missing (what this decision must define):**
- The capture **write API endpoint** and its **request/response contract per capture type**.
- The **idempotency / dedupe** strategy against the append-only Vault.
- The **provenance metadata** written at ingest.
- The **synchronous vs. deferred** processing boundary.

## THE DECISION QUESTIONS

1. **Request/response shape per capture type** — symptom, lab, document, note. What should each look like?
2. **Idempotency** — how is a re-submitted/retried capture made idempotent against an append-only store? (e.g. client-supplied idempotency key, deterministic/UUIDv5 id derived from a natural key, server dedupe.) What are the established patterns and their tradeoffs?
3. **Provenance metadata** — what provenance should be written at ingest (source, actor, timestamps, device, capture context), and what standards exist (e.g. W3C PROV, FHIR Provenance)?
4. **Sync vs. deferred processing** — which processing should run synchronously *before the write returns* vs. be deferred to async workers? What are the established patterns for write APIs feeding an event/append-only store?

## STAKES

The Vault cannot be mutated to repair a bad write. A non-idempotent or under-specified contract produces **permanent orphaned/duplicated raw context** and breaks the "every fact traces to a source" guarantee.

## WHERE TO LOOK (research directions, not answers)

- **Idempotency patterns** for at-least-once write paths: idempotency keys (e.g. the IETF idempotency-key draft, Stripe-style keys), deterministic/UUIDv5 ids from natural keys, server-side dedupe.
- **Append-only / event-store ingestion** contracts and event-sourcing write semantics.
- **Provenance metadata schemas** for health-data capture: W3C PROV, FHIR Provenance/AuditEvent.
- **Synchronous-vs-asynchronous processing boundaries** for write APIs (what to validate/return at write time vs. defer), and accept/202 vs. created/201 patterns.

Remember: **return findings with citations; do not recommend a final answer.**
