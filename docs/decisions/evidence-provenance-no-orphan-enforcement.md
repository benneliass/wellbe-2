# Decision: Evidence & Provenance link schema and no-orphan-claims enforcement

**Status:** Approved  
**Date opened:** 2026-05-31  
**Date approved:** 2026-05-31  
**Approved by:** User  
**Jira Spike:** WEL-97  
**Blocks:** WEL-83 — Build Evidence & Provenance linking layer (C5)  
**Extended by (Health Investigation OS):** [docs/decisions/external-evidence-graph-separation.md](external-evidence-graph-separation.md) — external sources get source-quality tiers and are never counted as evidence about the user. The no-orphan-claims rule below is unchanged for personal facts.

---

## Question

What is the evidence link schema between a derived fact and its raw source event(s), how is the "no orphan claims" rule enforced at write time, and how are multi-source facts (a single fact derived from multiple raw events) represented?

Specifically:
1. What fields does an `EvidenceLink` carry — source reference, confidence score, link type?
2. How is the "no orphan claims" rule enforced — application-layer check, DB constraint, or both?
3. How are multi-source facts represented — a join table between a fact and multiple raw events?
4. How is the `PotentialScore` on a C6 edge related to C5 evidence confidence — who computes it and when?

## Context

C5 is the rule that all derived outputs in the system — facts, signals, memory entries, summaries, AI responses — must have at least one traceable evidence link before they become visible. This is the structural enforcement of the system principle "every output has provenance." C5 sits at layer L2 and is a direct dependency of C6 (Knowledge Graph) and C8 (Six Memories).

Getting the evidence link schema wrong means either: (a) the graph has edges with no traceable source (violates the "no orphan claims" invariant), or (b) evidence linking is so rigid that multi-source facts cannot be expressed. W3C PROV-O is the conceptual model — it distinguishes between an `Entity` (the derived fact), a `wasDerivedFrom` relationship, and the `Entity` it was derived from (the raw source).

## Research provided

### Executive summary (C5)

Provenance is relational and enforced at both application and database layers. C5 maintains an `evidence_links` join table connecting derived objects to their raw source events. The no-orphan-claims rule is enforced at application write time by the C5 service (checks that evidence_refs list is non-empty and all referenced events exist) and defensively at commit time by a Postgres deferred constraint trigger. Multi-source facts are represented as multiple rows in the join table pointing from one fact to multiple raw events. `PotentialScore` on a C6 edge is computed by C6 scoring workers that consume evidence events — C5 owns the link schema; C6 owns the scoring computation.

### Q1 — `EvidenceLink` schema

**Recommended fields:**
```
id,
source_type (extracted_fact | health_signal | memory_entry | ai_summary | ai_response | ...),
source_id (UUID, references the derived object),
raw_context_event_id (FK to C2 raw_context_events),
link_type (primary | corroborating | contradicting | contextual),
confidence (numeric, 0–1),
confidence_basis (extraction_model | user_confirmation | clinical_source | system_computed | ...),
relevance_span_start (nullable), relevance_span_end (nullable),
linked_at,
linked_by (agent: user | system | pipeline | correction_service),
correction_id (nullable, FK if this link was created by a C11 correction),
schema_version,
created_at
```

`link_type` distinguishes primary evidence (the main support for the claim), corroborating (additional support), contradicting (evidence that opposes the claim — tracked, not deleted), and contextual (background context that influenced the extraction but is not the direct source).

### Q2 — No-orphan-claims enforcement

**Recommended approach:** dual enforcement — application service + Postgres deferred trigger.

**Application-layer (C5 service write gate):**
```python
def write_derived_object(obj, evidence_refs: list[EvidenceRef]):
    if not evidence_refs:
        raise NoEvidenceRefsError(f"{obj.type} {obj.id} has no evidence_refs — write rejected")
    for ref in evidence_refs:
        if not raw_context_event_exists(ref.raw_context_event_id):
            raise MissingRawEventError(ref.raw_context_event_id)
    # proceed to write derived object + evidence_links atomically
```

**Postgres deferred trigger (defensive layer):**
```sql
CREATE CONSTRAINT TRIGGER enforce_no_orphan_claims
  AFTER INSERT OR UPDATE ON extracted_facts, health_signals, memory_entries, ...
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW
  EXECUTE FUNCTION check_evidence_link_exists();
```

The deferred trigger fires at `COMMIT` time, allowing the application to insert both the derived object and its evidence links in the same transaction without ordering issues. If no evidence link exists at commit time, the transaction is rolled back. Use `SET CONSTRAINTS enforce_no_orphan_claims DEFERRED` within migration transactions.

### Q3 — Multi-source facts

**Recommended approach:** one `evidence_links` row per (derived object, raw source event) pair — natural join-table representation.

