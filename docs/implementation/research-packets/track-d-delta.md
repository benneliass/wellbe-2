# Research Context Packet — Track D / delta-semantics-window

> This packet is BOTH the user's review artifact AND the prompt sent to the research
> runner. Never propose an answer to the decision question. See `.cursor/rules/research-protocol.mdc`.

**Spike:** WEL-163
**Blocks:** WEL-56 WB2-F018: Note and document delta view
**Decision Record:** `docs/decisions/delta-semantics-window.md`
**Core component(s) touched:** Continuity & Closure (C9), Processing (C4)
**Date assembled:** 2026-06-17

---

## 1. Identity and guardrails (non-negotiables)

`docs/system-design/platform_identity.md`, `.cursor/rules/wellbe-vision-guardrails.mdc`, `.cursor/rules/audience-guardrails.mdc`. Personal-first; source-linked; non-diagnostic; calm/never-alarm. The delta view answers "what changed from my normal" without manufacturing alarm.

## 2. System placement

The `delta` pill sits at Connect → Clarify: surfacing what changed across time/sources for the user. See `docs/system-design/system_design.md`.

## 3. Component dossier

- **C9 Continuity & Closure** — pending item ledger, result tracker, longitudinal view. Depends on C7/C8.
- **C4 Processing** — computes facts/signals and (with baselines) value deltas. Depends on C2.
Blast radius: contained to the continuity/processing read path; component-local.

## 4. Current state (what exists vs. what is missing)

- Existing: `/v2/pending-items` (C13) — the continuity ledger; `/v1/threads`. UI stub at `apps/web/app/(workspace)/delta/page.tsx` (ComingSoon); Home "What Changed" region spec (WEL-145).
- Missing: the delta computation semantics, the comparison-window rule, and the ordering/ranking contract.

## 5. The decision question(s)

1. What counts as a meaningful change (new facts, status transitions, value deltas vs. baseline)?
2. What comparison window is used, and how is it chosen (fixed window, since-last-visit, since-last-open)?
3. How are deltas ordered/ranked for the user, calm and source-linked?

## 6. Stakes

Wrong delta semantics either hide real changes (a continuity failure — the exact harm WellBe exists to prevent) or manufacture noise/alarm (violating never-alarm).

## 7. Unblocks

WEL-56 (delta view) and the Home "What Changed" region (WEL-145) (Track D).

## 8. Prior art

`docs/system-design/system_design.md` (continuity/closure); approved decisions under `docs/decisions/`.

## 9. Where to look (research directions, NOT answers)

Change-detection/diff semantics for longitudinal health records; baseline/normal-range modeling; salience/ranking approaches that avoid alarm; time-window selection for "what changed" digests. No proposed answer.
