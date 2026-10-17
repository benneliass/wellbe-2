# Lab node separation v1

Shared rules for turning one benchmark person into lab nodes. Every case uses this file. Do not invent a second scheme.

The lab stores a note as a record the person can open. A link is a gentle, non-diagnostic association. A look (route handle, budget, frontier) is not stored on the note.

Use only `blind_pre_diagnosis/raw_events`. Do not open `answer_key`, `full_results_no_final_label`, or `_source`. Do not add a diagnosis, a cause, or a label the record does not already contain.

## One event, one node

- One raw event becomes one node. Do not split a sentence. Do not merge two events.
- Skip an event only when it has no person-facing text after the text rule below.
- Node id: `c0N-n` plus the three-digit `sequence_index` (`c01-n012`).
- `personId`: `case-c01` … `case-c05`. `label`: `Person 1` … `Person 5`.
- `lineageId` starts as the event UUID. `independence` starts as `source_family`.

## Text

- If `original.event` is a non-empty string, that string is the text.
- Otherwise build `Name: result unit`, omitting empty parts. If `reference_range` is a non-empty string, append ` (reference RANGE)`.
- If `notes` is a non-empty string and is not already contained in the text, append it after a space.
- Do not add words such as suggests, explains, caused, or diagnosis.

## Kind and arrival

Read `category` as `original.category`, otherwise `original.event_type`. Read `rule` as `benchmark.source_mapping_rule`.

Apply the first matching row:

| When | sourceType | sourceArrival |
|---|---|---|
| category is `pathology` or `procedure` | `pdf_extract` | `imported` |
| category is `imaging`, `imaging_endoscopy`, `procedure_imaging`, or `laboratory_imaging`, or rule is `imaging` | `image_caption` | `imported` |
| rule is `lab`, or category is `laboratory`, `serology`, `microbiology`, `genetic_panel`, `infectious_testing`, `stool_test`, `vitals_exam`, or `anthropometric` | `lab_text` | `imported` |
| rule is `user_reported` or `user_narrative` | `note` | `typed` |
| anything else | `note` | `imported` |

`copiedFromId` starts null. A later copy rule may change arrival, independence, lineage, and copiedFromId.

## Links

Undirected. At most one link between a pair. No `explicitly_linked`. No `possible_inconsistency`. Demographics (`category` or `event_type` is `demographics`) get no links except a copy link.

Apply in this order. Later rules skip a pair that is already linked.

1. **Copied.** Normalize text: lowercase, collapse whitespace. If two texts are equal and at least 12 characters, or the shorter is at least 40 characters and is contained in the longer, the later node is a copy of the earlier. Set the later node’s `sourceArrival` to `copied`, `independence` to `unknown`, `lineageId` to the earlier node’s `lineageId`, and `copiedFromId` to the earlier id. Add one link, relation `derived_or_copied`, reason `copied from another record`. A node is copied from the earliest match only.

2. **Same record.** Group nodes that share a UTC calendar day and the same non-empty `relative_time`, excluding demographics. Within a group, sort by sequence and link each node only to the next one. Relation `same_record_group`, reason `same record`. This is a chain, not a clique.

3. **Close in time.** For each node, at most one link to the earlier node with a different `relative_time` whose `captured_at` is within 36 hours, if that pair is not already linked and neither is demographics. Relation `near_in_time`, reason `close in time`.

4. **May relate.** Tokens are lowercase words of length at least 5, minus this stop list: patient, history, normal, result, laboratory, negative, positive, symptom, symptoms, treatment, years, months, weeks, days, after, before, during, with, from, this, that, were, was, and, the, for, had, has, have, not, but, his, her, she, they, their, been, into, over, under, about, which, when, then, than, also, other, more, most, some, such, only, very, reported, noted, shows, showed, showing, left, right, bilateral, mild, severe, acute, chronic, test, tests, level, levels, range, reference, value, values, clinical, medical, note, notes, time, year, month, week, day, old, male, female, man, woman. A pair may relate only when both are not demographics, they are not already linked, at least one side is a `note`, they share at least two tokens, and both nodes would still have total degree at most 3 after the link. Each node gets at most one such link. Choose the pair with the most shared tokens, then the earlier sequence. Relation `possible_semantic_association`, reason `may relate`.

Write `cases/case_0N/lab_nodes.json` only. Pretty-print with two-space indent. Keys on each node, in order: `id`, `sourceEventId`, `sequence`, `sourceType`, `text`, `capturedAt`, `relativeTime`, `lineageId`, `independence`, `sourceArrival`, `copiedFromId`. Link keys: `from`, `to`, `relation`, `reason`. Top-level keys: `principles`, `caseId`, `personId`, `label`, `mode`, `nodes`, `links`. `principles` is `lab-node-separation-v1`. `mode` is `blind_pre_diagnosis`.
