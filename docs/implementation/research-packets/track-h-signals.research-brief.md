# Research Brief — Track H: Home "signals" summary / health-adaptive UI — live health-status computation and never-alarm framing

> **How to use this file:** copy everything below the line into your research tool
> (ChatGPT/Gemini/Claude/Perplexity, web search on). It is fully self-contained — no
> access to our codebase is required. Paste the result back and it will be recorded
> verbatim into the decision record `docs/decisions/signals-summary-semantics.md` (Spike WEL-167).

---

## YOUR TASK (read first)

You are a research assistant producing a **DECISION-NEUTRAL research brief** for a software design decision. Everything below is context. Your job is to **actually perform research** (use web search to find real, citable sources) and **return findings — not to restate this packet, not to describe how you would research, and not to ask whether to proceed.**

Produce a brief with these sections, grounded only in sources you actually consulted:

1. **External patterns to examine** — established patterns/standards relevant to each decision question.
2. **Evidence inventory** — a table of concrete sources (name, URL, what it covers, context, limitations).
3. **Decision-neutral findings** — what the sources say, mapped to the decision questions and the affected components. Factual only.
4. **Tradeoffs and open questions** — the unresolved choices the maintainers must make, and the risks of each direction.

**HARD CONSTRAINT:** do **not** propose, recommend, or choose a final answer/policy for any decision question. Present the option space and the evidence; the human decides. Honor the product's identity guardrails (personal-first, user-controlled, source-linked, non-diagnostic, **calm/never-alarm**). Cite sources inline.

**OUTPUT FORMAT — deliver as a downloadable file:** write the complete brief to a **downloadable Markdown (`.md`) file** named **`track-h-signals-research-result.md`** and give me a download link/button. Do not put the brief only in the chat body — I need the file to download. Use the four section headings above as `##` Markdown headings, and keep all source citations as inline Markdown links.

---

## PRODUCT CONTEXT — what WellBe is

WellBe is a **Patient-Centered Health Investigation OS**. Its core is a **Personal Shared Health Memory OS**: a user-controlled memory layer for an individual's health context. **The individual is always the data controller.** It is **not** a diagnosis engine or medical authority.

**Non-negotiable design principles relevant here:**
- **Calm / never-alarm** — outputs must not manufacture alarm; any urgency is calibrated and paired with a next step.
- **Source-linked** — every derived claim traces back to a source.
- **Investigate, never diagnose** — the platform never asserts a diagnosis or a final medical judgment.
- **Personal-first** — the summary must serve the individual's own understanding.

## THE FEATURE — the Home "signals" summary (health-adaptive UI)

On the Home screen there is an at-a-glance status line — e.g. **"Your signals look steady · 6 of 6 systems in range"** — with a breakdown across systems (cardiovascular, metabolic, sleep, activity, inflammation, vitals). **Today this is hard-coded mock data.** This research informs how a **live** version should be computed and, critically, **framed** so it neither falsely reassures nor alarms. This is part of WellBe's "health-adaptive UI," which carries an explicit never-alarm rule.

## ARCHITECTURE CONTEXT — the components this touches

- **C4 — Processing Pipeline.** Extracts facts/signals from raw inputs and computes quality/confidence scores. Deriving "in range / steady" per system and an aggregate "N of N systems in range" is C4 work.
- **C10 — Safety & Governance Gate.** A user-facing aggregate **health-status judgment** ("your signals look steady") is exactly the kind of output the never-alarm rule and safety gate govern.

**Already exists in the system:** the UI renders the status line from a static mock constant; a processing pipeline and a safety-gate service exist.

**Missing (what this decision must define):** how status per system is derived, how the aggregate line is framed under never-alarm, how confidence/uncertainty is surfaced, and what is shown when data is missing or stale.

## THE DECISION QUESTIONS

1. **Signal computation:** which signals/systems should be summarized, and how is per-system status ("in range / steady / needs attention") derived from underlying data (reference ranges, personal baselines, trend vs. point value)?
2. **Never-alarm framing:** how should an aggregate health-status line be phrased so it avoids **both false reassurance** ("all good") **and alarm**? What is known about the risks of reassuring/normalizing health displays?
3. **Confidence / uncertainty:** how should confidence in each signal and in the aggregate be surfaced honestly to a layperson?
4. **Missing / stale data:** what should be shown when inputs are absent or out of date (so "6 of 6 in range" doesn't imply coverage that isn't there)?

## STAKES

A live aggregate health-status summary is a **derived health judgment**. Wrong framing risks **false reassurance** (a user ignores a real problem because the dashboard says "steady") or **alarm** (a normal fluctuation reads as a warning). Both undermine trust and safety.

## WHERE TO LOOK (research directions, not answers)

- **Reference ranges vs. personal baselines** and what constitutes a meaningful deviation (reference-change value, minimal clinically important difference, point-vs-trend).
- **Risk-communication / never-alarm** design: how health dashboards present "normal/steady" without false reassurance, and how they flag abnormality without panic.
- **Consumer-health-dashboard and wearable "health status" framing** patterns (e.g. how trackers summarize readiness/status), and documented risks of over-reassurance or over-alerting.
- **Uncertainty / confidence visualization** for laypeople, and **missing-data display** patterns (how to show "not enough data" honestly).

Remember: **return findings with citations; do not recommend a final answer.**
