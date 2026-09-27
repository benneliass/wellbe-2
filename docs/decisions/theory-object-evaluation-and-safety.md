# Decision: Theory object evaluation model and non-diagnostic safety routing

**Status:** Approved  
**Date opened:** 2026-05-31  
**Date approved:** 2026-06-01  
**Approved by:** User  
**Jira Spike:** WEL-129  
**Blocks:** WEL-114 (Theory object), WEL-115 (Theory Evaluator), WEL-125 (C4 extraction retrofit)

---

## Question

How should the **Theory** object (C15) be evaluated against personal data and external evidence to produce evidence-for / evidence-against / missing-data and a status — without ever crossing into diagnosis — and how does that output route through the Safety & Governance Gate (C10)?

Specifically:
1. What is the authoritative theory status taxonomy (unreviewed / needs_more_data / partially_supported / not_supported_by_current_data / contradicted_by_current_data / discuss_with_clinician / clinician_reviewed) and what transitions are permitted?
2. Where is a Theory stored relative to Six Memories (C8) — is it a Pattern Memory entry, a first-class object, or both?
3. What C10 rules block a theory output from asserting a diagnosis or a ranked differential, and what triggers the `discuss_with_clinician` / urgent routing?
4. How are external sources (C16) attached as evidence without importing their claims as facts about the user?

## Context

The Theory object is the safe vehicle for user/clinician hypotheses and is the single most diagnosis-adjacent surface in the product. Getting the status taxonomy and the C10 routing wrong risks the system implying a diagnosis — the hardest safety line in `docs/safety/do_not_diagnose_rules.md`. C8 (Six Memories) and C10 (Safety Gate) are both touched, and the theory-evidence contract is consumed by the Theory Evaluator engine and the clinician workspace.

## Research provided

_Research received: 2026-05-31_ — external consultant report, archived verbatim at [research-inputs/wellbe_c6_kg_retrofit_report.md](research-inputs/wellbe_c6_kg_retrofit_report.md). Section 4 addresses this decision. Source basis: FHIR Provenance / Evidence / DetectedIssue [S1, S10, S15]; W3C PROV [S2]; FDA Clinical Decision Support Software guidance [S19]; ONC Decision Support Intervention criteria, 45 CFR 170.315 [S20]; SNOMED CT context/concept model [S23, S24]; GRADE / OCEBM evidence-quality concepts [S11, S12].

## Approaches considered

_Based only on the provided research (report §4.2)._

1. **Reuse `ConditionHypothesis` node as Theory.** Minimal migration, reuses graph semantics/`potential_score`. Cons: too risky — `ConditionHypothesis` + clinical terms read as diagnostic and conflate an investigation hypothesis with a clinical condition concept; SNOMED context ambiguity argues for *less* overloading [S23, S24].
2. **First-class Theory aggregate (C15) with C6 projection + optional C8 derivative (recommended).** Strong lifecycle/safety boundary; clear separation of personal evidence vs external context vs user-facing narrative; supports immutable evaluation versions + additive correction. Cons: more schema/service logic, careful projection/consistency tests. Grounded in FHIR Provenance/PROV traceability [S1, S2] and FDA CDS / ONC DSI transparency + reviewability + source-attribute + risk-management expectations [S19, S20].
3. **Store Theory only in Six Memories / Pattern Memory.** Fits the memory-centric vision, simpler persistence. Cons: Pattern Memory is not a safe lifecycle authority for an object that can be unreviewed/blocked/clinician-reviewed/urgent-routed; memories are summaries, theories need commands, transitions, C10 results, external context, audit [S1].
4. **External-evidence-first model (source quality decides support).** Good for evidence-based research, can leverage GRADE/OCEBM [S11, S12]. Cons: violates the separation rule — external evidence can support general plausibility but cannot assert the theory is true *for the user* and must never upgrade personal support status by itself [S10, S15].

## Decision

_Proposed (report §4.3, §6.3):_ Model **Theory as a first-class C15 aggregate** (status, safety_level, immutable evaluation versions, personal-evidence references, missing-data items, external-context references), **projected into C6 as a `Theory` node** with `evidence_for`/`evidence_against` edges created **only from personal, C5-provenance-backed facts**. **Status and safety_level are kept separate** — status describes what personal-data review found; safety_level tells C10 what to do with any output. Authoritative status taxonomy: `unreviewed / needs_more_data / partially_supported / not_supported_by_current_data / contradicted_by_current_data / discuss_with_clinician / clinician_reviewed` (no `confirmed/ruled_out/diagnosed/likely`/ranked-differential). Safety levels: `low / needs_clinician_context / urgent_symptom_present / blocked_due_to_diagnostic_claim`. Theory text is **normalized into a non-diagnostic question** (or stored `blocked_due_to_diagnostic_claim` and withheld). **Personal support status is determined by personal facts only**; external sources (C16) attach as context that may explain general plausibility but never become graph evidence edges. **C8** may store a derived Pattern Memory summary **only after C10 passes** the output. **C10** blocks diagnostic assertions, ranked differentials, disease claims, unsupported personal statements, and external-context contamination, and enforces external-context labeling + urgent-symptom routing.

Satisfies the hard constraints: **G1** (status ≠ diagnosis; causal ceiling `may_explain`; C10 blocks prohibited verbs), **G2** (external sources are context-only, never `evidence_for/against` graph edges), **G3** (every personal evidence edge requires C5 provenance), **G4** (a theory cannot close a thread/investigation), **G5** (additive), **G6** (theory rows + nodes RLS-scoped), **G7** (`clinician_reviewed` requires a valid, unrevoked grant).

## Trade-offs accepted

