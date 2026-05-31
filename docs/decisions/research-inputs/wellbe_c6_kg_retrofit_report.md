Research Report - C6 Knowledge Graph Retrofit for the Health Investigation OS
Decision input for WEL-130, WEL-128, and WEL-129
External research synthesis prepared for WellBe
2026-05-31
Table of Contents

1	Research Report - C6 Knowledge Graph Retrofit for the Health Investigation OS
Prepared for: WellBe / external research consultant workflow Prepared: 2026-05-31 Owner: Ben Elias, data controller / product owner Scope: WEL-130, WEL-128, WEL-129; implementation input for WEL-135 Status: Decision input. The WellBe team should approve before implementation.
This report answers the three research questions in the requested format: approaches considered, recommended approach, accepted trade-offs, implementation notes, and open risks. It is written to be pasted into the three decision records named in the brief.
1.1	Executive recommendation matrix
Decision
Recommendation
Why this is the safest additive retrofit
WEL-130: External Evidence Graph separation
Use a separate external_kg schema in the same PostgreSQL database for v1, owned by C16 with separate roles, plus a patient-scoped external_bridge.relevance_links table with RLS. Do not put external nodes into graph.kg_nodes, and do not put cross-boundary links into graph.kg_edges. Optionally maintain a separate Apache AGE graph named wellbe_external only as a projection.
Keeps external evidence out of the personal graph and out of C5 personal evidence scoring while preserving transactional deployment simplicity. PostgreSQL schemas are useful namespaces but not hard isolation, so the design must also use role grants, RLS, service boundaries, and tests [S4, S5].
WEL-128: Investigation object and thread coupling
Model Investigation as a separate C14 aggregate with its own lifecycle, linked many-to-many to C7 Health Threads through a join table and projected into C6 as an Investigation node. C7 owns thread closure criteria; C14 owns investigation status; a shared policy/veto contract enforces cross-aggregate closure safety.
FHIR Task and CarePlan show workflow objects can have their own status and owners while remaining linked to patient context [S13, S14]. Domain events are a standard way to propagate side effects across aggregates without merging their lifecycles [S16, S17, S18].
WEL-129: Theory evaluation and safety routing
Model Theory as a first-class C15 aggregate with a C6 graph projection and an optional C8 Pattern Memory derivative. Only personal facts with C5 provenance create evidence_for / evidence_against graph edges. External sources attach as external context only. C10 blocks diagnostic, ranked-differential, and unsupported outputs before user display.
Separates hypothesis evaluation from diagnosis. FDA CDS guidance and ONC DSI rules emphasize transparency, source attributes, risk management, and reviewability for decision-support functions [S19, S20]. FHIR Provenance and W3C PROV support traceable claims [S1, S2].
1.2	Global design principles used in all three answers
	•	Keep source-of-truth boundaries explicit. Personal facts remain in C2/C5/C6 under patient RLS. External knowledge remains in C16. Bridge rows are links, not imports.
	•	Separate personal evidence from external context in both schema and code. A source can be medically strong and still never become evidence that anything is true about this individual.
	•	Use first-class aggregates for lifecycle-heavy objects. Investigations and theories have statuses, participants, safety flags, review events, and policy checks; those should not be hidden inside graph metadata.
	•	Keep C6 additive. Do not rename existing PascalCase node types. Add Investigation and Theory as new node types for compatibility, and expose lowercase aliases at the service/API layer.
	•	Use C10 as the last-mile safety boundary, not as the only boundary. Diagnostic verbs and external-contamination paths should also be blocked by database constraints, service contracts, and tests.
1.3	Source basis
This report relies primarily on standards and official documentation: HL7 FHIR Provenance, Consent, Evidence, Citation, ArtifactAssessment, Task, CarePlan, and DetectedIssue resources [S1, S3, S8, S9, S10, S13, S14, S15]; W3C PROV and SPARQL/RDF Dataset named-graph precedent [S2, S7]; PostgreSQL schemas and Row-Level Security [S4, S5]; Apache AGE graph creation [S6]; GRADE and OCEBM evidence-quality concepts [S11, S12]; FDA Clinical Decision Support Software guidance and ONC Decision Support Intervention criteria [S19, S20]; SNOMED CT context modeling [S23, S24]; and domain-event / aggregate patterns [S16, S17, S18].

