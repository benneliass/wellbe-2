# Decision: MVP onboarding consent + identity flow on top of C1

**Status:** Proposed (awaiting approval)  
**Date opened:** 2026-06-18  
**Date approved:** (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-183  
**Blocks:** WEL-181 [MVP onboarding / first-run flow: welcome, consent capture, baseline profile & goals]

---

## Question

For the MVP first-run onboarding flow, on top of the C1 Trust & Consent model:

1. Which consent scopes must be captured up front, and which are deferred to point-of-use?
2. What minimal baseline identity + profile data is collected, and what is optional/skippable?
3. How does identity bootstrap compose with the real session (ZITADEL / WEL-151)?
4. What are the resume/idempotency semantics if onboarding is abandoned mid-flow?

## Context

Onboarding is the first consent surface a new individual ever sees, and it touches **C1 (Trust & Consent Service)** — the root of trust that everything reading or writing user data calls. Capturing the wrong scopes (too broad violates personal-first/consent-scoped; too narrow makes core features silently fail), or making consent implicit/non-revocable, would be a trust-defining and expensive-to-reverse mistake once real users exist. The flow must keep the individual as controller and let a single user with no organizational affiliation complete onboarding alone.

## Research provided

**Research brief for the external observer:** [`research-briefs/WEL-183-onboarding-consent-identity-research-brief.md`](research-briefs/WEL-183-onboarding-consent-identity-research-brief.md).

**Findings (recorded verbatim):** [`research-briefs/WEL-183-onboarding-research-findings.md`](research-briefs/WEL-183-onboarding-research-findings.md) — 23 cited sources (EU Commission/ICO GDPR guidance, ISO/IEC 29184, HIPAA §164.508, HL7 FHIR Consent, Apple Health, Google Health Connect / Fit, OIDC Core, ZITADEL OIDC, NIST SP 800-63C, Stripe idempotency, FTC dark-patterns, NN/g, WCAG 2.2).

_Research received: 2026-06-18_

**Faithful summary of the findings (full text in the linked file):**

- **Q1 — Consent granularity & timing.** Standards converge on consent that is purpose-specific, actively chosen, recorded, granular, and easy to withdraw (ICO, ISO/IEC 29184), with health data needing heightened protection and data minimisation (EU/ICO). Comparable products (Apple Health, Google Health Connect) draw the line between **core local/personal functionality** and **external access / sharing / sync / research**, asking just-in-time for the latter. Recommended MVP line: capture up front **only the core personal-workspace processing the product cannot function without** — (1) establish controller + personal workspace bound to the OIDC identity, (2) store/retrieve user-provided health memory, (3) organize/link that content into Health Threads for the user's own use, (4) maintain privacy/security/audit/consent records. Defer to point-of-use: external imports, share grants, research/cross-patient analysis, model training, notifications/device permissions, and organizational/role workspaces. Use purpose/resource/action granularity; avoid semantics where a missing `resource_id`/data-category accidentally means "all data for all purposes."
- **Q2 — Minimal baseline.** Smallest first-run set: OIDC identity linkage (canonical key), contact claim from the IdP if available (not the key), consent/notice metadata (version + timestamp + choices), locale/time-zone/unit preferences only where needed for safe presentation, eligibility attestation only if legally required, and an **optional** first concern/goal in the user's own words. Date of birth, sex, height, weight, conditions, allergies, medications, emergency contacts → optional/progressive, requested only when a feature needs them. Do **not** require a diagnosis list at first run ("investigate, never diagnose").
- **Q3 — Identity bootstrap vs. OIDC.** **Authenticate-first, onboard-second.** ZITADEL/OIDC (Authorization Code + PKCE) proves identity; WellBe keys the controller account on `(issuer, subject)` — never email alone (OIDC Core, NIST SP 800-63C). After callback: `get_or_create_account_by_issuer_subject` → create/resume a `pending_onboarding` record → show onboarding/consent → on final confirm, atomically create controller self-access identity + personal workspace + core consent rows + audit event. Collect-then-bind is unsafe for health data (orphaned records, duplicate accounts, ambiguous consent subject).
- **Q4 — Abandonment / resume / idempotency.** **Pending state until explicit final confirmation** (maps to FHIR Consent draft→active; HIPAA treats incomplete authorizations as defective). No core consent rows, workspace grants, or third-party grants become active mid-flow. Finalization is **atomic and idempotent**, keyed on `(issuer, subject, onboarding_session_id, consent_version)` (Stripe idempotency pattern); identity idempotency anchored on `(issuer, subject)` with uniqueness constraints; consent is versioned so resuming under changed terms requires re-confirmation. Abandoned drafts need a retention policy (left to product/legal).
- **Q5 — Calm, non-coercive, accessible UX.** Layered plain-language consent cards ("what this allows / does not allow / you can change or delete later"), separate optional decisions (no bundling), just-in-time optional prompts, equal consequence-clear decline paths, a visible revocation/privacy dashboard, and WCAG-compliant labels/errors/focus. Anti-patterns to avoid: pre-checked boxes, single "agree to everything," conditioning core use on optional consent, false urgency/alarming language, revocation harder than consent.

## Approaches considered

Grounded in the findings file (its §"Approaches considered"):

- **Approach 1 — Authenticate-first, then minimal core consent + progressive point-of-use grants.** New user → ZITADEL/OIDC → create/resume pending account keyed on `(issuer, subject)` → layered core-workspace consent + minimal baseline → optional features asked later. *Pro:* strongest duplicate prevention, no orphaned health data, clean ZITADEL/PKCE fit, explicit auditable granular consent, safe resume. *Con:* requires auth before product value; needs a pending-onboarding state and careful later-prompt UX. **Strongest fit with all constraints.**
- **Approach 2 — Collect a light draft first, then authenticate and bind.** *Pro:* may feel lower-friction. *Con:* risky if the draft holds health data (orphaned sensitive records, duplicate accounts, ambiguous consent subject); misaligned with OIDC's role and NIST account-resolution caution. **Weak unless restricted to a non-health, non-persisted preview.**
- **Approach 3 — Authenticate-first, defer even core consent until first capture.** *Pro:* minimizes up-front prompts. *Con:* the product's core value depends on health-memory storage, so users hit "feature unavailable until consent" friction; under-communicates the trust relationship. **Better as an optional tour mode than the default activation path.**
- **Approach 4 — Full consent bundle up front.** *Pro:* simplest, fewer later prompts. *Con:* violates granular-consent, data-minimisation, and non-coercive principles; consent fatigue; dark-pattern resemblance. **Poor fit; conflicts with explicit constraints.**

## Decision

**Adopt Approach 1 — authenticate-first, then minimal core consent with progressive point-of-use grants.** Concretely, the MVP first-run flow is:

1. **Calm front door** with explicit choices ("New to WellBe", "Sign in") — no auto-sign-in.
2. **ZITADEL authentication** via OIDC Authorization Code + PKCE; WellBe validates the response and reads `(issuer, subject)`.
3. **Account/onboarding resume:** `get_or_create_by_issuer_subject` (canonical key `(issuer, subject)`, never email); resume pending onboarding, sign in if active, else create a pending account shell + pending onboarding state.
4. **Layered core consent** captured separately from general terms and from optional features, covering exactly the four core purposes: create personal workspace; store/retrieve user-provided health memory; organize/link content into Health Threads for the user's own use; maintain privacy/security/audit/consent records.
5. **Minimal baseline** only: IdP contact claim if available, optional preferred name, locale/time-zone/units where needed, legally-required eligibility attestation if any, and an **optional, skippable** first concern/goal in the user's own words. No medical-intake form; no required diagnosis list.
6. **Explicit final confirmation** before any consent scope activates; on submit, **atomically and idempotently** create the active controller record, personal workspace, controller self-access, core consent rows (with notice/consent versions), and the audit event — keyed on `(issuer, subject)` for identity and `(issuer, subject, onboarding_session_id, consent_version)` for finalization.
7. **Point-of-use consent after activation** for imports, sharing/grants, role workspaces, notifications/device permissions, and research/cross-patient analysis — each naming resource/data, action, recipient/actor, purpose, duration, and revocation path.
8. **Always-available privacy/consent dashboard** listing active core processing + optional grants with revoke/disable controls.

Consent rows follow the existing C1 model: subject = authenticated controller; explicit `resource_type` (e.g. `workspace`, `health_memory`, `thread`, `document`), `action`, `purpose`, effective period, revocation status — **never** a broad "all data / all purposes" default via missing `resource_id`/category.

## Trade-offs accepted

- **Higher trust + safer identity over lower first-click friction** — auth before health onboarding adds a step but prevents orphaned drafts and duplicate controllers.
- **One narrow up-front core consent over pure just-in-time** — justified because the personal core cannot function without storing/organizing user-provided health memory; everything optional still moves to point-of-use.
- **More later prompts over broad bundled consent** — better consent quality at the cost of needing consistent, non-interruptive point-of-use UX.
- **Product simplicity over medical completeness at first run** — less early personalization, but aligned with data minimisation and "investigate, never diagnose."
- **Open legal/product questions remain** (see findings §"Open risks"): exact GDPR Art. 6/Art. 9 basis, HIPAA/consumer-health-law applicability, minors/guardian consent, core-consent withdrawal behavior, abandoned-draft retention, MFA/recovery, AI/subprocessor disclosures, and the canonical consent-scope taxonomy. These are flagged for product/legal and do not block the flow's shape.

## Implementation notes

<!-- Filled after approval. -->
To be expanded on approval. Anchors that already exist: backend dev-header principal contract and `Principal.is_controller` (`backend/apps/api/src/wellbe_api/deps.py`); `ConsentService` consent-scope/grant/revocation primitives (`backend/packages/c1_consent/`); frontend single session resolver (`apps/web/lib/session.ts`) designed for a one-file OIDC swap; deployed-but-unwired ZITADEL. The flow above composes with WEL-151 (real session) and feeds the WEL-184 workspace model (personal workspace is the always-present default).

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
