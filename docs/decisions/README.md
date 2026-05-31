# Decision Records

This directory contains Decision Records for architectural and design choices made in the WellBe project. Every record documents a question that required research before implementation could proceed.

---

## What Is a Decision Record?

A Decision Record is a permanent, append-only account of one decision about a core component. It captures:

1. **The question** — the specific thing that had to be answered before implementation could begin
2. **The research** — what the user provided (verbatim or faithful summary)
3. **The approaches considered** — distinct options derived from the research
4. **The decision** — what was chosen and approved
5. **The trade-offs** — what was consciously given up

Records are not speculation documents. They do not capture what might be decided — only what was decided, by whom, and on what basis.

---

## How Records Get Created

Decision Records are always created by an agent as part of the research protocol in `.cursor/rules/research-protocol.mdc`. The lifecycle is:

1. An agent detects that a Story touches a core component (C1–C17 in `docs/architecture/component-map.md`)
2. The agent raises its hand, creates a Jira Spike, and creates a Decision Record stub here
3. The user provides research results
4. The agent records the research, writes approaches and a proposed decision, and presents the record for approval
5. The user approves (or edits and approves)
6. The record is committed with status `Approved`

**Records are never created manually without a Spike.** A Decision Record with no associated Jira Spike is incomplete and should be flagged.

---

## Status Lifecycle

```
Open → Research Received → Proposed → Approved
                                    ↘ Superseded (by a newer record)
```

| Status | Meaning |
|---|---|
| `Open` | Spike created, question written, waiting for research |
| `Research Received` | User has provided research; agent is writing approaches and proposed decision |
| `Proposed` | Agent has presented the decision; waiting for user approval |
| `Approved` | User has explicitly approved; record is now append-only historical truth |
| `Superseded` | A newer record replaces this one; link to the replacement is in the file |

---

## Finding Records by Component

Records are named with a slug derived from the question (not the component name), so the most reliable way to find records for a specific component is to search for the component name in the file contents:

```
# Search by component
grep -r "C7\|Health Thread Engine" docs/decisions/
```

Each record's front-matter includes a `**Blocks:**` field naming the Story it unblocked, and the associated Jira Spike key.

---

## What These Records Are NOT

- Decision Records are **not bible files** — they do not require governance approval to read, reference, or cite. See `.cursor/rules/doc-governance.mdc` for the bible file list.
- Decision Records are **not living documents** — once approved, they are append-only. A correction to an approved decision means creating a new record that supersedes the old one.
- Decision Records are **not a substitute for implementation comments** — they document the decision, not the code. Implementation notes are in the record but code comments should reference the record by filename if the decision is non-obvious.

---

## Template

Every Decision Record must use the template at `docs/decisions/_template.md`. No custom structures.
