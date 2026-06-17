# Research Brief — Track C: Deterioration check-in and safe-escalation rules behind the safety gate

> **How to use this file:** copy everything below the line into your research tool
> (ChatGPT/Gemini/Claude/Perplexity, web search on). It is fully self-contained — no
> access to our codebase is required. Paste the result back and it will be recorded
> verbatim into the decision record `docs/decisions/triage-escalation-safety-rules.md` (Spike WEL-162).
>
> Note: this concerns a **safety-critical** surface. Keep the brief decision-neutral and source-cited.

---

## YOUR TASK (read first)

You are a research assistant producing a **DECISION-NEUTRAL research brief** for a software design decision. Everything below is context. Your job is to **actually perform research** (use web search to find real, citable sources) and **return findings — not to restate this packet, not to describe how you would research, and not to ask whether to proceed.**

Produce a brief with these sections, grounded only in sources you actually consulted:

1. **External patterns to examine** — established patterns/standards/frameworks relevant to each decision question.
2. **Evidence inventory** — a table of concrete sources (name, URL, what it covers, jurisdiction/context if relevant, limitations).
3. **Decision-neutral findings** — what the sources say, mapped to the decision questions and the affected components. Factual only.
4. **Tradeoffs and open questions** — the unresolved choices the maintainers must make, and the risks of each direction.

**HARD CONSTRAINT:** do **not** propose, recommend, or choose a final answer/policy for any decision question. Present the option space and the evidence; the human decides. Honor the product's identity guardrails (personal-first, user-controlled, source-linked, **non-diagnostic**, **calm/never-alarm**; the system empowers the user within the clinical system and never replaces clinical judgment). Cite sources inline.

**OUTPUT FORMAT — deliver as a downloadable file:** write the complete brief to a **downloadable Markdown (`.md`) file** named **`track-c-triage-research-result.md`** and give me a download link/button. Do not put the brief only in the chat body — I need the file to download. Use the four section headings above as `##` Markdown headings, and keep all source citations as inline Markdown links.

---

## PRODUCT CONTEXT — what WellBe is

WellBe is a **Patient-Centered Health Investigation OS**. Its core is a **Personal Shared Health Memory OS**: a user-controlled memory layer for an individual's health context. **The individual is always the data controller.** It is **not** a diagnosis engine, **not** an EHR, **not** a medical authority, and **not** a replacement for clinical judgment.

**Operating loop:** Capture → Connect → Investigate → Clarify → Close → Correct.

**Non-negotiable design principles relevant here:**
- **Investigate, never diagnose** — the platform helps the user understand and act; it never names a condition, gives a probability of disease, or prescribes treatment.
- **Calm / never-alarm** — no alarm without a calibrated next step; tone must avoid catastrophizing.
- **Safety gate before every AI output** — a mandatory safety engine evaluates every user-facing AI output; no bypass.
- **Empower within the system** — the goal is to help the user act within the existing clinical/emergency system, not to replace it.

## THE FEATURE — the "Something feels off" check-in

A user-initiated check-in (a "Something feels off" pill on the Home screen) where a person describes how they feel and WellBe responds with **steady, non-diagnostic guidance on what to watch for and when/where to reach out** — never an alarm, never a diagnosis, always the user's decision. It spans **Capture → Clarify** and must route safely without diagnosing. Today it is an unbuilt placeholder; this research informs the question model, escalation criteria, never-alarm language rules, and response routing.

## ARCHITECTURE CONTEXT — the component this touches

- **C10 — Safety & Governance Gate.** The mandatory gate before any user-facing AI output: **do-not-diagnose enforcement, panic/never-alarm language controls, provenance, and bias controls.** This is the single hardest architectural rule in WellBe — every word the check-in emits passes through it. This is the most consequential surface in the build-out.

**Already exists in the system:** a safety-gate service and the product's safety rules. The check-in UI is an unbuilt placeholder.

**Missing (what this decision must define):**
- The **check-in question model** (what is asked).
- The **escalation tier criteria** (what maps a check-in to which tier).
- The **never-alarm language rules** (tone/phrasing constraints).
- The **response-routing contract** (self-care vs. seek care vs. emergency), all non-diagnostic and source-aware.

## THE DECISION QUESTIONS

1. **Do-not-diagnose boundaries** — what may and may not the check-in say? Where is the line between non-diagnostic triage/guidance and a diagnostic or treatment claim (including the regulatory boundary for consumer health software)?
2. **Never-alarm language constraints** — what tone/phrasing rules should govern any escalation message so it is calm, clear, action-oriented, and honest about uncertainty without catastrophizing?
3. **Escalation criteria + tiers** — what criteria map a check-in to an escalation tier, and what are the tiers? What validated red-flag / warning-sign frameworks exist?
4. **Response routing** — how should the system route between self-care guidance, "contact a clinician / seek care," and "emergency now" — non-diagnostically and source-aware, including handling of special populations and mental-health crisis?

## STAKES

A wrong escalation or never-alarm rule is a **direct safety risk** to the user — under-escalating a real emergency, or alarming the user without cause. The potential harm is irreversible, which is why this surface is treated as the most safety-critical in the product.

## WHERE TO LOOK (research directions, not answers)

- **Validated symptom-triage / self-triage frameworks** and digital triage services that explicitly **do not diagnose** (e.g. national health-line triage models) and their disposition/outcome taxonomies.
- **Red-flag / warning-sign** lists for urgent escalation from authoritative public-health/clinical sources (general adult, plus special populations such as pregnancy/postpartum, pediatric, stroke, mental-health crisis).
- **Crisis-safe / never-alarm communication** guidance (e.g. crisis & emergency risk communication principles, plain-language health communication).
- **Do-not-diagnose / regulatory boundary** for consumer health and clinical-decision-support software (what makes software "device" vs. non-device; intended-use framing).
- **Safe-routing taxonomies** (self-care / seek-care / emergency) and the evidence on **under-triage vs. over-triage** harms of symptom checkers.

Remember: **return findings with citations; do not recommend a final answer.**
