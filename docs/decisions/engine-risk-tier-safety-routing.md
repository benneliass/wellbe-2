# Decision: Per-engine safety risk tiers and Safety Gate routing

**Status:** Proposed - awaiting user approval  
**Date opened:** 2026-05-31  
**Date approved:** YYYY-MM-DD (fill on approval)  
**Approved by:** User  
**Jira Spike:** WEL-134  
**Blocks:** WEL-74 (C10 Safety & Governance Gate risk-tier extension)

---

## Question

How should **per-engine safety risk tiers** be defined and wired into the Safety & Governance Gate (C10) — what controls differ per tier, and how is the tier enforced before any user-facing output?

Specifically:
1. What is the authoritative tier assignment (lower: timeline/missing-context; medium: confounder/contradiction; medium-high: theory; high: external research, live-metric; very high: cross-patient) and where is it stored?
2. What concrete controls differ per tier (e.g. mandatory human-readable uncertainty, source-tier display, clinician-review marker, urgent routing, output blocking)?
3. How does C10 receive the engine's tier and refuse to emit if a higher-tier output lacks the required controls?
4. How are new engines forced to declare a tier (fail-closed default to highest)?

## Context

The expanded vision adds several higher-risk engines (theory, external research, live-metric, cross-patient). C10 is the single hardest architectural rule — the safety gate before any AI output. Without a tier-aware routing contract, higher-risk engines could emit through the same path as low-risk ones. C10 is already specced (WEL-74); this decides how the tier dimension extends it. Wrong design weakens the central safety guarantee for every workspace.

## Research provided

_Research received: 2026-06-01_ - external consultant report, archived verbatim at [research-inputs/c10_safety_gate_evaluation_contract_report.md](research-inputs/c10_safety_gate_evaluation_contract_report.md) (source `.docx` alongside it). This report also fills the broader C10 evaluation contract in [safety-gate-evaluation-contract.md](safety-gate-evaluation-contract.md).

The report says the proposed risk-tier taxonomy is mostly valid, but it must be formalized as **engine risk tier plus output type**. A low-risk engine can still produce a high-risk output if it mentions urgency, medication, diagnosis, external research relevance, cross-patient comparison, or user-specific medical conclusions.

The report defines five authoritative tiers:

- **Low** - formatting or reminding over already-known user data; no new clinical interpretation, external relevance, urgency, or medication guidance. Examples: timeline formatting, source-list formatting, missing-context reminders phrased as "not found in uploaded records."
- **Medium** - detects relationships, contradictions, confounders, missing context, or patterns across personal sources; may influence how a user interprets health data. Examples: contradiction detection, confounder detection, pattern/missing-context output.
- **Medium-high** - evaluates a Theory or expresses evidence for/against/missing in a way that could be mistaken for diagnosis. Examples: Theory evaluation, theory update summary, theory visit-prep questions.
- **High** - uses external medical evidence as relevant context, handles urgency/live metrics, medication-related content, or escalation language. Examples: External Evidence Watch, external research relevance, live-metric safe escalation, medication-safety reminders, urgent symptom routing.
- **Very high** - compares across people, cohorts, institutions, or research contexts where privacy, consent, representativeness, and misuse risk are high. Examples: cross-patient comparison, institution aggregate insight, cohort comparison, research sandbox outputs.

Risk tier controls from the report:

- All tiers require the base C10 DTO, claim map, review marker, source/provenance status, workspace/role/access context, policy versions, and C12 audit.
- Low-risk outputs may use per-item/source-drawer source display and "based on uploaded information" uncertainty language.
- Medium-risk outputs require claim-level source display, derivation/source refs, and wording such as "may indicate a mismatch" or "remains unresolved."
- Medium-high Theory outputs require `theory_id`, grouped support/contradiction/missing claim classes, claim-level sources, review markers, and wording such as "supports/does not support the theory; does not confirm or rule out."
- High-risk outputs require external tiers or live metric/device context, urgency context, action path for orange/red, source-quality/device caveats, and wording such as "context only / not specific to you / device reading not diagnosis."
- Very-high-risk outputs require cohort/aggregate ids, opt-in/privacy proof, aggregate methodology, no individual refs in UI, privacy/consent proof, and usually manual review before release/export.
- For MVP/WEL-74, all AI-generated user-facing health text runs deterministic rules, NeMo Guardrails, Llama Guard, final contract validation, and C12 audit. Risk tier changes enabled rules, NeMo config, obligations, manual review, output length caps, external evidence allowance, and urgent fallback templates; it must never create a bypass.
- New engines must declare a tier through an authoritative registry/policy version. Missing tier metadata fails closed; unknown/new engines default to highest risk until explicitly classified.

## Approaches considered

Approach 1: Engine-only tiering - classify by engine name alone. Pro: simple registry. Con: report says low-risk engines can produce high-risk output when content includes urgency, medication, external relevance, cross-patient comparison, or medical conclusions. Research recommendation: reject.

Approach 2: Output-only tiering - infer risk from output type/text only. Pro: catches escalated output even from low-risk engines. Con: loses the declared engine policy boundary and makes new engines easier to ship without classification. Research recommendation: reject as the only mechanism.

Approach 3: Engine risk tier plus output type escalation - require every engine to declare a tier, then let output type/content escalate controls. Pro: preserves a fail-closed registry while catching high-risk content from any producer. Con: needs more metadata and policy validation. Research recommendation: adopt.

## Decision

Adopt risk routing as **engine risk tier plus output type/content escalation**: every AI producer must declare an authoritative engine risk tier and output type in the C10 request; missing or unknown tiers fail closed and new engines default to `very_high` until classified; C10 may escalate controls based on output type/content, and every tier still passes the full MVP C10 pipeline without bypass.

## Trade-offs accepted

If approved, this accepts:

- More request metadata and registry management in exchange for fail-closed onboarding of new engines.
- Low-risk outputs still pay the full MVP C10 pipeline cost, which protects against accidental bypass but affects latency.
- Content escalation can make a low-risk engine subject to higher-risk obligations, increasing implementation complexity.
- Very-high-risk outputs may need manual review and privacy proof before release/export.
- The risk-tier matrix must remain versioned policy, not ad hoc application logic.

## Implementation notes

If approved:

- Add `engine_risk_tier`, `output_type`, `risk_tier_policy_version`, `engine_name`, and `engine_version` to the C10 request contract.
- Add an authoritative engine registry/policy table or config package. New engines must declare a tier; unknown engines fail closed/default very high.
- Implement output-type/content escalation: urgency, medication, diagnosis-like language, external relevance, live metrics, cross-patient/cohort, institution aggregate, and research outputs apply higher-tier controls even if the producer tier is lower.
- Use tier-specific obligations for source display, uncertainty wording, review markers, external source-quality tier display, device-data caveats, urgent action paths, aggregate privacy proof, and manual review.
- For MVP, do not create a low-risk bypass path; all AI-generated user-facing health text runs deterministic checks, NeMo, Llama Guard, final token validation, and audit.
- Keep this DR consistent with `docs/decisions/safety-gate-evaluation-contract.md`; the broader C10 request/response contract is the implementation vehicle for this tier decision.

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
