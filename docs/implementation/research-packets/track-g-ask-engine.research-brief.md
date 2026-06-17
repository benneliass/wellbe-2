# Research Brief — Track G: "Ask WellBe" answer engine — grounding, safety gating, provenance, and non-diagnostic Q&A

> **How to use this file:** copy everything below the line into your research tool
> (ChatGPT/Gemini/Claude/Perplexity, web search on). It is fully self-contained — no
> access to our codebase is required. Paste the result back and it will be recorded
> verbatim into the decision record `docs/decisions/ask-answer-engine-semantics.md` (Spike WEL-168).
>
> Note: this concerns a **safety-critical** AI-output surface. Keep the brief decision-neutral and source-cited.

---

## YOUR TASK (read first)

You are a research assistant producing a **DECISION-NEUTRAL research brief** for a software design decision. Everything below is context. Your job is to **actually perform research** (use web search to find real, citable sources) and **return findings — not to restate this packet, not to describe how you would research, and not to ask whether to proceed.**

Produce a brief with these sections, grounded only in sources you actually consulted:

1. **External patterns to examine** — established patterns/standards relevant to each decision question.
2. **Evidence inventory** — a table of concrete sources (name, URL, what it covers, context, limitations).
3. **Decision-neutral findings** — what the sources say, mapped to the decision questions and the affected components. Factual only.
4. **Tradeoffs and open questions** — the unresolved choices the maintainers must make, and the risks of each direction.

**HARD CONSTRAINT:** do **not** propose, recommend, or choose a final answer/architecture/policy for any decision question. Present the option space and the evidence; the human decides. Honor the product's identity guardrails (personal-first, user-controlled, source-linked, **non-diagnostic**, calm/never-alarm). Cite sources inline.

**OUTPUT FORMAT — deliver as a downloadable file:** write the complete brief to a **downloadable Markdown (`.md`) file** named **`track-g-ask-engine-research-result.md`** and give me a download link/button. Do not put the brief only in the chat body — I need the file to download. Use the four section headings above as `##` Markdown headings, and keep all source citations as inline Markdown links.

---

## PRODUCT CONTEXT — what WellBe is

WellBe is a **Patient-Centered Health Investigation OS**. Its core is a **Personal Shared Health Memory OS**: a user-controlled memory layer for an individual's health context. **The individual is always the data controller.** It is **not** a diagnosis engine, **not** an EHR, **not** a medical authority, and **not** a replacement for clinical judgment.

**Operating loop:** Capture → Connect → Investigate → Clarify → Close → Correct.

**Non-negotiable design principles relevant here:**
- **Source-linked** — every derived claim traces back to a source; no orphan outputs.
- **Investigate, never diagnose** — the platform asks better questions and surfaces evidence; it never gives final medical answers, names conditions, or prescribes treatment.
- **Safety gate before every AI output** — a mandatory safety engine evaluates every user-facing AI output; no bypass.
- **Calm / never-alarm** — no alarm without a calibrated next step.
- **Personal-first** — answers must serve the individual's own understanding and agency.

## THE FEATURE — "Ask WellBe"

A free-text entry point on the Home screen ("Ask WellBe …") where the user types a question about their own health. The entry point UI is **already built and shipped** (it routes the query to an `/ask` view). This research is about the **answer engine** behind it: how a free-text question should be answered **safely, grounded in the user's own data, source-linked, and non-diagnostic**.

## ARCHITECTURE CONTEXT — the components this touches

An answer is user-facing AI output, so it must pass the safety gate and ground itself in the user's own data:

- **C10 — Safety & Governance Gate (mandatory).** Every user-facing AI output passes through it: do-not-diagnose, panic/never-alarm language, provenance, bias controls. No bypass.
- **C7 — Health Thread Engine.** The user's threads (one per unresolved/ongoing concern) are the primary grounding corpus.
- **C6 — Knowledge Graph Store.** Typed nodes + evidence-weighted edges across the user's threads/time/sources; the strongest causal edge is the hedged `may_explain`.
- **C5 — Evidence & Provenance Service.** Enforces "no orphan claims" — every statement must trace to a source.
- **C14 — Investigation Engine** (likely) — the structured research process over a thread; an "Ask" may open or draw on an investigation.

**Already exists in the system:** the Ask entry point (frontend), a safety-gate service, threads/graph stores, and a provenance service.

**Missing (what this decision must define):** the answer engine's grounding scope, the C10 gating contract for generated answers, the provenance/citation contract, and out-of-scope/uncertain-question handling.

## THE DECISION QUESTIONS

1. **Grounding scope:** what may an answer draw on — the user's own threads/graph only (closed-corpus, source-linked), or also general medical knowledge? How should retrieval-augmented generation (RAG) over personal health data be scoped, and how is non-grounded/hallucinated content prevented?
2. **Safety gating (C10):** how do generated answers enforce do-not-diagnose, never-alarm, provenance, and bias control? What patterns exist for guardrailing health LLM output?
3. **Provenance / citation contract:** how should each answer cite the user's own sources so there are no orphan claims? What citation/attribution patterns work for grounded answers?
4. **Out-of-scope / uncertain handling:** when should the engine refuse, hedge, or redirect (e.g. to the triage check-in or a clinician)? What are established refusal/escalation patterns for consumer health assistants?

## STAKES

An answer is the most open-ended AI output in the product. Without strict grounding + C10 gating it can hallucinate, imply a diagnosis, alarm the user, or make an unsourced claim — each a direct safety/trust violation. The entry point is already live, which raises the urgency.

## WHERE TO LOOK (research directions, not answers)

- **Retrieval-augmented generation (RAG)** grounding patterns and hallucination-mitigation for closed-corpus question answering, especially over personal/health data.
- **LLM safety guardrails** for health/medical chatbots: do-not-diagnose constraints, medical-disclaimer and scope-limiting patterns, regulatory boundaries for consumer health Q&A.
- **Citation / attribution / provenance** patterns for grounded answers (inline source linking, answer-with-citations evaluation).
- **Refusal, hedging, and escalation** patterns for consumer health assistants (when to decline, when to route to triage/emergency/clinician).
- Evidence on **LLM medical-advice risks** (hallucination, over-confidence, bias) and mitigations.

Remember: **return findings with citations; do not recommend a final answer.**
