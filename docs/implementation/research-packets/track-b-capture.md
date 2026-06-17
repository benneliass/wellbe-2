# Research Context Packet — Track B / capture-write-path-contract

> This packet is BOTH the user's review artifact AND the prompt sent to the research
> runner. Never propose an answer to the decision question. See `.cursor/rules/research-protocol.mdc`.

**Spike:** WEL-161
**Blocks:** WEL-155 Capture write API endpoint (ingestion adapter to Vault) for Log something
**Decision Record:** `docs/decisions/capture-write-path-contract.md`
**Core component(s) touched:** Ingestion Layer (C3), Raw Context Vault (C2), Processing (C4)
**Date assembled:** 2026-06-17

---

## 1. Identity and guardrails (non-negotiables)

`docs/system-design/platform_identity.md`, `.cursor/rules/wellbe-vision-guardrails.mdc`, `.cursor/rules/audience-guardrails.mdc`. Personal-first; raw immutability (the Vault is append-only and never mutated); every derived fact traces to a raw source; correction is a new layer, never an overwrite.

## 2. System placement

This is the Capture step of the operating loop — the entry point of the Data Factory. See `docs/system-design/system_design.md` and `docs/system-design/integrations.md`.

## 3. Component dossier

- **C3 Ingestion Layer** — source-type adapters write into the Vault. Depends on C1/C2. Repo: `backend/packages/c3_ingestion/`, `backend/apps/ingestion-worker/`.
- **C2 Raw Context Vault** — immutable, append-only, full provenance. Depends on C1. Repo: `backend/packages/c2_vault/`, `backend/apps/vault-writer/`.
- **C4 Processing** — extracts entities/facts/signals from raw context; quality/confidence scoring. Depends on C2.
Blast radius: writes into an append-only store are permanent; a non-idempotent contract is not fixable after the fact.

## 4. Current state (what exists vs. what is missing)

- Existing: `CaptureModal` (`apps/web/components/capture/CaptureModal.tsx`) currently only calls `onClose` — it does not persist. vault-writer + ingestion-worker services run in the cluster. Ingestion-adapter pattern decided in WEL-95 (Done).
- Missing: the capture write API endpoint (C13), the request/response contract per capture type, the idempotency/dedupe strategy, and the sync-vs-deferred processing boundary.

## 5. The decision question(s)

1. Request/response shape per capture type (symptom, lab, document, note)?
2. How is a re-submitted/retried capture made idempotent against the append-only Vault (deterministic id from natural key? client-supplied idempotency key?)?
3. What provenance metadata is written at ingest?
4. Which C4 processing is synchronous (before the write returns) vs. deferred?

## 6. Stakes

The Vault cannot be mutated to repair a bad write. A non-idempotent or under-specified contract produces permanent orphaned/duplicated raw context and breaks the "every fact traces to a source" guarantee.

## 7. Unblocks

WEL-155 (capture write API) and wiring `CaptureModal` "Add to memory" (Track B).

## 8. Prior art

WEL-95 ingestion-adapter spike (Done); `docs/system-design/integrations.md` (all integration features write only through C3 into C2).

## 9. Where to look (research directions, NOT answers)

Idempotency patterns for at-least-once write paths (idempotency keys, deterministic/uuid5 ids); append-only/event-store ingestion contracts; provenance metadata schemas for health data capture; sync-vs-async processing boundaries for write APIs. No proposed answer.
