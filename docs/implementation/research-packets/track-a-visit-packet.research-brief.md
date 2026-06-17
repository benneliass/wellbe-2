# Research Brief — Track A: User-controlled clinician "Visit Packet" — composition, source-linking, scoped share/revocation, and safety gating

> **How to use this file:** copy everything below the line into your research tool
> (ChatGPT/Gemini/Claude/Perplexity, web search on). It is fully self-contained — no
> access to our codebase is required. Paste the result back and it will be recorded
> verbatim into the decision record `docs/decisions/visit-packet-composition-gating.md` (Spike WEL-160).

---

## YOUR TASK (read first)

You are a research assistant producing a **DECISION-NEUTRAL research brief** for a software design decision. Everything below is context. Your job is to **actually perform research** (use web search to find real, citable sources) and **return findings — not to restate this packet, not to describe how you would research, and not to ask whether to proceed.**

Produce a brief with these sections, grounded only in sources you actually consulted:

1. **External patterns to examine** — established patterns/standards relevant to each decision question.
2. **Evidence inventory** — a table of concrete sources (name, URL, what it covers, jurisdiction/context if relevant, limitations).
3. **Decision-neutral findings** — what the sources say, mapped to the decision questions and the affected components. Factual only.
4. **Tradeoffs and open questions** — the unresolved choices the maintainers must make, and the risks of each direction.

**HARD CONSTRAINT:** do **not** propose, recommend, or choose a final answer/architecture/policy for any decision question. Present the option space and the evidence; the human decides. Honor the product's identity guardrails (personal-first, user-controlled sharing only, source-linked, non-diagnostic, calm/never-alarm, grant-scoped and revocable). Cite sources inline.

**OUTPUT FORMAT — deliver as a downloadable file:** write the complete brief to a **downloadable Markdown (`.md`) file** named **`track-a-visit-packet-research-result.md`** and give me a download link/button. Do not put the brief only in the chat body — I need the file to download. Use the four section headings above as `##` Markdown headings, and keep all source citations as inline Markdown links.

---

## PRODUCT CONTEXT — what WellBe is

WellBe is a **Patient-Centered Health Investigation OS**. Its core is a **Personal Shared Health Memory OS**: a user-controlled memory layer that helps an individual carry their health context forward until each concern is resolved, explained, monitored, or safely handed off. **The individual is always the data controller**; any non-individual access (e.g. a clinician) is grant-based, scoped, time-boxed, purpose-bound, and revocable. WellBe is **not** a diagnosis engine, **not** an EHR or clinician system-of-record, and **not** a replacement for clinical judgment.

**Operating loop:** Capture → Connect → Investigate → Clarify → Close → Correct.

**Non-negotiable design principles relevant here:**
- **Source-linked** — every derived claim traces back to a source; no orphan outputs.
- **User-controlled sharing** — sharing and clinician access are always user-initiated.
- **Investigate, never diagnose** — the platform asks better questions; it never gives final medical answers.
- **Safety gate before every AI output** — a mandatory safety engine evaluates every user-facing AI output; no bypass.
- **Personal-first** — the packet is a tool the user creates and chooses to share with a clinician; it is **not** a clinician EHR module.

**Core object — Health Thread:** a living container for one unresolved/ongoing concern, holding the patient's own words, timeline/baseline change, symptom episodes, visits/contacts, test results (incl. normal-result context), referrals and their status, pending items, open questions, corrections, and source-linked evidence.

## THE FEATURE — the "Visit Packet"

A user-assembled, **source-linked summary** that an individual creates from one or more of their Health Threads to **prepare for or follow up on a clinical encounter**, and can **share with a clinician under a scoped, revocable grant** (or export). It sits at the **Clarify → Close** step of the loop. Today it is an unbuilt placeholder; this research informs how the packet is composed, source-linked, safety-gated, and shared/revoked.

## ARCHITECTURE CONTEXT — the components this touches

The Visit Packet composes from threads and crosses the personal-core boundary when shared, so it touches four core components:

- **C7 — Health Thread Engine + State Machine.** The central product object: lifecycle, linking, and status for one unresolved concern. Packets are composed from one or more threads.
- **C5 — Evidence & Provenance Service.** Links every derived fact back to its raw source and enforces **"no orphan claims."** Every claim in a packet must trace to a source.
- **C10 — Safety & Governance Gate.** The mandatory gate before any user-facing AI output: do-not-diagnose, panic/never-alarm language, provenance, and bias controls. Generated packet text must pass it before it can be shared.
- **C1 — Trust & Consent Service.** Owns auth identity, **consent scopes, share grants, and the revocation log.** The root of trust for who can see a shared packet.

**Blast radius:** once a packet is shared/exported it leaves the user's control boundary, so the C1 (share/revoke) and C10 (safety) decisions are effectively **irreversible once shared**.

**Already exists in the system:** a threads API (`/v1/threads`, `/v1/threads/{id}`), a consent service, and a safety-gate service.

**Missing (what this decision must define):**
- A packet-**generate** endpoint and the packet **composition rules**.
- The **scoped share/export + revocation** model.
- The **C10 gating contract** for generated packet text.

## THE DECISION QUESTIONS

1. **Composition + source-linking:** what is included in a packet, and how is each claim source-linked so there are no orphan claims? What standards exist for patient-generated clinical summaries (structure, content, provenance/citation)?
2. **Scoped share/export + revocation:** what is the audience/purpose/duration grant model, and what exactly does "revoke" mean — does revoking invalidate copies already exported/downloaded by a third party? What are the established patterns and their honest limits (e.g. copy-recall semantics)?
3. **Safety gating:** how does the generated summary pass the safety gate (do-not-diagnose, never-alarm, provenance, bias) **before** it can be shared with a clinician?

## STAKES

A shared/exported packet leaves the user's control boundary. A wrong share-scope or revocation model is a **privacy regression**; a wrong safety gate is a **safety regression**. Both are expensive or impossible to reverse once a packet is in a third party's hands.

## WHERE TO LOOK (research directions, not answers)

- Clinical communication standards for **patient-generated summaries** and patient→clinician handoff documents (structure, what clinicians find useful, provenance expectations).
- **Consent / grant patterns** for revocable third-party data sharing: purpose limitation, time-boxing, scope, and the realistic semantics of revocation when a copy has already been exported.
- **Provenance / citation** patterns for source-linked summaries (how each statement carries its evidence).
- Safety patterns for **non-diagnostic** patient-to-clinician handoffs (avoiding diagnosis/alarm while still being clinically useful).

Remember: **return findings with citations; do not recommend a final answer.**