2	WEL-130 - External Evidence Graph separation and relevance-link semantics
2.1	Question
How should the External Evidence Graph (C16) be separated from the personal Knowledge Graph (C6) and Evidence & Provenance Service (C5), and how are relevance links scored and constrained so external claims never become facts about the user?
2.2	Approaches considered
2.2.1	Option 1 - Separate database or separate graph store for C16
How it works. C16 stores external medical knowledge in a physically separate database or graph store. C6 personal graph tables remain unchanged except for a bridge table that stores (patient_id, personal_node_id, external_source_ref, relevance_score). The bridge uses an external URI or UUID but has no foreign key into the external database. The C16 API resolves the external reference when a user is allowed to see the contextual source.
Pros. This is the strongest structural separation. Backups, access roles, query paths, and operational privileges are separate. It also avoids pretending that a public medical article is tenant-owned personal data. This aligns with the hard distinction between patient-specific resources and community knowledge: FHIR Evidence is a machine-interpretable expression of evidence and is not patient-compartmented in the same way as clinical patient records [S10], while FHIR ArtifactAssessment explicitly distinguishes assessments about community knowledge from assessments about medical-record artifacts [S8].
Cons. Cross-store transactions are harder. Referential integrity between a personal relevance link and an external source must be implemented by service checks or a periodic repair job, not by a normal database foreign key. Local development and migrations are more complex. Search and ranking may need an asynchronous index.
Evidence / precedent. W3C PROV treats provenance as information about entities, activities, and people involved in producing a data item, which supports separating provenance chains by source context rather than merging all origins into one graph [S2]. FHIR Provenance similarly treats provenance as contextual metadata for resources and their source activity [S1].
2.2.2	Option 2 - Separate schema in the same PostgreSQL database, separate service role, bridge table with RLS (recommended)
How it works. C16 owns a new external_kg schema in the same PostgreSQL database. External source and external claim tables do not contain patient_id. C6 continues to own graph.kg_nodes and graph.kg_edges. Cross-boundary links live in a separate external_bridge.relevance_links table with patient_id, RLS, a personal endpoint FK, and an external endpoint FK. External source rows are never inserted into graph.kg_nodes, and cross-boundary links are never inserted into graph.kg_edges.
Pros. This gives a strong logical boundary with lower operational overhead than a separate database. The bridge table can use transactional FKs to both personal and external tables while preserving patient RLS on the bridge. It is easier to ship as an additive migration. It also fits the current C6 architecture, where relational tables are the authoritative store and Apache AGE is optional.
Cons. PostgreSQL schemas are namespaces, not hard isolation: a user connected to a database can access any schema objects for which they have privileges [S5]. Therefore the design must pair schema separation with explicit grants, search-path discipline, RLS on bridge tables, service roles, security-definer views, and tests. This is not as strong as a physically separate database.
Evidence / precedent. PostgreSQL RLS can restrict which rows are returned or modified, and without a policy, RLS uses a default-deny posture [S4]. PostgreSQL schemas support logical grouping and name isolation, but are not rigid separation boundaries [S5]. FHIR Citation supports identification and attribution of external knowledge artifacts [S9], and FHIR ArtifactAssessment can carry ratings or classifications about those artifacts without becoming the artifact’s provenance [S8].
2.2.3	Option 3 - Namespaced subgraph / separate Apache AGE graph in the same database
How it works. Keep relational C6 tables as-is, but create an optional AGE graph such as wellbe_external. External nodes and edges are loaded into AGE-only structures or into external tables that feed AGE. Personal graph and external graph are queried separately. A visualization service may draw both graphs but must label the external graph as contextual.
Pros. Useful for graph visualization, Cypher exploration, and research-watch traversal. Apache AGE supports create_graph(graph_name) and automatically creates tables for the graph [S6]. W3C RDF datasets and SPARQL named graphs provide a conceptual precedent for querying multiple graphs in one dataset [S7].
Cons. This is not sufficient as the source-of-truth separation because C6’s authoritative store is relational, not AGE. A namespaced graph can also be accidentally merged into a default graph or visualization path. W3C SPARQL explicitly allows datasets where named graphs are merged into the default graph in some arrangements [S7]; that is exactly the kind of contamination WellBe must prevent.
Evidence / precedent. Named-graph patterns are useful for graph-scoped queries, but the standard allows both strict named-graph access and merged default-graph arrangements [S7]. Therefore named graphs are a useful projection mechanism, not a sufficient safety boundary.
2.2.4	Option 4 - Single kg_nodes / kg_edges with scope or is_external
How it works. Add scope IN ('personal','external') or is_external to graph.kg_nodes, allow external rows with patient_id IS NULL, and store relevance_link in graph.kg_edges.
Pros. Minimal number of tables. Simple graph traversal. Reuses C6 edge scoring and edge-type code.
Cons. This option should be rejected. It makes external knowledge reachable through the same node and edge path used for personal facts. It creates constant risk that external nodes are counted by C5, auto-linkers, or downstream outputs as if they were personal. It also weakens the simple tenant-isolation invariant that every C6 node and edge is patient-scoped. SNOMED CT context guidance shows that the same clinical concept can mean current diagnosis, family history, possible diagnosis, or ruled-out diagnosis depending on record context [S23]; mixing external disease concepts into patient graph rows would amplify exactly this contextual ambiguity.
Evidence / precedent. PostgreSQL RLS can be robust, but conditional policies over mixed personal and non-personal rows are more complex than policies over tables with a single security meaning [S4]. FHIR DetectedIssue also distinguishes patient-specific issues from general patient-independent knowledge, recommending other resources for general knowledge [S15].
2.3	Recommended approach
Choose Option 2: separate external_kg schema in the same PostgreSQL database, with separate roles and a patient-scoped bridge table, plus optional AGE projection for visualization only.
This should be treated as a staged hardening path:
	•	Stage 1 / WEL-135: same PostgreSQL database, separate external_kg and external_bridge schemas, C16 service role, bridge table with RLS.
	•	Stage 2 / future high-assurance mode: move external_kg to a separate database or external graph store if the team needs stronger operational isolation, while keeping the same bridge API and immutable external identifiers.
2.3.1	How this satisfies the hard constraints
	•	G1 - Never diagnose: External claims are never stored as personal ConditionHypothesis or personal facts. The only allowed cross-boundary relationship is relevance_link, whose display verb is “is relevant context for” rather than “supports diagnosis” or “confirms”.
	•	G2 - External equals context, never fact: External rows are structurally outside graph.kg_nodes and cannot appear in graph.kg_edges. C5 personal evidence scoring ignores external_bridge.relevance_links.
	•	G3 - No orphan claims: Personal facts still require C5 evidence links to raw source events. External source provenance is tracked in C16, not substituted for personal source provenance.
	•	G4 - Closure safety: External context cannot close a thread or investigation. Closure policy consumes C7/C14 state and personal evidence only.
	•	G5 - Additive, non-destructive: Existing C6 rows stay untouched. New schemas, new node types, new edge types, and new bridge tables are additive.
	•	G6 - Tenant isolation preserved: Personal nodes/edges remain RLS-scoped by patient_id. The bridge table is patient-scoped and RLS-protected; external tables are not exposed through personal RLS as personal rows.
	•	G7 - Individual is controller: Any participant or reviewer who creates or views a relevance link must pass C1/C17 grant checks. FHIR Consent supports computable privacy preferences and rules for enforcement, which is a useful precedent for treating grants as explicit runtime authorization rather than static roles [S3].
2.4	Trade-offs accepted
	•	Less graph-traversal convenience. Cross-boundary traversal requires a join or service call instead of one kg_edges traversal.
	•	Slightly more schema surface. The bridge table and external tables introduce more migrations and tests.
	•	Not maximum physical isolation in v1. A separate schema is not as strong as a separate database. The accepted mitigation is strict role grants, no external rows in C6 tables, RLS on bridge rows, and service-level tests.
	•	Source quality and relevance are separate concepts. A low-quality anecdote can be textually relevant but must be surfaced with a low tier and a strict contextual warning.
2.5	Implementation notes
2.5.1	1. Node-type retrofit
Keep existing PascalCase node-type codes in C6 and add Investigation and Theory. Do not rename existing rows to lowercase. Expose lowercase aliases (investigation, theory) at API/service boundaries if the design spec uses lowercase.
Recommended migration pattern:
-- Keep existing rows and tests stable; expand the check. ALTER TABLE graph.kg_nodes   DROP CONSTRAINT IF EXISTS ck_node_type;  ALTER TABLE graph.kg_nodes   ADD CONSTRAINT ck_node_type CHECK (     node_type IN (       'ConditionHypothesis','Symptom','Medication','LabResult',       'Procedure','VitalSign','Allergy','Immunization',       'SocialFactor','FamilyHistory','Other',       'Investigation','Theory'     )   );  CREATE TABLE IF NOT EXISTS graph.node_type_aliases (   code text PRIMARY KEY,   canonical_code text NOT NULL,   domain text NOT NULL CHECK (domain IN ('clinical','process','hypothesis','other')),   display_name text NOT NULL );
Longer-term, migrate from a CHECK constraint to a graph.node_types reference table, mirroring graph.edge_types. For WEL-135, expanding the CHECK is lower risk because it preserves current test expectations.
2.5.2	2. Edge vocabulary retrofit
Add categories without weakening the may_explain ceiling:
ALTER TABLE graph.edge_types   DROP CONSTRAINT IF EXISTS edge_types_category_check;  ALTER TABLE graph.edge_types   ADD CONSTRAINT edge_types_category_check CHECK (     category IN (       'causal','correlation','temporal','therapeutic','adverse',       'contradiction','refinement','evidential','process',       'external_context'     )   );  INSERT INTO graph.edge_types (code, display_name, category) VALUES   ('evidence_for', 'Evidence for', 'evidential'),   ('evidence_against', 'Evidence against', 'evidential'),   ('investigates', 'Investigates', 'process'),   ('relevance_link', 'External relevance link', 'external_context') ON CONFLICT (code) DO NOTHING;
Then enforce storage rules separately:
	•	evidence_for, evidence_against, and investigates may be stored in graph.kg_edges when both endpoints are patient-scoped personal/meta nodes.
	•	relevance_link is registered in the vocabulary but not stored in graph.kg_edges. It is stored only in external_bridge.relevance_links.
	•	Add a trigger or CHECK to reject edge_type = 'relevance_link' in graph.kg_edges.