```
evidence_links
  source_type = extracted_fact, source_id = fact_X, raw_context_event_id = event_A, link_type = primary
  source_type = extracted_fact, source_id = fact_X, raw_context_event_id = event_B, link_type = corroborating
  source_type = extracted_fact, source_id = fact_X, raw_context_event_id = event_C, link_type = contradicting
```

A fact derived from three different raw events has three rows. Each row can carry its own confidence and link_type. C5 aggregate queries sum or weight the evidence when computing overall evidence strength.

**Evidence strength computation:**
```
primary evidence        → highest weight
corroborating evidence  → additional weight (diminishing returns)
contradicting evidence  → negative weight (reduces overall strength)
contextual evidence     → small positive contribution
```

Safety-aware wording: use "supported by", "reported in", "possibly related", "evidence strength". Never use "proven", "diagnosed", "caused by", "ruled out". C10 enforces language rules at output time, but C5 should not produce confidence labels that imply clinical certainty.

### Q4 — `PotentialScore` and C5 evidence confidence

**Recommended division of responsibility:**

- **C5 owns:** the evidence link schema, per-link confidence, and evidence strength aggregation for derived facts.
- **C6 owns:** `PotentialScore` on graph edges — computed asynchronously by C6 scoring workers.
- **C6 scoring inputs include:** C5 evidence confidence, co-occurrence frequency, temporal proximity, source quality, semantic similarity (pgvector), same-thread boost, cross-thread recurrence, user confirmation/correction, contradiction penalty, recency decay.

C6 scoring workers consume `evidence.linked` events emitted by C5. They do not call C5 synchronously to get confidence values — they receive the confidence in the event payload and recompute affected edge candidates.

### References

- W3C PROV-O — https://www.w3.org/TR/prov-o/
- PostgreSQL SET CONSTRAINTS — https://www.postgresql.org/docs/current/sql-set-constraints.html
- PostgreSQL 17 CREATE TRIGGER — https://www.postgresql.org/docs/17/sql-createtrigger.html

_Research received: 2026-05-31_

---

## Approaches considered

| Approach | Decision | Reason |
|---|---|---|
| Application-layer enforcement only | Rejected | Direct DB writes, migration bugs, or bypasses can create orphans |
| Postgres-only constraint | Rejected | Does not provide user-facing error messages or rich application context |
| Application service + Postgres deferred trigger | **Accepted** | Defence-in-depth; deferred trigger fires at commit without blocking in-transaction ordering |
| Single evidence ref on the derived object (JSON field) | Rejected | Not queryable; no link_type or per-link confidence; cannot represent multi-source facts cleanly |
| Separate `evidence_links` join table | **Accepted** | Relational, queryable, supports multiple links per derived object, typed link semantics |
| C5 computes PotentialScore | Rejected | C5 owns evidence links; PotentialScore depends on graph context (co-occurrence, embeddings) that C5 does not have |
| C6 computes PotentialScore from C5 events | **Accepted** | Clean separation: C5 emits evidence confidence in events; C6 scoring workers own the scoring formula |

## Decision

C5 enforces no-orphan claims through a relational `evidence_links` join table. All derived objects (facts, signals, memory entries, summaries, AI outputs) must have at least one evidence link before becoming visible. The C5 service enforces this at write time (checks evidence_refs are non-empty and all referenced raw events exist), and a Postgres deferred constraint trigger enforces it defensively at commit. Multi-source facts are represented as multiple `evidence_links` rows (one per raw event). C5 emits `evidence.linked` events carrying per-link confidence; C6 scoring workers consume these events and own the `PotentialScore` computation on graph edges.

## Trade-offs accepted

- Deferred constraint triggers add DB complexity — accepted as the cost of a robust safety net.
- Multiple evidence link rows per fact increase storage — accepted for queryability and link-type semantics.
- C5 computes evidence strength; C6 recomputes PotentialScore — accepted duplication because the two are computing different things (evidence support vs. graph edge relevance).

## Implementation notes

- The C5 write gate is the **single point** where derived objects enter the system. No other component may write `extracted_facts`, `health_signals`, or `memory_entries` without going through C5.
- The `link_type = contradicting` case must be explicitly handled: contradicting evidence is stored, not deleted. The scoring formula uses it as a negative weight.
- Events emitted via outbox: `evidence.linked`, `evidence.corrected`, `provenance.orphan_rejected`.
- The `provenance.orphan_rejected` event should include the `source_type`, `source_id`, and the missing `raw_context_event_ids` for debugging.

---

_This record is append-only once approved. To supersede: create a new record at docs/decisions/<new-slug>.md and add a link here: "Superseded by: [docs/decisions/<new-slug>.md]"_