- External evidence does not directly increase personal support status — intentionally conservative.
- Two-layer storage (C15 authoritative, C6 projection, C8 derived) is more complex but safer.
- More blocked/rewritten outputs when phrasing sounds diagnostic.
- Theory-text normalization (reframing assertions as questions) may frustrate some users — required for the safety posture.

## Implementation notes

_From report §4.5 (verbatim DDL in the archived report)._

- **Tables (schema `c15`):** `theories` (patient_id, created_by, linked_investigation_id FK→`c14.investigations`, theory_text, `normalized_question`, theory_type CHECK, status CHECK, safety_level CHECK, latest_evaluation_id, supersedes_theory_id); `theory_evaluations` (immutable: evaluation_version, evidence_for/against_node_ids[], missing_data, external_context_link_ids[], proposed_status, proposed_safety_level, `c10_gate_result jsonb`, evaluator_actor); `theory_external_context` (external_source_id/claim_id, relevance_link_id, context_direction, `context_only IS TRUE` CHECK). RLS on all.
- **C6 projection + edges:** `Theory` node (`normalized_key='theory:'||id`, metadata incl. theory_type/status/safety_level/linked_investigation_id); `evidence_for`/`evidence_against` edges **personal fact node → Theory node**, both endpoints same `patient_id`, source fact must have C5 provenance; `potential_score` stays an internal provenance/completeness metric (`score_semantics='personal_evidence_quality'`), not theory probability.
- **Evaluation flow:** normalize text → safe question (or block); collect personal facts via C6/C5 (no provenance ⇒ no edge); create personal evidence edges only; list missing data; attach external context separately (`theory_external_context` + `relevance_links`); assign status from personal data; pass all user-facing text through C10.
- **C10 rules:** block diagnostic assertions ("you have", "diagnosis is", "most likely", "rules out", "confirms", "proves", "caused by", ranked differentials); causal ceiling `may_explain`; provenance required for any statement about the user's data; external sources must show type+tier+"context only — not evidence about you"; `urgent_symptom_present` suppresses the theory and shows approved urgent-routing; bias/equity check per ONC DSI [S20].
- **Discuss-with-clinician / urgent triggers:** medication/adverse/contraindication/allergy/abnormal-lab/vital/care-gap concerns, contradictory/incomplete evidence that could change care, Tier 3–5-only external context that would overstate weak evidence, active clinician grant prepared for visit, or C10 judging clinical interpretation required. `urgent_symptom_present` set by validated red-flag rules.
- **Six Memories relationship:** C15 authoritative; C6 projection; C8 derived summary only post-C10, carrying `source_theory_id`/`source_evaluation_id`/`c10_gate_id`.
- **Prohibited (test-enforced) paths:** `external_claim → evidence_for → Theory`, `external_claim → may_explain → Symptom`, `external_source → corroborating evidence_link → personal fact`.
- **Open risks:** users reading `partially_supported` as diagnosis (label = "some of your data is consistent with this question"); external leakage into personal support (status uses personal evidence only); C10-as-sole-guardrail (also enforce via prohibited edge types, schema constraints, validators, tests); hidden diagnostic claims in text (normalize/block); `clinician_reviewed` implying endorsement (means "reviewed under grant", require `review_note_type`); memory/authoritative divergence (C8 derived + additive supersede).

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_

---

## Amendment — 2026-09-27: user-authored theory evaluation

**Status:** Approved (owner, 2026-09-27). Additive only — nothing above is changed or superseded.

**What changes.** The user can evaluate their own theory: they mark it **supported**, **weakened**, **ruled out**, **under review**, or reopen it (**open**), and **must** cite at least one piece of their own evidence plus a short rationale. The system never auto-decides a user evaluation.

**How it fits G1 (no diagnostic statuses).** The user's mark is a separate, user-attributed `assessment`; it is **not** a new status. It maps onto the existing taxonomy, which is unchanged (the `c15.theories.status` CHECK is untouched):

| User mark | Stored status |
|---|---|
| open | `unreviewed` |
| under_review | `needs_more_data` |
| supported | `partially_supported` |
| weakened | `not_supported_by_current_data` |
| ruled_out | `contradicted_by_current_data` |

Copy is always attributed to the user ("You marked this theory as ruled out"), never phrased as a system finding, and every response still carries `not_diagnosis: true`. A user mark never lowers `safety_level`; theories withheld as `blocked_due_to_diagnostic_claim` cannot be evaluated.

**Evidence (G2/G3).** Each cited ref (a C5 evidence link, C4 fact, or C2 capture) must belong to the same patient **and** to a thread linked to the theory's investigation, otherwise the request is rejected (422 `theory_evidence_not_found` / `theory_evidence_unrelated`). External sources cannot be cited. In C6, the cited facts' graph nodes get `evidence_for` (supported) or `evidence_against` (weakened / ruled out) edges to the Theory node, marked `source: user_evaluation`. The graph shows the user's *current* view: edges from an earlier user evaluation that the latest one no longer cites are removed (open / under review removes them all), while the immutable evaluation log in `c15.theory_evaluations` keeps the full history. Edges written by the system evaluator are never touched.

**Mechanics.** Evaluations are recorded in the existing `c15.theory_evaluations` log (`evaluation_kind = 'user'`), with a DB CHECK requiring rationale + ≥1 evidence ref for user rows. `c15.theories.version` provides optimistic concurrency (`expected_version`, 409 on conflict). Writes are controller-only, audited (`c13.theory.evaluated`), idempotent (`Idempotency-Key`), and emit `c15.theory.evaluated.v1`. No AI-rendered copy is produced, so no C10 pass is needed for this path; any future AI copy about evaluations must go through C10.
