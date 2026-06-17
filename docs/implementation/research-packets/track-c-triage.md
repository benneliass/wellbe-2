# Research Context Packet — Track C / triage-escalation-safety-rules

> This packet is BOTH the user's review artifact AND the prompt sent to the research
> runner. Never propose an answer to the decision question. See `.cursor/rules/research-protocol.mdc`.
>
> **MANDATORY C10 spike.** Per research-protocol Section I, the agent MUST confirm with the
> user before agent-running research for this Spike.

**Spike:** WEL-162
**Blocks:** WEL-47 WB2-F019: Deterioration check-in and escalation guidance
**Decision Record:** `docs/decisions/triage-escalation-safety-rules.md`
**Core component(s) touched:** Safety & Governance Gate (C10)
**Date assembled:** 2026-06-17

---

## 1. Identity and guardrails (non-negotiables)

`docs/system-design/platform_identity.md`, `.cursor/rules/wellbe-vision-guardrails.mdc`, `.cursor/rules/audience-guardrails.mdc`, `docs/safety/safety_model.md`, `docs/safety/do_not_diagnose_rules.md`. Investigate-never-diagnose; calm/never-alarm; the safety gate runs before any user-facing output; the system empowers the user within the clinical system, it does not replace clinical judgment.

## 2. System placement

The `triage` pill is the user-initiated "Something feels off" check-in. It spans Capture → Clarify and must route safely without diagnosing. See `docs/system-design/system_design.md`.

## 3. Component dossier

- **C10 Safety & Governance Gate** — mandatory gate before any user-facing AI output: do-not-diagnose, panic-language, provenance, bias controls. Depends on C5/C7. Repo: `backend/apps/safety-gate/`. This is the single hardest architectural rule; the most consequential spike in the build-out.

## 4. Current state (what exists vs. what is missing)

- Existing: safety-gate service in the cluster; `docs/safety/` rules. UI stub at `apps/web/app/(workspace)/triage/page.tsx` (ComingSoon).
- Missing: the check-in question model, the escalation tier criteria, the never-alarm language rules, and the response-routing contract behind C10.

## 5. The decision question(s)

1. What are the do-not-diagnose boundaries for the check-in (what may/may not be said)?
2. What never-alarm language constraints govern any escalation message?
3. What criteria map a check-in to an escalation tier, and what are the tiers?
4. What is the response routing (self-care guidance vs. "seek care" vs. emergency), non-diagnostic and source-aware?

## 6. Stakes

A wrong escalation or never-alarm rule is a direct safety risk to the user — under-escalating a real emergency, or alarming the user without cause. Irreversible harm potential.

## 7. Unblocks

WEL-47 (deterioration check-in + escalation guidance) (Track C).

## 8. Prior art

`docs/safety/safety_model.md`, `docs/safety/do_not_diagnose_rules.md`; any prior C10 decisions under `docs/decisions/`.

## 9. Where to look (research directions, NOT answers)

Validated symptom-triage/escalation frameworks and self-triage standards; crisis-safe and never-alarm communication guidelines; do-not-diagnose constraints for consumer health tools; safe-routing taxonomies (self-care / seek-care / emergency). No proposed answer.