2.5.3	3. External graph schema
CREATE SCHEMA IF NOT EXISTS external_kg; CREATE SCHEMA IF NOT EXISTS external_bridge;  CREATE TABLE external_kg.external_evidence_sources (   id uuid PRIMARY KEY,   source_type text NOT NULL CHECK (source_type IN (     'clinical_guideline','official_body','systematic_review',     'peer_reviewed_paper','case_report','early_research',     'medical_blog','expert_explainer','forum_post','anecdote','social_post'   )),   source_quality_tier smallint NOT NULL CHECK (source_quality_tier BETWEEN 1 AND 5),   tier_reason text NOT NULL,   title text NOT NULL,   citation_text text,   url text,   doi text,   publisher text,   publication_date date,   version_label text,   retraction_status text NOT NULL DEFAULT 'not_retracted'     CHECK (retraction_status IN ('not_retracted','expression_of_concern','retracted','superseded')),   assigned_by text NOT NULL,   assigned_at timestamptz NOT NULL DEFAULT now(),   metadata jsonb NOT NULL DEFAULT '{}'::jsonb,   created_at timestamptz NOT NULL DEFAULT now(),   updated_at timestamptz NOT NULL DEFAULT now() );  CREATE TABLE external_kg.external_claims (   id uuid PRIMARY KEY,   source_id uuid NOT NULL REFERENCES external_kg.external_evidence_sources(id),   claim_text text NOT NULL,   claim_kind text NOT NULL CHECK (claim_kind IN (     'association','risk_factor','mechanism','contraindication',     'guideline_recommendation','educational_context','anecdote'   )),   population_context jsonb NOT NULL DEFAULT '{}'::jsonb,   evidence_attributes jsonb NOT NULL DEFAULT '{}'::jsonb,   created_at timestamptz NOT NULL DEFAULT now() );
FHIR Citation and Evidence provide precedents for representing bibliographic metadata and machine-interpretable evidence/certainty separately [S9, S10]. ArtifactAssessment provides a precedent for classifications and ratings about knowledge artifacts [S8]. GRADE and OCEBM provide evidence-quality taxonomies, but WellBe’s Tier 1-5 values should remain a product-specific simplification rather than a full GRADE rating [S11, S12].
2.5.4	4. Relevance-link bridge table
CREATE TABLE external_bridge.relevance_links (   id uuid PRIMARY KEY,   patient_id uuid NOT NULL,   personal_node_id uuid NOT NULL REFERENCES graph.kg_nodes(id),   thread_id uuid,   external_source_id uuid NOT NULL     REFERENCES external_kg.external_evidence_sources(id),   external_claim_id uuid     REFERENCES external_kg.external_claims(id),   edge_type text NOT NULL DEFAULT 'relevance_link'     CHECK (edge_type = 'relevance_link'),   relevance_score numeric(5,4) NOT NULL     CHECK (relevance_score >= 0 AND relevance_score <= 1),   relevance_score_version text NOT NULL,   relevance_inputs jsonb NOT NULL DEFAULT '{}'::jsonb,   source_quality_tier_snapshot smallint NOT NULL CHECK (source_quality_tier_snapshot BETWEEN 1 AND 5),   context_only boolean NOT NULL DEFAULT true CHECK (context_only IS TRUE),   created_by_actor_id uuid,   created_under_grant_id uuid,   created_at timestamptz NOT NULL DEFAULT now(),   UNIQUE (patient_id, personal_node_id, external_source_id, external_claim_id) );  ALTER TABLE external_bridge.relevance_links ENABLE ROW LEVEL SECURITY;  CREATE POLICY patient_isolation_relevance_links ON external_bridge.relevance_links USING (patient_id = current_setting('app.patient_id')::uuid) WITH CHECK (patient_id = current_setting('app.patient_id')::uuid);
Add a trigger that verifies graph.kg_nodes.patient_id = relevance_links.patient_id for personal_node_id.
2.5.5	5. Source-quality tier assignment
Store source quality as a controlled field on external_kg.external_evidence_sources:
	•	Tier 1: clinical guideline or official body.
	•	Tier 2: peer-reviewed paper, systematic review, or high-quality evidence synthesis.
	•	Tier 3: case report or early research.
	•	Tier 4: medical blog or expert explainer.
	•	Tier 5: forum, anecdote, or social post.
Tier is assigned by deterministic source-type rules plus human review for ambiguous cases. Usage can never upgrade a tier. A popular forum post remains Tier 5. Usage can create separate fields such as usage_count, user_saved_count, or retrieval_priority, but not source_quality_tier. Tier can change only through an auditable editorial event: retraction, guideline update, peer-review status change, source correction, or manual quality review.
Recommended tier-history table:
CREATE TABLE external_kg.source_quality_reviews (   id uuid PRIMARY KEY,   source_id uuid NOT NULL REFERENCES external_kg.external_evidence_sources(id),   previous_tier smallint CHECK (previous_tier BETWEEN 1 AND 5),   new_tier smallint NOT NULL CHECK (new_tier BETWEEN 1 AND 5),   reason text NOT NULL,   reviewer_actor_id uuid NOT NULL,   reviewed_at timestamptz NOT NULL DEFAULT now() );
2.5.6	6. Relevance scoring
relevance_score is not a diagnostic confidence and not the existing potential_score. It means only: “how strongly does this external artifact appear topically/contextually related to this personal fact or thread?”
Recommended v1 scoring inputs:
relevance_score = clamp(   0.35 * entity_or_code_match +   0.25 * semantic_similarity +   0.15 * thread_context_match +   0.10 * population_or_context_applicability +   0.10 * source_currentness +   0.05 * reviewer_or_user_query_signal,   0, 1 )
Keep source_quality_tier separate from relevance_score. Tier controls surfacing and warning labels, not whether the source is related. Suggested surfacing caps:
Tier
Maximum default surfacing priority
Required label
1
1.00
Guideline / official reference; context only
2
0.90
Peer-reviewed or synthesized evidence; context only
3
0.65
Early or case-level signal; not general proof
4
0.45
Educational explainer; not evidence about you
5
0.25
Anecdotal; never evidence about you
2.5.7	7. C5 provenance treatment
C5 should have two distinct constructs:
	•	evidence.evidence_links: personal evidence only. Inputs are C2 raw source events or C4 extracted facts derived from personal data. These links may be PRIMARY, CORROBORATING, CONTRADICTING, or CONTEXTUAL and can feed the existing PotentialScoreComputer.
	•	evidence.external_context_refs or C16 bridge links: external context only. These are never passed into PotentialScoreComputer, never count as personal evidence, and never satisfy provenance requirements for a derived personal fact.
