# Research Context Packet — <Track letter> / <Spike slug>

> This packet is BOTH the user's review artifact AND the prompt sent to the research
> runner (`scripts/spike_research.py`). Fill every section with concrete, source-linked
> context. Never propose an answer to the decision question — that is what the research
> produces and the user approves. See `.cursor/rules/research-protocol.mdc`.

**Spike:** WEL-XXX
**Blocks:** WEL-XXX <Story title>
**Decision Record:** `docs/decisions/<slug>.md`
**Core component(s) touched:** <e.g. Health Thread Engine + State Machine (C7)>
**Date assembled:** YYYY-MM-DD

---

## 1. Identity and guardrails (non-negotiables)

What WellBe is and the hard constraints any answer must respect. Link, do not restate:
- `docs/system-design/platform_identity.md`
- `.cursor/rules/wellbe-vision-guardrails.mdc`
- `.cursor/rules/audience-guardrails.mdc`

Call out the specific guardrails this decision must not violate (personal-first,
user-controlled, source-linked, non-diagnostic, calm, grant-scoped).

## 2. System placement

Where this feature sits in the Capture → Connect → Investigate → Clarify → Close →
Correct loop. Link `docs/system-design/system_design.md` and the architecture notes.

## 3. Component dossier

The exact core component(s) touched, their dependencies and blast radius, from
`docs/architecture/component-map.md`. List upstream/downstream components and any
already-approved decisions that constrain this one.

## 4. Current state (what exists vs. what is missing)

Concrete file paths and contract excerpts:
- Existing endpoints / schema / types relevant to this decision.
- What is already built and stable (safe to consume).
- What is missing and must be designed.

## 5. The decision question(s)

Precise, concrete decision questions — not "how does X work". Each question must be a
crisp choice ("should we do A or B given constraint Y?") that an implementer can act on.

## 6. Stakes

Why it matters. What breaks or becomes irreversible/expensive to correct if guessed wrong.

## 7. Unblocks

What implementation proceeds once the Decision is approved.

## 8. Prior art

Related already-approved Spikes/Decisions (e.g. WEL-95, WEL-98, WEL-135) and the
Decision Records under `docs/decisions/`.

## 9. Where to look (research directions, NOT answers)

Suggested source types and directions for the research — standards bodies, clinical
guidelines, established patterns. Never a proposed answer.
