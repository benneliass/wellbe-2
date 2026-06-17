# Research Context Packet — Track F / graph-query-api-contract

> This packet is BOTH the user's review artifact AND the prompt sent to the research
> runner. Never propose an answer to the decision question. See `.cursor/rules/research-protocol.mdc`.

**Spike:** WEL-165
**Blocks:** WEL-156 Graph query/read API endpoint for thread-scoped graph view
**Decision Record:** `docs/decisions/graph-query-api-contract.md`
**Core component(s) touched:** Knowledge Graph (C6, read), API & Contract Layer (C13)
**Date assembled:** 2026-06-17

---

## 1. Identity and guardrails (non-negotiables)

`docs/system-design/platform_identity.md`, `.cursor/rules/wellbe-vision-guardrails.mdc`, `.cursor/rules/audience-guardrails.mdc`. Personal-first; thread/user-scoped (no unscoped data exposure); source-linked; non-diagnostic (`may_explain` strongest edge).

## 2. System placement

The `graph` pill is a read/visualize surface over the user's own knowledge graph (Connect/Investigate). See `docs/system-design/knowledge_graph.md`.

## 3. Component dossier

- **C6 Knowledge Graph** — typed nodes + evidence-weighted edges; this is a read consumer, not a schema change.
- **C13 API & Contract Layer** — the single contract boundary; needs a new graph-query endpoint with versioning discipline.
Blast radius: component-local; the main risk is a query/response contract that is hard to evolve or leaks scope.

## 4. Current state (what exists vs. what is missing)

- Existing: C6 schema decided and migrated (WEL-98, WEL-135 Done); migration `db/migrations/versions/006_c6_graph_schema.py`. UI stub at `apps/web/app/(workspace)/graph/page.tsx` (ComingSoon). WEL-78 targets Cytoscape thread view / Sigma investigation landscape.
- Missing: the read/query API contract, response shape for a viz client, and viz scoping rules.

## 5. The decision question(s)

1. What is the query shape (thread-scoped node/edge selection, traversal depth, edge-type filters)?
2. What is the C13 response contract a viz client consumes (and how versioned)?
3. What is the viz scoping (what subset renders; how is unscoped data kept out)?

## 6. Stakes

A wrong query contract leaks unscoped graph data (privacy) or forces a breaking C13 change once viz clients depend on it.

## 7. Unblocks

WEL-156 (graph query/read API) and WEL-78 (graph visualization) (Track F).

## 8. Prior art

WEL-98, WEL-135 (graph schema, Done); `docs/system-design/knowledge_graph.md`; existing C13 patterns in `backend/apps/api/`.

## 9. Where to look (research directions, NOT answers)

Graph read/query API patterns (scoped traversal, depth limits, edge filtering); response contracts for Cytoscape/Sigma viz; API versioning for graph payloads; scoping/authorization patterns for per-thread graph reads. No proposed answer.