Recommended enforcement:
ALTER TABLE evidence.evidence_links   ADD COLUMN IF NOT EXISTS source_scope text NOT NULL DEFAULT 'personal'   CHECK (source_scope = 'personal');
If adding this column is too disruptive, enforce the same rule in service code and tests first, then add the column in a later migration.
2.6	Open risks / what could go wrong
	•	Visualization leakage. A UI could draw external claims near personal nodes without the context-only label, making the user infer diagnosis. Mitigation: C10 must gate all user-facing graph summaries, and external nodes must render with a distinct label, tier, and context warning.
	•	Scoring confusion. Engineers may confuse relevance_score with potential_score. Mitigation: different table, different column name, different service, and tests that external context never changes kg_edges.potential_score.
	•	Schema separation over-trusted. PostgreSQL schemas are not hard boundaries [S5]. Mitigation: separate roles, no broad grants, forced search_path, RLS, and migration tests that wellbe_graph cannot read or write external tables except through approved views.
	•	External content accidentally copied into personal metadata. Avoid storing claim text snapshots in kg_nodes.metadata. The bridge may store IDs and short display metadata only if labeled context-only.
	•	Tier gaming. Usage metrics or popularity could pressure tier upgrades. Mitigation: hard rule that usage never upgrades source quality; keep usage separate from tier.

3	WEL-128 - Investigation object model and coupling to the Health Thread state machine
3.1	Question
How should the Investigation object (C14) be modeled and persisted relative to the Health Thread (C7), and how do Investigation status transitions couple to Health Thread state transitions?
3.2	Approaches considered
3.2.1	Option 1 - Embed Investigation as a sub-state inside Health Thread
How it works. Add investigation fields directly to the Health Thread record: investigation_status, primary_question, active_theory_ids, missing_context_items, and outputs.
Pros. Simple join path. Thread closure and investigation closure can be checked in one aggregate. Good for a single investigation per thread.
Cons. The brief says a thread may carry many investigations. Embedding a lifecycle-heavy object inside a thread makes many-to-one and many-to-many cases awkward, especially if a single investigation spans multiple threads. It also entangles C7 thread state with C14 investigation workflow state, making it harder to test safety invariants independently.
Evidence / precedent. FHIR CarePlan is a separate workflow/request resource that can describe care intentions for a patient or condition over time [S14]. FHIR Task is also an independent workflow resource with its own state machine and owner/requester concepts [S13]. These precedents favor separate workflow objects over overloading the patient problem/thread record.
3.2.2	Option 2 - Separate Investigation aggregate with join table and graph projection (recommended)
How it works. C14 owns an investigations table and lifecycle. C14 links investigations to threads through c14.investigation_threads. C6 receives a projection node of type Investigation and optional investigates edges to personal entity nodes. C7 remains authoritative for thread lifecycle and closure criteria.
Pros. Clean lifecycle boundaries. Supports multiple investigations per thread and one investigation spanning multiple threads. Lets C14 evolve without modifying C7’s thread schema for every investigation field. Also lets C6 answer graph questions without becoming the lifecycle authority.
Cons. Requires cross-aggregate policy and events. Closure and safety propagation must be carefully designed to avoid stale states. There is more schema and test surface than embedded state.
Evidence / precedent. Domain-event patterns are designed to trigger side effects across aggregates while keeping aggregate boundaries clear [S16, S17, S18]. FHIR Task explicitly supports workflow engines or agents updating task status while maintaining a consistent view of workflow status [S13].
3.2.3	Option 3 - Pure graph node, no separate C14 aggregate table
How it works. Store Investigation only as a C6 node with metadata fields for status, participants, outputs, and safety flags. Link to thread IDs through kg_nodes.thread_ids and to entities through investigates edges.
Pros. Very small relational schema change. Easy graph queries. C6 remains the visible center of investigation relationships.
Cons. C6 is not currently the owner of workflow lifecycles, grants, participant state, or closure policy. JSON metadata is a poor place for lifecycle invariants. This also risks making graph traversal mutate business state, which would be an architectural inversion.
Evidence / precedent. FHIR Task and CarePlan represent workflow state explicitly rather than hiding status inside graph metadata [S13, S14]. FHIR Provenance also distinguishes the resource whose state changes from the record of the activity that produced or changed it [S1].
3.2.4	Option 4 - Delegate Investigation entirely to a generic workflow engine
How it works. Model Investigation as a generic workflow/case object in a workflow engine. Store only IDs and projections in C7/C6.
Pros. Strong workflow tooling, timers, subscriptions, retry, and audit. Could handle next_review_due_at, waiting states, and task completion well.
Cons. Overkill for WEL-135 and can obscure the health-specific safety rules. Closure safety, individual-controller grants, and non-diagnostic outputs still need product-specific policy. It introduces operational dependency and more failure modes.
Evidence / precedent. FHIR Task supports both server-as-task-repository and centrally controlled workflow-engine models [S13]. That makes a workflow engine a plausible later implementation detail, but not necessary for the first additive retrofit.
3.3	Recommended approach
Choose Option 2: Investigation as a separate C14 aggregate with a join table to Health Threads and a C6 graph projection.
3.3.1	Ownership rules
	•	C14 owns: Investigation creation, participants, lifecycle status, missing context, evidence bundles, active theories, investigation-level outputs, and investigation safety flags.
	•	C7 owns: Health Thread lifecycle, closure criteria, thread escalation state, thread unresolved/resolved semantics, and thread summaries.
	•	Shared policy owns cross-aggregate invariants: A shared policy module, for example InvestigationThreadCouplingPolicy, determines whether C14 may transition an investigation based on C7’s closure and safety snapshot. The policy is shared code, but C7 remains the source of truth for thread closure facts.
3.3.2	How this satisfies the hard constraints
	•	G1: Investigation statuses describe workflow state, not diagnoses. No investigation status may be named diagnosed, ruled_out, confirmed, or similar.
	•	G2: Investigation may reference external context only through C16 relevance links and C15 theory context; it cannot import external claims into thread facts.
	•	G3: Any derived personal fact surfaced in an investigation output still points to C5 provenance.
	•	G4: C14 cannot close an investigation unless C7 closure criteria are satisfied for linked threads. If the work is done but the thread is unresolved, C14 uses handed_off, monitoring, or waiting_for_data, not closed.
	•	G5: Existing C6 tables remain intact; new tables and node/edge types are additive.
	•	G6: Investigation rows and graph projection nodes carry patient_id and are RLS-scoped like other personal data.
	•	G7: Participants exist only under C1/C17 grants. FHIR Consent’s computable-rule model is a precedent for enforcing consent/grant rules at runtime [S3].
3.4	Trade-offs accepted
	•	Eventual consistency between C14 and C7. Safety events and state changes propagate by events/commands rather than a single giant transaction.
	•	More policy code. A shared policy module is required to prevent C14 and C7 from duplicating or diverging on closure logic.
	•	Graph is a projection, not source of truth. Some graph queries will need to join C14 tables for authoritative status.
	•	Thread-as-node deferred. The current C6 schema has thread_ids arrays, not first-class HealthThread nodes. Do not invent fake thread nodes in WEL-135.
