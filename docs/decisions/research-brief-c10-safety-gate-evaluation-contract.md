# Research brief: C10 Safety Gate evaluation contract

Prepared for: external safety / clinical AI governance consultant  
Date prepared: 2026-06-01  
Owner: Ben Elias, product owner / individual data controller  
Related Jira Story: WEL-74 — Implement layered Safety Gate service with deterministic rules, NeMo Guardrails, and Llama Guard  
Related Jira Spike: WEL-134 — Per-engine safety risk tiers wired into Safety Gate  
Decision record target: `docs/decisions/safety-gate-evaluation-contract.md`  
Related open decision record: `docs/decisions/engine-risk-tier-safety-routing.md`

---

## 1. Assignment summary

WellBe needs a researched, implementation-ready decision for the C10 Safety & Governance Gate. C10 is the mandatory safety gate before any AI-generated or AI-assisted health output reaches a user in any workspace.

The consultant should answer:

> What is the approved C10 Safety Gate evaluation contract for user-facing AI output in the Patient-Centered Health Investigation OS?

The answer must be concrete enough that an engineer can implement the service, write tests, and verify the behavior on a local Kubernetes cluster. It should cover deterministic checks, model-based guardrail layers, fail-closed behavior, per-engine risk tiers, provenance obligations, output obligations, audit events, and latency/degradation behavior.

Do not design WellBe as a diagnosis engine. The output of this research must preserve the product boundary: WellBe investigates, tracks uncertainty, explains source-linked context, and helps users prepare for care conversations. It never diagnoses, rules out diagnoses, ranks differential diagnoses, or replaces clinical judgment.

---

## 2. Product background

WellBe is a Patient-Centered Health Investigation OS. Its sovereign core is a Personal Shared Health Memory OS: a user-controlled memory layer that helps individuals carry health context forward until each concern is resolved, explained, monitored, or safely handed off.

The operating loop is:

```text
Capture -> Connect -> Investigate -> Clarify -> Close -> Correct
```

Important product primitives:

- A **Health Thread** is a living container for one unresolved or ongoing health concern.
- An **Investigation** is the active structured research process around one or more Health Threads.
- A **Theory** is a user- or clinician-proposed explanation evaluated against available evidence. It is never a diagnosis, ranked differential, or disease claim.
- **External Evidence** lives in a separate graph. It can be relevant context, but it is never converted into a fact about the user.
- **Workspace / Role / Grant** controls multi-audience access. Clinicians, institutions, and researchers may use role-specific workspaces only under scoped, purpose-bound, revocable grants. The individual remains the controller.

The primary user is always the individual managing their own health. Clinicians, care teams, institutions, and researchers can be workspace users, but they do not control the individual's data and do not receive default access.

---

## 3. Canonical constraints

The following constraints are already approved and should be treated as fixed.

### 3.1 Investigate, never diagnose

WellBe may help a user understand what is known, unknown, missing, pending, unresolved, or worth discussing with a clinician.

WellBe must not output:

- "You have [condition]."
- "You do not have [condition]."
- "This is [condition]."
- "Your doctor missed [condition]."
- "Stop / start / change this medication."
- "This normal test rules everything out."
- "This referral means you are safe to wait."
- "This is not serious."
- "You probably have X" / "almost certainly X."
- Ranked differential diagnosis lists.

Approved safer framing examples:

- "This symptom is still unresolved in your thread."
- "This result was normal, but your thread still shows symptoms after the test."
- "Here are questions worth discussing with a clinician."
- "This item appears pending based on the information you uploaded."
- "The source of this claim is [patient-reported / lab report / imported note]."
- "Your data partially supports this theory; X and Y remain unknown. Worth discussing with a clinician."
- "This source discusses a similar pattern, but it is low-certainty and not specific to you."

### 3.2 No bypass

The Safety Engine must evaluate every user-facing AI output. No assistant, agent, summary generator, research mode, workspace, feature flag, or configuration can bypass it.

This applies to:

