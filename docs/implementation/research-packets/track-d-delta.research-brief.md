# Research Brief — Track D: Delta semantics for a "What Changed?" health view

> **How to use this file:** copy everything below the line into your research tool
> (ChatGPT/Gemini/Claude/Perplexity, web search on). It is fully self-contained — no
> access to our codebase is required. Paste the result back and it will be recorded
> verbatim into the decision record `docs/decisions/delta-semantics-window.md` (Spike WEL-163).

---

## YOUR TASK (read first)

You are a research assistant producing a **DECISION-NEUTRAL research brief** for a software design decision. Everything below is context. Your job is to **actually perform research** (use web search to find real, citable sources) and **return findings — not to restate this packet, not to describe how you would research, and not to ask whether to proceed.**

Produce a brief with these sections, grounded only in sources you actually consulted:

1. **External patterns to examine** — established patterns/standards relevant to each decision question.
2. **Evidence inventory** — a table of concrete sources (name, URL, what it covers, jurisdiction/context if relevant, limitations).
3. **Decision-neutral findings** — what the sources say, mapped to the decision questions and the affected components. Factual only.
4. **Tradeoffs and open questions** — the unresolved choices the maintainers must make, and the risks of each direction.

**HARD CONSTRAINT:** do **not** propose, recommend, or choose a final answer/architecture/policy for any decision question. Present the option space and the evidence; the human decides. Honor the product's identity guardrails (personal-first, user-controlled, source-linked, non-diagnostic, calm/never-alarm). Cite sources inline.

**OUTPUT FORMAT — deliver as a downloadable file:** write the complete brief to a **downloadable Markdown (`.md`) file** named **`track-d-delta-research-result.md`** and give me a download link/button. Do not put the brief only in the chat body — I need the file to download. Use the four section headings above as `##` Markdown headings, and keep all source citations as inline Markdown links.

---

## PRODUCT CONTEXT — what WellBe is

WellBe is a **Patient-Centered Health Investigation OS**. Its core is a **Personal Shared Health Memory OS**: a user-controlled memory layer that helps an individual carry their health context forward until each concern is resolved, explained, monitored, or safely handed off. **The individual is always the data controller.** It is **not** a diagnosis engine, not an EHR, not a medical authority.

**Operating loop:** Capture → Connect → Investigate → Clarify → Close → Correct.

**Non-negotiable design principles relevant here:**
- **Source-linked** — every derived claim traces back to a source; no orphan outputs.
- **Investigate, never diagnose** — the platform asks better questions; it never gives final medical answers.
- **Calm / never-alarm** — outputs must not manufacture alarm; any urgency is calibrated and always paired with a next step.
- **Personal-first** — every feature must serve the individual's own understanding and agency.

**Core object — Health Thread:** a living container for one unresolved/ongoing concern. It holds the patient's own words, timeline and baseline change, symptom episodes, related visits/contacts, test results (including normal-result context), referrals and their status, pending items, open questions, corrections, and source-linked evidence.

## THE FEATURE — the "What Changed?" (delta) view

A surface (a "What changed?" pill on the Home screen) that shows the user **what has changed in their health context** across time and across sources — "what changed from my normal" — calmly and without alarm. It sits at the **Connect → Clarify** steps of the loop. Today it is an unbuilt placeholder; this research informs how it should compute and present change.

## ARCHITECTURE CONTEXT — the components this touches

WellBe has a layered architecture. The delta view is a **read consumer** over two core components:

- **C9 — Continuity & Closure Engine.** Owns the *pending item ledger*, referral lifecycle, *result tracker*, post-visit plan checker, and the repeat-visit/longitudinal view. It is the part of the system that tracks open loops until they are resolved, explained, monitored, or handed off. (Depends on the Health Thread Engine and the Six Memories store.)
- **C4 — Processing Pipeline.** Extracts entities, facts, and signals from raw inputs and computes quality/confidence scores. With baselines, it is where value deltas (e.g. a lab value vs. a prior baseline) would be computed.

**Already exists in the system:**
- A continuity ledger API (`/v2/pending-items`) and a threads API (`/v1/threads`).
- A spec for a Home "What Changed" region.

**Missing (what this decision must define):**
- The **delta computation semantics** (what change is detected and how).
- The **comparison-window rule** (what timeframe is compared).
- The **ordering/ranking contract** (how changes are presented).

## THE DECISION QUESTIONS

1. **What counts as a meaningful change?** Consider: new facts, status transitions (e.g. pending → resolved), and value deltas vs. a baseline/normal range. What distinguishes a *meaningful* change from noise in a longitudinal personal health record?
2. **What comparison window is used, and how is it chosen?** Options seen in the wild include a fixed rolling window, "since last clinical visit," "since the user last opened the view," or event-anchored windows. What are the established patterns and their tradeoffs?
3. **How are deltas ordered/ranked for the user** — in a way that is calm, non-alarming, and source-linked? How do change-digest / "what's new" systems prioritize salience without creating anxiety?

## STAKES

Wrong delta semantics either **hide a real change** (a continuity failure — exactly the harm WellBe exists to prevent) or **manufacture noise/alarm** (violating the calm/never-alarm principle). The view must respect non-diagnostic and source-linked constraints.

## WHERE TO LOOK (research directions, not answers)

- Change-detection / diff semantics for longitudinal health records and patient timelines.
- Baseline / "normal range" modeling and what counts as a clinically or personally meaningful change vs. measurement noise (e.g. minimal clinically important difference, reference-change value concepts).
- Salience / ranking approaches for "what's new" or digest feeds that deliberately avoid alarm.
- Time-window selection strategies for "what changed since…" digests (fixed vs. event-anchored vs. last-seen).
- Calm-technology / non-alarming notification design patterns in health and consumer software.

Remember: **return findings with citations; do not recommend a final answer.**
