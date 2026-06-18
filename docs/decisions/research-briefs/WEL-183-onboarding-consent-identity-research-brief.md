# Research Brief — MVP Onboarding, Consent & Identity Flow (C1)

**For:** External researcher / analyst (no prior knowledge of this codebase assumed)
**Spike:** WEL-183 · **Blocks:** WEL-181 (MVP onboarding / first-run flow)
**Decision record to be filled from this research:** `docs/decisions/onboarding-consent-identity-flow.md`
**Status:** Awaiting research · **Brief written:** 2026-06-18

---

## 0. How to use this brief (read first)

You are an **external observer**. Assume you have **no access to the source code, the running system, or the team**. Everything you need to reason about the problem is in this document. Your job is **not** to write code — it is to research how comparable products and established standards solve the questions in §6, and to return a findings document we can turn into a design decision.

> **Do not** propose a solution that depends on details not in this brief. If something is missing, state the assumption explicitly in your findings.

### What to deliver — return your research as a downloaded file

Produce a **single self-contained file** and **download/export it** (do not paste only into a chat). We will ingest that file directly.

- **Filename:** `WEL-183-onboarding-research-findings.md` (Markdown preferred; PDF acceptable).
- **Structure (use these exact headings):**
  1. `## Summary` — 5–10 line executive answer.
  2. `## Sources reviewed` — every source with title, author/org, year, URL, and a one-line note on why it is credible.
  3. `## Findings by question` — one subsection per question Q1–Q5 in §6, each with the evidence and how comparable products/standards handle it.
  4. `## Approaches considered` — 2–4 distinct end-to-end approaches to the onboarding+consent+identity flow, each as: *Approach N — what it does | Pros | Cons | Fit with our constraints (§5)*.
  5. `## Recommendation` — one concrete recommended approach and why, with the explicit trade-offs you are accepting.
  6. `## Open risks / unknowns` — anything that still needs a product or legal decision.
- **Citations:** every non-obvious claim must cite a source from your "Sources reviewed" list.
- **Grounding rule:** base findings on the sources you cite, not on unstated assumptions. If you rely on your own prior knowledge, label it clearly as such.

---

## 1. What WellBe is (context for an outsider)

WellBe is a **patient-centered health investigation operating system**. Its core is a **personal, user-controlled health memory**: an individual collects their own health context (symptoms in their own words, lab PDFs, referral messages, wearable trends), and the system links those signals into **Health Threads** — living containers for one unresolved or ongoing health concern — and helps the person carry each concern forward until it is resolved, explained, monitored, or safely handed off.

The operating loop is **Capture → Connect → Investigate → Clarify → Close → Correct**.

**The individual is always the data controller.** Other audiences (caregivers, clinicians, care teams, institutions, researchers) may use role-specific *workspaces*, but only under the individual's explicit, scoped, time-boxed, purpose-bound **grant**. There is **no default access** by any third party. WellBe is **not** a diagnosis engine, **not** an EHR, and **not** a population-analytics platform; it investigates and organizes, it does not diagnose.

This matters for onboarding because **onboarding is the first consent surface a new person ever sees.** It defines the trust relationship for everything afterward.

## 2. The feature we are designing

We are replacing today's behavior (the app silently acts as a single hard-coded identity — see §4) with a real **first-run / entry experience**. The product intent has three distinct entry paths from one calm front door:

1. **New user → onboarding.** Welcome → consent capture → minimal baseline profile & goals → land in a freshly-created **personal** workspace that is theirs and theirs alone.
2. **Returning ("already-initiated") user → sign in.** An existing identity authenticates and lands back in their workspace.
3. **Switch into a specific workspace** (including a "dev"/test workspace) — selecting a workspace is an explicit act, never an automatic default. (Switcher mechanics are a separate brief, WEL-184; here we only need to know onboarding ends by establishing the *personal* workspace and a signed-in identity.)

**This brief is specifically about path 1 and the identity bootstrap shared by 1 & 2.** We need to decide what a calm, trustworthy, legally-sound, minimal MVP onboarding + consent + identity flow looks like.

## 3. Non-negotiable product principles (these constrain every answer)

- **Personal-controller-first.** The individual is the controller; the flow must be completable by a single person with **no** organizational affiliation, alone.
- **Consent is explicit, scoped, and revocable.** Never implicit, never bundled into a single "I agree to everything," never irreversible.
- **Calm, never alarming.** No dark patterns, no pressure, no fake urgency. Skipping optional steps must be easy and consequence-free.
- **Investigate, never diagnose.** Onboarding must not ask the user to self-diagnose or imply the product gives medical answers.
- **Minimal data up front.** Collect the least needed to make the personal core useful; defer the rest to point-of-use.
- **Source-linked & auditable.** Consent decisions become durable, auditable records.

## 4. Current technical state (what already exists — factual, for grounding)

You do not need to write code, but knowing what exists helps you scope realistic recommendations.