- individual workspace outputs,
- clinician case-investigation workspace outputs,
- shared thread workspace outputs,
- institution continuity workspace outputs,
- research sandbox outputs,
- visit packets and summaries,
- Theory evaluation,
- External Evidence Watch / Research Agent results,
- pattern / contradiction / missing-context outputs,
- live-metric safe escalation,
- cross-patient comparison.

### 3.3 Source-linked output

Every health claim derived from AI or pattern detection must be traceable to a source. "WellBe says" is not a source. The source is the raw input, imported record, lab report, user-entered note, wearable reading, or external reference.

A claim with no traceable source may not be surfaced.

### 3.4 External evidence is context, not fact

External medical knowledge is stored in a separate External Evidence Graph. It can link to personal data only through patient-scoped relevance links. It must not become evidence proving something about the user.

Source-quality tiers:

| Tier | Source type | Use |
|---|---|---|
| Tier 1 | Clinical guidelines, official medical bodies | Strongest external reference |
| Tier 2 | Peer-reviewed papers, systematic reviews | Useful, still contextual |
| Tier 3 | Case reports, early research | Signal only |
| Tier 4 | Medical blogs, expert explainers | Educational context only |
| Tier 5 | Forums, anecdotes, social posts | Anecdotal; never evidence about the user |

### 3.5 Clinical review markers

Every output should carry a review-state marker:

- `patient-entered`
- `AI-summarized`
- `not-clinician-reviewed`
- `clinician-reviewed`
- `clinician-annotated`
- `ready-for-visit`
- `needs-urgent-care-consideration`

### 3.6 Urgency routing

Urgency must be handled carefully:

- Red/orange safety triage must include a next-step path such as emergency services, urgent care, or "contact your clinician today."
- WellBe must never add urgency language and leave the user with no action.
- WellBe must never suppress genuine urgent-risk language merely to avoid anxiety.
- Urgent outputs still must not diagnose.

### 3.7 Audience and access

Every feature must benefit the individual user. No clinician, institution, researcher, employer, or deployer receives default individual-level data access.

Institution access, when present, is aggregate-only, consented, and privacy-preserving.

---

## 4. Core architecture context

The C10 Safety Gate sits at layer L7 and depends on provenance and thread state.

Core components relevant to this research:

| Component | Purpose | Why it matters for C10 |
|---|---|---|
| C1 Trust & Consent | Auth identity, consent scopes, grants, revocation, cross-patient opt-in | C10 must respect workspace, grant, role, and purpose context |
| C2 Raw Context Vault | Immutable raw event store | C10 source/provenance checks ultimately trace back to raw inputs |
| C3 Ingestion Layer | Source adapters | C10 may need to know source type and provenance quality |
| C4 Processing Pipeline | Extracts facts/signals and quality/confidence scores | C10 evaluates derived outputs from processing |
| C5 Evidence & Provenance | Enforces no orphan claims | C10 must reject provenance-absent claims |
| C6 Knowledge Graph Store | Typed nodes and evidence-weighted edges | C10 gates graph-derived insights and Theory support/contradiction |
| C7 Health Thread Engine | Health Thread lifecycle/status | C10 may need unresolved/urgent/thread status context |
| C10 Safety & Governance Gate | Mandatory gate before AI output | Subject of this research |
| C12 Notification & Audit | Append-only audit and low-alarm notifications | C10 decisions must emit auditable events |
| C13 API & Contract Layer | Contract boundary all workspaces call | C10 evaluation request/response should be part of contract |
| C14 Investigation Engine | Investigation lifecycle and evidence bundles | C10 gates Investigation summaries and next-step text |
| C15 Theory Service | Theory object and evaluation | C10 prevents Theory from becoming diagnosis |
| C16 External Evidence Graph | Separate external source graph | C10 enforces source-quality/context-only language |
| C17 Workspace, Role & Grant | Deep grant/workspace model | C10 evaluates output under workspace role/purpose constraints |

Architecture principle:

```text
AI producer -> C10 Safety Gate -> C13/API -> user-facing surface
```

No user-facing output should be sent directly from an engine, agent, worker, or workspace service without C10 evaluation.

---

## 5. Current implementation state

This repo is in active development. Relevant implemented pieces:

