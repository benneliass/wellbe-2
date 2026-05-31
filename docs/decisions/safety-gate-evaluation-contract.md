# Decision: Safety Gate evaluation contract for AI output

**Status:** Proposed - awaiting user approval  
**Date opened:** 2026-06-01  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-134  
**Blocks:** WEL-74 — Implement layered Safety Gate service with deterministic rules, NeMo Guardrails, and Llama Guard

---

## Question

What is the approved C10 Safety & Governance Gate evaluation contract for user-facing AI output in the Patient-Centered Health Investigation OS?

Specifically:
1. Which deterministic rule classes must run before any model-based guardrail layer?
2. What provenance, source-quality, clinical-review marker, and uncertainty obligations are required for each risk tier?
3. How are engine risk tiers declared, validated, and enforced fail-closed before output reaches the user?
4. What outputs must be blocked, rewritten, routed to urgent guidance, or allowed with obligations?
5. What audit events and payload fields must C12 receive for allowed, denied, rewritten, and failed evaluations?
6. What latency and degradation behavior is acceptable when external guardrail layers are unavailable?

## Context

C10 is the mandatory gate before any user-facing AI output across every WellBe workspace. The new Investigation OS adds higher-risk output producers: Theory evaluation, External Evidence relevance, Live Metrics safe escalation, cross-patient comparison, clinician workspaces, institution continuity, and research sandbox outputs. A weak C10 contract would allow one of those engines to bypass do-not-diagnose, provenance, source-quality, urgency, or review-state requirements, undermining the platform's central safety guarantee.

## Research provided

_Research received: 2026-06-01_ - external consultant report, archived verbatim at [research-inputs/c10_safety_gate_evaluation_contract_report.md](research-inputs/c10_safety_gate_evaluation_contract_report.md) (source `.docx` alongside it).

The report recommends defining C10 as a mandatory synchronous enforcement service, not as an AI authoring layer. Every user-facing AI or AI-assisted health output must be submitted to C10 with enough context to evaluate the exact text for the current actor, workspace, grant, purpose, patient/thread/investigation/theory context, evidence bundle, and audience.

The recommended service flow is:

```text
AI producer
  -> C10 schema/context/provenance validation
  -> deterministic hard-safety rules
  -> NeMo Guardrails policy layer
  -> Llama Guard response classifier
  -> final response contract validation + signed render token
  -> C13/API
  -> user-facing surface
```

The report's central conclusion is that hard WellBe rules are never delegated to a model. No-diagnosis, no rule-out, no medication directives, no orphan claims, access/grant enforcement, source-quality boundaries, urgent-action requirements, and fail-closed behavior must be deterministic and testable. NeMo Guardrails and Llama Guard add semantic defense-in-depth, but they are not the source of truth for non-negotiable product safety rules.

The report recommends MVP implementation blockers:

- Versioned C10 request/response DTOs with mandatory source, access, risk-tier, urgency, and review-marker fields.
- Claim-level provenance map for every health claim.
- Deterministic hard-rule tests with zero false negatives on the do-not-diagnose corpus.
- C12 audit events for allowed, blocked, rewritten, urgent, manual-review, and fail-closed outcomes.
- C13 enforcement that renders only text carrying a C10 signed render token tied to the exact output hash.
- A measured local-cluster latency plan. The 500 ms p99 target is realistic only with warm in-cluster guardrail services, bounded output length, precomputed provenance, optimized guardrail calls, fast audit enqueue, and no remote third-party model call on the critical path.

The proposed C10 request contract includes:

- exact candidate output text, `text_sha256`, format, language, output type, target audience, surface, review markers, urgency context, claim map, claim-map completeness flag, and no-health-claims flag;
- producer metadata: engine name/version, engine risk tier, upstream run id, optional model/provider/template/config hashes;
- actor/access context: actor id, subject/patient id when applicable, workspace id/type, active role type, grant id when needed, purpose code, access decision id, access predicate hash, organization id, and data scope ids;
- health context: Health Thread, Investigation, Theory, Visit Packet, live metric session, cohort query, or aggregate result ids as applicable;
- source context: evidence bundle id, provenance completeness, personal sources, external sources, relevance links, negative-evidence query ids, aggregate privacy context;
- policy context: C10 policy version, deterministic ruleset version, NeMo config id, Llama Guard policy version, risk-tier policy version, and allowed rewrite mode;
- trace context: correlation/trace/span ids.