3.5	Implementation notes
3.5.1	1. Tables
CREATE SCHEMA IF NOT EXISTS c14;  CREATE TABLE c14.investigations (   id uuid PRIMARY KEY,   patient_id uuid NOT NULL,   owner_type text NOT NULL CHECK (owner_type IN (     'individual','clinician','shared','institution','research'   )),   owner_grant_id uuid,   primary_question text NOT NULL,   status text NOT NULL CHECK (status IN (     'open','monitoring','waiting_for_data','ready_for_visit',     'handed_off','closed'   )),   scope jsonb NOT NULL DEFAULT '{}'::jsonb,   evidence_bundle_ids uuid[] NOT NULL DEFAULT '{}',   active_theory_ids uuid[] NOT NULL DEFAULT '{}',   missing_context_items jsonb NOT NULL DEFAULT '[]'::jsonb,   pending_item_ids uuid[] NOT NULL DEFAULT '{}',   safety_flags jsonb NOT NULL DEFAULT '[]'::jsonb,   last_reviewed_at timestamptz,   next_review_due_at timestamptz,   outputs jsonb NOT NULL DEFAULT '[]'::jsonb,   status_reason text,   created_by_actor_id uuid NOT NULL,   created_under_grant_id uuid,   created_at timestamptz NOT NULL DEFAULT now(),   updated_at timestamptz NOT NULL DEFAULT now() );  CREATE TABLE c14.investigation_threads (   investigation_id uuid NOT NULL REFERENCES c14.investigations(id),   patient_id uuid NOT NULL,   thread_id uuid NOT NULL,   relationship text NOT NULL DEFAULT 'primary'     CHECK (relationship IN ('primary','secondary','related')),   link_reason text,   created_at timestamptz NOT NULL DEFAULT now(),   PRIMARY KEY (investigation_id, thread_id) );  CREATE TABLE c14.investigation_participants (   id uuid PRIMARY KEY,   investigation_id uuid NOT NULL REFERENCES c14.investigations(id),   patient_id uuid NOT NULL,   actor_id uuid NOT NULL,   role text NOT NULL,   grant_id uuid NOT NULL,   status text NOT NULL DEFAULT 'active'     CHECK (status IN ('active','revoked','expired')),   created_at timestamptz NOT NULL DEFAULT now() );
Enable RLS on all C14 patient-scoped tables using the same current_setting('app.patient_id') pattern as C6.
3.5.2	2. C6 projection
When an investigation is created, C14 emits a projection command to C6:
	•	Create graph.kg_nodes row:
	•	node_type = 'Investigation'
	•	normalized_key = 'investigation:' || id
	•	display_label = primary_question or a safe redacted label
	•	status = 'active' for all non-closed states; resolved for closed; superseded only if explicitly replaced
	•	thread_ids = linked thread IDs
	•	metadata includes investigation_status, owner_type, safety_flag_count, and last_reviewed_at, but not participant secrets or external claim text.
	•	Add graph.kg_edges rows with edge_type = 'investigates' from the Investigation node to personal entity nodes under investigation. Do not use graph edges to represent thread coupling until/unless C7 introduces a first-class HealthThread node type.
3.5.3	3. Closure rule ownership
Use a shared policy with C7 as the data authority:
CloseInvestigationCommand(id, actor, reason)   -> C14 loads investigation + linked thread IDs   -> C14 asks C7 for ThreadClosureSnapshot[]   -> InvestigationThreadCouplingPolicy.evaluate_close(        investigation_status,        pending_items,        safety_flags,        thread_closure_snapshots      )   -> if denied: return policy_denial with unmet criteria   -> if allowed: C14 status = closed; emit investigation.closed.v1
C14 does not directly compute whether a symptom is resolved or whether a single normal test is sufficient. C7 owns that closure safety logic.
3.5.4	4. Status transitions
Recommended permitted transitions:
From
To
Notes
open
waiting_for_data, monitoring, ready_for_visit, handed_off, closed
closed only if policy allows.
waiting_for_data
open, monitoring, ready_for_visit, handed_off, closed
Data arrival can reopen analysis.
monitoring
open, waiting_for_data, ready_for_visit, handed_off, closed
Monitoring does not mean resolved.
ready_for_visit
open, waiting_for_data, handed_off, closed
Often closes only after visit outcome is captured and thread policy permits.
handed_off
monitoring, closed
Closure only when handoff and thread closure criteria are satisfied.
closed
open
Only by explicit reopen command with additive event; never destructive mutation.
3.5.5	5. Safety flag propagation
Investigation-level safety flags should be structured, not just strings:
{   "flag_type": "urgent_symptom_present",   "severity": "urgent",   "source": "c15_theory_gate",   "source_id": "...",   "created_at": "...",   "requires_thread_state": "escalated",   "message_key": "urgent_symptom_general" }
Propagation rule:
	•	C14 emits investigation.safety_flag_raised.v1.
	•	C7 consumes it and decides whether to transition the linked thread to escalated, needs_attention, or another C7-defined safe state.
	•	C14 may request escalation but does not mutate thread state directly.
	•	C7 emits thread.state_changed.v1 after applying its own state machine.
FHIR DetectedIssue is a useful precedent because it represents a patient-specific potential issue and is not used for general patient-independent knowledge [S15].
3.5.6	6. Event contract between C14 and C7
Use both directions.
C14 emits:
	•	investigation.created.v1
	•	investigation.linked_to_thread.v1
	•	investigation.unlinked_from_thread.v1
	•	investigation.state_changed.v1
	•	investigation.safety_flag_raised.v1
	•	investigation.safety_flag_cleared.v1
	•	investigation.pending_item_added.v1
	•	investigation.pending_item_resolved.v1
	•	investigation.ready_for_visit.v1
	•	investigation.handed_off.v1
	•	investigation.closed.v1
	•	investigation.reopened.v1
C14 consumes:
	•	thread.state_changed.v1
	•	thread.closure_criteria_changed.v1
	•	thread.pending_item_changed.v1
	•	thread.corrected.v1
	•	consent.grant_revoked.v1
	•	theory.safety_level_changed.v1
C7 consumes:
	•	investigation.safety_flag_raised.v1
	•	investigation.state_changed.v1
	•	investigation.closed.v1
	•	investigation.handed_off.v1
Use a transactional outbox for C14 and C7 state changes. Domain-event patterns are specifically intended to propagate state-change side effects across aggregates while maintaining decoupling [S16, S17].
3.6	Open risks / what could go wrong
	•	C14 and C7 closure logic diverge. Mitigation: C7 owns thread closure snapshots; C14 calls a shared policy and cannot close on local heuristics.
	•	Event lag leaves stale UI state. Mitigation: UI reads authoritative C14/C7 state for critical actions and treats graph projection as non-authoritative.
	•	Grant revocation not propagated. Mitigation: C14 consumes consent.grant_revoked.v1 and immediately marks affected participants revoked/expired.
	•	Safety flag loops. A C14 safety event could trigger C7 escalation, which triggers C14 updates, causing loops. Mitigation: idempotency keys and event causal-chain IDs.
	•	Thread hidden by closed investigation. Mitigation: C7 thread visibility is independent of C14 investigation closure. Closing an investigation never hides an unresolved thread.