### C1/C17 deep Grant/Role model

The deep Grant/Role decision is approved in `docs/decisions/deep-grant-role-workspace-model.md`.

Implementation already includes:

- role bindings,
- workspaces,
- workspace membership separated from data access,
- grants as active permission objects,
- capability policy rows,
- contribution permanence policy,
- `AccessPredicate` / workspace access decision behavior,
- institution aggregate-only database role checks.

Important implication for C10:

C10 requests should carry enough actor/workspace/grant/purpose context to evaluate whether the output is appropriate for the current audience and workspace. For example, a clinician workspace may use more technical language but still must preserve source-linking, uncertainty, and no-diagnosis boundaries.

### C2 Raw Context Vault

C2 has DB append-only controls:

- runtime role has `INSERT`/`SELECT` only,
- mutation trigger rejects `UPDATE`/`DELETE`,
- RLS enabled,
- raw blobs use object-lock storage in the local cluster path.

Important implication for C10:

Source/provenance obligations can rely on immutable raw event IDs and blob metadata.

### C3/C4/C5 external evidence retrofit

Recent retrofit work adds:

- C3 external evidence ingestion path that writes external sources to C16/external graph, never C2 Raw Context Vault.
- C4 Theory/external-claim extraction types where Theory is not a personal fact and external claim extraction remains external-scoped.
- C5 external evidence policy guards: external sources may be context-only relevance, not personal fact evidence.

Important implication for C10:

C10 must inspect whether an output uses personal evidence, external evidence, or both, and must enforce different language obligations. External evidence cannot be phrased as "this proves something about you."

### C6 external evidence graph separation

C6 retrofit separates:

- personal Knowledge Graph (`graph.*`),
- external evidence graph (`external_kg.*`),
- relevance bridge (`external_bridge.relevance_links`).

Important implication for C10:

External claims and relevance links are allowed only as context. User-facing text must display source-quality tier and avoid converting relevance into diagnosis or fact.

---

## 6. Existing C10-related open decisions

### 6.1 `engine-risk-tier-safety-routing.md`

Status: Open.  
Jira Spike: WEL-134.  
Blocks: WEL-74 risk-tier extension.

Current question:

> How should per-engine safety risk tiers be defined and wired into C10 — what controls differ per tier, and how is the tier enforced before any user-facing output?

The research requested in this brief should either answer this record directly or provide enough content for the agent to fill it faithfully.

### 6.2 `live-metric-safe-escalation-rules.md`

Status: Open.  
Jira Spike: WEL-132.  
Blocks: WEL-121.

This is a narrower C10-adjacent question for live metrics: thresholds, safe escalation, no panic language, no disease prediction, no silent urgent handling.

The C10 contract should be compatible with this later live-metric decision. It does not need to fully solve live metrics thresholds, but it should define how a live-metric engine is classified and gated.

---

## 7. What WEL-74 asks for

WEL-74 acceptance criteria:

- All AI-generated text passes through the safety pipeline before any user-facing output.
- Deterministic rule layer rejects:
  - diagnosis claims,
  - clinical certainty statements,
  - panic language,
  - provenance-absent claims.
- NeMo Guardrails policy layer runs after deterministic rules.
- Llama Guard classification runs as final gate.
- Any rejection emits `ai_output.blocked` event to the event backbone with reason code.
- Fail-closed: any exception in the pipeline blocks output.
- Safety eval harness regression suite passes with zero false-negatives on the do-not-diagnose corpus.
- Performance: p99 latency below 500 ms for full pipeline.

The implementation must not start until the research question is answered and the Decision Record is approved.

---

## 8. Specific research questions

Please answer the questions below in enough detail that an engineering team can implement and test the service.

### Q1 — C10 evaluation request contract

What fields should every C10 evaluation request include?

Consider:

- output text,
- output type,
- engine name,
- engine risk tier,
- workspace type,
- active role type,
- grant ID / purpose code,
- patient/user ID,
- Health Thread ID,
- Investigation ID,
- Theory ID,
- source references,
- source-quality tiers,
- clinical-review marker,
- urgency classification,
- provenance completeness,
- whether output is user-facing, clinician-facing, institution-facing, or research-facing.

