# WellBe Jira Triage System — Design Spec

**Date:** 2026-05-30
**Status:** Approved for implementation planning
**Scope:** Automated triage, impact analysis, and Jira lifecycle management for the WellBe v2 project

---

## 1. Philosophy

**Jira is state. Repo is knowledge. Rules are behavior.**

The system enforces a strict separation of concerns across three layers:

| Layer | Where | What it holds | Who writes it |
|---|---|---|---|
| Design reference | `docs/` in repo | Architecture, principles, component definitions | You + agent (collaboratively) |
| Execution state | Jira `wellbe-v2` | Current priorities, roadmap, what's in flight | Agent only (within approval gates) |
| Agent behavior | `.cursor/rules/` in repo | Triage logic, taxonomy, autonomy thresholds | You + agent |

**Key constraints:**
- No state files live in the repo. The repo is stateless with respect to project execution.
- No Jira structure is duplicated into the docs. System design docs are the design reference only.
- The agent is the bridge: reads both repo and Jira, writes only to Jira within its defined rules.
- The Jira Roadmap view is the always-live priority picture. It is the single surface that reflects the current state of the project.

---

## 2. Jira Project Structure

**Project:** `wellbe-v2`
**Issue hierarchy:** Epic → Story → Sub-task, plus Bug and Spike at the Story level.

### 2.1 Special Epic: SYSTEM-MAP

A reserved root Epic that defines all system components and their inter-Epic dependency links. It is never built or deployed — it exists purely to encode the component graph in Jira. Every other Epic links back to it via `relates to` links.

### 2.2 Metadata Fields

The `WEL` project is team-managed (next-gen). Native Jira Components are not available in team-managed projects. All classification is carried via **Labels** on each issue. Versions are used for phase targeting.

All fields are required on every item. No partial items are written to Jira.

| Field | Jira mechanism | Values |
|---|---|---|
| `layer` | Label | `layer:core` / `layer:infra` / `layer:feature-backend` / `layer:feature-frontend` / `layer:feature-api` / `layer:feature-integration` |
| `component` | Label | `component:health-thread` / `component:data-factory` / `component:state-machine` / `component:safety-model` / `component:share-export` / `component:story-memory` / `component:pending-tracker` / `component:referral-lifecycle` / `component:visit-packet` / `component:responsibility-memory` |
| `impact-radius` | Label | `impact:self-contained` / `impact:component-local` / `impact:cross-cutting` |
| `priority-tier` | Priority field | `P0-blocker` / `P1-critical` / `P2-important` / `P3-backlog` |
| `phase` | Fix Version | `mvp` (id:10000) / `post-mvp` (id:10001) / `deferred` (id:10002) |
| `re-eval-flag` | Label | `re-eval:clean` / `re-eval:needs-review` / `re-eval:blocked-by-change` |

Additionally, every item created or updated during a triage run is stamped with:

| Field | Jira mechanism | Purpose |
|---|---|---|
| `triage-session-id` | Label | Links the item to the triage run that created/updated it. Format: `triage-YYYY-MM-DD-NNN`. Used by the VERIFY step to audit execution completeness. |

### 2.3 Roadmap View

The Jira Roadmap is ordered by `priority-tier` then `phase`. After every approved triage run this view automatically reflects the new state. It is the canonical answer to "what matters right now."

### 2.4 Dashboard Widgets

| Widget | What it shows |
|---|---|
| Needs attention | Items flagged `needs-review` or `blocked-by-change` |
| Active priorities | All P0 and P1 items currently open |
| Recent changes | Items re-prioritized in the last 7 days |
| Deferred backlog | All items with `phase=deferred` — visible but non-blocking |

---

## 3. Triage Flow

### 3.1 Entry Points (Triggers)

| Trigger | What fires it |
|---|---|
| **Conversation** | You describe a new idea or meaningful change in chat. Agent detects it from context — no explicit command needed. |
| **Doc change** | A commit touches `docs/system-design/` or `docs/feature-backlog/`. Agent reads the diff and evaluates whether Jira re-evaluation is warranted. |
| **Explicit** | You say "triage this", "add this feature", or "re-evaluate priorities." |
| **Orphan check** | During any triage run, the agent detects Jira items with no `triage-session-id` in the blast radius. These are folded into the current triage as candidates for classification. |

The agent is context-driven — it recognizes meaningful changes without being explicitly told. Minor doc edits, typo fixes, and reformatting are not triggers.

### 3.2 The Eight-Step Flow

The agent must follow this sequence in order. No steps are skipped or combined.

```
DETECT    Agent recognizes a meaningful change from an entry point.
          Identifies: is this a new feature, a core change, or a priority shift?

FETCH     Reads current Jira state via MCP.
          → All open Epics, Stories, their metadata, links, and flags.
          → Detects orphaned items (no triage-session-id) in the relevant area.

CLASSIFY  Assigns all six metadata fields to the new item:
          layer / component / impact-radius / priority-tier / phase / re-eval-flag.
          Classification references the taxonomy in jira-triage-taxonomy.mdc
          and the system design docs in docs/ for component definitions.

WALK      Forward and backward dependency walk via Epic links.
          → Follows "blocks", "is blocked by", and "relates to" links.
          → Blast radius can expand here as new dependencies are discovered.
          → Final blast radius is LOCKED at the end of WALK.
          → No further expansion happens during EXECUTE or VERIFY.

PROPOSE   Produces a triage report. Content and approval requirement depend on
          impact-radius (see Section 4 — Autonomy Thresholds).
          Report includes: new item details, affected components, proposed
          priority changes, and reasoning grounded in system design docs.

CONFIRM   User reviews and approves, edits, or rejects the proposal.
          Scope of what requires approval is defined in Section 4.
          The hard rule: any Epic create/delete/move/relabel always requires
          explicit approval regardless of impact-radius.

EXECUTE   Agent fires Jira MCP calls:
          → Creates new items with all six fields + triage-session-id populated.
          → Updates priorities, phases, and re-eval-flags on affected items.
          → Sets re-eval-flag = "needs-review" on items in blast radius not
            already covered by this triage run.

VERIFY    Agent re-reads Jira after execution.
          → Cross-checks every component in the locked blast radius.
          → Confirms: items exist, all metadata fields are populated, links
            are in place, triage-session-id is stamped.
          → If a gap is found: agent surfaces it and asks "handle now or defer?"
          → If deferred: creates a P3-backlog item with phase=deferred so
            nothing disappears silently.
          → Triage does not close until VERIFY passes cleanly.
```