4	WEL-129 - Theory evaluation model and non-diagnostic safety routing
4.1	Question
How should the Theory object (C15) be evaluated against personal data and external evidence to produce evidence-for / evidence-against / missing-data and a status - without ever crossing into diagnosis - and how does that output route through the Safety & Governance Gate (C10)?
4.2	Approaches considered
4.2.1	Option 1 - Reuse ConditionHypothesis node as Theory
How it works. Store theory text as a ConditionHypothesis node or extend that node type with theory metadata. Use existing may_explain and associated_with edges to personal nodes.
Pros. Minimal migration. Reuses existing graph semantics and potential_score.
Cons. Too risky. The name ConditionHypothesis plus clinical terminology can be read as diagnostic. It also conflates a structured investigation hypothesis with a clinical condition concept. SNOMED CT context guidance shows the same disease concept can mean current diagnosis, possible diagnosis, family history, or excluded diagnosis depending on the EHR context [S23]. WellBe should reduce, not increase, this ambiguity.
Evidence / precedent. SNOMED CT distinguishes top-level concept branches and notes that clinical finding concepts include concepts used to represent diagnoses [S24]. A non-diagnostic Theory object should therefore be distinct from diagnosis-like condition concepts.
4.2.2	Option 2 - First-class Theory aggregate with C6 projection and optional C8 derivative (recommended)
How it works. C15 owns theories, theory_evaluations, evidence references, status, safety level, and transition rules. C6 stores a Theory node and personal evidence edges. C8 may store a derived Pattern Memory entry after C10 passes the output.
Pros. Strong lifecycle and safety boundary. Clear separation between personal evidence, external context, and user-facing narrative. Supports immutable evaluation versions and additive correction.
Cons. More schema and service logic. Requires careful projection and consistency tests.
Evidence / precedent. FHIR Provenance and W3C PROV both support traceable generated resources and the activities/entities that produced them [S1, S2]. FDA CDS guidance clarifies that decision-support functions require careful consideration of whether users can independently review the basis of recommendations [S19]. ONC DSI criteria require source attributes and risk management for decision-support interventions [S20].
4.2.3	Option 3 - Store Theory only in Six Memories / Pattern Memory
How it works. Treat a theory as a Pattern Memory entry. The memory record stores theory text, supporting/contradicting observations, and status.
Pros. Fits the memory-centric product vision. Simplifies C15 persistence.
Cons. Pattern Memory is not a safe lifecycle authority for an object that can be unreviewed, blocked, clinician-reviewed, or urgent-routed. Memories are summaries; theories need commands, transitions, C10 gate results, external context, and audit.
Evidence / precedent. FHIR Provenance emphasizes that resources can have multiple provenance records and version-specific references [S1]. Theory evaluations should be versioned and traceable rather than overwritten as memory summaries.
4.2.4	Option 4 - External-evidence-first model using source quality to evaluate theories
How it works. Use external evidence quality tiers and source content to decide whether a theory is supported, partially supported, or contradicted. Personal data is used mainly for matching.
Pros. Good for evidence-based research. Can leverage GRADE/OCEBM-style source quality [S11, S12].
Cons. Violates WellBe’s separation rule unless very constrained. External evidence can support general plausibility but cannot assert that the theory is true for the user. It should never upgrade personal support status by itself.
Evidence / precedent. FHIR Evidence can express statistics and certainty for studies [S10], but this is not the same as a personal fact. FHIR DetectedIssue draws a useful boundary between patient-specific concerns and general patient-independent knowledge [S15].
4.3	Recommended approach
Choose Option 2: first-class C15 Theory aggregate, projected into C6, optionally summarized into C8 after C10 approval.
4.3.1	Authoritative taxonomy
Keep status and safety_level separate.
Theory status:
	•	unreviewed
	•	needs_more_data
	•	partially_supported
	•	not_supported_by_current_data
	•	contradicted_by_current_data
	•	discuss_with_clinician
	•	clinician_reviewed
Theory safety level:
	•	low
	•	needs_clinician_context
	•	urgent_symptom_present
	•	blocked_due_to_diagnostic_claim
A status says what the current personal-data review found. A safety level says what C10 must do with any output. This separation prevents a dangerous shortcut where partially_supported is interpreted as safe to show or clinically true.
4.3.2	Permitted transitions
Recommended status transitions should be encoded as service policy rather than inferred from free text:
	•	From unreviewed to needs_more_data when personal evidence is insufficient or required source context is missing.
	•	From unreviewed to partially_supported when personal evidence-for exists, C5 provenance is present, no strong contradiction is present, and C10 language checks pass.
	•	From unreviewed to not_supported_by_current_data when relevant personal data exists but does not support the theory.
	•	From unreviewed to contradicted_by_current_data when personal evidence-against directly conflicts.
	•	From unreviewed to discuss_with_clinician when medication, medical-action, abnormal-lab, care-gap, or other safety context requires human clinical review.
	•	From any non-final state to a display-blocked state when safety_level = blocked_due_to_diagnostic_claim; the theory may remain stored, but user-facing output is withheld until rewritten.
	•	From needs_more_data, partially_supported, not_supported_by_current_data, or contradicted_by_current_data to another non-final review status only after new personal data, a new source link, or an explicit review result.
	•	From discuss_with_clinician to clinician_reviewed only under a valid clinician grant, or back to a data-review status when new data arrives.
	•	From clinician_reviewed back to needs_more_data or discuss_with_clinician only through an explicit new-data or reopen event.
Do not add confirmed, ruled_out, diagnosed, likely, or ranked differential statuses.
4.3.3	How evaluation works
	•	Normalize theory text into a safe question. A user or model may write “I have X”. C15 must normalize or reject it as “Could X be relevant to the thread?” or “Could Y may_explain Z?” before persistence. If the text cannot be made non-diagnostic, store it with safety_level = blocked_due_to_diagnostic_claim and do not show it as a theory output.
	•	Collect personal facts through C6 and C5. Candidate facts must trace to raw C2 events through C5. No C5 provenance means no evidence edge.
	•	Create personal evidence edges only. evidence_for and evidence_against graph edges connect personal fact nodes to a Theory node. External sources do not become endpoints in kg_edges.
	•	Identify missing data. Missing data is represented as a list of needed observations, documents, dates, medication timing, symptom details, follow-up results, or clinician questions. Missing data should not imply diagnosis.
	•	Attach external context separately. C16 sources attach through c15.theory_external_context and external_bridge.relevance_links. They can explain general plausibility or why a clinician discussion may be useful, but they cannot change personal evidence into diagnosis.
	•	Assign status from personal data. External source quality may influence whether the UI surfaces context and how it labels it, but personal support status is determined by personal facts and their C5 provenance.
	•	Pass through C10. Any user-facing text must pass the do-not-diagnose, provenance, panic-language, bias/equity, external-context-labeling, and urgent-symptom rules.
4.3.4	How this satisfies the hard constraints
	•	G1: Theory status is not diagnosis. The strongest causal graph verb remains may_explain. C10 blocks diagnostic assertions, disease claims, ranked differentials, and prohibited verbs.
	•	G2: External sources are attached only as context. They never create evidence_for or evidence_against personal graph edges unless represented only by a separate external-context table, not kg_edges.
	•	G3: Every personal evidence edge requires C5 provenance to raw source events.
	•	G4: A theory cannot close a thread or investigation. Closure remains C7/C14 policy.
	•	G5: Existing C6 data is untouched; Theory is additive.
	•	G6: Theory rows and graph nodes are patient-scoped and RLS-protected.
	•	G7: Clinician review requires a valid grant; clinician_reviewed cannot be set by an actor whose grant is revoked, expired, or out of scope.
4.4	Trade-offs accepted
	•	External evidence does not directly increase personal support status. This is intentionally conservative and may feel less powerful than a diagnosis-support system.
	•	Two-layer storage. C15 is authoritative; C6 is a graph projection; C8 is a derived memory. This is more complex but safer.
	•	More blocked outputs. Some user-friendly phrasing will be blocked or rewritten if it sounds diagnostic.
	•	Theory text normalization may frustrate users. The system may reframe user assertions as questions. This is necessary for WellBe’s identity and safety posture.