What fields are mandatory? Which may be optional? Which missing fields should fail closed?

### Q2 — Deterministic rule layer

Define the deterministic checks that run before model-based guardrails.

At minimum, cover:

- diagnosis language,
- ruling-out language,
- ranked differential diagnosis,
- medication start/stop/change advice,
- clinical certainty / false closure,
- panic language,
- urgency-without-action,
- source/provenance absence,
- external evidence incorrectly phrased as user-specific fact,
- missing review marker,
- unsupported institution or research claims,
- privacy/access leakage between workspaces.

For each rule, provide:

- rule name,
- examples it should block,
- allowed alternative phrasing,
- reason code,
- whether it should block, rewrite, or allow with obligations.

### Q3 — Risk-tier taxonomy

Define the authoritative risk-tier taxonomy for engines.

Starting proposal from current docs:

| Tier | Engine examples |
|---|---|
| Low | timeline formatting, missing-context reminders |
| Medium | confounder detection, contradiction detection |
| Medium-high | Theory evaluation |
| High | external research relevance, live-metric escalation |
| Very high | cross-patient comparison / cohort comparison |

Please validate or revise this taxonomy.

For each tier, define:

- required input metadata,
- required source display,
- required uncertainty wording,
- clinical-review marker rules,
- whether rewrite is allowed,
- whether human review is required,
- whether urgent routing rules apply,
- whether external/model guardrails are mandatory,
- whether output can be generated if an upstream source is missing.

### Q4 — Output actions and obligations

What are the possible C10 decisions?

Potential actions:

- `allow`
- `allow_with_obligations`
- `rewrite_required`
- `block`
- `route_urgent`
- `manual_review_required`
- `fail_closed`

For each action, define:

- when it applies,
- whether the original text can be shown,
- whether rewritten text can be returned,
- what obligations downstream C13/UI must enforce,
- what C12 audit event is emitted.

### Q5 — NeMo Guardrails and Llama Guard layering

WEL-74 references deterministic rules, NeMo Guardrails, and Llama Guard.

Please recommend the layer order and purpose:

1. deterministic rule checks,
2. policy/dialogue guardrails,
3. model-based safety classifier,
4. final response contract validation.

Questions:

- What should deterministic rules catch before invoking model guardrails?
- What should NeMo Guardrails own?
- What should Llama Guard own?
- What should never be delegated to model-based guardrails?
- If NeMo or Llama Guard is unavailable, should the service block, degrade, or allow only low-risk outputs?
- How should C10 avoid relying on a model to enforce hard non-negotiable rules?

### Q6 — Provenance and source-quality obligations

What exactly counts as enough provenance for an output?

Consider:

- raw context event IDs,
- evidence link IDs,
- extracted fact IDs,
- source text span hashes,
- external source IDs,
- external source-quality tiers,
- relevance link IDs,
- thread/investigation/theory IDs.

Questions:

- Which output types require personal evidence refs?
- Which output types may use only external evidence?
- Which outputs require both?
- How should C10 handle summaries where claims aggregate multiple sources?
- How should C10 enforce "no orphan claims" at the text/output level?

### Q7 — Theory output safety

Theory outputs are especially sensitive.

Please define allowed and blocked phrasing for:

- evidence for a theory,
- evidence against a theory,
- missing data,
- theory status,
- next questions to discuss,
- clinician-reviewed theory annotation.

Hard constraint:

A Theory can never become a diagnosis, ranked differential, or "this is likely X" statement.

### Q8 — External evidence output safety

External evidence outputs must preserve the context-not-fact boundary.

Questions:

- How should source-quality tiers be displayed?
- What wording should be required for Tier 3-5 sources?
- Should Tier 5 sources ever be shown in user-facing output?
- How should C10 phrase "similar pattern" without implying it applies to the user?
- How should it block claims like "this paper proves your symptoms are caused by X"?

### Q9 — Urgency and live-metric compatibility

Define general C10 urgency behavior without solving all live metric thresholds.

