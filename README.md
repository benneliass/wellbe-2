# WellBe — Personal Shared Health Memory OS

> WellBe helps you carry your health context forward until an issue is resolved, explained, monitored, or safely handed off.

## What this is

WellBe is a **Personal Shared Health Memory OS** — a user-controlled memory layer for unresolved health concerns, built on a traceable data factory and organized around **Health Threads**.

The system's job is to help a person remember, connect, clarify, close, and correct health context across time — not to diagnose, replace clinicians, or manage hospital workflows.

## Start here

1. **[System design](docs/system-design/wellbe_v2_system_design.md)** — design thesis, core object model, operating loop, six memories, and MVP shape
2. **[Architecture](docs/system-design/architecture.md)** — layered system architecture and module map
3. **[MVP plan](docs/feature-backlog/mvp_plan.md)** — what to build first and why
4. **[Implementation roadmap](docs/implementation/implementation_roadmap.md)** — phased plan with milestones

## Repository structure

```
wellbe-2/
├── docs/                   ← single source of truth
│   ├── system-design/      Core system design, architecture, data model, state machine
│   ├── workflows/          Patient, pre-visit, post-visit, referral, handoff workflows
│   ├── feature-backlog/    Feature backlog, prioritization, MVP plan, deferred items
│   ├── safety/             Safety model, do-not-diagnose rules, privacy, risk register
│   ├── implementation/     Roadmap, API/event model, migration notes, success metrics
│   └── evidence/           Evidence-to-decision cross-reference, source index
├── archive/                Prior research and analysis (synthesized into docs/, read-only)
│   ├── research/           Six raw evidence research packages
│   └── analysis/           Pre-synthesis canvas artifact
├── VISION.md               Original product vision
└── AGENTS.md               Agent instructions
```

## Core concept: Health Thread

A **Health Thread** is a living container for one unresolved or ongoing health concern. It combines the patient's own words, timeline, symptom episodes, daily-life impact, related visits, tests/results (including normal-test context), referrals, pending items, open questions, patient corrections, and a user-controlled clinician-share packet.

The product organizes around threads — not documents, metrics, visits, or isolated symptoms.

## Operating loop

**Capture → Connect → Clarify → Close → Correct**

| Step | What it does |
|---|---|
| Capture | Collect raw and structured context (symptoms, labs, referrals, wearable trends) |
| Connect | Link signals into Health Threads |
| Clarify | Show what is known, unknown, missing, pending, and worsening |
| Close | Track open loops until resolved, explained, monitored, or safely handed off |
| Correct | Let the user repair the memory |

## Design boundary

WellBe is **personal-first**. It can create clinician-readable outputs, but the user controls sharing. WellBe is not a hospital EHR, referral-management platform, population analytics platform, or autonomous diagnostic engine.

See [safety model](docs/safety/safety_model.md) and [do-not-diagnose rules](docs/safety/do_not_diagnose_rules.md).
