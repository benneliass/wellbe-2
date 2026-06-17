# Home Build-Out — Master Orchestration Doc

> In-repo shared source of truth for the multi-agent, spike-gated Home Build-Out.
> The canonical plan lives in the agent plan file; this doc mirrors it for execution
> and is the per-track checklist every agent follows. It is **not** a bible file.

## Objective

Take the Home surface (the `Launcher` at `/`, `apps/web/components/launcher/Launcher.tsx`)
from a static, mock-data prototype to a fully functional product surface: every action
pill, the capture modal, the "Ask WellBe" box, and the sidebar nav reach real,
source-linked behavior end to end (UI + API + core services), while strictly honoring
the repo's research-protocol spike gates.

## Operating rules

1. **Vertical slices.** Each feature is one slice: `Spike (if core touch) → backend
   endpoint (C13) → regenerate client types → frontend wiring → unit/integration tests
   → e2e → deploy to kind-desktop → smoke verify`. A slice is not done until it is green
   and running on the local cluster.
2. **Spike gates are hard stops.** Per `.cursor/rules/research-protocol.mdc`, the moment
   a track touches a core component (C1–C17 in `docs/architecture/component-map.md`), the
   agent STOPS feature implementation, emits a Research Context Packet, and creates a Jira
   Spike + Decision Record stub. No scaffolding, no placeholder core logic.
3. **Research is agent-run via the user key (Section I, opt-in).** The agent runs the
   configured model, records output verbatim in the Decision Record, and proposes a
   Decision — but the user explicitly approves every Decision before the Spike closes.
   The agent confirms with the user before agent-running any C10 (Safety Gate) spike.
4. **No orphan work.** Every task ties to an existing WEL item or a new one created via
   `.cursor/rules/jira-triage-protocol.mdc`. Each commit references its ticket.

## Definition of Done (quality gate for every slice)

A slice is complete only when all pass:

- **Backend checks** (per `.github/workflows/ci.yml`): `uv run ruff check .`,
  `uv run mypy packages/ apps/`, `uv run pytest`. New endpoints ship with unit +
  integration tests following `backend/apps/api/tests/`.
- **Frontend checks:** `npm run lint`, `npm run typecheck`, `npm run build`, plus new
  unit tests (Vitest + React Testing Library, introduced in Track 0).
- **Contract check:** regenerate the OpenAPI client types
  (`packages/api-client/src/generated.ts`); `backend/apps/api/tests/test_openapi_specs.py`
  stays green.
- **E2e:** Playwright flow that drives the real Home pill against the app served from the
  live `kind-desktop` cluster ingress (full-cluster e2e every slice, not a dev-server
  shortcut).
- **Local deploy + smoke:** `helm upgrade --install` the `infra/helm/wellbe-local` chart
  onto kind `kind-desktop` (namespace `wellbe`), actively monitored per
  `.cursor/rules/infra-live-monitoring.mdc`, then run the e2e smoke flow against the
  ingress URL. Helm-managed only — no raw `kubectl apply` (`.cursor/rules/infra-constraints.mdc`).

### Gate order per slice

`lint → typecheck → unit (be + fe) → build → contract/openapi → helm deploy to
kind-desktop → monitor rollout → full Playwright e2e on cluster ingress → slice green`

## Track 0 — Foundation (no core touch, do first)

| Task | What | Jira |
|---|---|---|
| T0.0 | Spike research setup: Section I amendment, `WELLBE_RESEARCH_API_KEY` handling, `scripts/spike_research.py` runner | new Track-0 Story (research setup folded into home-wiring Story) |
| T0.1 | Fix routing bugs in `Launcher.tsx` (`triage → /threads/labs` mis-wire; Ask WellBe input discard) | home-wiring Story |
| T0.2 | Honest placeholder framework + route stubs for unbuilt pills | home-wiring Story |
| T0.3 | Real data into Home/Workspace/Threads (`/v1/threads` + `/v2/pending-items` via typed client + React Query, replacing `mock-data`) | home-wiring Story (impl WEL-145) |
| T0.4 | Frontend auth/session so endpoints are reachable | WEL-151 |
| T0.5 | Test + e2e harness (Vitest + RTL, Playwright) + CI test step | test-harness Story (relates WEL-76) |
| T0.6 | Local kind-desktop deploy + verify loop (web in Tiltfile, helm deploy, monitored rollout, smoke e2e) | deploy-gate Story (relates WEL-76, WEL-99) |
| T0.7 | Orchestration scaffolding (this doc + Research Context Packet template) | home-wiring Story |

## Feature tracks (parallel after Track 0)

Component IDs from `docs/architecture/component-map.md`. Each track: Spike (if core
touch) → backend endpoint → client → frontend → tests → deploy → e2e.

| Track | Pill | Components | Spike | Jira anchors |
|---|---|---|---|---|
| A — Prepare / Visit Packet | `prep` | C7, C5, C10, C1 | required | WEL-30, WEL-68 |
| B — Log something / Capture | `log` | C3, C2 (+C4) | required (write-path; WEL-95 adapter spike Done) | WEL-18, WEL-85, WEL-32, WEL-84 |
| C — Something feels off / Triage | `triage` | C10 | MANDATORY (safety) | WEL-47 |
| D — What changed / Delta | `delta` | C9, C4 | required | WEL-56, WEL-145 |
| E — Check my patterns | `pattern` | C4, C6, C8 | required | WEL-37, WEL-79, WEL-58 |
| F — Open the graph | `graph` | C6 (read) + C13 | lighter (schema decided WEL-98/WEL-135) | WEL-35, WEL-60, WEL-78 |
| G — Ask WellBe + nav stubs | ask box, `NAV_ITEMS` | C8 (Memory, exists); C10 if Ask produces AI output | new Story; Ask may stay scoped placeholder | WEL-14, WEL-21 |

## Wave ordering

- **Wave 1 (now):** Track 0 in full, including the test/e2e harness and the kind-desktop
  deploy+verify loop, so the gate exists before any feature track runs.
- **Wave 2:** Track A (Visit Packet) + Track B (Capture) spikes first (both mvp/High).
- **Wave 3:** Track C (Triage, safety) — the C10 spike is the most consequential.
- **Wave 4:** Tracks D, E, F, G as research lands.

## Spike research mechanism (Section I, agent-run)

- Key read from `WELLBE_RESEARCH_API_KEY`; never committed/logged/written to disk.
- Runner `scripts/spike_research.py`: OpenAI Responses API, `gpt-5.5-pro` + `web_search`,
  background + poll. Records output verbatim into the Decision Record under
  "Research provided", attributed "Agent-run LLM research (model, date)".
- Approval gate unchanged: agent writes "Approaches considered" + proposed "Decision",
  presents `DECISION RECORD READY FOR APPROVAL`, and waits. Commits carry
  `[research-agent-run]`.
- C10 carve-out: confirm with the user before agent-running any safety-gate spike.

The prompt sent to the runner is a **Research Context Packet** — see the template at
`docs/implementation/research-context-packet-template.md`.

## Open inputs (do not block Track 0 foundation)

- Rotated `WELLBE_RESEARCH_API_KEY` — before the first Wave 2 spike.
- Seed-data approach (seed script vs. e2e self-creates via POST) — before T0.3 e2e.
- Local backend test Postgres (cluster vs. separate) — before Track 0 backend tests.