**Identity / auth today (the thing we're changing):**
- The backend authenticates each request via a **dev header contract**: requests carry `X-Wellbe-Actor-Id`, `X-Wellbe-Patient-Id`, and `X-Wellbe-Actor-Type` (defaulting to `controller`). A request with no actor id is treated as unauthenticated.
- "Controller self-access" is defined as `actor_id == patient_id AND actor_type == "controller"` — the data subject acting on their own data, always allowed. Any other actor must hold a live consent grant (default-deny).
- The web app currently **bakes a single dev identity into the build** via environment variables and uses it for every request — i.e., it is **auto-signed-in** as one fixed test patient. There is **no login screen** and no per-user onboarding.
- A real OIDC identity provider (**ZITADEL**) is deployed in the environment but is **not yet wired into the UI**. The frontend has a single "who is acting" resolver designed so swapping dev headers for a real OIDC token is a localized change.

**Consent / trust service that already exists (C1):**
- There is a **Trust & Consent Service** with:
  - **Consent scopes** — rows describing `(subject, resource_type, action, resource_id?, valid_from, valid_until?, revoked_at?)`; access checks query these.
  - **Share grants** — scoped, purpose-bound, expiring permissions to other parties, with a **revocation log**.
  - A **privacy-preference** record used to gate sensitive capabilities (e.g., cross-patient analysis is **off** unless explicitly enabled).
- So the *storage and enforcement* primitives for consent exist. **What does not exist is the onboarding UX and the policy decision about which scopes to capture when.**

**The gap this research closes:** what the first-run flow asks for, in what order, with what consent granularity, and how the resulting identity + consent records are established — without over-collecting, without implicit consent, and in a way that composes with real OIDC (ZITADEL) later.

## 5. Constraints your recommendation must satisfy

1. A lone individual with no organization can finish onboarding and end up as the **controller** of a new personal workspace.
2. Consent is captured as **explicit, granular, revocable** decisions — not one blanket checkbox.
3. The flow must distinguish **up-front consent** (needed for the personal core to function at all) from **point-of-use consent** (asked later, only when a feature needs it). Your research should tell us where that line should sit.
4. **Minimal baseline:** define the smallest profile/identity dataset worth collecting at first run, and what must be optional/skippable.
5. **Identity bootstrap must compose with OIDC (ZITADEL).** Recommend how onboarding sits relative to authentication (e.g., authenticate-then-onboard vs. onboard-then-bind), given a standard OIDC provider.
6. **Resume / abandonment:** the flow must be safe if a user drops off mid-onboarding and returns later (no duplicate identities, no half-consented state that silently grants access).
7. **Regulatory awareness:** answers should be informed by recognized consent/privacy norms for personal health data (e.g., GDPR lawful basis & consent quality, HIPAA authorization concepts, ISO/IEC 29184 consent notices). We are not asking for legal advice — we are asking what established norms say a good health-app consent flow does.

## 6. The research questions (answer each in your deliverable)

- **Q1 — Consent granularity & timing.** For a personal health app where the user is the controller, **which consent scopes should be captured at first run vs. deferred to point-of-use?** What do comparable consumer-health products and consent standards (e.g., ISO/IEC 29184, GDPR consent guidance) treat as "must ask up front" vs. "ask when needed"? What granularity avoids both over-asking (consent fatigue) and under-asking (features silently failing or over-reaching)?
- **Q2 — Minimal baseline identity & profile.** What is the **smallest** set of identity/profile/goal data that a first-run flow should collect to make a personal health-memory product useful, and what should be optional or skippable? What do leading onboarding flows collect at step one vs. progressively?
- **Q3 — Identity bootstrap vs. OIDC.** Given a standard **OIDC** provider (ZITADEL), what is the recommended ordering and responsibility split between **authentication** (proving who you are) and **onboarding/consent** (establishing the controller + consent records)? Authenticate-first then onboard, or collect-then-bind? How do comparable products avoid creating orphaned or duplicate accounts?
- **Q4 — Abandonment / resume / idempotency.** How should a first-run flow behave if abandoned midway and resumed later? What are good patterns to guarantee **no duplicate identity** and **no partially-granted consent** is left active? (e.g., draft/pending state, single canonical account keyed on the OIDC subject, consent only effective on explicit final confirmation.)
- **Q5 — Calm, non-coercive, accessible consent UX.** What concrete UX patterns make health-data consent **clear, non-alarming, and non-coercive** while remaining legally robust (layered notices, just-in-time prompts, plain-language summaries, easy decline, visible revocation)? What anti-patterns (dark patterns, pre-checked boxes, bundled consent) must be avoided?

## 7. Out of scope for this brief

- The mechanics of switching between multiple workspaces → covered by **WEL-184** (`workspace-switcher-scope-presentation.md`).
- Implementation/code design — we will derive that after a decision is approved.
- Choosing the identity provider — ZITADEL (OIDC) is already selected; assume a standard OIDC provider.

## 8. Glossary

- **Controller** — the individual who owns and controls the data. Always the data subject in WellBe.
- **Health Thread** — a living container for one unresolved/ongoing health concern.
- **Consent scope** — an explicit, revocable permission row: who may do what action on what resource, for how long.
- **Grant** — a scoped, purpose-bound, time-boxed permission to a third party (e.g., a clinician). Not relevant to a lone new user, but relevant to why consent is modeled granularly.
- **OIDC / ZITADEL** — OpenID Connect authentication; ZITADEL is the deployed identity provider.
- **Point-of-use consent** — consent requested at the moment a specific feature needs it, rather than all up front.

---

_When your findings file is ready, return it to the team. It will be recorded verbatim under "Research provided" in `docs/decisions/onboarding-consent-identity-flow.md`, after which approaches and a proposed decision are written and sent for approval. No implementation happens until that decision is approved._