4.5	Implementation notes
4.5.1	1. Theory tables
CREATE SCHEMA IF NOT EXISTS c15;  CREATE TABLE c15.theories (   id uuid PRIMARY KEY,   patient_id uuid NOT NULL,   created_by text NOT NULL CHECK (created_by IN (     'individual','clinician','system_suggested_question'   )),   created_by_actor_id uuid,   created_under_grant_id uuid,   linked_investigation_id uuid NOT NULL REFERENCES c14.investigations(id),   theory_text text NOT NULL,   normalized_question text NOT NULL,   theory_type text NOT NULL CHECK (theory_type IN (     'symptom_trigger','medication_effect','lifestyle_factor',     'environmental_factor','clinical_condition_question',     'care_process_gap'   )),   status text NOT NULL CHECK (status IN (     'unreviewed','needs_more_data','partially_supported',     'not_supported_by_current_data','contradicted_by_current_data',     'discuss_with_clinician','clinician_reviewed'   )),   safety_level text NOT NULL CHECK (safety_level IN (     'low','needs_clinician_context','urgent_symptom_present',     'blocked_due_to_diagnostic_claim'   )),   status_reason text,   latest_evaluation_id uuid,   supersedes_theory_id uuid,   created_at timestamptz NOT NULL DEFAULT now(),   updated_at timestamptz NOT NULL DEFAULT now() );  CREATE TABLE c15.theory_evaluations (   id uuid PRIMARY KEY,   theory_id uuid NOT NULL REFERENCES c15.theories(id),   patient_id uuid NOT NULL,   evaluation_version text NOT NULL,   evidence_for_node_ids uuid[] NOT NULL DEFAULT '{}',   evidence_against_node_ids uuid[] NOT NULL DEFAULT '{}',   missing_data jsonb NOT NULL DEFAULT '[]'::jsonb,   external_context_link_ids uuid[] NOT NULL DEFAULT '{}',   proposed_status text NOT NULL,   proposed_safety_level text NOT NULL,   c10_gate_result jsonb NOT NULL DEFAULT '{}'::jsonb,   evaluator_actor text NOT NULL,   evaluated_at timestamptz NOT NULL DEFAULT now() );  CREATE TABLE c15.theory_external_context (   id uuid PRIMARY KEY,   theory_id uuid NOT NULL REFERENCES c15.theories(id),   patient_id uuid NOT NULL,   external_source_id uuid NOT NULL REFERENCES external_kg.external_evidence_sources(id),   external_claim_id uuid REFERENCES external_kg.external_claims(id),   relevance_link_id uuid REFERENCES external_bridge.relevance_links(id),   context_direction text NOT NULL CHECK (context_direction IN (     'generally_supports_plausibility','generally_weakens_plausibility',     'background','safety_context','educational_only'   )),   context_only boolean NOT NULL DEFAULT true CHECK (context_only IS TRUE),   created_at timestamptz NOT NULL DEFAULT now() );
Enable RLS on C15 patient-scoped tables.
4.5.2	2. C6 projection and evidence edges
Create a Theory node when a theory is persisted:
	•	node_type = 'Theory'
	•	normalized_key = 'theory:' || id
	•	display_label = safe short form of normalized_question
	•	status = 'active' unless superseded or merged
	•	thread_ids inherited from the linked investigation
	•	metadata includes theory_type, theory_status, safety_level, linked_investigation_id, and latest_evaluation_id
Evidence edge rules:
	•	evidence_for: from personal fact node to Theory node.
	•	evidence_against: from personal fact node to Theory node.
	•	Both endpoints must have the same patient_id.
	•	Source personal fact must have C5 provenance.
	•	potential_score on these edges is still an internal provenance/completeness score, not theory probability. Consider adding score_semantics = 'personal_evidence_quality' in score_inputs.
4.5.3	3. C10 Safety & Governance Gate rules for theory output
C10 must block or rewrite any output that violates these rules:
	•	Diagnostic assertion block. Reject text that asserts the user has, likely has, does not have, or has ruled out a condition. Block phrases such as “you have”, “diagnosis is”, “most likely”, “rules out”, “confirms”, “proves”, “caused by”, or ranked-differential phrasing.
	•	Causal ceiling. The strongest permitted causal language is may_explain. Use “may be relevant”, “could be worth discussing”, or “is a question to investigate”.
	•	No ranked differential. Do not output ranked lists of diseases or conditions. A list of open questions is allowed only if not ranked and not framed as diagnoses.
	•	Provenance required. Any statement about the user’s data must cite the personal source category and C5 provenance. If provenance is absent, the output must say the data is missing or unverified.
	•	External context label required. Every external source displayed must include source type, tier, and “context only - not evidence about you” or equivalent.
	•	Urgent route override. If safety_level = urgent_symptom_present, suppress theory explanation and show the approved urgent-symptom routing message. The theory may remain stored for clinician follow-up but should not be used to reason with the user in real time.
	•	Bias/equity check. C10 should flag unsupported assumptions based on age, sex, race, disability, weight, socioeconomic status, or other protected or equity-relevant attributes. ONC DSI criteria explicitly call out risk analysis across fairness, safety, privacy, and related characteristics for predictive DSIs [S20].
FDA CDS guidance is relevant because it clarifies regulatory thinking on CDS functions and differentiates software functions based partly on intended users and reviewability [S19]. ONC DSI criteria require source-attribute access/modification and risk management for predictive decision-support interventions in certified health IT [S20]. Even if WellBe is not implementing a certified EHR module in this story, the transparency and risk-control pattern is directly useful.
4.5.4	4. Discuss-with-clinician and urgent triggers
Set status = discuss_with_clinician or safety_level = needs_clinician_context when any of the following are true:
	•	Theory concerns medication effect, adverse effect, contraindication, allergy, abnormal lab, vital-sign concern, or care-process gap.
	•	Personal evidence is contradictory or incomplete in a way that could change care decisions.
	•	External context is Tier 3-5 only and the user-facing explanation would otherwise overstate weak evidence.
	•	A clinician-authored grant/workspace is active and the theory has been prepared for visit discussion.
	•	C10 detects that safe language is possible but clinical interpretation is required.
Set safety_level = urgent_symptom_present when validated red-flag symptom rules trigger. The theory output must then be replaced by urgent routing language. Do not present a causal or diagnostic theory in that path.
4.5.5	5. Storage relative to Six Memories
	•	C15 Theory is authoritative. It owns lifecycle, status, safety level, and evaluation versions.
	•	C6 is the graph projection. It supports traversals and evidence relationships.
	•	C8 Pattern Memory is derived. It may store a safe, user-facing summary such as “Question under investigation: whether medication timing may be relevant to dizziness episodes” only after C10 passes it. Store source_theory_id, source_evaluation_id, and c10_gate_id in the memory entry.
