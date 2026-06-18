# Research Brief — Workspace Switcher: Presentation & Scoping (C17)

**For:** External researcher / analyst (no prior knowledge of this codebase assumed)
**Spike:** WEL-184 · **Blocks:** WEL-182 (Workspace identity + switcher UI)
**Decision record to be filled from this research:** `docs/decisions/workspace-switcher-scope-presentation.md`
**Status:** Awaiting research · **Brief written:** 2026-06-18

---

## 0. How to use this brief (read first)

You are an **external observer**. Assume you have **no access to the source code, the running system, or the team**. Everything you need is in this document. Your job is **not** to write code — it is to research how comparable products and security/UX standards solve the questions in §6, and to return a findings document we can turn into a design decision.

> **Do not** propose a solution that depends on details not in this brief. If something is missing, state the assumption explicitly in your findings.

### What to deliver — return your research as a downloaded file

Produce a **single self-contained file** and **download/export it** (do not paste only into a chat). We will ingest that file directly.

- **Filename:** `WEL-184-workspace-switcher-research-findings.md` (Markdown preferred; PDF acceptable).
- **Structure (use these exact headings):**
  1. `## Summary` — 5–10 line executive answer.
  2. `## Sources reviewed` — every source with title, author/org, year, URL, and a one-line note on credibility.
  3. `## Findings by question` — one subsection per question Q1–Q5 in §6.
  4. `## Approaches considered` — 2–4 distinct end-to-end approaches to workspace presentation + switching + scoping, each as: *Approach N — what it does | Pros | Cons | Fit with our constraints (§5)*.
  5. `## Recommendation` — one concrete recommended approach and the trade-offs accepted.
  6. `## Open risks / unknowns` — anything still needing a product, legal, or security decision.
- **Citations:** every non-obvious claim cites a source from "Sources reviewed".
- **Grounding rule:** base findings on the sources you cite. Label any reliance on your own prior knowledge as such.

---

## 1. What WellBe is (context for an outsider)

WellBe is a **patient-centered health investigation operating system**. Its core is a **personal, user-controlled health memory**: an individual collects their own health context and the system links it into **Health Threads** (containers for one unresolved/ongoing health concern) and helps carry each concern forward until it is resolved, explained, monitored, or safely handed off.

**The individual is always the data controller.** Other audiences — caregiver, clinician, care team, institution, researcher — may operate inside **role-specific workspaces**, but only under the individual's explicit, scoped, time-boxed, purpose-bound **grant**. There is **no default access** for any third party, and **businesses/institutions are distribution channels, not data controllers** — deploying WellBe never confers access to or control over an individual's data.

This brief is about the **workspace switcher**: the UI surface where a user sees and moves between the workspaces available to them. It is the visible boundary of the entire multi-audience access model, so getting its presentation and scoping right is a trust- and safety-critical decision.

## 2. The feature we are designing

Today the app shows a single hard-coded workspace label ("Your workspace") and silently acts as one fixed identity. We are introducing a **workspace identity + switcher**:

- The **personal workspace is always present** and **stands alone** — a user with no grants and no organizational affiliation has exactly one workspace (their own) and the switcher must still make sense.
- Additional workspaces appear **only** when the user holds a relevant role/grant: e.g., a caregiver workspace for a dependent they were granted access to, a clinician case-investigation workspace they were invited into, etc.
- Switching is an **explicit user act**. The active workspace must be **unambiguous** at all times.
- A **"dev"/test workspace** is, in this model, just **one selectable workspace** — never the automatic default.

The product question is: **how should the switcher present available workspaces and scope what each one can see/do, such that the controller/grant invariants can never be violated through the UI?**

## 3. The audience & workspace model (factual — already defined in our system)

WellBe separates four concepts:

- **Audience** — who uses a surface (individual, caregiver, clinician, care team, institution, researcher).
- **Data controller** — always the individual.
- **Workspace** — the role-specific interface. Defined types in our model: `individual`, `clinician_case_investigation`, `shared_health_thread`, `institution_continuity`, `research_sandbox`.
- **Grant** — the user-approved, scoped, time-boxed, purpose-bound permission that lets another party view or contribute.

Hard constraints baked into the product identity:
- Every feature must benefit the **individual**, even when another audience uses it.
- **No audience gets default access**; access is grant-based, scoped, revocable.
- **Cross-patient comparison is always opt-in and user-initiated** — never an institutional default.
- Institutions receive only **aggregate, consented** intelligence — never default individual-level access.

## 4. Current technical state (what already exists — factual, for grounding)

You do not need to write code, but this scopes realistic recommendations.