Mandatory missing, malformed, stale, or inconsistent fields fail closed. Examples from the report: absent risk tier, absent claim map, absent review marker, absent provenance, clinician workspace without grant id, external source without tier, orange/red urgency without action path, theory output without theory id, and institution output carrying patient-level claims.

The proposed response contract returns a decision (`allow`, `allow_with_obligations`, `rewrite_required`, `block`, `route_urgent`, `manual_review_required`, `fail_closed`), original-text renderability, optional safe effective text, signed render token, obligations, reason codes, layer results, emitted audit ids, latency breakdown, policy versions, and manual-review queue metadata when needed.

C13 must refuse to render any AI output unless:

- the C10 decision is `allow`, `allow_with_obligations`, or `route_urgent`;
- a valid render token is present;
- the render token's text hash matches the exact rendered text;
- all C10 obligations are fulfilled by the UI/API surface;
- any post-C10 edit triggers re-evaluation.

The proposed deterministic rule layer includes: context/contract required, no safety bypass, no diagnosis assertion, no rule-out assertion, no ranked differential, no probability diagnosis, no medication directive, no clinician blame diagnosis, no false closure, no panic language, urgency requires action, no urgent suppression, no orphan health claims, claim-source match, external context only, external tier required, low-tier external overclaim, review marker required, clinician review proof, device data boundary, access scope match, workspace leakage, institution aggregate-only, cross-patient opt-in, aggregate privacy minimum, theory not diagnosis, and final text hash match.

The proposed C12 audit events are:

- `ai_output.allowed`
- `ai_output.allowed_with_obligations`
- `ai_output.rewrite_required`
- `ai_output.rewritten`
- `ai_output.blocked`
- `ai_output.routed_urgent`
- `ai_output.manual_review_required`
- `ai_output.fail_closed`

The report recommends storing text hashes, matched span offsets, rule ids, source ids, sanitized reason codes, layer statuses, latency, and workspace/role/grant context in C12. Full candidate text should not be placed on the event backbone by default. If blocked text is retained for safety QA, it must be encrypted in a restricted safety-review store with a separate retention policy and referenced by `secure_text_ref`.

The regression harness must include do-not-diagnose, rule-out/false-closure, ranked differential, medication directive, panic language, urgency-without-action, urgent safe phrasing, external misuse, Tier 3-5 overclaim, provenance absent, missing-context safe phrasing, theory-as-diagnosis, theory-safe phrasing, workspace leakage, institution leakage, cross-patient no-opt-in, review-marker missing, clinician-marker unsupported, device overclaim, and safe device caveat corpora. MVP CI gates require zero false negatives for do-not-diagnose, rule-out, medication directive, provenance absent, access leakage, urgent-without-action, panic language, and contract-missing-fields corpora.

## Approaches considered

Approach 1: Model-only guardrail enforcement - rely primarily on NeMo/Llama Guard to classify unsafe output. Pro: simple integration and flexible semantic coverage. Con: the report says hard WellBe rules cannot be delegated to model guardrails because access, provenance, no-diagnosis, no-orphan-claims, source-tier boundaries, render-token enforcement, fail-closed behavior, and audit emission must be deterministic. Research recommendation: reject.

Approach 2: Deterministic rules only - enforce exact lexicons/metadata checks without NeMo or Llama Guard. Pro: testable and fast. Con: regex/rule-only checks miss paraphrases and implied diagnosis/certainty. Research recommendation: reject as insufficient for WEL-74, but make deterministic rules the source of truth for non-negotiable constraints.