Questions:

- What language is allowed when urgent attention may be needed?
- What language is panic-inducing and blocked?
- When must C10 require a next-step path?
- How should C10 distinguish device data from clinical data?
- How should C10 avoid both over-alerting and silent urgent-risk handling?

### Q10 — C12 audit event contract

Define the audit/event contract for C10.

At minimum:

- event names,
- payload fields,
- reason codes,
- whether event is user-visible, security-only, or admin-only,
- source references included,
- workspace/role/grant context,
- decision latency,
- guardrail layer that triggered the decision,
- failure/exception details without leaking sensitive text unnecessarily.

Existing WEL-74 says rejections emit `ai_output.blocked`. Please decide whether additional events are needed, such as:

- `ai_output.allowed`
- `ai_output.rewritten`
- `ai_output.routed_urgent`
- `ai_output.manual_review_required`
- `ai_output.fail_closed`

### Q11 — Performance and fail-closed behavior

WEL-74 has a target p99 latency below 500 ms for the full pipeline.

Questions:

- Is this realistic with deterministic checks + NeMo + Llama Guard?
- Should low-risk outputs use a different path than high-risk outputs?
- Which checks must be synchronous?
- Which checks can be async, cached, or precomputed?
- What happens if any layer times out?
- What timeout values are acceptable?
- Are there outputs that should be held for manual review instead of failing closed?

### Q12 — Regression harness

Define the safety eval harness.

It should include:

- do-not-diagnose corpus,
- panic language corpus,
- urgency-without-action corpus,
- external-evidence-misuse corpus,
- provenance-absent corpus,
- theory-as-diagnosis corpus,
- workspace leakage corpus,
- false-positive tracking for acceptable educational phrasing.

For each corpus, describe expected outcome and examples.

---

## 9. Expected deliverable from consultant

Please provide a written report with:

1. Executive recommendation.
2. Proposed C10 request DTO.
3. Proposed C10 response DTO.
4. Risk-tier taxonomy and controls matrix.
5. Deterministic rules table with reason codes.
6. NeMo Guardrails / Llama Guard layering recommendation.
7. Provenance and source-quality requirements.
8. Theory and external evidence phrasing rules.
9. Urgency routing rules.
10. C12 audit event contract.
11. Fail-closed and latency strategy.
12. Regression harness design with example test cases.
13. Open risks and trade-offs.
14. Source list / references.

The report should distinguish:

- requirements that are mandatory for MVP,
- requirements that can be post-MVP,
- requirements that should block implementation until resolved.

---

## 10. Files to reference

Canonical product and safety docs:

- `docs/system-design/platform_identity.md`
- `docs/system-design/system_design.md`
- `docs/system-design/system_principles.md`
- `docs/safety/safety_model.md`
- `docs/safety/do_not_diagnose_rules.md`
- `docs/architecture/component-map.md`

Relevant open decisions:

- `docs/decisions/safety-gate-evaluation-contract.md`
- `docs/decisions/engine-risk-tier-safety-routing.md`
- `docs/decisions/live-metric-safe-escalation-rules.md`
- `docs/decisions/theory-object-evaluation-and-safety.md`
- `docs/decisions/external-evidence-graph-separation.md`
- `docs/decisions/deep-grant-role-workspace-model.md`

Relevant implemented package areas:

- `backend/packages/c10_safety/`
- `backend/packages/c5_evidence/`
- `backend/packages/c6_graph/`
- `backend/packages/c1_consent/`
- `backend/packages/contracts/`

---

## 11. Non-goals

Do not propose:

- a diagnosis engine,
- ranked differential diagnosis output,
- autonomous medication advice,
- institution-controlled safety policy that weakens individual protections,
- default clinician or institution access,
- cross-patient comparison without explicit individual opt-in,
- model-only enforcement for hard safety rules,
- safety bypasses for "trusted" workspaces.

---

## 12. Agent protocol note

Research results must be provided by the user. Agents may record, summarize, and propose a Decision Record from the provided research, but agents may not conduct external research for this Spike or implement WEL-74 before the Decision Record is approved.