This mirrors the broader FHIR Provenance principle that generated resources should remain traceable to activities and source entities [S1].
4.5.6	6. External sources attached without importing claims
External context should be attached by ID and displayed through C16:
Theory -> theory_external_context -> external_source / external_claim Theory -> external_bridge.relevance_links -> personal node + external source
Do not create:
external_claim -> evidence_for -> Theory external_claim -> may_explain -> Symptom external_source -> corroborating evidence_link -> personal fact
The first path is contextual. The second and third paths would make external knowledge behave like personal evidence and should be prohibited by tests.
4.6	Open risks / what could go wrong
	•	Users read partially_supported as a diagnosis. Mitigation: display label should be “some of your data is consistent with this question” or similar, not “supported diagnosis”.
	•	External evidence leaks into personal support. Mitigation: status assignment uses personal evidence only; external context has separate tables and display labels.
	•	C10 becomes the only guardrail. Mitigation: prohibited edge types, schema constraints, service validators, and tests must block unsafe states before output generation.
	•	Theory text contains hidden diagnostic claim. Mitigation: normalize theory into question form and store blocked_due_to_diagnostic_claim when unsafe.
	•	Clinician-reviewed status implies endorsement. Mitigation: clinician_reviewed means “reviewed under grant,” not “confirmed.” Require review_note_type such as reviewed_for_discussion, needs_follow_up, or not_a_diagnosis.
	•	Memory summary diverges from authoritative theory. Mitigation: C8 entries are derived and carry source_theory_id; updates are additive and supersede prior summaries rather than overwriting them.

5	Cross-cutting migration checklist for WEL-135
	•	Expand graph.kg_nodes.ck_node_type to include Investigation and Theory.
	•	Add graph.node_type_aliases or graph.node_types as a compatibility/metadata table, but keep existing PascalCase values.
	•	Expand graph.edge_types.category to include evidential, process, and external_context.
	•	Insert evidence_for, evidence_against, investigates, and relevance_link into graph.edge_types.
	•	Add a guard that prevents relevance_link rows in graph.kg_edges.
	•	Create external_kg schema for C16 external sources and claims.
	•	Create external_bridge.relevance_links with patient RLS.
	•	Ensure external source quality tier is auditable and never upgraded by usage.
	•	Add C14 tables, RLS, status transition policy, and C6 projection writer.
	•	Add C15 tables, RLS, theory status transition policy, C6 projection writer, and C10 integration.
	•	Add C5 enforcement that evidence.evidence_links remains personal-source-only.
	•	Add tests for prohibited verbs and edge codes: causes, diagnoses, confirms_diagnosis, rules_out, proves.
	•	Add tests proving external sources cannot change kg_edges.potential_score or satisfy personal provenance.
	•	Add tests proving grant revocation removes participant access.
	•	Add event-contract tests for C14/C7 coupling and C15/C10 routing.
6	Suggested decision-record wording
6.1	WEL-130 proposed decision
Adopt a separate C16 external evidence graph in an external_kg schema with separate ownership and grants. Store personal-to-external relationships only in external_bridge.relevance_links, which is patient-scoped and RLS-protected. Do not store external evidence nodes in graph.kg_nodes; do not store relevance_link rows in graph.kg_edges; do not allow C5 personal evidence scoring to consume external context references. Source-quality tier is an editorial/source-classification attribute, not usage-derived, and usage can never upgrade it.
6.2	WEL-128 proposed decision
Model Investigation as a first-class C14 aggregate with its own lifecycle, many-to-many thread links, participant grants, safety flags, and C6 graph projection. C14 owns investigation status. C7 owns Health Thread closure criteria and thread state. A shared policy module and event contract enforce that C14 cannot close an investigation unless linked threads meet C7 closure criteria, and that safety flags propagate to C7 escalation through events.
6.3	WEL-129 proposed decision
Model Theory as a first-class C15 aggregate with status, safety level, immutable evaluation versions, personal evidence references, missing-data items, and external-context references. Project Theory into C6 as a Theory node and create evidence_for / evidence_against edges only from personal, provenance-backed facts. C8 may store a derived Pattern Memory summary only after C10 passes the output. C10 blocks diagnostic assertions, ranked differentials, disease claims, unsupported personal statements, and external-context contamination.
7	Appendix - sources
[S1] HL7 FHIR R5, “Provenance”. https://fhir.hl7.org/fhir/provenance.html
[S2] W3C, “PROV-Overview: An Overview of the PROV Family of Documents”. https://www.w3.org/TR/prov-overview/
[S3] HL7 FHIR R5, “Consent”. https://fhir.hl7.org/fhir/consent.html
[S4] PostgreSQL Documentation, “Row Security Policies”. https://www.postgresql.org/docs/current/ddl-rowsecurity.html
[S5] PostgreSQL Documentation, “Schemas”. https://www.postgresql.org/docs/current/ddl-schemas.html
[S6] Apache AGE Documentation, “Graphs”. https://age.apache.org/age-manual/master/intro/graphs.html
[S7] W3C, “SPARQL Query Language for RDF,” section on RDF Dataset and named graphs. https://www.w3.org/TR/rdf-sparql-query/
[S8] HL7 FHIR R5, “ArtifactAssessment”. https://fhir.hl7.org/fhir/artifactassessment.html
[S9] HL7 FHIR R5, “Citation”. https://fhir.hl7.org/fhir/citation.html
[S10] HL7 FHIR R5, “Evidence”. https://fhir.hl7.org/fhir/evidence.html
[S11] Cochrane / GRADE Working Group, “GRADE Handbook”. https://www.cochrane.org/learn/courses-and-resources/cochrane-methodology/grade-approach/grade-handbook
[S12] Oxford Centre for Evidence-Based Medicine, “OCEBM Levels of Evidence”. https://www.cebm.ox.ac.uk/resources/levels-of-evidence/ocebm-levels-of-evidence
[S13] HL7 FHIR R5, “Task”. https://fhir.hl7.org/fhir/task.html
[S14] HL7 FHIR R5, “CarePlan”. https://fhir.hl7.org/fhir/careplan.html
[S15] HL7 FHIR R5, “DetectedIssue”. https://fhir.hl7.org/fhir/detectedissue.html
[S16] Microsoft Learn, “.NET Microservices: Domain events - design and implementation”. https://learn.microsoft.com/en-us/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/domain-events-design-implementation
[S17] Microservices.io, “Pattern: Domain event”. https://microservices.io/patterns/data/domain-event.html
[S18] Martin Fowler, “Domain Event”. https://martinfowler.com/eaaDev/DomainEvent.html
[S19] U.S. Food and Drug Administration, “Clinical Decision Support Software Guidance for Industry and Food and Drug Administration Staff”. https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software
[S20] eCFR, 45 CFR 170.315, ONC Certification Criteria for Health IT, Decision Support Intervention provisions. https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-D/part-170/subpart-C/section-170.315
[S21] National Academies of Sciences, Engineering, and Medicine, “Improving Diagnosis in Health Care”. https://www.nationalacademies.org/projects/IOM-HCS-13-03/publication/21794
[S22] AHRQ, “Diagnostic Safety and Quality”. https://www.ahrq.gov/diagnostic-safety/index.html
[S23] SNOMED International, “Situation with Explicit Context Modeling”. https://docs.snomed.org/snomed-ct-specifications/snomed-ct-editorial-guide/readme/authoring/domain-specific-modeling/situation-with-explicit-context/situation-with-explicit-context-modeling
[S24] SNOMED International, “SNOMED CT Concept Model”. https://docs.snomed.org/snomed-ct-practical-guides/snomed-ct-starter-guide/6-snomed-ct-concept-model
[S25] openEHR Foundation, “openEHR Specifications”. https://specifications.openehr.org/