Approach 3: Asynchronous/post-render safety checking - allow producers or C13 to render while safety checks run separately. Pro: lower apparent latency. Con: violates the non-bypass rule and can expose unsafe output before enforcement. Research recommendation: reject.

Approach 4: Mandatory synchronous layered enforcement - validate schema/access/provenance, run deterministic hard-safety rules, then NeMo Guardrails, then Llama Guard, then final token/obligation/audit validation before C13 render. Pro: preserves WellBe's safety invariants and adds semantic defense-in-depth. Con: more implementation complexity and the 500 ms p99 target requires warm local guardrail services and bounded output. Research recommendation: adopt.

## Decision

Adopt a mandatory synchronous C10 Safety Gate contract: every user-facing AI or AI-assisted health output must be submitted with a complete versioned request DTO, claim-level provenance map, actor/workspace/grant/access context, risk tier, urgency context, review markers, and policy versions; C10 must enforce deterministic hard-safety rules before NeMo Guardrails and Llama Guard, return a versioned decision with obligations and reason codes, emit C12 audit events, and issue a signed render token bound to the exact output hash that C13 must verify before rendering.

## Trade-offs accepted

If approved, this accepts the following trade-offs from the report:

- C10 becomes a synchronous critical path service, increasing latency and operational complexity.
- The 500 ms p99 target is conditional on warm in-cluster guardrail services, short/bounded outputs, precomputed provenance, optimized model serving, fast audit enqueue, and no remote model API on the critical path.
- Upstream producers must emit structured claim maps and source refs; C10 verifies them but does not invent missing provenance.
- Llama Guard and NeMo may overblock safe health education, requiring a false-positive tracking corpus and ongoing tuning.
- Tier 5 external material is hidden by default in MVP; this limits breadth of research/community context in exchange for safety.
- Very-high-risk outputs may require manual review, which creates operational requirements for reviewer roles, queues, SLAs, and grant boundaries.
- Fail-closed behavior may suppress otherwise useful output when metadata, provenance, guardrails, or audit systems are unavailable.

## Implementation notes

If approved, implementation should:

- Add versioned C10 request/response contracts under `backend/packages/contracts/src/wellbe_contracts/`.
- Include `C10SafetyEvaluationRequestV1`, `C10SafetyEvaluationResponseV1`, `ClaimMapEntry`, source refs, urgency context, obligations, layer results, guardrail results, risk tiers, decisions, and reason-code enums.
- Implement `backend/packages/c10_safety/` as a synchronous service/evaluator with schema validation, access/provenance hooks, deterministic rule engine, NeMo/Llama Guard adapter interfaces, final token generation, and C12 audit emission.
- Keep hard WellBe rules deterministic: no diagnosis, no rule-out, no ranked differential, no medication directive, no false closure, no panic language, urgency-without-action, no orphan claims, external-context-only, source-tier required, review-marker proof, device-data boundary, access/workspace/institution/privacy leakage, cross-patient opt-in, and render-token hash match.
- Implement C13 render-token enforcement so post-C10 text edits invalidate renderability and require re-evaluation.
- Emit C12 events for allowed, allowed-with-obligations, rewrite-required, rewritten, blocked, routed-urgent, manual-review-required, and fail-closed decisions.
- Do not place raw blocked text on the event backbone; use text hash and restricted encrypted storage only if safety QA retention is explicitly enabled.
- Fail closed on missing mandatory DTO fields, stale/inconsistent policy versions, missing provenance, guardrail timeout/unavailability, access decision failure, source verification failure, render-token mismatch, or exceptions.
- Allow manual-review-required only for policy holds such as very-high-risk cross-patient/cohort outputs, aggregate privacy uncertainty, Tier 3-5 external evidence in care-facing contexts, unsupported clinician review marker, or repeated false-positive classes under QA.
- Implement MVP regression corpora with zero false negatives for do-not-diagnose, rule-out, medication directive, provenance absent, access leakage, urgent-without-action, panic language, and contract-missing-fields.
- Measure local `kind-desktop` p99 latency with warm in-cluster guardrail services before claiming WEL-74 performance acceptance.

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