### 3.3 Triage Report Format

When approval is required, the agent presents:

```
NEW ITEM
  → [Epic/Story] <Title>
  → layer: <value> | component: <value> | impact-radius: <value>

AFFECTED ITEMS (<N> found)
  → [<priority>] <Item title>  — <proposed action>
  → ...

PROPOSED PRIORITY CHANGES
  → <Item>: <old priority> → <new priority> (<reason>)
  → ...

REASONING
  <Grounded explanation referencing system design docs and current Jira state>

[Approve all]  [Edit]  [Reject]
```

---

## 4. Autonomy Thresholds

The agent's autonomy is determined by the `impact-radius` of the change being triaged.

| Impact radius | Agent acts autonomously | Requires user approval |
|---|---|---|
| `self-contained` | Creates/updates Stories and Sub-tasks, stamps all metadata | Nothing — silent execution |
| `component-local` | Creates Stories, flags affected items with `needs-review` | Creating, moving, or re-labeling Epics |
| `cross-cutting` | Sets `needs-review` flags on affected items only | Everything else — presents full report before any write |

**Hard rule (no exceptions):** Creating, deleting, moving, or re-labeling an Epic always requires explicit user approval, regardless of impact-radius.

---

## 5. Edge Cases and How They Are Handled

| Edge case | Handling |
|---|---|
| **Manually created Jira items (no triage provenance)** | Not given a dedicated triage trigger. Detected as orphans during the next triage run that touches the same area, then folded into that triage as classification candidates. |
| **Identifying what the agent created** | Every triage run stamps a `triage-session-id` on all items it creates or updates. Format: `triage-YYYY-MM-DD-NNN`. The VERIFY step uses this to confirm execution completeness. |
| **Blast radius growing during execution** | The WALK step locks the final blast radius before PROPOSE. No expansion happens during EXECUTE. If the agent discovers additional dependencies at VERIFY time, it flags them as a new triage candidate — not mid-run expansion. |
| **Deferred gaps disappearing silently** | When VERIFY finds a gap and the user defers it, the agent creates a P3-backlog item with `phase=deferred` in Jira. Nothing is dropped. |

---

## 6. Rules Structure

Five rule files live in `.cursor/rules/`. Together they encode the agent's full behavioral contract.

```
.cursor/rules/
├── jira-triage-taxonomy.mdc        # Classification vocabulary
├── jira-triage-protocol.mdc        # The 8-step flow
├── jira-autonomy-thresholds.mdc    # Approval matrix
├── jira-writing-standards.mdc      # Required fields, triage-session-id, link conventions
└── jira-trigger-detection.mdc      # What constitutes a meaningful change
```

### `jira-triage-taxonomy.mdc`
Defines the full vocabulary for classification: all layer values and their definitions, all component names mapped to their corresponding `docs/system-design/` sections, impact radius definitions with examples, priority tier definitions (P0–P3) grounded in WellBe's system principles, and phase definitions tied to the existing MVP plan in `docs/feature-backlog/mvp_plan.md`.

### `jira-triage-protocol.mdc`
The eight-step flow written as explicit agent instructions. Steps must be followed in order. VERIFY must pass before the triage is declared closed. The agent must never invent architectural context — if it cannot find a clear component owner or dependency in `docs/` or Jira, it must surface the ambiguity to the user before proceeding.

### `jira-autonomy-thresholds.mdc`
The full approval matrix from Section 4. Includes the hard Epic rule. Specifies what "explicit approval" means (user must type a clear affirmative — not silence or ambiguous response).

### `jira-writing-standards.mdc`
All six metadata fields are required before any item is written to Jira. Defines the `triage-session-id` format (`triage-YYYY-MM-DD-NNN`), the three valid link types (`blocks`, `is blocked by`, `relates to`), and the deferred gap recording format. No item may be written without a link back to its parent Epic.

### `jira-trigger-detection.mdc`
Defines what the agent recognizes as a meaningful change: conversational signals (new feature discussion, architecture question, priority question), doc change paths that trigger re-evaluation (`docs/system-design/`, `docs/feature-backlog/`), and what is explicitly NOT a trigger (typo fixes, formatting, adding examples to existing docs). Also defines orphan detection: any item in the blast radius with no `triage-session-id` label is an orphan candidate.

---

## 7. What This System Does Not Do

To keep scope clear:

- Does not replace the system design docs. Jira is execution state, not design rationale.
- Does not auto-merge or auto-close PRs. No code lifecycle involvement.
- Does not run on a schedule. All triage is event-driven (trigger-based).
- Does not involve any external services beyond Jira MCP.
- Does not create or manage Confluence pages, Jira Automations rules, or webhooks.
- Does not operate without the Cursor IDE — the agent lives in `.cursor/rules/`.
