# Design-session clarifications — 2026-10-22

## Authority

**Source:** Founder clarification during the Raw Context Brain design session.

**Purpose:** Preserve the design inputs that were not part of the dated WEL-87 issue snapshot.

**Applied by:** The [current design](README.md).

**Does not approve production:** The [decision record](../../decisions/raw-context-brain-theory-lab.md) remains Proposed.

## Terminology

**Link:** Use “Link” for the durable contextual association. Do not call it a “line.”

**Comparison anchor:** Use this for the earlier eligible content Node around which the controller builds the first small link map. Do not call it a “seed.”

**Small link map:** Use this for the bounded local graph context. Do not replace it with generic “context” or “neighborhood” wording when the bounded route view matters.

**Context graph explorer:** Use systematic interface terminology instead of “picture” or “drawing.”

## Candidate routing

Before association assessment:

1. Extract about five to ten request-scoped keywords from the new Content.
2. Keep earlier Content with the exact same category.
3. Count how many extracted keywords occur in each candidate's resolved text.
4. Require at least the current keyword bar.
5. Rank eligible, untried Nodes.
6. Select one comparison anchor.
7. Build a small link map around that anchor.

If the model rejects the whole map:

- lower the keyword bar,
- exclude comparison anchors already tried,
- create a new candidate snapshot,
- and build a new map around a different comparison anchor.

The exact category vocabulary and the X → Y → floor values remain open.

## Network behavior

The routing analogy should remain visible where it explains behavior.

The active topology supplies adjacency.

The controller resolves candidates, selects a bounded route view, and decides what may be exported.

The model receives only that local exported view.

It does not receive the person's full graph or choose arbitrary retrieval routes.

## Documentation style

- Explain what an object is before listing exclusions.
- Prefer exact technical verbs such as “stores `contentId`” over generic phrases such as “points at content.”
- Use tables only when comparison or field structure requires them.
- Keep short labeled statements on separate lines.
- Give complex flows their own subsections and diagrams.
- Avoid one full template section per minor object.
- Use precise system terms rather than shallow visual words.
