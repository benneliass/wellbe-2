# Research Context Packet — Track A / visit-packet-composition-gating

> This packet is BOTH the user's review artifact AND the prompt sent to the research
> runner (`scripts/spike_research.py`). Never propose an answer to the decision question.
> See `.cursor/rules/research-protocol.mdc`.

**Spike:** WEL-160
**Blocks:** WEL-68 Build Visit Packet generator with source-linked summary and scoped share/export
**Decision Record:** `docs/decisions/visit-packet-composition-gating.md`
**Core component(s) touched:** Health Thread Engine (C7), Evidence & Provenance (C5), Safety & Governance Gate (C10), Trust & Consent (C1)
**Date assembled:** 2026-06-17

---

## 1. Identity and guardrails (non-negotiables)

WellBe is a patient-centered Health Investigation OS on a sovereign personal core; the individual is always the data controller. Non-negotiables any answer must respect:
- `docs/system-design/platform_identity.md`, `.cursor/rules/wellbe-vision-guardrails.mdc`, `.cursor/rules/audience-guardrails.mdc`.
- Personal-first; user-controlled sharing only; source-linked (no orphan claims); non-diagnostic; calm/never-alarm; grant-scoped and revocable. The packet is a tool the user creates and chooses to share with a clinician — NOT a clinician EHR module.

## 2. System placement

The Visit Packet sits at the Clarify → Close step of Capture → Connect → Investigate → Clarify → Close → Correct: the user assembles what they know to prepare for/around a clinical encounter. See `docs/system-design/system_design.md`.

## 3. Component dossier

- **C7 Health Thread Engine** — packets are composed from one or more threads; depends on C5/C6.
- **C5 Evidence & Provenance** — every claim in the packet must trace to raw source; enforces "no orphan claims". Depends on C2/C4.
- **C10 Safety & Governance Gate** — mandatory gate before any user-facing AI output; do-not-diagnose, panic language, provenance, bias. Depends on C5/C7.
- **C1 Trust & Consent** — share grants, scopes, revocation log. Root of trust.
Blast radius: a shared packet crosses the personal-core boundary, so C1 + C10 decisions are effectively irreversible once shared.

## 4. Current state (what exists vs. what is missing)

- Existing: `/v1/threads` + `/v1/threads/{id}` (C13), C1 consent service (`backend/packages/c1_consent/`), C10 safety-gate service (`backend/apps/safety-gate/`). UI stub at `apps/web/app/(workspace)/prepare/page.tsx` (ComingSoon).
- Missing: a packet-generate endpoint, the packet composition rules, the scoped-share/export grant shape, and the C10 gating contract for generated packet text.

## 5. The decision question(s)

1. What is included in a packet and how is each claim source-linked (C5) so there are no orphan claims?
2. What is the scoped share/export + revocation model (C1): audience, purpose, duration, and exact revoke semantics (does revoke invalidate already-exported copies)?
3. How does the generated summary pass C10 (do-not-diagnose, never-alarm, provenance, bias) before it can be shared?

## 6. Stakes

A shared/exported packet leaves the user's control boundary. A wrong share-scope or revocation model is a privacy regression; a wrong C10 gate is a safety regression. Both are expensive or impossible to reverse once a packet is in a third party's hands.

## 7. Unblocks

WEL-68 (packet generator) and the `Prepare for appointment` UI (Track A), plus the scoped-share/export surface.

## 8. Prior art

C1 consent model (`docs/safety/privacy_and_consent_model.md`); C10 model (`docs/safety/safety_model.md`, `docs/safety/do_not_diagnose_rules.md`); related approved spikes under `docs/decisions/`.

## 9. Where to look (research directions, NOT answers)

Clinical communication standards for patient-generated summaries; consent/grant patterns for revocable third-party sharing (purpose limitation, time-boxing); provenance/citation patterns for source-linked summaries; safety patterns for non-diagnostic patient-to-clinician handoffs. No proposed answer.
