# Research Brief — Track E: Non-diagnostic pattern-detection semantics over a personal health graph

> **How to use this file:** copy everything below the line into your research tool
> (ChatGPT/Gemini/Claude/Perplexity, web search on). It is fully self-contained — no
> access to our codebase is required. Paste the result back and it will be recorded
> verbatim into the decision record `docs/decisions/pattern-detection-semantics.md` (Spike WEL-164).

---

## YOUR TASK (read first)

You are a research assistant producing a **DECISION-NEUTRAL research brief** for a software design decision. Everything below is context. Your job is to **actually perform research** (use web search to find real, citable sources) and **return findings — not to restate this packet, not to describe how you would research, and not to ask whether to proceed.**

Produce a brief with these sections, grounded only in sources you actually consulted:

1. **External patterns to examine** — established patterns/standards/methods relevant to each decision question.
2. **Evidence inventory** — a table of concrete sources (name, URL, what it covers, context, limitations).
3. **Decision-neutral findings** — what the sources say, mapped to the decision questions and the affected components. Factual only.
4. **Tradeoffs and open questions** — the unresolved choices the maintainers must make, and the risks of each direction.

**HARD CONSTRAINT:** do **not** propose, recommend, or choose a final answer/architecture/policy for any decision question. Present the option space and the evidence; the human decides. Honor the product's identity guardrails (personal-first, user-controlled, source-linked, **non-diagnostic**, calm/never-alarm). Cite sources inline.

---

## PRODUCT CONTEXT — what WellBe is

WellBe is a **Patient-Centered Health Investigation OS**. Its core is a **Personal Shared Health Memory OS**: a user-controlled memory layer that helps an individual carry their health context forward. **The individual is always the data controller.** It is **not** a diagnosis engine, not an EHR, not a medical authority, and **not a replacement for clinical judgment.**

**Operating loop:** Capture → Connect → Investigate → Clarify → Close → Correct.

**Non-negotiable design principles relevant here:**
- **Investigate, never diagnose** — the platform surfaces patterns and asks better questions; it never asserts cause or a diagnosis.
- **Source-linked** — every derived claim traces back to a source.
- A **Theory** in WellBe is a user/clinician-proposed explanation evaluated against evidence — *never* a diagnosis, a ranked differential, or a disease claim; it carries evidence-for, evidence-against, missing-data, and a safety level.

**Critical product rule for this feature:** pattern surfacing is **read/annotate only**. The strongest causal relationship the system may ever express is a hedged **`may_explain`** edge. The system must never imply causation or diagnosis from correlation/co-occurrence.

## THE FEATURE — the "Check my patterns" view

A surface (a "Check my patterns" pill on the Home screen) that surfaces **patterns across the user's own health data** — for the user's understanding — without ever asserting cause. It sits at the **Connect → Investigate** steps. Today it is an unbuilt placeholder; this research informs the semantics of what a "pattern" is, how event order is determined, and how confidence is represented.

## ARCHITECTURE CONTEXT — the components this touches

The pattern view is a **read/annotate consumer** over three core components:

- **C4 — Processing Pipeline.** Extracts facts/signals from raw inputs and computes quality/confidence scores.
- **C6 — Knowledge Graph Store.** Typed nodes + **evidence-weighted edges** connecting entities across threads, time, and sources. (The graph schema is already designed and migrated; this decision is about *semantics over* it, not a schema change.) Read/annotate consumers of this graph **never assert diagnosis** — `may_explain` is the strongest causal edge.
- **C8 — Six Memories Store.** Story, Clinical, **Pattern**, Decision, Responsibility, and Equity/Access memories around each thread. "Pattern memory" is one of the six.

This feature is part of an **Intelligence Engine Suite** (Pattern, Temporal, Confounder, Missing-Data, Contradiction engines) that reads the graph and annotates it — but never diagnoses.

**Already exists in the system:** the C6 graph schema (typed nodes + evidence-weighted edges), and design docs for the intelligence engines.

**Missing (what this decision must define):**
- **Temporal-precedence semantics** (how event order is decided).
- **Co-occurrence / pattern definition** (what is worth surfacing).
- **Confidence scoring and surfacing** (read/annotate only, never diagnosis).

## THE DECISION QUESTIONS

1. **Temporal precedence:** how should the order between two co-occurring events be determined — by recorded timestamp order, by user-reported order ("this started before that"), or a confidence-weighted combination? What are the established methods and their failure modes (e.g. timestamp unreliability, recall bias)?
2. **Co-occurrence / pattern definition:** what counts as a pattern worth surfacing to a user (vs. coincidence/noise)? How do analytics and epidemiology distinguish a meaningful co-occurrence from a spurious one, in a *single-subject* (n-of-1) context?
3. **Confidence:** how should confidence/uncertainty be **scored and surfaced** for a non-diagnostic pattern, so it informs without implying causation or diagnosis? What representations communicate uncertainty honestly to a layperson?

## STAKES

Wrong precedence or confidence semantics risk **implying causation/diagnosis** — a do-not-diagnose violation and a direct trust/safety breach. Co-occurrence presented carelessly reads as a causal claim.

## WHERE TO LOOK (research directions, not answers)

- Temporal-precedence reasoning and its caveats (e.g. Granger-causality limitations, "temporal precedence ≠ causation," timestamp vs. self-reported onset reliability).
- Correlation-vs-causation safeguards; confounding; how observational/co-occurrence findings are framed responsibly.
- n-of-1 / single-subject analytics: detecting personal patterns from one individual's longitudinal data.
- Uncertainty / confidence communication to non-experts (verbal vs. numeric probability, confidence intervals, "evidence strength" framing) and how health UIs avoid implying diagnosis.
- Confounder and missing-data handling when surfacing personal patterns.

Remember: **return findings with citations; do not recommend a final answer.**
