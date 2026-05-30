# Architecture

Implementation architecture for WellBe — the **Personal Shared Health Memory OS**. This area translates the product/system design into a concrete component separation, technology stack, infrastructure, and development backlog.

It builds on, and cross-references, the design source of truth in `../system-design/`, `../safety/`, `../implementation/`, and `../feature-backlog/`. It does not restate the product vision — see `../system-design/system_design.md` and `../../.cursor/rules/wellbe-vision-guardrails.mdc`.

## Index

| Doc | What it covers |
|---|---|
| [component-map.md](component-map.md) | The canonical split of **CORE components** (the spine, `C1`–`C13`) vs **FEATURE components** (`F-*`), with purpose and dependencies for each, and the tier-boundary rule. |
| [tech-stack.md](tech-stack.md) | Chosen technology per concern (backend, workers, datastore, vector/graph/time-series, events, API, auth, LLM + safety, OCR, FHIR, wearables, frontend, graph viz) with version, rationale, alternatives, and sources. |
| [infra-stack.md](infra-stack.md) | Deployment/runtime, IaC, CI/CD, observability, secrets, and PHI compliance posture. Two profiles: Lean (MVP) and Platform (scale). |
| [core-stack-relations.md](core-stack-relations.md) | How core components and the core stack relate: end-to-end data flow, dependency direction, and the load-bearing relationships. Includes mermaid diagrams. |
| [development-backlog.md](development-backlog.md) | Structured dev work items (`WB-DEV-*`) for everything still to build, plus proposed Jira Stories to file under the WEL Epics. |

## Guardrails honored here

Every decision in this area respects `../../.cursor/rules/wellbe-vision-guardrails.mdc`:

- **Personal-first** — the user is the data controller; the institution is a distribution channel, not a data controller.
- **User-pull, not institution-push** — FHIR integration is user-initiated only (`tech-stack.md` §10).
- **No cross-patient analytics by default** — there is no enabled data path without the explicit opt-in gate (`core-stack-relations.md`).
- **Investigate, never diagnose** — the Safety & Governance Gate (C10) is structurally the only door to user-facing AI output and fails closed.
- **Every output has provenance** — the Vault → Provenance chain (C2 → C5) backs every derived fact and AI output.

## Reading order

1. `component-map.md` — what the pieces are and which tier they live in.
2. `core-stack-relations.md` — how the core pieces connect and depend on each other.
3. `tech-stack.md` + `infra-stack.md` — what each piece is built and run with.
4. `development-backlog.md` — the work to build it, and how it maps to Jira.
