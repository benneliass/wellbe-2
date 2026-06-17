# Research Brief — Track F: Thread-scoped graph read/query API contract for a visualization client

> **How to use this file:** copy everything below the line into your research tool
> (ChatGPT/Gemini/Claude/Perplexity, web search on). It is fully self-contained — no
> access to our codebase is required. Paste the result back and it will be recorded
> verbatim into the decision record `docs/decisions/graph-query-api-contract.md` (Spike WEL-165).

---

## YOUR TASK (read first)

You are a research assistant producing a **DECISION-NEUTRAL research brief** for a software design decision. Everything below is context. Your job is to **actually perform research** (use web search to find real, citable sources) and **return findings — not to restate this packet, not to describe how you would research, and not to ask whether to proceed.**

Produce a brief with these sections, grounded only in sources you actually consulted:

1. **External patterns to examine** — established API/query/response patterns relevant to each decision question.
2. **Evidence inventory** — a table of concrete sources (name, URL, what it covers, context, limitations).
3. **Decision-neutral findings** — what the sources say, mapped to the decision questions and the affected components. Factual only.
4. **Tradeoffs and open questions** — the unresolved choices the maintainers must make, and the risks of each direction.

**HARD CONSTRAINT:** do **not** propose, recommend, or choose a final answer/architecture/contract for any decision question. Present the option space and the evidence; the human decides. Honor the product's identity guardrails (personal-first, user-controlled, source-linked, non-diagnostic; **strict per-thread/user scoping — no unscoped data exposure**). Cite sources inline.

---

## PRODUCT CONTEXT — what WellBe is

WellBe is a **Patient-Centered Health Investigation OS**. Its core is a **Personal Shared Health Memory OS**: a user-controlled memory layer for an individual's health context. **The individual is always the data controller**; any non-individual access is grant-based, scoped, time-boxed, purpose-bound, and revocable. It is **not** a diagnosis engine or EHR.

**Non-negotiable principles relevant here:**
- **Personal-first & strictly scoped** — a per-thread graph read must expose only that thread's (and that user's) data. No leakage of unscoped graph data.
- **Source-linked** — graph edges are evidence-weighted; provenance must survive into the response.
- **Non-diagnostic** — `may_explain` is the strongest causal edge type the graph expresses.

## THE FEATURE — the "Open the graph" view

A surface (an "Open the graph" pill on the Home screen) that lets the user **read and visualize their own knowledge graph**, scoped to a single Health Thread. It is a read/visualize surface at the Connect/Investigate steps. The target visualization is a **thread-scoped node-link graph** (planned with Cytoscape for the thread view, and a Sigma-based "investigation landscape" for larger exploration). Today it is an unbuilt placeholder; this research informs the **read/query API contract** that feeds the visualization client.

**Important scope note:** the underlying graph **schema is already decided and migrated** (typed nodes + evidence-weighted edges). This decision is **only about the read/query contract** — how a client asks for a thread-scoped subgraph and what shape it gets back. It is **not** a schema change.

## ARCHITECTURE CONTEXT — the components this touches

- **C6 — Knowledge Graph Store** (as a **read consumer**). Typed nodes + evidence-weighted edges connecting entities across threads, time, and sources. The strongest causal edge is `may_explain`. This decision does not change the schema; it defines how to *read* a thread-scoped slice.
- **C13 — API & Contract Layer.** The single REST/OpenAPI contract boundary that every surface and feature calls. A new **graph-query/read endpoint** is needed here, with versioning discipline so the contract can evolve without breaking viz clients.

**Already exists in the system:**
- The C6 graph schema, decided and migrated (a DB migration for the graph schema exists).
- Established REST/OpenAPI patterns in the backend API layer.
- A target of a Cytoscape thread view / Sigma investigation landscape for the visualization.

**Missing (what this decision must define):**
- The **query shape** a client sends.
- The **response contract** a visualization client consumes.
- The **viz scoping rules** that keep unscoped data out.

## THE DECISION QUESTIONS

1. **Query shape:** how should a thread-scoped query select nodes/edges? Consider traversal depth limits, edge-type filters, node-type filters, and pagination for a per-thread subgraph. What are the established patterns for scoped graph reads over a REST/HTTP boundary?
2. **Response contract (C13):** what response shape should a visualization client consume, and how should it be versioned so it can evolve without breaking clients? Consider node-link JSON formats, how provenance/evidence-weight metadata travels, and graph-payload versioning.
3. **Viz scoping:** what subset renders for a thread view, and how is unscoped data structurally kept out of the response (authorization + query scoping)? What patterns prevent over-fetching or leaking out-of-scope nodes/edges?

## STAKES

A wrong query contract either **leaks unscoped graph data** (a privacy violation — the individual's strict scoping guarantee) or **forces a breaking C13 change** once visualization clients depend on it. Getting the versioning and scoping right early is the point of this spike.

## WHERE TO LOOK (research directions, not answers)

- Graph read/query API patterns over HTTP/REST: scoped traversal, depth/hop limits, edge/node-type filtering, pagination of subgraphs (and how GraphQL or REST handle this).
- Response/serialization formats for node-link graph visualization clients (e.g. Cytoscape.js JSON, Sigma/graphology, JSON Graph Format) and how metadata (weights, provenance) is carried.
- API/contract versioning strategies specifically for evolving graph payloads without breaking consumers.
- Authorization/scoping patterns for per-tenant or per-record graph reads (preventing out-of-scope traversal and over-fetching); object-/row-level scoping for graph data.

Remember: **return findings with citations; do not recommend a final answer.**
