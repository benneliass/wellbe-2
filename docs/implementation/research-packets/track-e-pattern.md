# Research Context Packet — Track E / pattern-detection-semantics

> This packet is BOTH the user's review artifact AND the prompt sent to the research
> runner. Never propose an answer to the decision question. See `.cursor/rules/research-protocol.mdc`.

**Spike:** WEL-164
**Blocks:** WEL-79 Implement Pattern, Temporal, Confounder, Missing-Data, and Contradiction intelligence engines
**Decision Record:** `docs/decisions/pattern-detection-semantics.md`
**Core component(s) touched:** Processing (C4), Knowledge Graph (C6), Six Memories (C8)
**Date assembled:** 2026-06-17

---

## 1. Identity and guardrails (non-negotiables)

`docs/system-design/platform_identity.md`, `.cursor/rules/wellbe-vision-guardrails.mdc`, `.cursor/rules/audience-guardrails.mdc`, `docs/safety/do_not_diagnose_rules.md`. Read/annotate only; never diagnosis; `may_explain` is the strongest causal edge; non-diagnostic and source-linked.

## 2. System placement

The `pattern` pill sits at Connect → Investigate: surfacing patterns across the user's own graph for their understanding, never asserting cause. See `docs/system-design/intelligence_engines.md`.

## 3. Component dossier

- **C4 Processing** — derives facts/signals and quality/confidence.
- **C6 Knowledge Graph** — typed nodes, evidence-weighted edges; `F-ENGINES` is a read/annotate consumer that never asserts diagnosis.
- **C8 Six Memories** — Pattern memory among them.
Blast radius: spans three core components; cross-cutting; diagnosis-implication risk.

## 4. Current state (what exists vs. what is missing)

- Existing: C6 graph schema (WEL-98, WEL-135 Done); `docs/system-design/intelligence_engines.md`. UI stub at `apps/web/app/(workspace)/patterns/page.tsx` (ComingSoon).
- Missing: precedence semantics, co-occurrence/pattern definition, and confidence scoring/surfacing.

## 5. The decision question(s)

1. How is temporal precedence between two co-occurring events determined: timestamp order, user-reported order, or a confidence-weighted combination?
2. What counts as a co-occurrence/pattern worth surfacing?
3. How is confidence scored and surfaced, read/annotate only (never diagnosis)?

## 6. Stakes

Wrong precedence/confidence semantics risk implying causation/diagnosis — a do-not-diagnose violation and a trust/safety breach.

## 7. Unblocks

WEL-79 (intelligence engines) and the pattern view (Track E). Relates WEL-37, WEL-58.

## 8. Prior art

WEL-98, WEL-135 (graph schema, Done); `docs/system-design/intelligence_engines.md`; `docs/system-design/knowledge_graph.md`.

## 9. Where to look (research directions, NOT answers)

Temporal-precedence and Granger-style ordering caveats; co-occurrence vs. causation safeguards; confidence/uncertainty representation for non-diagnostic pattern surfacing; confounder handling. No proposed answer.
