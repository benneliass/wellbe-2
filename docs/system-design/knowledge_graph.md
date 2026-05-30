# Knowledge Graph

## Purpose

The Knowledge Graph is the structural substrate connecting all health entities in WellBe. Where the Health Thread organizes context around one unresolved concern over time, the graph connects entities *across* threads, domains, time, and sources — making latent relationships visible and queryable.

Every processed entity (symptom, lab result, medication, visit, referral, hypothesis, body region, practitioner, document, environmental event) becomes a node. Every meaningful relationship between entities becomes a typed, evidence-weighted edge.

## Node types

| Category | Node types |
|---|---|
| Clinical | `symptom`, `condition`, `medication`, `lab_result`, `imaging_result`, `procedure`, `diagnosis`, `hypothesis` |
| Care pathway | `visit`, `referral`, `referral_appointment`, `pending_item`, `practitioner`, `care_setting` |
| Personal context | `body_region`, `mood_state`, `baseline_deviation`, `wearable_metric`, `document` |
| External context | `environmental_event`, `public_health_signal` |
| Meta | `health_thread`, `story_memory_entry`, `patient_correction` |

Each node carries: `privacy_class`, `confidence`, `evidence_level`, `source_context_ids[]`, `created_at`, `last_updated_at`.

## Edge types

| Edge type | Meaning |
|---|---|
| `co_occurs_with` | Two entities appear together in the same window or episode |
| `temporally_precedes` | Entity A consistently appears before entity B |
| `may_explain` | Entity A is a plausible explanation for entity B (hypothesis-level, not diagnostic) |
| `contradicts` | Entity A conflicts with entity B — preserved, not resolved |
| `confirms` | Entity A strengthens the evidence for entity B |
| `aggravates` | Entity A worsens or correlates with worsening of entity B |
| `resolves` | Entity A corresponds to reduction or closure of entity B |
| `part_of` | Entity A is a component or manifestation of entity B |
| `derived_from` | Derived fact linked back to its raw source event |
| `belongs_to_thread` | Entity is a member of a specific Health Thread |

Edges carry: `PotentialScore` (0–100), `score_level` (7 levels), `source_context_ids[]`, `confidence`, `is_user_corrected`.

## Evidence weighting

`PotentialScore` is computed from: source quality, temporal recency, repetition across independent sources, and user-confirmed vs. inferred status. Edges from user corrections outweigh inferred edges for subjective signals.

## Auto-linking

A background worker runs after each processing pipeline completion. It:
1. Identifies new or updated entities
2. Queries existing nodes for co-occurrence, temporal, and semantic matches
3. Creates or updates edges with computed scores
4. Flags contradictions for the Contradiction Resolution engine

## Visualization modes

| Mode | Scope | When used |
|---|---|---|
| Thread-scoped view | Entities and relationships within one Health Thread | Default — opens from any thread |
| Investigation landscape | Full user graph, filterable by domain, time, concern | Investigation mode, pattern exploration |
| Comparison overlay | Two threads or time periods side-by-side | Temporal pattern analysis |

All visualization nodes are clickable — drill down to source events, evidence chain, and correction history.

## Integration with Health Thread

Each Health Thread maintains a `thread_subgraph_id` linking to its slice of the full graph. When a new entity is linked to a thread, the graph updates in real time. When a user adds a correction, the correction node attaches to the relevant entity and is reflected in the graph.

## Relation to Intelligence Engines

The graph is the primary input for the Intelligence Engines (see `intelligence_engines.md`). Pattern detection, temporal analysis, confounder detection, missing data identification, and contradiction resolution all query and write back to the graph.

## Safety constraints

- Graph edges never assert diagnosis. `may_explain` is the strongest causal language.
- Contradiction edges are preserved — the system does not silently pick one side.
- Evidence-level and confidence are displayed with every node and edge.
- Raw source is always accessible from any graph element.
