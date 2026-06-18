# Decision: Workspace switcher presentation + scoping under C17

**Status:** Proposed (awaiting approval)  
**Date opened:** 2026-06-18  
**Date approved:** (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-184  
**Blocks:** WEL-182 [Workspace identity + switcher UI (personal + grant-scoped role workspaces)]

---

## Question

For the workspace identity + switcher UI:

1. How are the user's available workspaces enumerated and presented (personal always-present + grant-scoped role workspaces) without leaking the existence of grants the user should not see?
2. What exactly changes on switch (data scope, allowed actions, visible surfaces), and how is the active context made unambiguous?
3. How is the controller/grant invariant enforced in the UI so no institution-enabled or default cross-patient view can ever appear?
4. How does the active workspace compose with the session (WEL-151)?

## Context

The switcher is the UI boundary for the entire C17 audience model and touches **C17 (Workspace, Role & Grant Layer)**. Getting scoping wrong risks showing one context's data in another, implying institution control, or surfacing cross-patient views by default — all hard violations of the audience guardrails (`audience-guardrails.mdc`, `platform_identity.md`) and irreversible trust damage. The personal workspace must always be present and stand alone; every other workspace is grant-scoped, purpose-bound, and revocable, never institution-enabled by default.

## Research provided

**Research brief for the external observer:** [`research-briefs/WEL-184-workspace-switcher-research-brief.md`](research-briefs/WEL-184-workspace-switcher-research-brief.md).

**Findings (recorded verbatim):** [`research-briefs/WEL-184-workspace-switcher-research-findings.md`](research-briefs/WEL-184-workspace-switcher-research-findings.md) — 35 cited sources (Slack / GitHub / Google / Notion / Atlassian / Teams / QuickBooks switchers, AWS IAM role-switch, GOV.UK & HMRC delegated authority, HSBC third-party access, NHS App proxy access, HL7 FHIR Consent / AuditEvent / Security-Privacy / Security Labels, HIPAA §164.312, OWASP Authz + ASVS V4, NIST SP 800-162 ABAC & SP 800-63B, NN/g modes & indicators, Open Banking & CDR consent dashboards, OAuth RAR/Introspection/Revocation RFCs, Epic & WA break-the-glass).

_Research received: 2026-06-18_

**Faithful summary of the findings (full text in the linked file):**

- **Q1 — Enumeration & no leakage.** Enumerate **only** contexts the signed-in actor may currently act in (mirroring Slack/Atlassian/QuickBooks "only accessible workspaces"; stricter healthcare proxy/agent patterns appear only after authorization). The switcher is a **view over active, displayable memberships/grants**, never a searchable directory of patients/clinicians/orgs/cohorts/possible grants. Present in a hierarchy — **Personal first**, then delegated ("Acting for…"), clinical/care-team, institution-aggregate, research sandbox, with dev/test clearly grouped as testing. Label by **controller + role + purpose + expiry + capability class**, not by distributor/institution. Never show locked/ineligible rows that would reveal a relationship the actor isn't entitled to. Break-the-glass is **not** a normal switcher item.
- **Q2 — What a switch changes & how to signal it.** A switch is a **mode change** (NN/g: unsignaled modes cause errors). It changes three things, all of which must be signaled: **data scope**, **actions/capabilities**, **available surfaces** — driven by the C17 access predicate. Keep a **persistent indicator** (name, role, subject/controller or "aggregate only", purpose, expiry/review, short capability summary like "read + comment; no export"; AWS role-switch / NHS "Acting for" banner). Higher-risk entries (different subject, aggregate/research, export/invite-capable, near-expiry, stale session) get an **acknowledgement or step-up**. Text does the safety work; color may reinforce but is never the only cue. Reset/scope transient cross-context state (selections, search, export queues, invite drafts, uploads). Deep links resolve against current authorization, never silently dropping into a non-personal/other-subject context.
- **Q3 — Enforcing the invariant in the UI.** The UI is a **projection of the server-side C17 predicate**, not its own permission system (OWASP: client checks are UX-only; ASVS: least privilege, fail-secure, no IDOR). Never fetch-then-hide out-of-scope data; configure nav/actions/filters from a **display-safe predicate summary**; hide high-risk capabilities not granted (export/invite/run-analysis/view-aggregate) and disable-with-minimal-explanation only where the user can legitimately know the feature exists ("Export is not included in this grant"). Aggregate/institution contexts **remove individual-record affordances entirely** (no patient table). Treat absent/stale/expired/revoked/mismatched predicate as **deny → fall back to personal workspace**. Single entitlement source for both nav and data to avoid "visible-but-denied" / "hidden-but-URL-accessible." Org membership alone never unlocks individual data. Surface "views are audited" where it builds trust.
- **Q4 — Personal-first coherence.** Personal workspace is the **default mental model**, always present and pinned first; a solo user sees a normal identity/status affordance ("Your workspace" / "[Name]'s health workspace"), **not** an empty enterprise selector or institutional language. The control lives in the **global app shell / profile area**; it expands into a true switcher only when ≥2 displayable workspaces exist, adding role groups only when populated. Dev/test appears only with an active membership and is explicitly labeled "Test data / Dev workspace" — never the default. **Grant management is a separate sharing/permissions surface** ("who can access what, until when") distinct from the switcher ("where am I acting now").
- **Q5 — Session composition & safety.** One authenticated session; **active workspace is a fresh, server-validated in-session scope** (switch without full re-login, like GitHub/Google/Notion/Teams), but authorization state (binding/grant/purpose/capabilities/filters/expiry) is checked/refreshed independently of the base session (NIST ABAC). Client may remember the last workspace for convenience but it is **not authoritative** — fail closed to personal on refresh failure. **Risk-based step-up** for export/invite/research/aggregate/break-glass/long-idle (NIST 800-63B; HIPAA auto-logoff). **Revocation/expiry take effect mid-session** (remove from enumeration, invalidate predicate, cancel pending actions; OAuth introspection/revocation patterns). **Audit context entry + sensitive actions** (FHIR AuditEvent who/what/where/when/why). Every scoped request carries the intended workspace + purpose; server rejects on mismatch; short-lived predicate cache refreshed on switch/sensitive action/expiry/revocation.

## Approaches considered

Grounded in the findings file (its §"Approaches considered"):

- **Approach 1 — Minimal SaaS-style dropdown.** Header dropdown lists accessible workspaces; selecting switches instantly, label changes, no confirmation/banner beyond the label. *Pro:* simple, familiar, scales. *Con:* under-communicates healthcare scoping — users may not notice acting for a different subject under a grant with different actions (mode-error risk). **Weak on the unambiguous-scope, capability-change, aggregate-opt-in, and audit constraints.**
- **Approach 2 — Personal-first explicit switcher with grant cards + persistent active-scope banner.** Global shell always shows the active personal workspace; when more exist it expands to a role-grouped list of only displayable workspaces; each non-personal item is a compact grant card (subject/controller or aggregate-only, role, purpose, capabilities, expiry, audit note); higher-risk entry shows an acknowledgement/step-up; after entry a persistent banner/chip states the active context with switch-back. *Pro:* unambiguous context, personal-first coherence, no-leak enumeration, communicates what changes, matches proxy/consent-dashboard patterns, natural home for audit/expiry. *Con:* more verbose, adds friction; needs careful copy/visual design. **Strongest fit with all constraints.**
- **Approach 3 — Separate login / impersonation session per workspace.** *Pro:* strong context separation; useful as a narrow step-up for very sensitive actions. *Con:* conflicts with "workspace is a scope within one authenticated identity"; risks credential-sharing / "log in as the patient" (HMRC warns against this). **Poor fit as the general model.**
- **Approach 4 — Global all-workspaces inbox/dashboard.** *Pro:* efficient for users with many contexts. *Con:* a global dashboard can leak relationships/patient names/grant existence and normalize cross-patient views, which WellBe forbids by default. **Limited fit; only a heavily-redacted, server-filtered notification count might be acceptable — not a default content dashboard.**

## Decision

**Adopt Approach 2 — a personal-first explicit workspace switcher with grant cards and a persistent active-scope indicator.** Concretely:

1. **Global app-shell control, personal-first.** Default and always-pinned-first is the personal workspace, labeled in personal-controller language. For a single-workspace user it reads as a normal identity/status affordance — never an empty enterprise selector or institutional language.
2. **Enumerate only displayable contexts** returned by an authorization-backed workspace/membership enumeration (the switcher is a view over active memberships/grants). No directory, no locked/ineligible rows, no revealing of patients/orgs/cohorts/grants the actor isn't entitled to. Group by role/purpose (Personal → Acting for → clinical/care-team → institution-aggregate → research sandbox → dev/test), adding a group only when populated.
3. **Display-safe cards.** Each non-personal row shows only: display name, type, role, purpose, capability summary, expiry/review, audit indicator. Delegated = "Acting for [controller]"; institution = "aggregate only — no individual records"; research = "research sandbox" + purpose; dev/test explicitly labeled and never default.
4. **Switch changes data scope + capabilities + surfaces**, driven solely by the server-side C17 access predicate, with a **persistent active-context banner/chip** after entry and a clear switch-back to personal. Text carries the meaning; color only reinforces.
5. **Higher-risk entry requires acknowledgement/step-up** (different subject, aggregate/research, export/invite/run-analysis-capable, near-expiry, insufficient session freshness), stating data scope, allowed actions, purpose, expiry, and that views are audited.
6. **UI is a projection of the predicate and fails closed.** Configure nav/actions/filters from a display-safe predicate summary; never fetch-then-hide; hide ungranted high-risk capabilities (disable-with-explanation only where legitimate); aggregate/institution contexts remove individual-record affordances entirely; absent/stale/expired/revoked/mismatched predicate → stop rendering scoped data, cancel pending actions, drop the workspace from enumeration, return to personal. Server-side authorization remains mandatory for every read/search/export/invite/contribute.
7. **One session, workspace as a fresh in-session scope.** Switch without full re-login; refresh the predicate on switch, sensitive action, page load, expiry boundary, and revocation event; client-remembered last workspace is non-authoritative. Honor revocation/expiry mid-session; carry intended workspace + purpose on every scoped request; reject on mismatch.
8. **Grant management is a separate sharing/permissions surface** ("who can access what, for what purpose, until when, how to revoke"), distinct from the switcher ("where am I acting now").
9. **Audit** context entry and sensitive actions with actor + active workspace + role binding + grant/purpose + subject/aggregate label + action + resource category + decision + obligations + timestamp.

## Trade-offs accepted

- **More friction and visual footprint for non-personal work** (banner/cards/acknowledgements) in exchange for unambiguous context and fewer mode errors.
- **Some actions hidden/blocked even when users expect them** (capability-scoped UI) to prevent implying latent entitlement.
- **Aggregate/cross-patient workflows require deliberate opt-in** and never appear as a default — consistent with the audience guardrails.
- **Precise copy is now a hard requirement** (roles, purposes, capabilities, expiry, audit) — plain-language mappings for internal scope codes are outstanding work.
- **Open risks remain** (see findings §"Open risks"): exact personal-workspace label, capability-summary vocabulary, step-up thresholds, audit visibility rules, notification-metadata leakage rules, minor/dependent & safeguarding policy, whether any emergency/break-glass exists at all, aggregate/research de-identification thresholds, jurisdictional/legal mapping, offline/degraded behavior, and dev/test workspace governance. These are flagged for product/legal/security and do not block the switcher's shape.

## Implementation notes

<!-- Filled after approval. -->
To be expanded on approval. Anchors that already exist: the C17 deep-grant **policy evaluator** returning a scoped `AccessPredicate` (`backend/packages/c1_consent/src/wellbe_c1_consent/deep_grants.py`) — the source of the "display-safe predicate summary"; the dev-header principal + `Principal.is_controller` personal-first path and fail-closed `require_access` (`backend/apps/api/src/wellbe_api/deps.py`); the static "Your workspace" placeholder to replace (`apps/web/components/shell/NavRail.tsx`); the single session resolver (`apps/web/lib/session.ts`). **What does not yet exist and must be built:** a workspace/membership **enumeration API**, a display-safe predicate-summary contract for the UI, and the switcher UI itself. Composes with WEL-151 (session) and the WEL-183 onboarding decision (personal workspace is the always-present default created at onboarding).

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