**A deep authorization model already exists (the C17 layer), as a pure policy evaluator:**
- There are defined enums for **roles** (individual_controller, caregiver, clinician, care_team, institution, researcher), **workspace types** (as in §3), **grant types** (controller_entitlement, delegated_individual, workspace_share, institution_aggregate, research_sandbox), **grant status** (draft, requested, pending, active, suspended, expired, revoked, superseded, rejected, cancelled), **scope codes** (e.g., visit-packet-only, specific-thread, labs+symptoms, wearable-trends-only, full-investigation, aggregate-metrics, research-protocol), and **capabilities** (read, comment, export, invite, contribute, view_aggregate, run_analysis).
- A **policy evaluator** takes an access-decision request (actor, role binding, workspace, memberships, grants, action, purpose, resource, data category, security labels) and returns a **scoped access predicate** — not a bare yes/no, but an allow + resource filter (which resource ids, which data categories, which security labels) plus obligations (e.g., "audit each view") and an expiry. Downstream reads must be constrained by this predicate **before** retrieval/search/export.
- Key invariants already enforced by the evaluator: the role binding must belong to the acting actor; role binding and workspace must be `active`; the actor must have an active **membership** in that workspace; a matching **active, unexpired, unrevoked grant** for that workspace + purpose is required; `aggregate_only` grants only permit `view_aggregate`; export/invite require explicit capabilities; resources outside the grant's scope are denied.
- **Controller self-access** is the simple personal-first case: when the actor is the data subject acting on their own data (`actor_id == patient_id`, `actor_type == controller`), access is always allowed without a grant.

**What does NOT exist yet:**
- Persistence + API to **enumerate a user's workspaces and memberships** for display.
- Any **switcher UI** or "active workspace" concept in the frontend (today it's one baked-in identity and a static label).
- The product decision for **how to present** workspaces and **what the active-context switch changes** in the UI.

**The gap this research closes:** the presentation model and scoping rules for a switcher that exposes the above authorization model to users without ever leaking grant existence, implying institutional control, or surfacing cross-patient/aggregate data as a default.

## 5. Constraints your recommendation must satisfy

1. The **personal workspace is always present** and the switcher must be coherent for a user who has **only** that one workspace.
2. Switching is an **explicit** action; the **active workspace is always unambiguous** (the user can never be confused about which context — and therefore which data scope — they are in).
3. The switcher must **not leak the existence of grants/workspaces the user should not see**, and must never imply an institution can control or default-access the individual's data.
4. On switch, it must be crystal-clear **what changes**: visible data scope, allowed actions (e.g., read vs. comment vs. export), and which surfaces are available — all bounded by the C17 access predicate.
5. **No cross-patient or aggregate view may ever appear as a default**; any such view is explicitly opt-in and clearly labeled.
6. The active workspace must **compose cleanly with the session/identity** (the user authenticates once; the workspace is a scope *within* that authenticated identity, not a separate login).
7. **Auditable:** entering/using a non-personal workspace should be consistent with "audit each view" obligations.

## 6. The research questions (answer each in your deliverable)

- **Q1 — Enumeration & presentation without leakage.** How do comparable multi-context products (e.g., multi-tenant SaaS workspace/org switchers, Google/Slack/GitHub-style context switchers, electronic-health "break-the-glass"/delegated-access patterns, banking "act on behalf of") **present the set of contexts a user can act in** without revealing contexts, relationships, or grants the user shouldn't know exist? What presentation patterns (grouping by role, labeling personal vs. delegated, etc.) are clearest?
- **Q2 — What a context switch should change, and how to signal it.** What are best practices for making an **active context switch unambiguous** and safe — persistent context indicators, color/scoping cues, confirmation on entering a more-privileged or different-subject context, preventing accidental cross-context actions? How do products communicate "you are now acting in X, which can see/do Y"?
- **Q3 — Enforcing the controller/grant invariant in the UI.** Given that the real authorization is enforced server-side by a scoped access predicate (see §4), what should the **UI** do to ensure it never *presents* an action or data the active grant doesn't permit (e.g., hiding vs. disabling export/invite, never rendering out-of-scope data, never implying default institutional access)? What patterns keep UI and server authorization consistent and fail-closed?
- **Q4 — Personal-first coherence & the "always present" personal workspace.** How should the switcher behave for the **common case of one personal workspace only** (don't make a solo user feel like they're missing something or part of an institution), while scaling gracefully as delegated/role workspaces are added? Where should "switch workspace" live in the IA, and when should it even be visible?
- **Q5 — Session composition & safety.** How should "active workspace" relate to the authenticated **session** (single sign-in, workspace as an in-session scope)? Best practices for: switching without re-auth vs. requiring step-up for sensitive contexts, expiry/revocation taking effect mid-session, audit of context entry, and avoiding stale-scope bugs (acting in a context after a grant was revoked or expired)?

## 7. Out of scope for this brief

- The **onboarding / first-run / consent** flow and identity bootstrap → covered by **WEL-183** (`onboarding-consent-identity-flow.md`).
- Implementation/code design — derived after a decision is approved.
- Designing the deep-grant *data model* — it already exists (§4); we are designing its **presentation and switching UX** and the **UI-side scoping rules**.

## 8. Glossary

- **Controller** — the individual who owns/controls the data; always the data subject.
- **Workspace** — a role-specific interface; types listed in §3. The personal (individual) workspace is always present.
- **Grant** — a scoped, time-boxed, purpose-bound permission to a third party; can be revoked.
- **Membership** — an active link binding a role to a workspace; required for non-personal access.
- **Access predicate** — the server-side result of an authorization check: allow + a resource filter (which ids/categories/labels), obligations, and expiry. The UI must never present beyond it.
- **Aggregate-only** — a grant that permits only aggregate (`view_aggregate`) views, never individual-level data; relevant to institution contexts.

---

_When your findings file is ready, return it to the team. It will be recorded verbatim under "Research provided" in `docs/decisions/workspace-switcher-scope-presentation.md`, after which approaches and a proposed decision are written and sent for approval. No implementation happens until that decision is approved._
