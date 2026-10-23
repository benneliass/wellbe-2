# Raw Context Brain theory lab

Picture lab for [WEL-87](https://belias.atlassian.net/browse/WEL-87). The engine now lives in `backend/packages/raw_context_brain` and the signed-in person calls it at `/v2/context`. This page remains the map. It is not the workspace screen.

The lab stores synthetic notes in an append-only vault, keeps a pointer graph, and asks a local judge for `link`, `no_link`, or `uncertain`. A model abstention stays in the log and does not delete an accepted edge. `@cosmos.gl/graph` draws one person's accepted links. The page opens on the full map. Choosing a note narrows to that note and its neighbors, and the opened notes stay in click order. A route button continues that saved exploration along a route the lab advertised. Clear choice returns to the full map.

**Current design:** [`docs/system-design/raw-context-brain/README.md`](../../docs/system-design/raw-context-brain/README.md).

**Network-concept gaps:** [`docs/system-design/raw-context-brain/lab-implementation-gaps.md`](../../docs/system-design/raw-context-brain/lab-implementation-gaps.md).

**Decision status:** [`docs/decisions/raw-context-brain-theory-lab.md`](../../docs/decisions/raw-context-brain-theory-lab.md) remains Proposed.

## Implementation map

**Controller and routing:** `src/router.ts`

**Lab contracts:** `src/types.ts`

**Advertisement log and accepted projection:** `src/store.ts`

**Assessment models:** `src/judge.ts`

**Ranking and approximate discovery:** `src/rank.ts`, `src/hnsw.ts`

**Navigation facets and labels:** `src/facets.ts`

**Persistence experiment:** `src/persist/`

**Graph interface:** `src/viz/`

**Generated scorecard:** `src/scorecard.ts` → `REPORT.md`

**Behavioral evidence:** `tests/`

## Run

```bash
cd labs/raw-context-brain
npm install
npm test
npm run scorecard
./dev-server.sh start
```

Open the lab at http://localhost:5199.

`./dev-server.sh` is the way to run this server, on macOS and Linux. Use it for start, stop, restart, and status. Do not start Vite on port 5199 by hand.

```bash
./dev-server.sh start
./dev-server.sh status
./dev-server.sh logs
./dev-server.sh restart
./dev-server.sh stop
```

`start` installs dependencies when `node_modules` is missing, then leaves the server in the background. `status` exits 1 when nothing is listening. The log is `.dev-server.log`.

`npm test` uses the heuristic judge and does not call OpenAI. `npm run scorecard` rewrites `REPORT.md`.

## Optional live judge

Set `OPENAI_API_KEY` in the environment of a local script. Do not commit it. The helper is `openAiJudge` in `src/judge.ts`. The scorecard does not call it.

## What this lab will not do

- It does not read real personal health information.
- It does not change production capture, processing, or the knowledge graph.
- A passing run is not a medical result and not an approved architecture.
